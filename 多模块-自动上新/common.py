import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import config


def wait_click(driver, xpath, timeout=config.WAIT_SEC):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )


def wait_present(driver, xpath, timeout=config.WAIT_SEC):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )


def wait_visible(driver, xpath, timeout=config.WAIT_SEC):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.XPATH, xpath))
    )


def safe_input(driver, xpath, value, clear_first=True):
    try:
        elem = wait_present(driver, xpath, timeout=config.ATTR_TIMEOUT)
        if clear_first:
            elem.clear()
        elem.send_keys(value)
    except TimeoutException:
        print(f"⚠️ skip attr: {xpath}")


def wait_present_scroll(driver, xpath, timeout=config.WAIT_SEC):
    end = time.time() + timeout
    while time.time() < end:
        try:
            return driver.find_element(By.XPATH, xpath)
        except Exception:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(config.SLEEP_SHORT)
    raise TimeoutException(f"element not found: {xpath}")


def fill_description(driver, text):
    try:
        area = wait_present_scroll(
            driver,
            '//*[contains(@class,"descriptionTextarea") or contains(@class,"note-editable")]',
            timeout=5,
        )
        area.clear()
        area.send_keys(text)
    except TimeoutException:
        print("⚠️ description editor not found")


def close_all_close_buttons(driver, try_times=2):
    for _ in range(try_times):
        close_buttons = driver.find_elements(
            By.XPATH, '//button[contains(text(), "关闭")]'
        )
        if not close_buttons:
            break
        for btn in close_buttons:
            try:
                btn.click()
                time.sleep(config.SLEEP_SHORT)
            except Exception:
                pass
        time.sleep(0.5)
