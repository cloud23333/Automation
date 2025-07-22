import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import logging
import config
from utils import wait_click, login  # 引入login函数
from fill_forms import fill_basic_info, fill_variants, fill_sku_details
from uploader import upload_images_dialog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

df_products = pd.read_excel(config.PRODUCTS_FILE)
df_images = pd.read_excel(config.IMAGES_FILE)

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 10)

driver.get(config.LOGIN_URL)
login(driver, config.USERNAME, config.PASSWORD)  # 调用登录函数

for _, product_row in df_products.iterrows():
    try:
        product_id = product_row["id"]
        info = {
            "title": product_row["title"],
            "desc": product_row["desc"],
            "global_price": product_row["global_price"],
        }

        images = df_images[df_images["product_id"] == product_id].copy()
        variants = {
            "sizes": images["size"].dropna().unique().tolist(),
            "pack": images["pack"].dropna().unique().tolist(),
            "color": images["color"].dropna().unique().tolist(),
        }

        sku_values = images["sku"].tolist()

        logging.info(f"开始上传：{info['title']}")
        driver.get(config.UPLOAD_URL)

        fill_basic_info(driver, wait, info)
        fill_variants(driver, variants)
        fill_sku_details(driver, sku_values)

        for idx, (_, sku_row) in enumerate(images.iterrows()):
            img_paths = [str(sku_row[f"img_path{i}"]).strip() for i in range(1, 21)
                         if pd.notna(sku_row.get(f"img_path{i}", None)) and str(sku_row[f"img_path{i}"]).strip()]

            if img_paths:
                button_xpath = f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx+1}]/dt/div[1]/button"
                menu_xpath = f"/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[{idx+1}]/dt/div[1]/ul/li[1]/a"

                wait_click(driver, button_xpath)
                wait_click(driver, menu_xpath)
                upload_images_dialog(img_paths)

        wait_click(driver, '/html/body/form/div/div[13]/div[2]/button')
        wait_click(driver, '/html/body/form/div/div[13]/div[2]/ul/li[1]/a')

        logging.info(f"{info['title']} 上传成功")

    except Exception as e:
        logging.error(f"{product_row['title']} 上传失败: {e}")

logging.info("所有产品已上传完成！")
input("按回车退出...")
driver.quit()
