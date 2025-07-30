WAIT_SEC = 15
SLEEP_SHORT = 0.3
ATTR_TIMEOUT = 3

import os, sys, warnings, logging
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os, time
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
from collections import defaultdict
from selenium.common.exceptions import TimeoutException
from contextlib import suppress

chrome_opts = Options()
chrome_opts.add_argument("--log-level=3")
chrome_opts.add_experimental_option("excludeSwitches", ["enable-logging"])
service = Service(log_path=os.devnull)

warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")
logging.getLogger("absl").setLevel(logging.ERROR)

df_products = pd.read_excel(r"C:\Users\Administrator\Documents\Mecrado\Automation\products.xlsx", engine="openpyxl")
df_images = pd.read_excel(r"C:\Users\Administrator\Documents\Mecrado\Automation\images.xlsx", engine="openpyxl")

def safe_input(xpath, value, clear_first=True):
    try:
        elem = wait_present(xpath, timeout=ATTR_TIMEOUT)
        if clear_first:
            elem.clear()
        elem.send_keys(value)
    except TimeoutException:
        print(f"⚠️  skip attr: {xpath}")

def wait_present_scroll(xpath, timeout=WAIT_SEC):
    end = time.time() + timeout
    while time.time() < end:
        try:
            return driver.find_element(By.XPATH, xpath)
        except Exception:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(SLEEP_SHORT)
    raise TimeoutException(f"element not found: {xpath}")

def wait_click(xpath, timeout=WAIT_SEC):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))

def wait_visible(xpath, timeout=WAIT_SEC):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.XPATH, xpath)))

def wait_present(xpath, timeout=WAIT_SEC):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))

def fill_description(text):
    try:
        area = wait_present_scroll('//*[contains(@class,"descriptionTextarea") or contains(@class,"note-editable")]',
                                   timeout=5)
        area.clear()
        area.send_keys(text)
        return
    except TimeoutException:
        pass

    try:
        frame = wait_present('//iframe[contains(@id,"ueditor") or contains(@class,"note-editable") or contains(@src,"editor")]',
                             timeout=5)
        driver.switch_to.frame(frame)
        body = wait_present('//body')
        body.clear()
        body.send_keys(text)
        driver.switch_to.default_content()
    except TimeoutException:
        print("⚠️  description editor not found")

def fill_more_attrs():
    try:
        wait_click('//*[@id="otherAttrShowAndHide"]').click()
        inp = wait_present('//*[@id="productAttributeShow"]/table/tbody/tr[22]/td[2]/input')
        inp.clear()
        inp.send_keys("1")
        wait_click('//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/input').click()
        wait_click('//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/div[1]/div[2]').click()
        wait_click('//*[@id="productAttributeShow"]/table/tbody/tr[26]/td[2]/div/input').click()
        wait_click('//*[@id="productAttributeShow"]/table/tbody/tr[26]/td[2]/div/div[1]/div[1]').click()
    except TimeoutException:
        print("⚠️  extra attributes timeout")

def _open_uploader(button_xpath, menu_xpath, retries=3):
    for _ in range(retries):
        try:
            btn = wait_click(button_xpath)
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            btn.click()
            wait_click(menu_xpath).click()
        except Exception:
            time.sleep(SLEEP_SHORT)

        for _ in range(20):
            handles = findwindows.find_windows(title_re="打开|Open", class_name="#32770")
            if handles:
                dlg = Application(backend="win32").connect(handle=handles[0]).window(handle=handles[0])
                dlg.wait("ready", timeout=10)
                return dlg
            time.sleep(0.3)

    raise TimeoutException("文件对话框未弹出，已重试多次")

def _upload_in_dialog(dlg, paths):
    dirpath = os.path.dirname(paths[0])
    dlg["Edit"].set_edit_text(dirpath)
    send_keys("{ENTER}")
    time.sleep(SLEEP_SHORT)
    if len(paths) == 1:
        dlg["Edit"].set_edit_text(os.path.basename(paths[0]))
    else:
        dlg["Edit"].set_edit_text(" ".join(f'"{os.path.basename(p)}"' for p in paths))
    dlg["Button"].click()
    time.sleep(2)

def choose_category(keyword):
    wait_click("/html/body/form/div/div[3]/div[2]/table/tbody/tr[3]/td[2]/button").click()
    search_box = wait_present('//*[@id="searchCategory"]')
    search_box.clear()
    search_box.send_keys(keyword)
    wait_click('//*[@id="categoryIdAndName"]/div[1]/div/button').click()
    wait_click('//*[@id="categoryIdAndName"]/div[4]/ul/li[1]').click()
    try:
        wait_click('//*[@id="categoryIdAndName"]/div[5]/button[1]').click()
    except Exception:
        pass

