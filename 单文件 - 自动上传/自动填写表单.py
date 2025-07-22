import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os, time
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
from collections import OrderedDict, defaultdict
from selenium.common.exceptions import TimeoutException

# 1. 读取主表和图片表
df_products = pd.read_excel(
    r"C:\Users\Administrator\Documents\Mecrado\Automation\products.xlsx",
    engine="openpyxl",
)
df_images = pd.read_excel(
    r"C:\Users\Administrator\Documents\Mecrado\Automation\images.xlsx",
    engine="openpyxl",
)

def fill_more_attrs(driver, wait):
    try:
        # 1⃣️ 展开「更多属性」面板
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="otherAttrShowAndHide"]'))
        ).click()

        # 2⃣️ 在第 22 行输入框填入 “1”
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[22]/td[2]/input'))
        ).clear()
        driver.find_element(
            By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[22]/td[2]/input'
        ).send_keys("1")

        # 3⃣️–4⃣️  第 25 行下拉：点输入框 → 选第 2 个选项
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/input'))
        ).click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/div[1]/div[2]'))
        ).click()

        # 5⃣️–6⃣️  第 26 行下拉：点输入框 → 选第 1 个选项
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[26]/td[2]/div/input'))
        ).click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[26]/td[2]/div/div[1]/div[1]'))
        ).click()

    except TimeoutException:
        print("⚠️  额外属性填写超时，已跳过")

def _open_uploader(driver, button_xpath, menu_xpath):
    driver.find_element(By.XPATH, button_xpath).click()
    time.sleep(0.3)
    driver.find_element(By.XPATH, menu_xpath).click()
    time.sleep(1)
    dlg = _get_open_dialog()
    dlg.wait("ready", timeout=10)
    return dlg


def _upload_in_dialog(dlg, paths):
    """
    paths 都在同一目录 ⇒ 一次多选；否则只能单张（调用处保证）。
    """
    dirpath = os.path.dirname(paths[0])
    dlg["Edit"].set_edit_text(dirpath)
    send_keys("{ENTER}")
    time.sleep(0.4)

    if len(paths) == 1:
        dlg["Edit"].set_edit_text(os.path.basename(paths[0]))
    else:
        multi = " ".join(f'"{os.path.basename(p)}"' for p in paths)
        dlg["Edit"].set_edit_text(multi)

    dlg["Button"].click()  # “打开(&O)”
    time.sleep(2.5)


def choose_category(driver, wait, keyword: str):
    """
    打开分类弹窗 → 输入关键词 → 点击搜索 → 选第一条结果
    """
    # 1) 打开弹窗（“选择分类”按钮）
    wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "/html/body/form/div/div[3]/div[2]/table/tbody/tr[3]/td[2]/button",
            )
        )
    ).click()

    # 2) 输入关键词
    search_box = wait.until(EC.element_to_be_clickable((By.ID, "searchCategory")))
    search_box.clear()
    search_box.send_keys(keyword)

    # 3) 点击搜索按钮
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="categoryIdAndName"]/div[1]/div/button')
        )
    ).click()

    # 4) 点第一条搜索结果
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="categoryIdAndName"]/div[4]/ul/li[1]')
        )
    ).click()

    # 5) （如果有“确认/保存”按钮，再点一下；没有就删掉下面两行）
    try:
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="categoryIdAndName"]/div[5]/button[1]')
            )
        ).click()
    except Exception:
        pass  # 某些页面没有确认按钮就直接关闭弹窗


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
    choose_category(driver, wait, info["category"])

    # 1. 保险的属性输入
    attr_xpath = '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input'
    attr_val   = info.get("attribute", "Generic")

    try:
        attr_input = wait.until(EC.element_to_be_clickable((By.XPATH, attr_xpath)))
        attr_input.clear()
        attr_input.send_keys(attr_val)
    except TimeoutException:
        print("属性输入框在指定时间内不可用，已跳过")

    # 2. 其它内容正常处理
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
    desc_input.send_keys(info["desc"])
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


def _get_open_dialog():
    # 1) 只取第一个匹配到的窗口句柄
    handles = findwindows.find_windows(
        title_re="打开|Open", class_name="#32770"
    )  # Windows file-dlg class
    if not handles:
        raise RuntimeError("没找到文件对话框！")
    # 2) 连接到该句柄
    return (
        Application(backend="win32")
        .connect(handle=handles[0])
        .window(handle=handles[0])
    )


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


