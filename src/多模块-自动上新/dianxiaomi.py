from selenium.webdriver import Chrome, ChromeOptions, ChromeService
import os, warnings, logging, time, config, common

def init_driver():
    opts = ChromeOptions()
    opts.binary_location = r"chrome\chrome.exe"
    opts.add_argument(r"--user-data-dir=chrome\User Data")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = ChromeService(executable_path=r"chrome\chromedriver.exe", log_path=os.devnull)
    warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")
    logging.getLogger("absl").setLevel(logging.ERROR)
    return Chrome(service=service, options=opts)

def login(driver):
    driver.get("https://www.dianxiaomi.com/")
    time.sleep(1)
    common.wait_present(driver, '//*[@id="exampleInputName"]').send_keys(config.USERNAME)
    common.wait_present(driver, '//*[@id="exampleInputPassword"]').send_keys(config.PASSWORD)
    input("验证码后回车...")