def close_all_close_buttons(try_times=2):
    for _ in range(try_times):
        close_buttons = driver.find_elements(By.XPATH, '//button[contains(text(), "关闭")]')
        if not close_buttons:
            break
        for btn in close_buttons:
            try:
                btn.click()
                time.sleep(SLEEP_SHORT)
            except Exception:
                pass
        time.sleep(0.5)

def fill_basic_info(info):
    choose_category(info["category"])

    safe_input('//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input',
               info.get("attribute", "Generic"))
    try:
        Select(wait_present('//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select',
                            timeout=ATTR_TIMEOUT)).select_by_index(info.get("attr_index", 1))
    except TimeoutException:
        print("⚠️  skip attr select")

    safe_input('//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input',
               info.get("attr_value", "beads"))

    wait_present('//*[@id="productTitle"]').clear()
    wait_present('//*[@id="productTitle"]').send_keys(info["title"])

    fill_description(info["desc"])

    wait_present('//*[@id="globalPrice"]').clear()
    wait_present('//*[@id="globalPrice"]').send_keys(str(info["global_price"]))
    time.sleep(SLEEP_SHORT)

def fill_site_prices(price):
    paths = [
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[1]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[2]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[3]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[4]/input',
    ]
    for x in paths:
        e = wait_present(x)
        e.clear()
        e.send_keys(str(price))

def _get_open_dialog():
    handles = findwindows.find_windows(title_re="打开|Open", class_name="#32770")
    return Application(backend="win32").connect(handle=handles[0]).window(handle=handles[0])

def fill_listing_type():
    for i in range(1, 5):
        Select(wait_present(f'//*[@id="siteProductTypeDiv"]/table/tbody/tr/td[{i}]/select')).select_by_index(1)
        time.sleep(SLEEP_SHORT)

def fill_variants(v):
    row_idx = 1

    def add_group(values, select_xpath_tpl):
        nonlocal row_idx
        if not values:
            return
        Select(wait_present(select_xpath_tpl.format(row_idx))).select_by_index(1)
        inx = f'//*[@id="skuParameterList"]/tbody/tr[{row_idx}]/td[2]/div[3]/input'
        btn = f'//*[@id="skuParameterList"]/tbody/tr[{row_idx}]/td[2]/div[3]/button'
        for val in values:
            wait_present(inx).clear()
            wait_present(inx).send_keys(str(val))
            wait_click(btn).click()
            time.sleep(SLEEP_SHORT)
        row_idx += 1

    add_group(v["sizes"],  '//*[@id="skuParameterList"]/tbody/tr/td[2]/div[1]/select')
    add_group(v["pack"],   '//*[@id="skuParameterList"]/tbody/tr/td[2]/div[1]/select')
    add_group(v["color"],  '//*[@id="skuParameterList"]/tbody/tr/td[2]/div[1]/select')

def fill_sku_details(sku_list):
    for i, sku in enumerate(sku_list, 1):
        ip = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
        e = wait_present(ip)
        e.clear()
        e.send_keys(sku)
    wait_click('//*[@id="mercadoSkuAdd"]/table/thead/tr/th[5]/span[2]/a').click()
    wait_visible('//*[@id="upcBatchEdit"]')
    sel = Select(wait_click('//*[@id="upcSelect"]'))
    for _ in range(10):
        if len(sel.options) > 1:
            break
        time.sleep(SLEEP_SHORT)
    try:
        sel.select_by_index(1)
    except Exception as e:
        print("选择UPC失败", e)
    wait_click('//*[@id="upcBatchEdit"]/div[2]/div/div[2]/table/tbody/tr[4]/td[2]/label[2]/input').click()
    wait_click('//*[@id="upcBatchEdit"]/div[2]/div/div[3]/button[1]').click()
    wait_click('//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a').click()
    wait_visible('//*[@id="skuPackageLength"]')
    wait_present('//*[@id="skuPackageLength"]').clear()
    wait_present('//*[@id="skuPackageLength"]').send_keys("15")
    wait_present('//*[@id="skuPackageWidth"]').clear()
    wait_present('//*[@id="skuPackageWidth"]').send_keys("12")
    wait_present('//*[@id="skuPackageHeight"]').clear()
    wait_present('//*[@id="skuPackageHeight"]').send_keys("1")
    wait_click('//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]').click()
    wait_click('//*[@id="mercadoSkuAdd"]/table/thead/tr/th[7]/span[2]/a').click()
    wait_visible('//*[@id="skuWeight"]')
    wait_present('//*[@id="skuWeight"]').clear()
    wait_present('//*[@id="skuWeight"]').send_keys("100")
    wait_click('//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]').click()
    wait_click('//*[@id="mercadoSkuAdd"]/table/thead/tr/th[8]/span[2]/a').click()
    wait_visible('//*[@id="num2"]')
    wait_present('//*[@id="num2"]').clear()
    wait_present('//*[@id="num2"]').send_keys("50")
    wait_click('//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]').click()

