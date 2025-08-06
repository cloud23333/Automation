from contextlib import suppress
import time
import pandas as pd
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
import config
import dianxiaomi
import common
from common import wait_click, wait_present, wait_visible, safe_input, fill_description
import uploader


def choose_category(driver, keyword):
    wait_click(
        driver, "/html/body/form/div/div[3]/div[2]/table/tbody/tr[3]/td[2]/button"
    ).click()
    box = wait_present(driver, '//*[@id="searchCategory"]')
    box.clear()
    box.send_keys(keyword)
    wait_click(driver, '//*[@id="categoryIdAndName"]/div[1]/div/button').click()
    wait_click(driver, '//*[@id="categoryIdAndName"]/div[4]/ul/li[1]').click()
    try:
        wait_click(driver, '//*[@id="categoryIdAndName"]/div[5]/button[1]').click()
    except Exception:
        pass


def fill_basic_info(driver, info):
    choose_category(driver, info["category"])
    wait_visible(driver, '//*[@id="productAttributeShow"]/table/tbody/tr[2]')
    safe_input(
        driver,
        '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input',
        info.get("attribute", "Generic"),
    )
    sel_el = wait_present(
        driver, '//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select'
    )
    driver.execute_script(
        "arguments[0].selectedIndex = arguments[1];"
        "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
        sel_el,
        info.get("attr_index", 1),
    )
    safe_input(
        driver,
        '//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input',
        info.get("attr_value", "beads"),
    )
    title_el = wait_present(driver, '//*[@id="productTitle"]')
    title_el.clear()
    title_el.send_keys(info["title"])
    fill_description(driver, info["desc"])
    price_el = wait_present(driver, '//*[@id="globalPrice"]')
    price_el.clear()
    price_el.send_keys(str(info["global_price"]))
    time.sleep(config.SLEEP_SHORT)


def fill_more_attrs(driver):
    try:
        wait_click(driver, '//*[@id="otherAttrShowAndHide"]').click()
        inp = wait_present(
            driver, '//*[@id="productAttributeShow"]/table/tbody/tr[22]/td[2]/input'
        )
        inp.clear()
        inp.send_keys("1")
        wait_click(
            driver, '//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/input'
        ).click()
        wait_click(
            driver,
            '//*[@id="productAttributeShow"]/table/tbody/tr[25]/td[2]/div/div[1]/div[2]',
        ).click()
        wait_click(
            driver, '//*[@id="productAttributeShow"]/table/tbody/tr[26]/td[2]/div/input'
        ).click()
        wait_click(
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
        e = wait_present(driver, xp)
        e.clear()
        e.send_keys(str(price))


def fill_listing_type(driver):
    for i in range(1, 5):
        Select(
            wait_present(
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
            wait_present(
                driver, '//*[@id="skuParameterList"]/tbody/tr/td[2]/div[1]/select'
            )
        ).select_by_index(1)
        inx = f'//*[@id="skuParameterList"]/tbody/tr[{row_idx}]/td[2]/div[3]/input'
        btn = f'//*[@id="skuParameterList"]/tbody/tr[{row_idx}]/td[2]/div[3]/button'
        for val in values:
            wait_present(driver, inx).clear()
            wait_present(driver, inx).send_keys(str(val))
            wait_click(driver, btn).click()
            time.sleep(config.SLEEP_SHORT)
        row_idx += 1

    add_group(v["sizes"])
    add_group(v["pack"])
    add_group(v["color"])


def fill_sku_details(driver, sku_list):
    for i, sku in enumerate(sku_list, 1):
        ip = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
        e = wait_present(driver, ip)
        e.clear()
        e.send_keys(sku)
    wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[5]/span[2]/a'
    ).click()
    wait_visible(driver, '//*[@id="upcBatchEdit"]')
    sel = Select(wait_click(driver, '//*[@id="upcSelect"]'))
    for _ in range(10):
        if len(sel.options) > 1:
            break
        time.sleep(config.SLEEP_SHORT)
    try:
        sel.select_by_index(1)
    except Exception as e:
        print("选择UPC失败", e)
    wait_click(
        driver,
        '//*[@id="upcBatchEdit"]/div[2]/div/div[2]/table/tbody/tr[4]/td[2]/label[2]/input',
    ).click()
    wait_click(driver, '//*[@id="upcBatchEdit"]/div[2]/div/div[3]/button[1]').click()
    wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a'
    ).click()
    for xp, val in [
        ('//*[@id="skuPackageLength"]', "15"),
        ('//*[@id="skuPackageWidth"]', "12"),
        ('//*[@id="skuPackageHeight"]', "1"),
    ]:
        box = wait_present(driver, xp)
        box.clear()
        box.send_keys(val)
    wait_click(
        driver, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'
    ).click()
    wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[7]/span[2]/a'
    ).click()
    wt = wait_present(driver, '//*[@id="skuWeight"]')
    wt.clear()
    wt.send_keys("100")
    wait_click(
        driver, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'
    ).click()
    wait_click(
        driver, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[8]/span[2]/a'
    ).click()
    qty = wait_present(driver, '//*[@id="num2"]')
    qty.clear()
    qty.send_keys("50")
    wait_click(
        driver, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'
    ).click()


