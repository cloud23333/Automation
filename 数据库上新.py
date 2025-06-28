# -*- coding: utf-8 -*-
"""
db_autofill.py —— 数据库驱动 Mercado 上新 (含UPC调试模式开关)
"""
import os, time, pymysql, pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pywinauto

# ---------- 配置区 -----------------------------------------------------------
DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

ROOT_SCAN = r"D:\图片录入测试"
ACCOUNT = "Cloud23333"
PASSWORD = "Dzj9876543"
SHOP_NAME = "子杰"

DEBUG_MODE = True  # True: 跳过填写UPC（调试模式）, False: 正式填写UPC
# -----------------------------------------------------------------------------


def db():
    return pymysql.connect(**DB_CONF)


def abs_path(rel):
    return os.path.join(ROOT_SCAN, rel)


# ---------- 数据库读取函数 -----------------------------------------------------


def fetch_next_task(cur):
    cur.execute(
        """SELECT * FROM listing_queue
                   WHERE is_pushed = 0 ORDER BY id LIMIT 1"""
    )
    return cur.fetchone()


def fetch_variants(cur, queue_id):
    cur.execute(
        """SELECT * FROM listing_queue_variant
                   WHERE queue_id=%s ORDER BY id""",
        (queue_id,),
    )
    return pd.DataFrame(cur.fetchall())


def fetch_main_detail_imgs(cur, folder_id):
    cur.execute(
        """SELECT img_role, file_path FROM image_asset
                   WHERE folder_id=%s AND img_role IN ('main','detail')""",
        (folder_id,),
    )
    main, detail = [], []
    for r in cur.fetchall():
        p = abs_path(r["file_path"])
        (main if r["img_role"] == "main" else detail).append(p)
    return main[:10], detail[:10]


# ---------- UI函数（原脚本完全复用） --------------------------------------------


def js_set(driver, elem, value: str):
    """双保险：Ctrl+A 清空，再用 JS 直接赋值"""
    elem.send_keys(Keys.CONTROL, "a")
    elem.send_keys(Keys.DELETE)
    driver.execute_script("arguments[0].value = arguments[1];", elem, value)


def set_package_size(driver, wait, length="15", width="12", height="1"):
    # 1) 点击“包裹”批量按钮，弹窗出现
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a'
    ).click()

    # 2) 等弹窗文本框出现并可交互
    len_input = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="skuPackageLength"]'))
    )
    wid_input = driver.find_element(By.XPATH, '//*[@id="skuPackageWidth"]')
    hei_input = driver.find_element(By.XPATH, '//*[@id="skuPackageHeight"]')

    # --- 双保险：先 Ctrl+A 清空，再 JS 赋值 -----------------
    for elem, val in [(len_input, length), (wid_input, width), (hei_input, height)]:
        elem.send_keys(Keys.CONTROL, "a")
        elem.send_keys(Keys.DELETE)
        driver.execute_script("arguments[0].value = arguments[1];", elem, val)

    # 3) 点击确定按钮
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()

    time.sleep(0.4)  # 给页面一次渲染机会


def close_all_close_buttons(driver, try_times=2):
    for _ in range(try_times):
        close_buttons = driver.find_elements(
            By.XPATH, '//button[contains(text(), "关闭")]'
        )
        if not close_buttons:
            break
        for btn in close_buttons:
            try:
                btn.click()
                time.sleep(0.3)
            except Exception:
                pass
        time.sleep(0.5)


def fill_basic_info(driver, wait, info):
    # 点击分类按钮，弹出分类选择框
    driver.find_element(
        By.XPATH, "/html/body/form/div/div[3]/div[2]/table/tbody/tr[3]/td[2]/button"
    ).click()
    time.sleep(1)

    # 输入搜索关键词并搜索
    search_input = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="searchCategory"]'))
    )
    search_input.clear()
    search_input.send_keys(info["category"])
    time.sleep(0.5)

    # 点击搜索按钮
    driver.find_element(
        By.XPATH, '//*[@id="categoryIdAndName"]/div[1]/div/button'
    ).click()
    time.sleep(2)

    # 点击搜索结果中的第一个匹配项（可根据实际修改XPath）
    try:
        first_result = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '//li[contains(@node-id, "CBT95407")]')
            )
        )
        first_result.click()
        print(f"✅ 已选中分类: {first_result.text}")
    except Exception as e:
        print(f"⚠️ 未找到分类 '{info['category']}', 请手动确认！")
        input("⚠️ 请手动选择分类后，按回车继续...")

    # 1. 保险的属性输入
    attr_xpath = '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input'
    attr_val = info.get("attribute", "Generic")
    for _ in range(5):
        try:
            attr_input = wait.until(EC.element_to_be_clickable((By.XPATH, attr_xpath)))
            if attr_input.is_displayed() and attr_input.is_enabled():
                attr_input.clear()
                attr_input.send_keys(attr_val)
                break
        except Exception as e:
            print(f"attr_input not ready, retry... {e}")
            time.sleep(0.5)
    else:
        print("多次尝试失败，JS强制写入属性！")
        attr_input = driver.find_element(By.XPATH, attr_xpath)
        driver.execute_script("arguments[0].value=arguments[1];", attr_input, attr_val)

    # 2. 其他内容正常处理
    attr_select = Select(
        driver.find_element(
            By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select'
        )
    )
    attr_select.select_by_index(info.get("attr_index", 1))

    input_beads = driver.find_element(
        By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input'
    )
    input_beads.clear()
    input_beads.send_keys(info.get("attr_value", "beads"))

    title_input = driver.find_element(By.XPATH, '//*[@id="productTitle"]')
    title_input.clear()
    title_input.send_keys(info["title"])

    desc_input = driver.find_element(By.CLASS_NAME, "descriptionTextarea")
    desc_input.clear()
    desc_input.send_keys(info["description"])

    global_price_input = driver.find_element(By.XPATH, '//*[@id="globalPrice"]')
    global_price_input.clear()
    global_price_input.send_keys(str(info["global_price"]))
    time.sleep(0.2)


