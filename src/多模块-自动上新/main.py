# 运行 Mercado
# cd C:\Users\Administrator\Documents\Mecrado\Automation\src\多模块-自动上新
# python main.py --platform=mercado

# 运行 Shopee
# python main.py --platform=shopee


import argparse, importlib
from contextlib import suppress
import dianxiaomi

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=["mercado", "shopee"])
    args = parser.parse_args()

    module = importlib.import_module(args.platform)
    driver = dianxiaomi.init_driver()
    try:
        dianxiaomi.login(driver)
        module.run(driver)
        input("全部产品上传完毕，回车退出...")
    finally:
        with suppress(Exception):
            driver.quit()

if __name__ == "__main__":
    main()
