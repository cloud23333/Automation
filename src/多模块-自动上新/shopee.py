import time
from common import wait_click, wait_present
import uploader, config
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from uploader import upload_img_in_one_slot
import pandas as pd

def choose_category(driver, title, desc, img_list):
    input_elem = wait_click(driver, '//*[@id="rc_select_0"]')
    input_elem.clear()
    input_elem.send_keys("5105209", Keys.ENTER)
    wait_click(driver, '//*[@id="basicInfo"]/div[2]/div/form/div[2]/div/div[2]/div/div/button').click()
    input_box = wait_present(driver, '/html/body/div[7]/div/div[2]/div/div[2]/div[2]/div/div[1]/span/span/input')
    input_box.clear()
    input_box.send_keys("Charms, Pendants & Ornaments")
    wait_click(driver, '/html/body/div[7]/div/div[2]/div/div[2]/div[2]/div/div[1]/span/span/span/button').click()
    wait_click(driver, '//div[contains(@class,"search-result-item")]//span[contains(@class,"f-red") and contains(text(),"Charms, Pendants & Ornaments")]//ancestor::div[contains(@class,"search-result-item")]').click()
    wait_click(driver, '//*[@id="basicInfo"]/div[2]/div/form/div[4]/div/div[2]/div/div/div/div/div/form/div[1]/div[1]/div/div[2]/div/div/div/div/div/div').click()
    wait_click(driver, '//div[@class="in-check-options" and .//span[text()="NoBrand"]]').click()
    elem = wait_click(driver, '//*[@id="basicInfo"]/div[2]/div/form/div[4]/div/div[2]/div/div/div/div/div/form/div[1]/div[2]/div/div[2]/div/div/div/div[1]/div[19]/label/span[2]')
    checkbox = elem.find_element(By.XPATH, '..//input[@type="checkbox"]')
    if not checkbox.is_selected():
        elem.click()
    wait_click(driver, '//*[@id="basicInfo"]/div[2]/div/form/div[4]/div/div[2]/div/div/div/div/div/form/div[1]/div[3]/div/div[2]/div/div/div/div/div/div/span[2]').click()
    wait_click(driver, '//div[@class="in-check-options" and .//span[text()="男女皆宜(Unisex)"]]').click()
    title_box = wait_click(driver, '//*[@id="productInfo"]/div[2]/div/form/div[1]/div[1]/div[2]/div[1]/div/div/div[1]/span/span/input')
    title_box.clear()
    title_box.send_keys(title)
    desc_box = wait_click(driver, '//*[@id="productInfo"]/div[2]/div/form/div[2]/div/div[2]/div/div/div/div[1]/div/textarea')
    desc_box.clear()
    desc_box.send_keys(desc)
    upload_img_in_one_slot(
        driver,
        '//*[@id="imageInfo"]/div[2]/div/form/div[1]/div/div[2]/div/div/header/button',
        '/html/body/div[10]/div/div/ul/li[1]',
        img_list
    )

def run(driver):
    df_products = pd.read_excel(config.Shopee_products, engine="openpyxl")
    for _, row in df_products.iterrows():
        title = row['title']
        desc = row['desc']
        img_list = [row[c] for c in df_products.columns if c.startswith('img') and pd.notna(row[c])]
        choose_category(driver, title, desc, img_list)