def fill_site_prices(driver, price):
    site_price_xpaths = [
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[1]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[2]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[3]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[4]/input',
    ]
    for xpath in site_price_xpaths:
        inp = driver.find_element(By.XPATH, xpath)
        inp.clear()
        inp.send_keys(str(price))


def fill_listing_type(driver):
    for i in range(1, 5):
        select_elem = driver.find_element(
            By.XPATH, f'//*[@id="siteProductTypeDiv"]/table/tbody/tr/td[{i}]/select'
        )
        select_obj = Select(select_elem)
        select_obj.select_by_index(1)
        time.sleep(0.1)


def fill_variants(driver, wait, variants):
    # 第1组：尺寸
    select_1 = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[1]/select'
    )
    Select(select_1).select_by_index(1)
    input_box_xpath = '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[3]/input'
    add_button_xpath = '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[3]/button'

    for value in variants["sizes"]:
        for _ in range(5):
            input_box = wait.until(
                EC.presence_of_element_located((By.XPATH, input_box_xpath))
            )
            if input_box.is_displayed() and input_box.is_enabled():
                try:
                    input_box.clear()
                    input_box.send_keys(str(value))
                    driver.find_element(By.XPATH, add_button_xpath).click()
                    time.sleep(0.2)
                    break
                except Exception as e:
                    print(f"input_box 交互失败（sizes），重试... {e}")
                    time.sleep(0.3)
            else:
                print("input_box 不可交互（sizes），等待重试...")
                time.sleep(0.3)
        else:
            print(f"多次尝试失败（sizes），用JS强制赋值: {value}")
            driver.execute_script(
                "arguments[0].value=arguments[1];", input_box, str(value)
            )
            driver.find_element(By.XPATH, add_button_xpath).click()
            time.sleep(0.2)

    # 第2组：pack
    select_2 = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[1]/select'
    )
    Select(select_2).select_by_index(1)
    input_box_2_xpath = '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[3]/input'
    add_button_2_xpath = '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[3]/button'

    for value in variants["pack"]:
        for _ in range(5):
            input_box_2 = wait.until(
                EC.presence_of_element_located((By.XPATH, input_box_2_xpath))
            )
            if input_box_2.is_displayed() and input_box_2.is_enabled():
                try:
                    input_box_2.clear()
                    input_box_2.send_keys(str(value))
                    driver.find_element(By.XPATH, add_button_2_xpath).click()
                    time.sleep(0.2)
                    break
                except Exception as e:
                    print(f"input_box_2 交互失败（pack），重试... {e}")
                    time.sleep(0.3)
            else:
                print("input_box_2 不可交互（pack），等待重试...")
                time.sleep(0.3)
        else:
            print(f"多次尝试失败（pack），用JS强制赋值: {value}")
            driver.execute_script(
                "arguments[0].value=arguments[1];", input_box_2, str(value)
            )
            driver.find_element(By.XPATH, add_button_2_xpath).click()
            time.sleep(0.2)

    # 第3组：color
    color_input_xpath = '//*[@id="skuParameterList"]/tbody/tr[3]/td[2]/div[3]/input'
    add_button_3_xpath = '//*[@id="skuParameterList"]/tbody/tr[3]/td[2]/div[3]/button'

    for value in variants["color"]:
        for _ in range(5):
            color_input = wait.until(
                EC.presence_of_element_located((By.XPATH, color_input_xpath))
            )
            if color_input.is_displayed() and color_input.is_enabled():
                try:
                    color_input.clear()
                    color_input.send_keys(str(value))
                    driver.find_element(By.XPATH, add_button_3_xpath).click()
                    time.sleep(0.2)
                    break
                except Exception as e:
                    print(f"color_input 交互失败（color），重试... {e}")
                    time.sleep(0.3)
            else:
                print("color_input 不可交互（color），等待重试...")
                time.sleep(0.3)
        else:
            print(f"多次尝试失败（color），用JS强制赋值: {value}")
            driver.execute_script(
                "arguments[0].value=arguments[1];", color_input, str(value)
            )
            driver.find_element(By.XPATH, add_button_3_xpath).click()
            time.sleep(0.2)