def fill_additional_info(driver):
    Select(wait_click(driver, '//*[@id="warrantyType"]')).select_by_index(3)
    time.sleep(config.SLEEP_SHORT)
    wait_click(driver, "/html/body/form/div/div[13]/div[2]/button").click()
    time.sleep(config.SLEEP_SHORT)
    wait_click(driver, "/html/body/form/div/div[13]/div[2]/ul/li[1]/a").click()
    time.sleep(config.SLEEP_SHORT)


def apply_secondary_images(driver):
    wait_click(driver, '//*[@id="picAppVariant"]/a').click()
    wait_click(driver, '//*[@id="picAppVariant"]/ul/li[7]/a').click()
    time.sleep(1.5)


def get_img_paths_from_row(row):
    res = []
    for i in range(1, 21):
        col = f"img_path{i}"
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            res.append(str(row[col]).strip())
    return res


def run(driver):
    df_products = pd.read_excel(config.MERCADO_PRODUCTS_XLSX, engine="openpyxl")
    df_images = pd.read_excel(config.MERCADO_IMAGES_XLSX, engine="openpyxl")
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
        product_images = product_images.sort_values(
            ["color", "size", "pack"], ascending=[True, True, True]
        ).reset_index(drop=True)
        main_sec = product_images.apply(
            lambda r: (
                get_img_paths_from_row(r)[0],
                tuple(get_img_paths_from_row(r)[1:]),
            ),
            axis=1,
        )
        product_images["main"] = main_sec.apply(lambda t: t[0])
        product_images["secondary"] = main_sec.apply(lambda t: t[1])
        sec_lists = product_images["secondary"].unique()
        identical_sec = len(sec_lists) == 1
        common_sec = list(sec_lists[0]) if identical_sec else []
        sizes = sorted(product_images["size"].dropna().unique())
        packs = sorted(product_images["pack"].dropna().unique())
        colors = product_images["color"].dropna().unique().tolist()
        varying = [
            n
            for n, v in [("sizes", sizes), ("pack", packs), ("color", colors)]
            if len(v) > 1
        ]
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
        common.close_all_close_buttons(driver, 2)
        Select(wait_present(driver, '//*[@id="mercadoShopId"]')).select_by_visible_text(
            "子杰"
        )
        time.sleep(config.SLEEP_SHORT)
        wait_click(driver, '//label[contains(., "全选")]').click()
        time.sleep(config.SLEEP_SHORT)
        fill_basic_info(driver, info_dict)
        fill_more_attrs(driver)
        fill_site_prices(driver, info_dict["global_price"])
        fill_listing_type(driver)
        fill_variants(driver, variants_dict)
        fill_sku_details(driver, sku_values)
        for t in upload_tasks:
            uploader.upload_img_in_one_slot(
                driver, t["button_xpath"], t["menu_xpath"], t["image_paths"]
            )

        if identical_sec and common_sec:
            apply_secondary_images(driver)

        fill_additional_info(driver)
        print(f"{info_dict['title']} 完成\n")
        time.sleep(config.SLEEP_SHORT)

    return


if __name__ == "__main__":
    driver = dianxiaomi.init_driver()
    try:
        dianxiaomi.login(driver)
        run(driver)
        input("全部产品上传完毕，回车退出...")
    finally:
        with suppress(Exception):
            driver.quit()
