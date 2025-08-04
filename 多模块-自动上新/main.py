import pandas as pd, time
from selenium.webdriver.support.ui import Select
import dianxiaomi, mercado, uploader, common, config
from contextlib import suppress

df_products = pd.read_excel(config.PRODUCTS_XLSX, engine="openpyxl")
df_images = pd.read_excel(config.IMAGES_XLSX, engine="openpyxl")

driver = dianxiaomi.init_driver()
try:
    dianxiaomi.login(driver)

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
                mercado.get_img_paths_from_row(r)[0],
                tuple(mercado.get_img_paths_from_row(r)[1:]),
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
        Select(
            common.wait_present(driver, '//*[@id="mercadoShopId"]')
        ).select_by_visible_text("子杰")
        time.sleep(config.SLEEP_SHORT)

        common.wait_click(driver, '//label[contains(., "全选")]').click()
        time.sleep(config.SLEEP_SHORT)

        mercado.fill_basic_info(driver, info_dict)
        mercado.fill_more_attrs(driver)
        mercado.fill_site_prices(driver, info_dict["global_price"])
        mercado.fill_listing_type(driver)
        mercado.fill_variants(driver, variants_dict)
        mercado.fill_sku_details(driver, sku_values)

        for t in upload_tasks:
            uploader.upload_img_in_one_slot(
                driver, t["button_xpath"], t["menu_xpath"], t["image_paths"]
            )

        if identical_sec and common_sec:
            mercado.apply_secondary_images(driver)

        mercado.fill_additional_info(driver)
        print(f"{info_dict['title']} 完成\n")
        time.sleep(config.SLEEP_SHORT)

    input("全部产品上传完毕，回车退出...")

finally:
    with suppress(Exception):
        driver.quit()
