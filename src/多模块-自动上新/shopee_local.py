import os
import time
from common import wait_click, wait_present
import config
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from uploader import upload_img_in_one_slot
import pandas as pd
import pyperclip
import pyautogui
from selenium.webdriver import ActionChains


def choose_category(driver, title, desc, img_list):
    input_elem = wait_click(driver, '//*[@id="rc_select_0"]')
    input_elem.clear()
    input_elem.send_keys("5105209", Keys.ENTER)
    wait_click(
        driver, '//*[@id="basicInfo"]/div[2]/div/form/div[2]/div/div[2]/div/div/button'
    ).click()
    input_box = wait_present(
        driver,
        "/html/body/div[7]/div/div[2]/div/div[2]/div[2]/div/div[1]/span/span/input",
    )
    input_box.clear()
    input_box.send_keys("Charms, Pendants & Ornaments")
    wait_click(
        driver,
        "/html/body/div[7]/div/div[2]/div/div[2]/div[2]/div/div[1]/span/span/span/button",
    ).click()
    wait_click(
        driver,
        '//div[contains(@class,"search-result-item")]//span[contains(@class,"f-red") and contains(text(),"Charms, Pendants & Ornaments")]//ancestor::div[contains(@class,"search-result-item")]',
    ).click()
    wait_click(
        driver,
        '//*[@id="basicInfo"]/div[2]/div/form/div[4]/div/div[2]/div/div/div/div/div/form/div[1]/div[1]/div/div[2]/div/div/div/div/div/div',
    ).click()
    wait_click(
        driver, '//div[@class="in-check-options" and .//span[text()="NoBrand"]]'
    ).click()
    elem = wait_click(
        driver,
        '//*[@id="basicInfo"]/div[2]/div/form/div[4]/div/div[2]/div/div/div/div/div/form/div[1]/div[2]/div/div[2]/div/div/div/div[1]/div[19]/label/span[2]',
    )
    checkbox = elem.find_element(By.XPATH, '..//input[@type="checkbox"]')
    if not checkbox.is_selected():
        elem.click()
    wait_click(
        driver,
        '//*[@id="basicInfo"]/div[2]/div/form/div[4]/div/div[2]/div/div/div/div/div/form/div[1]/div[3]/div/div[2]/div/div/div/div/div/div/span[2]',
    ).click()
    wait_click(
        driver,
        '//div[@class="in-check-options" and .//span[text()="男女皆宜(Unisex)"]]',
    ).click()
    title_box = wait_click(
        driver,
        '//*[@id="productInfo"]/div[2]/div/form/div[1]/div[1]/div[2]/div[1]/div/div/div[1]/span/span/input',
    )
    title_box.clear()
    title_box.send_keys(title)
    desc_box = wait_click(
        driver,
        '//*[@id="productInfo"]/div[2]/div/form/div[2]/div/div[2]/div/div/div/div[1]/div/textarea',
    )
    desc_box.clear()
    desc_box.send_keys(desc)
    upload_img_in_one_slot(
        driver,
        '//*[@id="imageInfo"]/div[2]/div/form/div[1]/div/div[2]/div/div/header/button',
        "/html/body/div[10]/div/div/ul/li[1]",
        img_list,
    )


def fill_sku_table(driver, product_id, df_skus):
    time.sleep(1.5)
    wait_click(driver, '//*[@id="skuAttrInfo"]/div[1]/div/div[2]/button').click()
    wait_click(
        driver,
        '//li[contains(@class, "ant-dropdown-menu-item") and contains(.,"第二步：粘贴导入")]',
    ).click()
    rows = df_skus[df_skus["product_id"] == product_id][["color", "size"]]
    lines = ["Color\tSize"]
    for _, r in rows.iterrows():
        lines.append(f"{r['color']}\t{r['size']}")
    table = "\n".join(lines)
    pyperclip.copy(table)
    textarea = wait_click(
        driver,
        '//textarea[contains(@class,"ant-input") and @placeholder="请将Excel内容粘贴到此处"]',
    )
    textarea.click()

    pyautogui.hotkey("ctrl", "v")

    wait_click(
        driver, "/html/body/div[14]/div/div[2]/div/div[2]/div[3]/button[2]"
    ).click()


def upload_color_images(driver, df_skus, img_dir):
    if df_skus.empty:
        return
    imgs = []
    for color, g in df_skus.groupby("color"):
        g = g.sort_values("size")
        row = g.iloc[0]
        if pd.notna(row.get("img_path")):
            path = os.path.join(img_dir, row["img_path"])
            if os.path.exists(path):
                imgs.append(path)
    if not imgs:
        return

    wait_click(
        driver, '//*[@id="themeImageContainer"]/div[1]/div[2]/div/div/div[1]/a/div/span'
    ).click()
    wait_click(driver, '//span[contains(text(),"批量传图")]').click()
    select_img_el = wait_click(
        driver,
        '//button[contains(@class,"ant-btn-primary") and .//span[text()="选择图片"]]',
    )
    ActionChains(driver).move_to_element(select_img_el).perform()
    local_img_els = driver.find_elements(
        By.XPATH,
        '//span[@class="ant-dropdown-menu-title-content" and text()="本地图片"]',
    )
    for tag in local_img_els:
        if tag.is_displayed():
            tag.click()
            break


def run(driver):
    df_products = pd.read_excel(
        config.SHOPEE_PRODUCTS_XLSX, sheet_name="shopee_product", engine="openpyxl"
    )
    df_skus = pd.read_excel(
        config.SHOPEE_PRODUCTS_XLSX, sheet_name="shopee_images", engine="openpyxl"
    )
    for _, row in df_products.iterrows():
        title = row["title"]
        desc = row["desc"]
        img_list = [
            row[c]
            for c in df_products.columns
            if c.startswith("img") and pd.notna(row[c])
        ]
        choose_category(driver, title, desc, img_list)
        fill_sku_table(driver, row["product_id"], df_skus)
