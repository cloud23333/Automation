from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os, warnings, logging, time
import config, common
from selenium.webdriver import ChromeOptions, Chrome, ChromeService


def init_driver():
    chrome_opts = ChromeOptions()
    chrome_opts.binary_location = r"chrome\chrome.exe"
    chrome_opts.add_argument(r"--user-data-dir=chrome\User Data")
    chrome_opts.add_argument("--log-level=3")
    chrome_opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = ChromeService(executable_path=r"chrome\chromedriver.exe")
    warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")
    logging.getLogger("absl").setLevel(logging.ERROR)
    driver = Chrome(service=service, options=chrome_opts)
    return driver


def login(driver):
    driver.get("https://www.dianxiaomi.com/")
    time.sleep(1)
    common.wait_present(driver, '//*[@id="exampleInputName"]').send_keys(
        config.USERNAME
    )
    common.wait_present(driver, '//*[@id="exampleInputPassword"]').send_keys(
        config.PASSWORD
    )
    input("验证码后回车...")