def fill_sku_details(driver, wait, sku_list, debug_mode=False):
    # 1) 顺序填写每行 SKU
    for i, sku in enumerate(sku_list, start=1):
        input_xpath = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
        wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
        inp = driver.find_element(By.XPATH, input_xpath)
        inp.clear()
        inp.send_keys(sku)

    # 2) 如果是 DEBUG 模式，直接返回（不填 UPC / 尺寸 / 重量 / 库存）
    if debug_mode:
        print("⚠️ DEBUG模式：跳过 UPC + 包裹尺寸/重量/库存")
        return

    # 3) =======  UPC 批量设置  =======
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[5]/span[2]/a'
    ).click()
    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="upcBatchEdit"]')))

    sel = Select(
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="upcSelect"]')))
    )
    if len(sel.options) > 1:
        sel.select_by_index(1)  # 选“美客多”

    wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="upcBatchEdit"]/div[2]/div/div[2]/table/tbody/tr[4]/td[2]/label[2]/input',
            )
        )
    ).click()

    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="upcBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.4)

    # 4) =======  包裹尺寸  =======
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a'
    ).click()
    wait.until(
        EC.visibility_of_element_located((By.XPATH, '//*[@id="skuPackageLength"]'))
    )
    js_set(driver, driver.find_element(By.XPATH, '//*[@id="skuPackageLength"]'), "15")
    js_set(driver, driver.find_element(By.XPATH, '//*[@id="skuPackageWidth"]'), "12")
    js_set(driver, driver.find_element(By.XPATH, '//*[@id="skuPackageHeight"]'), "1")
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.4)

    # 5) =======  重量  =======
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[7]/span[2]/a'
    ).click()
    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="skuWeight"]')))
    js_set(driver, driver.find_element(By.XPATH, '//*[@id="skuWeight"]'), "100")
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.4)

    # 6) =======  库存  =======
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[8]/span[2]/a'
    ).click()
    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="num2"]')))
    js_set(driver, driver.find_element(By.XPATH, '//*[@id="num2"]'), "50")
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.4)


def upload_img_in_one_slot(driver, button_xpath, menu_xpath, img_list):
    for img_path in img_list:
        if not os.path.exists(img_path):
            print(f"图片文件不存在，已跳过：{img_path}")
            continue  # 文件不存在就跳过
        upload_btn = driver.find_element(By.XPATH, button_xpath)
        upload_btn.click()
        time.sleep(0.3)
        local_img_menu = driver.find_element(By.XPATH, menu_xpath)
        local_img_menu.click()
        time.sleep(1)
        app = pywinauto.Application().connect(title_re="打开|Open")
        dlg = app.window(title_re="打开|Open")
        dlg["Edit"].set_edit_text(img_path)
        dlg["Button"].click()
        time.sleep(2)


def fill_additional_info(driver, wait):
    warranty_select = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="warrantyType"]'))
    )
    Select(warranty_select).select_by_index(3)
    time.sleep(0.2)
    button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "/html/body/form/div/div[13]/div[2]/button")
        )
    )
    button.click()
    time.sleep(0.2)
    menu_item = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "/html/body/form/div/div[13]/div[2]/ul/li[1]/a")
        )
    )
    menu_item.click()
    time.sleep(0.2)


def get_img_paths_from_row(row):
    img_paths = []
    for i in range(1, 21):  # 如果你最多img_path10就写range(1, 11)
        col = f"img_path{i}"
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            img_paths.append(str(row[col]).strip())
    return img_paths


