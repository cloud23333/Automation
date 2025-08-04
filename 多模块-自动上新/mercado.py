import time
import pandas as pd
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
import common, config


def choose_category(driver, keyword):
    common.wait_click(
        driver, "/html/body/form/div/div[3]/div[2]/table/tbody/tr[3]/td[2]/button"
    ).click()
    box = common.wait_present(driver, '//*[@id="searchCategory"]')
    box.clear()
    box.send_keys(keyword)
    common.wait_click(driver, '//*[@id="categoryIdAndName"]/div[1]/div/button').click()
    common.wait_click(driver, '//*[@id="categoryIdAndName"]/div[4]/ul/li[1]').click()
    try:
        common.wait_click(
            driver, '//*[@id="categoryIdAndName"]/div[5]/button[1]'
        ).click()
    except Exception:
        pass


def fill_basic_info(driver, info):
    choose_category(driver, info["category"])
    common.wait_visible(driver, '//*[@id="productAttributeShow"]/table/tbody/tr[2]')
    common.safe_input(
        driver,
        '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input',
        info.get("attribute", "Generic"),
    )
    sel_el = common.wait_present(
        driver, '//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select'
    )
    driver.execute_script(
        "arguments[0].selectedIndex = arguments[1];"
        "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
        sel_el,
        info.get("attr_index", 1),
    )
    common.safe_input(
        driver,
        '//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input',
        info.get("attr_value", "beads"),
    )
    title_el = common.wait_present(driver, '//*[@id="productTitle"]')
    title_el.clear()
    title_el.send_keys(info["title"])
    common.fill_description(driver, info["desc"])
    price_el = common.wait_present(driver, '//*[@id="globalPrice"]')
    price_el.clear()
    price_el.send_keys(str(info["global_price"]))
    time.sleep(config.SLEEP_SHORT)


def fill_more_attrs(driver):
    try:
        common.wait_click(driver, '//*[@id="otherAttrShowAndHide"]').click()
        inp = common.wait_present(
            driver, '//*[@id="productAttributeShow"]/table/tbody/tr[22]/td[2]/input'
        )
        inp.clear()
        inp.send_keys("1")
        common.wait_click(
            driver, '//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/input'
        ).click()
        common.wait_click(
            driver,
            '//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/div[1]/div[2]',
        ).click()
        common.wait_click(
            driver, '//*[@id="productAttributeShow"]/table/tbody/tr[26]/td[2]/div/input'
        ).click()
        common.wait_click(
            driver,
            '//*[@id="productAttributeShow"]/table/tbody/tr[26]/td[2]/div/div[1]/div[1]',
        ).click()
    except TimeoutException:
        print("⚠️  extra attributes timeout")


def fill_site_prices(driver, price):
    xpaths = [
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[1]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[2]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[3]/input',
        '//*[@id="sitePriceDiv"]/table/tbody/tr/td[4]/input',
    ]
    for xp in xpaths:
        e = common.wait_present(driver, xp)
        e.clear()
        e.send_keys(str(price))


def fill_listing_type(driver):
    for i in range(1, 5):
        Select(
            common.wait_present(
                driver, f'//*[@id="siteProductTypeDiv"]/table/tbody/tr/td[{i}]/select'
            )
        ).select_by_index(1)
        time.sleep(config.SLEEP_SHORT)


def fill_variants(driver, v):
    row_idx = 1

    def add_group(values):
        nonlocal row_idx
        if not values:
            return
        Select(
            common.wait_present(
                driver, '//*[@id="skuParameterList"]/tbody/tr/td[2]/div[1]/select'
            )
        ).select_by_index(1)
        inx = f'//*[@id="skuParameterList"]/tbody/tr[{row_idx}]/td[2]/div[3]/input'
        btn = f'//*[@id="skuParameterList"]/tbody/tr[{row_idx}]/td[2]/div[3]/button'
        for val in values:
            common.wait_present(driver, inx).clear()
            common.wait_present(driver, inx).send_keys(str(val))
            common.wait_click(driver, btn).click()
            time.sleep(config.SLEEP_SHORT)
        row_idx += 1

    add_group(v["sizes"])
    add_group(v["pack"])
    add_group(v["color"])


def fill_sku_details(driver, sku_list):
    for i, sku in enumerate(sku_list, 1):
        ip = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
        e = common.wait_present(driver, ip)
        e.clear()
        e.send_keys(sku)
    common.wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[5]/span[2]/a'
    ).click()
    common.wait_visible(driver, '//*[@id="upcBatchEdit"]')
    sel = Select(common.wait_click(driver, '//*[@id="upcSelect"]'))
    for _ in range(10):
        if len(sel.options) > 1:
            break
        time.sleep(config.SLEEP_SHORT)
    try:
        sel.select_by_index(1)
    except Exception as e:
        print("选择UPC失败", e)
    common.wait_click(
        driver,
        '//*[@id="upcBatchEdit"]/div[2]/div/div[2]/table/tbody/tr[4]/td[2]/label[2]/input',
    ).click()
    common.wait_click(
        driver, '//*[@id="upcBatchEdit"]/div[2]/div/div[3]/button[1]'
    ).click()
    common.wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a'
    ).click()
    for xp, val in [
        ('//*[@id="skuPackageLength"]', "15"),
        ('//*[@id="skuPackageWidth"]', "12"),
        ('//*[@id="skuPackageHeight"]', "1"),
    ]:
        box = common.wait_present(driver, xp)
        box.clear()
        box.send_keys(val)
    common.wait_click(
        driver, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'
    ).click()
    common.wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[7]/span[2]/a'
    ).click()
    wt = common.wait_present(driver, '//*[@id="skuWeight"]')
    wt.clear()
    wt.send_keys("100")
    common.wait_click(
        driver, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'
    ).click()
    common.wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[8]/span[2]/a'
    ).click()
    qty = common.wait_present(driver, '//*[@id="num2"]')
    qty.clear()
    qty.send_keys("50")
    common.wait_click(
        driver, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'
    ).click()


def fill_additional_info(driver):
    Select(common.wait_click(driver, '//*[@id="warrantyType"]')).select_by_index(3)
    time.sleep(config.SLEEP_SHORT)
    common.wait_click(driver, "/html/body/form/div/div[13]/div[2]/button").click()
    time.sleep(config.SLEEP_SHORT)
    common.wait_click(driver, "/html/body/form/div/div[13]/div[2]/ul/li[1]/a").click()
    time.sleep(config.SLEEP_SHORT)


def apply_secondary_images(driver):
    common.wait_click(driver, '//*[@id="picAppVariant"]/a').click()
    common.wait_click(driver, '//*[@id="picAppVariant"]/ul/li[7]/a').click()
    time.sleep(1.5)


def get_img_paths_from_row(row):
    res = []
    for i in range(1, 21):
        col = f"img_path{i}"
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            res.append(str(row[col]).strip())
    return res