def upload_img_in_one_slot(button_xpath, menu_xpath, img_list):
    img_list = [p for p in img_list if os.path.exists(p)]
    if not img_list:
        return
    done = set()
    for p in img_list:
        d = os.path.dirname(p)
        if d in done:
            continue
        group = [x for x in img_list if os.path.dirname(x) == d]
        dlg = _open_uploader(button_xpath, menu_xpath)
        _upload_in_dialog(dlg, group)
        done.add(d)

def fill_additional_info():
    Select(wait_click('//*[@id="warrantyType"]')).select_by_index(3)
    time.sleep(SLEEP_SHORT)
    wait_click("/html/body/form/div/div[13]/div[2]/button").click()
    time.sleep(SLEEP_SHORT)
    wait_click("/html/body/form/div/div[13]/div[2]/ul/li[1]/a").click()
    time.sleep(SLEEP_SHORT)

def get_img_paths_from_row(row):
    res = []
    for i in range(1, 21):
        c = f"img_path{i}"
        if c in row and pd.notna(row[c]) and str(row[c]).strip():
            res.append(str(row[c]).strip())
    return res

def apply_secondary_images():
    wait_click('//*[@id="picAppVariant"]/a').click()
    wait_click('//*[@id="picAppVariant"]/ul/li[7]/a').click()
    time.sleep(1.5)

driver = webdriver.Chrome(service=service, options=chrome_opts)
wait = WebDriverWait(driver, WAIT_SEC)
try:
    driver.get("https://www.dianxiaomi.com/")
    time.sleep(1)
    wait_present('//*[@id="exampleInputName"]').send_keys("Cloud23333")
    wait_present('//*[@id="exampleInputPassword"]').send_keys("Dzj9876543")
    input("验证码后回车...")
    time.sleep(5)

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
        product_images = df_images[df_images["product_id"] == product_id].copy()
        main_sec = product_images.apply(lambda r: (get_img_paths_from_row(r)[0], tuple(get_img_paths_from_row(r)[1:])), axis=1)
        product_images["main"] = main_sec.apply(lambda t: t[0])
        product_images["secondary"] = main_sec.apply(lambda t: t[1])
        sec_lists = product_images["secondary"].unique()
        identical_sec = len(sec_lists) == 1
        common_sec = list(sec_lists[0]) if identical_sec else []
        sizes = product_images["size"].dropna().unique().tolist()
        packs = product_images["pack"].dropna().unique().tolist()
        colors = product_images["color"].dropna().unique().tolist()
        varying = [n for n, v in [("sizes", sizes), ("pack", packs), ("color", colors)] if len(v) > 1]
        variants_dict = {
            "sizes": sizes,
            "pack": packs,
            "color": colors,
        }
        sku_values = product_images["sku"].tolist()
        upload_tasks = []
        for pos, row in enumerate(product_images.itertuples(index=False), 1):
            imgs = [row.main]
            if identical_sec and common_sec:
                if pos == 1:
                    imgs += common_sec
            else:
                imgs += list(row.secondary)
            upload_tasks.append(
                {
                    "button_xpath": f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{pos}]/dt/div[1]/button",
                    "menu_xpath": f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{pos}]/dt/div[1]/ul/li[1]/a",
                    "image_paths": imgs,
                }
            )
        print(f"正在上传：{info_dict['title']}")
        driver.get("https://www.dianxiaomi.com/mercadoGlobalProduct/add.htm")
        time.sleep(1)
        close_all_close_buttons(2)
        Select(wait_present('//*[@id="mercadoShopId"]')).select_by_visible_text("子杰")
        time.sleep(SLEEP_SHORT)
        try:
            wait_click('//label[contains(., "全选")]').click()
        except Exception:
            cb = wait_click('//label[contains(., "全选")]/input[@type="checkbox"]')
            driver.execute_script("arguments[0].scrollIntoView(true);", cb)
            cb.click()
        time.sleep(SLEEP_SHORT)
        fill_basic_info(info_dict)
        fill_more_attrs()
        fill_site_prices(info_dict["global_price"])
        fill_listing_type()
        fill_variants(variants_dict)
        fill_sku_details(sku_values)
        for t in upload_tasks:
            upload_img_in_one_slot(t["button_xpath"], t["menu_xpath"], t["image_paths"])
        if identical_sec and common_sec:
            apply_secondary_images()
        fill_additional_info()
        print(f"{info_dict['title']} 完成\n")
        time.sleep(SLEEP_SHORT)
    input("全部产品上传完毕，回车退出...")
finally:
    with suppress(Exception):
        driver.quit()
