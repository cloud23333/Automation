from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def wait_click(driver, xpath, timeout=10):
    WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    ).click()

def wait_send_keys(driver, xpath, text, timeout=10):
    elem = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.XPATH, xpath))
    )
    elem.clear()
    elem.send_keys(text)

def login(driver, username, password):
    wait_send_keys(driver, '//*[@id="exampleInputName"]', username)
    wait_send_keys(driver, '//*[@id="exampleInputPassword"]', password)
    
    # 点击登录按钮
    wait_click(driver, '//*[@id="login-btn" or @id="loginBtn" or @type="submit"]', timeout=5)

    # 人工确认登录完成
    input("请完成登录和验证码操作，确认成功后按回车继续……")

