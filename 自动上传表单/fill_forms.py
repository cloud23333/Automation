from selenium.webdriver.support.ui import Select
from utils import wait_click, wait_send_keys
import logging

def fill_basic_info(driver, info):
    wait_send_keys(driver, '//*[@id="productTitle"]', info["title"])
    wait_send_keys(driver, '//*[@class="descriptionTextarea"]', info["desc"])
    wait_send_keys(driver, '//*[@id="globalPrice"]', str(info["global_price"]))

def fill_variants(driver, variants):
    variant_groups = [(1, "sizes"), (2, "pack"), (3, "color")]
    for idx, key in variant_groups:
        select_xpath = f'//*[@id="skuParameterList"]/tbody/tr[{idx}]/td[2]/div[1]/select'
        Select(driver.find_element("xpath", select_xpath)).select_by_index(1)
        input_xpath = f'//*[@id="skuParameterList"]/tbody/tr[{idx}]/td[2]/div[3]/input'
        add_btn_xpath = f'//*[@id="skuParameterList"]/tbody/tr[{idx}]/td[2]/div[3]/button'
        for val in variants[key]:
            wait_send_keys(driver, input_xpath, str(val))
            wait_click(driver, add_btn_xpath)

def fill_sku_details(driver, sku_list):
    script = """
    document.querySelectorAll('#mercadoSkuAdd tbody tr td:nth-child(4) input').forEach((input, idx) => {
        input.value = arguments[0][idx];
    });
    """
    driver.execute_script(script, sku_list)


def choose_category(driver, wait, keyword):
    wait_click(driver, "/html/body/form/div/div[3]/div[2]/table/tbody/tr[3]/td[2]/button")
    wait_send_keys(driver, "//*[@id='searchCategory']", keyword)
    wait_click(driver, '//*[@id="categoryIdAndName"]/div[1]/div/button')
    wait_click(driver, '//*[@id="categoryIdAndName"]/div[4]/ul/li[1]')
    try:
        wait_click(driver, '//*[@id="categoryIdAndName"]/div[5]/button[1]')
    except:
        pass

def fill_basic_info(driver, wait, info):
    choose_category(driver, wait, info["category"])

    wait_send_keys(driver, '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input', info.get("attribute", "Generic"))
    
    Select(driver.find_element("xpath", '//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select')).select_by_index(info.get("attr_index", 1))
    
    wait_send_keys(driver, '//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input', info.get("attr_value", "beads"))
    
    wait_send_keys(driver, '//*[@id="productTitle"]', info["title"])
    wait_send_keys(driver, '//*[@class="descriptionTextarea"]', info["desc"])
    wait_send_keys(driver, '//*[@id="globalPrice"]', str(info["global_price"]))