def fill_sku_details(driver, wait, sku_list):
    for i, sku in enumerate(sku_list, start=1):
        input_xpath = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
        wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
        input_elem = driver.find_element(By.XPATH, input_xpath)
        input_elem.clear()
        input_elem.send_keys(sku)

    # 点击“UPC”批量设置
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[5]/span[2]/a'
    ).click()
    # 等弹窗出现
    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="upcBatchEdit"]')))

    # ====== 新增：选择下拉框第二项 ======
    # 等待下拉框出现且可点击
    upc_select_elem = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="upcSelect"]'))
    )
    select_obj = Select(upc_select_elem)

    # 等option足够
    for _ in range(10):
        if len(select_obj.options) > 1:
            break
        time.sleep(0.3)

    # 打印调试
    print("upcSelect options:", [o.text for o in select_obj.options])

    try:
        select_obj.select_by_index(1)  # 1为“美客多”
    except Exception as e:
        print("选择UPC下拉框第二项失败，错误：", e)

    # 勾选“随机UPC”第2个radio
    wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="upcBatchEdit"]/div[2]/div/div[2]/table/tbody/tr[4]/td[2]/label[2]/input',
            )
        )
    ).click()
    # 点确定
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="upcBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.5)
    # 批量设置包裹、重量、库存
    driver.find_element(
        By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a'
    ).click()
    wait.until(
        EC.visibility_of_element_located((By.XPATH, '//*[@id="skuPackageLength"]'))
    )
    driver.find_element(By.XPATH, '//*[@id="skuPackageLength"]').clear()
    driver.find_element(By.XPATH, '//*[@id="skuPackageLength"]').send_keys("15")
    driver.find_element(By.XPATH, '//*[@id="skuPackageWidth"]').clear()
    driver.find_element(By.XPATH, '//*[@id="skuPackageWidth"]').send_keys("12")
    driver.find_element(By.XPATH, '//*[@id="skuPackageHeight"]').clear()
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
    driver.find_element(By.XPATH, '//*[@id="skuWeight"]').clear()
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
    driver.find_element(By.XPATH, '//*[@id="num2"]').clear()
    driver.find_element(By.XPATH, '//*[@id="num2"]').send_keys("50")
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]')
        )
    ).click()
    time.sleep(0.5)


def upload_img_in_one_slot(driver, button_xpath, menu_xpath, img_list):
    """
    • 同一文件夹 ≥2 张 ⇒ 批量多选一次上传
    • 只有 1 张的文件夹 ⇒ 单独上传
    • 顺序以 img_list 首次出现的先后为准
    """
    img_list = [p for p in img_list if os.path.exists(p)]
    if not img_list:
        print("无可用图片，已跳过")
        return

    # —— 1. 统计每个目录下有几张 —— #
    dir_count = defaultdict(int)
    for p in img_list:
        dir_count[os.path.dirname(p)] += 1

    # —— 2. 维持原顺序分批上传 —— #
    done_dirs = set()
    for path in img_list:
        d = os.path.dirname(path)
        if d in done_dirs:
            continue  # 这一目录已经处理过
        group = [p for p in img_list if os.path.dirname(p) == d]

        dlg = _open_uploader(driver, button_xpath, menu_xpath)
        _upload_in_dialog(dlg, group)  # group 大小可为 1 或 >1

        done_dirs.add(d)


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


# 2. 启动浏览器、登录一次
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 5)
driver.get("https://www.dianxiaomi.com/")
time.sleep(1)
driver.find_element(By.ID, "exampleInputName").send_keys("Cloud23333")
driver.find_element(By.ID, "exampleInputPassword").send_keys("Dzj9876543")
input("请在浏览器手动输入验证码，然后回车继续...")
time.sleep(5)

# 3. 主批量上新流程
for _, product_row in df_products.iterrows():
    product_id = product_row["id"]
    info_dict = {
        "category": product_row["category"],
        "attribute": product_row["attribute"],
        "attr_index": 1,
        "attr_value": product_row["attr_value"],
        "title": product_row["title"],
        "desc": product_row["desc"],
        "global_price": str(product_row["global_price"]),
    }
    # 提取本产品所有图片和变体取值（每一行是一个SKU）
    product_images = df_images[df_images["product_id"] == product_id].copy()
    sizes = product_images["size"].dropna().unique().tolist()
    packs = product_images["pack"].dropna().unique().tolist()
    colors = product_images["color"].dropna().unique().tolist()
    variants_dict = {"sizes": sizes, "pack": packs, "color": colors}
    sku_values = product_images["sku"].tolist()  # 顺序即页面顺序
    upload_tasks = []
    for idx, (_, sku_row) in enumerate(product_images.iterrows()):
        img_paths = get_img_paths_from_row(sku_row)
        upload_tasks.append(
            {
                "button_xpath": f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx+1}]/dt/div[1]/button",
                "menu_xpath": f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx+1}]/dt/div[1]/ul/li[1]/a",
                "image_paths": img_paths,
            }
        )
    print(f"正在上传：{info_dict['title']}")
    driver.get("https://www.dianxiaomi.com/mercadoGlobalProduct/add.htm")
    time.sleep(1)
    close_all_close_buttons(driver, try_times=2)
    select_elem = driver.find_element(By.ID, "mercadoShopId")
    shop_select = Select(select_elem)
    shop_select.select_by_visible_text("子杰")
    time.sleep(0.5)
    try:
        label = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//label[contains(., "全选")]'))
        )
        label.click()
    except Exception:
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//label[contains(., "全选")]/input[@type="checkbox"]')
            )
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        checkbox.click()
    time.sleep(0.2)
    fill_basic_info(driver, wait, info_dict)
    fill_more_attrs(driver, wait)
    fill_site_prices(driver, info_dict["global_price"])
    fill_listing_type(driver)
    fill_variants(driver, wait, variants_dict)
    fill_sku_details(driver, wait, sku_values)
    for task in upload_tasks:
        upload_img_in_one_slot(
            driver, task["button_xpath"], task["menu_xpath"], task["image_paths"]
        )
    fill_additional_info(driver, wait)
    print(f"{info_dict['title']} 完成\n")
    time.sleep(1)

input("全部产品上传完毕，回车退出...")
driver.quit()
