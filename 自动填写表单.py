from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def close_all_close_buttons(driver, try_times=5):
    """
    多次查找并点击页面上所有含‘关闭’文字的按钮
    """
    for _ in range(try_times):
        close_buttons = driver.find_elements(By.XPATH, '//button[contains(text(), "关闭")]')
        if not close_buttons:
            break
        for btn in close_buttons:
            try:
                btn.click()
                time.sleep(0.3)
            except Exception:
                pass
        time.sleep(0.5)

# 账号密码
username = "Cloud23333"
password = "Dzj9876543"

# 1. 启动浏览器，进入登录页
driver = webdriver.Chrome()
driver.get("https://www.dianxiaomi.com/")
time.sleep(1)

# 2. 自动填写账号和密码
driver.find_element(By.ID, "exampleInputName").send_keys(username)
driver.find_element(By.ID, "exampleInputPassword").send_keys(password)

# 3. 暂停让用户手动输入验证码
input("请在浏览器手动输入验证码，然后回车继续...")

# 4. 登录完成后等待跳转
time.sleep(5)

# 5. 跳转到“线上产品”页面（产品创建页）
driver.get("https://www.dianxiaomi.com/mercadoGlobalProduct/add.htm")
time.sleep(3)

# 6. 自动关闭弹窗
close_all_close_buttons(driver, try_times=2)

# 7. 选择全球账号“子杰”
select_elem = driver.find_element(By.ID, "mercadoShopId")
shop_select = Select(select_elem)
shop_select.select_by_visible_text("子杰")
time.sleep(0.5)

# 8. 点击“全选”checkbox，优先点label，如不行点input
try:
    # 推荐方式，优先点击label（部分网站只有label触发事件）
    label = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//label[contains(., "全选")]'))
    )
    label.click()
    print("已点击label全选")
except Exception as e:
    print("label无法点击，尝试input...")
    checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//label[contains(., "全选")]/input[@type="checkbox"]'))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
    checkbox.click()
    print("已点击input全选")
time.sleep(0.5)

# 9. 分类选择“Beads(珠子)”
category_select = Select(driver.find_element(By.ID, "categoryHistoryId"))
category_select.select_by_visible_text("Beads(珠子)")
time.sleep(0.5)

# 10. 输入“Generic”
attribute_input = driver.find_element(By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input')
attribute_input.clear()
attribute_input.send_keys("Generic")
time.sleep(0.5)

# 1. 选择下拉菜单第二项
attr_select = Select(driver.find_element(By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select'))
attr_select.select_by_index(1)
time.sleep(0.5)

# 2. 填写“beads”
input_beads = driver.find_element(By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input')
input_beads.clear()
input_beads.send_keys("beads")
time.sleep(0.5)

input("流程结束，按回车关闭浏览器...")

driver.quit()
