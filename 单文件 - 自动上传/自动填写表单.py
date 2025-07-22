import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pyperclip
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
import logging
from collections import defaultdict

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Excel路径相对化
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
df_products = pd.read_excel(os.path.join(BASE_DIR, "products.xlsx"), engine="openpyxl")
df_images = pd.read_excel(os.path.join(BASE_DIR, "images.xlsx"), engine="openpyxl")

# 浏览器等待函数
def wait_clickable(driver, xpath, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))

# 优化后的图片上传函数
def open_upload_dialog(driver, button_xpath, menu_xpath):
    wait_clickable(driver, button_xpath).click()
    wait_clickable(driver, menu_xpath).click()
    handles = findwindows.find_windows(title_re="打开|Open", class_name="#32770")
    if not handles:
        raise RuntimeError("未找到文件对话框")
    return Application(backend="win32").connect(handle=handles[0]).window(handle=handles[0])

def upload_images(dlg, paths):
    pyperclip.copy('"{}"'.format('" "'.join(paths)))
    dlg["Edit"].click_input()
    send_keys('^v')
    time.sleep(0.3)
    dlg["Button"].click()

# 分类选择
def choose_category(driver, keyword: str):
    wait_clickable(driver, "/html/body/form/div/div[3]/div[2]/table/tbody/tr[3]/td[2]/button").click()
    search_box = wait_clickable(driver, "//*[@id='searchCategory']")
    search_box.clear()
    search_box.send_keys(keyword)
    wait_clickable(driver, '//*[@id="categoryIdAndName"]/div[1]/div/button').click()
    wait_clickable(driver, '//*[@id="categoryIdAndName"]/div[4]/ul/li[1]').click()

# 基本信息填写（删除JS强制输入）
def fill_basic_info(driver, info):
    choose_category(driver, info["category"])
    attr_xpath = '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input'
    attr_input = wait_clickable(driver, attr_xpath)
    attr_input.clear()
    attr_input.send_keys(info.get("attribute", "Generic"))

    Select(driver.find_element(By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select')).select_by_index(info.get("attr_index", 1))
    input_beads = driver.find_element(By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input')
    input_beads.clear()
    input_beads.send_keys(info.get("attr_value", "beads"))

    driver.find_element(By.XPATH, '//*[@id="productTitle"]').send_keys(info["title"])
    driver.find_element(By.CLASS_NAME, "descriptionTextarea").send_keys(info["desc"])
    driver.find_element(By.XPATH, '//*[@id="globalPrice"]').send_keys(str(info["global_price"]))

# SKU批量填写优化
def fill_sku_details(driver, sku_list):
    script = """
    let inputs = document.querySelectorAll('#mercadoSkuAdd tbody tr td:nth-child(4) input');
    inputs.forEach((input, i) => input.value = arguments[0][i]);
    """
    driver.execute_script(script, sku_list)

# 主流程
try:
    driver = webdriver.Chrome()
    driver.get("https://www.dianxiaomi.com/")
    driver.find_element(By.ID, "exampleInputName").send_keys("Cloud23333")
    driver.find_element(By.ID, "exampleInputPassword").send_keys("Dzj9876543")
    input("请手动输入验证码后回车继续...")

    for _, product_row in df_products.iterrows():
        try:
            product_id = product_row["id"]
            info_dict = {
                "category": product_row["category"],
                "attribute": product_row["attribute"],
                "attr_index": 1,
                "attr_value": product_row["attr_value"],
                "title": product_row["title"],
                "desc": product_row["desc"],
                "global_price": product_row["global_price"],
            }

            product_images = df_images[df_images["product_id"] == product_id]
            sizes = product_images["size"].dropna().unique().tolist()
            packs = product_images["pack"].dropna().unique().tolist()
            colors = product_images["color"].dropna().unique().tolist()
            variants_dict = {"sizes": sizes, "pack": packs, "color": colors}
            sku_values = product_images["sku"].tolist()

            logging.info(f"正在上传：{info_dict['title']}")
            driver.get("https://www.dianxiaomi.com/mercadoGlobalProduct/add.htm")

            select_elem = Select(wait_clickable(driver, "//*[@id='mercadoShopId']"))
            select_elem.select_by_visible_text("子杰")
            wait_clickable(driver, "//label[contains(.,'全选')]").click()

            fill_basic_info(driver, info_dict)
            fill_sku_details(driver, sku_values)

            for idx, (_, sku_row) in enumerate(product_images.iterrows(), 1):
                img_paths = [sku_row[f"img_path{i}"] for i in range(1, 21) if pd.notna(sku_row.get(f"img_path{i}"))]
                if img_paths:
                    dlg = open_upload_dialog(driver,
                        f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx}]/dt/div[1]/button",
                        f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx}]/dt/div[1]/ul/li[1]/a"
                    )
                    upload_images(dlg, img_paths)

            logging.info(f"产品上传完成：{info_dict['title']}")
            time.sleep(1)

        except Exception as e:
            logging.error(f"上传产品 {product_row['title']} 时发生错误：{e}")
            continue
finally:
    input("全部产品上传完毕，回车退出...")
    driver.quit()