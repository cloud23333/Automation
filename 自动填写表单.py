from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pywinauto

# ==== 参数区 ====
info_dict = {
    "category": "Beads(珠子)",
    "attribute": "Generic",
    "attr_index": 1,
    "attr_value": "beads",
    "title": "100Pcs hematite beads ",
    "desc": "good beads",
    "global_price": "3",
}
variants_dict = {"sizes": ["3", "4", "6", "8"], "pack": ["5"], "color": ["Black"]}
sku_values = ["HDS3-3mm", "HDS3-4mm", "HDS3-6mm", "HDS3-8mm"]
upload_tasks = [
    {
        "button_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[1]/dt/div[1]/button",
        "menu_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[1]/dt/div[1]/ul/li[1]/a",
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\3mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg",
        ],
    },
    {
        "button_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[2]/dt/div[1]/button",
        "menu_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[2]/dt/div[1]/ul/li[1]/a",
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\4mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg",
        ],
    },
    {
        "button_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[3]/dt/div[1]/button",
        "menu_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[3]/dt/div[1]/ul/li[1]/a",
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\6mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg",
        ],
    },
    {
        "button_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[4]/dt/div[1]/button",
        "menu_xpath": "/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[4]/dt/div[1]/ul/li[1]/a",
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\8mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg",
        ],
    },
]


# ==== 功能函数 ====
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
    category_select = Select(driver.find_element(By.ID, "categoryHistoryId"))
    category_select.select_by_visible_text(info["category"])
    time.sleep(0.5)
    attr_input = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input')
        )
    )
    attr_input.clear()
    attr_input.send_keys(info.get("attribute", "Generic"))
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
    global_price_input.send_keys(info["global_price"])
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
        inp.send_keys(price)


def fill_listing_type(driver):
    for i in range(1, 5):
        select_elem = driver.find_element(
            By.XPATH, f'//*[@id="siteProductTypeDiv"]/table/tbody/tr/td[{i}]/select'
        )
        select_obj = Select(select_elem)
        select_obj.select_by_index(1)
        time.sleep(0.1)


def fill_variants(driver, wait, variants):
    select_1 = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[1]/select'
    )
    Select(select_1).select_by_index(1)
    input_box = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[3]/input'
    )
    add_button = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[3]/button'
    )
    for value in variants["sizes"]:
        input_box.clear()
        input_box.send_keys(value)
        add_button.click()
        time.sleep(0.2)
    select_2 = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[1]/select'
    )
    Select(select_2).select_by_index(1)
    input_box_2 = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[3]/input'
    )
    add_button_2 = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[3]/button'
    )
    for value in variants["pack"]:
        input_box_2.clear()
        input_box_2.send_keys(value)
        add_button_2.click()
        time.sleep(0.2)
    color_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[3]/td[2]/div[3]/input')
        )
    )
    add_button = driver.find_element(
        By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[3]/td[2]/div[3]/button'
    )
    for value in variants["color"]:
        color_input.clear()
        color_input.send_keys(value)
        add_button.click()
        time.sleep(0.2)


def fill_sku_details(driver, wait, sku_list):
    for i, sku in enumerate(sku_list, start=1):
        input_xpath = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
        wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
        input_elem = driver.find_element(By.XPATH, input_xpath)
        input_elem.clear()
        input_elem.send_keys(sku)
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
    for img_path in img_list:
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


# ==== 主流程 ====
if __name__ == "__main__":
    username = "Cloud23333"
    password = "Dzj9876543"

    driver = webdriver.Chrome()
    driver.get("https://www.dianxiaomi.com/")
    time.sleep(1)
    driver.find_element(By.ID, "exampleInputName").send_keys(username)
    driver.find_element(By.ID, "exampleInputPassword").send_keys(password)
    input("请在浏览器手动输入验证码，然后回车继续...")
    time.sleep(5)
    driver.get("https://www.dianxiaomi.com/mercadoGlobalProduct/add.htm")
    time.sleep(1)
    close_all_close_buttons(driver, try_times=2)

    # 选择账号
    select_elem = driver.find_element(By.ID, "mercadoShopId")
    shop_select = Select(select_elem)
    shop_select.select_by_visible_text("子杰")
    time.sleep(0.5)

    # 全选
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

    wait = WebDriverWait(driver, 20)
    fill_basic_info(driver, wait, info_dict)
    fill_site_prices(driver, info_dict["global_price"])
    fill_listing_type(driver)
    fill_variants(driver, wait, variants_dict)
    fill_sku_details(driver, wait, sku_values)
    for task in upload_tasks:
        upload_img_in_one_slot(
            driver, task["button_xpath"], task["menu_xpath"], task["image_paths"]
        )
    fill_additional_info(driver, wait)
    input("流程结束，按回车关闭浏览器...")
    driver.quit()
