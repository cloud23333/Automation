from common import wait_click, wait_present
import dianxiaomi, time
import shopee   
import config

def main():
    driver = dianxiaomi.init_driver()
    try:
        dianxiaomi.login(driver)
        driver.get("https://www.dianxiaomi.com/web/shopeeGlobal/add")
        wait_present(driver, '//*[@id="basicInfo"]')
        import pandas as pd
        df = pd.read_excel(config.SHOPEE_PRODUCTS_XLSX, engine="openpyxl")
        row = df.iloc[0]
        title = row['title']
        desc = row['desc']
        img_list = [row[c] for c in df.columns if c.startswith('img') and pd.notna(row[c])]
        shopee.choose_category(driver, title, desc, img_list)
        input("表单已填，回车结束测试...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