# ---------- 修改后的fill_sku_details，支持调试模式 -----------------------------
def fill_sku_details(driver, wait, sku_list, debug_mode=False):
    for i, sku in enumerate(sku_list, start=1):
        input_xpath = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
            input_elem = driver.find_element(By.XPATH, input_xpath)
            input_elem.clear()
            input_elem.send_keys(sku)
        except Exception as e:
            print(f"⚠️【严重错误】找不到第{i}个SKU输入框，可能SKU数量与网页实际不一致！")
            print(f"👉 当前尝试的SKU: {sku}")
            print(f"❌ 异常详情: {e}")
            print(
                f"📌 请检查：网页实际生成的SKU数量 vs 数据库中提供的SKU数量 ({len(sku_list)}个)"
            )
            raise e

    if debug_mode:
        print("⚠️ DEBUG模式：跳过UPC填写")
        return

    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[5]/span[2]/a'
    ).click()
    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="upcBatchEdit"]')))

    upc_select_elem = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="upcSelect"]'))
    )
    select_obj = Select(upc_select_elem)

    for _ in range(10):
        if len(select_obj.options) > 1:
            break
        time.sleep(0.3)

    try:
        select_obj.select_by_index(1)  # “美客多”
    except Exception as e:
        print("选择UPC失败:", e)

    wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="upcBatchEdit"]/div[2]/div/div[2]/table/tbody/tr[4]/td[2]/label[2]/input',
            )
        )
    ).click()

    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="upcBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()

    time.sleep(0.5)

    # 批量设置包裹尺寸、重量、库存（以下部分未变）
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a'
    ).click()
    wait.until(
        EC.visibility_of_element_located((By.XPATH, '//*[@id="skuPackageLength"]'))
    )
    driver.find_element(By.XPATH, '//*[@id="skuPackageLength"]').send_keys("15")
    driver.find_element(By.XPATH, '//*[@id="skuPackageWidth"]').send_keys("12")
    driver.find_element(By.XPATH, '//*[@id="skuPackageHeight"]').send_keys("1")
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.5)
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[7]/span[2]/a'
    ).click()
    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="skuWeight"]')))
    driver.find_element(By.XPATH, '//*[@id="skuWeight"]').send_keys("100")
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.5)
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[8]/span[2]/a'
    ).click()
    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="num2"]')))
    driver.find_element(By.XPATH, '//*[@id="num2"]').send_keys("50")
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.5)


# ---------- 主程序 ------------------------------------------------------------
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)
driver.get("https://www.dianxiaomi.com/")
driver.find_element(By.ID, "exampleInputName").send_keys(ACCOUNT)
driver.find_element(By.ID, "exampleInputPassword").send_keys(PASSWORD)
input("手动完成登录后回车继续...")
print("✅ 开始自动上新\n")

conn = db()
cur = conn.cursor(pymysql.cursors.DictCursor)

try:
    while True:
        task = fetch_next_task(cur)
        if not task:
            print("✅ 所有任务完成")
            break

        qid, title = task["id"], task["title"]
        print(f"🔹 正在上新: {title}")

        variants = fetch_variants(cur, qid)
        if variants.empty:
            print("⚠️ 无变体数据,跳过")
            cur.execute("UPDATE listing_queue SET is_pushed=-1 WHERE id=%s", (qid,))
            conn.commit()
            continue

        print(f"数据库SKU数量: {len(variants)}")
        main_imgs, _ = fetch_main_detail_imgs(cur, task["folder_id"])

        main_imgs, _ = fetch_main_detail_imgs(cur, task["folder_id"])

        driver.get("https://www.dianxiaomi.com/mercadoGlobalProduct/add.htm")
        close_all_close_buttons(driver)

        Select(driver.find_element(By.ID, "mercadoShopId")).select_by_visible_text(
            SHOP_NAME
        )
        wait.until(
            EC.element_to_be_clickable((By.XPATH, '//label[contains(., "全选")]'))
        ).click()

        fill_basic_info(driver, wait, task)
        fill_site_prices(driver, task["global_price"])
        fill_listing_type(driver)

        variant_dict = {
            "sizes": variants["sku_code"]
            .str.extract(r"(\d+\.?\d*)mm")[0]
            .dropna()
            .unique()
            .tolist(),
            "pack": variants["sku_code"]
            .str.extract(r"-(\d+)PCS")[0]
            .dropna()
            .unique()
            .tolist(),
            "color": variants["sku_code"]
            .str.extract(r"([A-Z]+)$")[0]
            .dropna()
            .unique()
            .tolist(),
        }
        fill_variants(driver, wait, variant_dict)
        fill_sku_details(
            driver, wait, variants["sku_code"].tolist(), debug_mode=DEBUG_MODE
        )

        upload_img_in_one_slot(
            driver,
            '//*[@id="productMainPic"]/div/button',
            '//*[@id="productMainPic"]/div/ul/li[1]/a',
            main_imgs,
        )

        for idx, row in variants.iterrows():
            if pd.notna(row["option_img"]):
                upload_img_in_one_slot(
                    driver,
                    f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx+1}]/dt/div[1]/button",
                    f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx+1}]/dt/div[1]/ul/li[1]/a",
                    [abs_path(row["option_img"])],
                )

        fill_additional_info(driver, wait)

        cur.execute(
            "UPDATE listing_queue SET is_pushed=1, pushed_at=NOW() WHERE id=%s", (qid,)
        )
        conn.commit()
        print(f"✔️ 已完成 {title}\n")

finally:
    cur.close()
    conn.close()
    driver.quit()
