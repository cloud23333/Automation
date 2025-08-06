from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os, warnings, logging, time
import config, common


def init_driver():
    chrome_opts = Options()
    chrome_opts.add_argument("--log-level=3")
    chrome_opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = Service(log_path=os.devnull)
    warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")
    logging.getLogger("absl").setLevel(logging.ERROR)
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    return driver


def login(driver):
    driver.get("https://www.dianxiaomi.com/")
    time.sleep(1)
    username = config.USERNAME
    password = config.PASSWORD
    if not username or not password:
        raise RuntimeError(
            "Environment variables DXM_USERNAME and DXM_PASSWORD must be set"
        )

    common.wait_present(driver, '//*[@id="exampleInputName"]').send_keys(username)
    common.wait_present(driver, '//*[@id="exampleInputPassword"]').send_keys(password)
    input("验证码后回车...")
    time.sleep(1)
