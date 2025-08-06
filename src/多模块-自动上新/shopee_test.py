from common import wait_present
import dianxiaomi
import shopee_local as shopee
import config

def main():
    driver = dianxiaomi.init_driver()
    try:
        dianxiaomi.login(driver)
        driver.get("https://www.dianxiaomi.com/web/shopeeGlobal/add")
        wait_present(driver, '//*[@id="basicInfo"]', timeout=15)
        import pandas as pd
        df = pd.read_excel(
            config.SHOPEE_PRODUCTS_XLSX,
            sheet_name="shopee_product",
            engine="openpyxl",
        )
        df_skus = pd.read_excel(
            config.SHOPEE_PRODUCTS_XLSX,
            sheet_name="shopee_images",
            engine="openpyxl",
        )
        row = df.iloc[0]
        title = row["title"]
        desc = row["desc"]
        img_list = [row[c] for c in df.columns if c.startswith("img") and pd.notna(row[c])]
        shopee.choose_category(driver, title, desc, img_list)
        shopee.fill_sku_table(driver, row["product_id"], df_skus)
        input("表单已填，回车结束测试...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
