from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pywinauto

def upload_img_in_one_slot(button_xpath, menu_xpath, img_list):
    for img_path in img_list:
        # 点击上传按钮
        upload_btn = driver.find_element(By.XPATH, button_xpath)
        upload_btn.click()
        time.sleep(0.3)
        # 选择“本地图片”
        local_img_menu = driver.find_element(By.XPATH, menu_xpath)
        local_img_menu.click()
        time.sleep(1)
        # pywinauto操作文件选择窗口
        import pywinauto
        app = pywinauto.Application().connect(title_re="打开|Open")
        dlg = app.window(title_re="打开|Open")
        dlg['Edit'].set_edit_text(img_path)
        dlg['Button'].click()
        time.sleep(2)

def close_all_close_buttons(driver, try_times=2):
    """
    多次查找并点击页面上所有含‘关闭’文字的按钮
    """
    for _ in range(try_times):
        close_buttons = driver.find_elements(
            By.XPATH, '//button[contains(text(), "关闭")]'
        )
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
time.sleep(1)

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
        EC.element_to_be_clickable(
            (By.XPATH, '//label[contains(., "全选")]/input[@type="checkbox"]')
        )
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
    checkbox.click()
    print("已点击input全选")
time.sleep(0.2)

wait = WebDriverWait(driver, 20)
# 基本信息
# 9. 分类选择“Beads(珠子)”
category_select = Select(driver.find_element(By.ID, "categoryHistoryId"))
category_select.select_by_visible_text("Beads(珠子)")
time.sleep(0.5)

# 10. 输入“Generic”

attribute_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[1]/td[2]/input')))

attribute_input.clear()
attribute_input.send_keys("Generic")
time.sleep(0.5)

# 1. 选择下拉菜单第二项
attr_select = Select(
    driver.find_element(
        By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[2]/td[2]/select'
    )
)
attr_select.select_by_index(1)
time.sleep(0.5)

# 2. 填写“beads”
input_beads = driver.find_element(
    By.XPATH, '//*[@id="productAttributeShow"]/table/tbody/tr[3]/td[2]/input'
)
input_beads.clear()
input_beads.send_keys("beads")
time.sleep(0.2)

# 产品信息
# 假设你已经获得了如下变量
product_title = "100Pcs hematite beads "
product_desc = "good beads"
global_price = "3"

# 产品标题
title_input = driver.find_element(By.XPATH, '//*[@id="productTitle"]')
title_input.clear()
title_input.send_keys(product_title)
time.sleep(0.2)

# 产品描述
desc_input = driver.find_element(By.CLASS_NAME, "descriptionTextarea")
desc_input.clear()
desc_input.send_keys(product_desc)
time.sleep(0.2)

# 全球价格
global_price_input = driver.find_element(By.XPATH, '//*[@id="globalPrice"]')
global_price_input.clear()
global_price_input.send_keys(global_price)
time.sleep(0.2)

# 站点价格（全部和全球价格一样）
site_price_inputs = [
    driver.find_element(
        By.XPATH, '//*[@id="sitePriceDiv"]/table/tbody/tr/td[1]/input'
    ),  # 智利
    driver.find_element(
        By.XPATH, '//*[@id="sitePriceDiv"]/table/tbody/tr/td[2]/input'
    ),  # 墨西哥
    driver.find_element(
        By.XPATH, '//*[@id="sitePriceDiv"]/table/tbody/tr/td[3]/input'
    ),  # 巴西
    driver.find_element(
        By.XPATH, '//*[@id="sitePriceDiv"]/table/tbody/tr/td[4]/input'
    ),  # 哥伦比亚
]
for inp in site_price_inputs:
    inp.clear()
    inp.send_keys(global_price)
    time.sleep(0.1)

# 刊登类型
for i in range(1, 5):  # 1到4
    select_elem = driver.find_element(
        By.XPATH, f'//*[@id="siteProductTypeDiv"]/table/tbody/tr/td[{i}]/select'
    )
    select_obj = Select(select_elem)
    select_obj.select_by_index(1)  # 选第2个（下标从0开始）
    time.sleep(0.1)


# 变种参数
# 操作第1行
# 1.1 选择第一个select的第2个选项（index=1）
select_1 = driver.find_element(
    By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[1]/select'
)
Select(select_1).select_by_index(1)
time.sleep(0.5)

# 1.2 依次填写 3, 4, 6, 8 并点击按钮
input_box = driver.find_element(
    By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[3]/input'
)
add_button = driver.find_element(
    By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[1]/td[2]/div[3]/button'
)
for value in ["3", "4", "6", "8"]:
    input_box.clear()
    input_box.send_keys(value)
    add_button.click()
    time.sleep(0.2)

# 操作第2行
# 2.1 选择第二个select的第2个选项
select_2 = driver.find_element(
    By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[1]/select'
)
Select(select_2).select_by_index(1)
time.sleep(0.2)

# 2.2 填写5并点击
input_box_2 = driver.find_element(
    By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[3]/input'
)
add_button_2 = driver.find_element(
    By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[2]/td[2]/div[3]/button'
)
input_box_2.clear()
input_box_2.send_keys("5")
add_button_2.click()
time.sleep(0.2)

# 颜色
# 先等输入框可用

for color in ['Black']:
    color_input = wait.until(EC.presence_of_element_located(
        (By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[3]/td[2]/div[3]/input')
    ))
    add_button = driver.find_element(By.XPATH, '//*[@id="skuParameterList"]/tbody/tr[3]/td[2]/div[3]/button')
    color_input.clear()
    color_input.send_keys(color)
    add_button.click()
    time.sleep(0.2)


# 变种信息
# SKU 填写内容
wait.until(EC.presence_of_element_located(
    (By.XPATH, '//*[@id="mercadoSkuAdd"]/table/tbody/tr[1]/td[4]/input')
    
))
sku_values = [
    "HDS3-3mm",
    "HDS3-4mm",
    "HDS3-6mm",
    "HDS3-8mm"
]

# 等待所有SKU输入框都出现再填
for i, sku in enumerate(sku_values, start=1):
    input_xpath = f'//*[@id="mercadoSkuAdd"]/table/tbody/tr[{i}]/td[4]/input'
    
    wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
    input_elem = driver.find_element(By.XPATH, input_xpath)
    input_elem.clear()
    input_elem.send_keys(sku)
    time.sleep(0.1)

# 点击“UPC”批量设置
#driver.find_element(By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[5]/span[2]/a').click()
# 等弹窗出现
#wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="upcBatchEdit"]')))
# 勾选“随机UPC”第2个radio
#wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="upcBatchEdit"]/div[2]/div/div[2]/table/tbody/tr[4]/td[2]/label[2]/input'))).click()
# 点确定
#wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="upcBatchEdit"]/div[2]/div/div[3]/button[1]'))).click()
#time.sleep(0.5)

# 批量设置“包裹尺寸”
driver.find_element(By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[6]/span[2]/a').click()
wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="skuPackageLength"]')))
driver.find_element(By.XPATH, '//*[@id="skuPackageLength"]').clear()
driver.find_element(By.XPATH, '//*[@id="skuPackageLength"]').send_keys("15")
driver.find_element(By.XPATH, '//*[@id="skuPackageWidth"]').clear()
driver.find_element(By.XPATH, '//*[@id="skuPackageWidth"]').send_keys("12")
driver.find_element(By.XPATH, '//*[@id="skuPackageHeight"]').clear()
driver.find_element(By.XPATH, '//*[@id="skuPackageHeight"]').send_keys("1")
wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'))).click()
time.sleep(0.5)

# 批量设置“重量”
driver.find_element(By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[7]/span[2]/a').click()
wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="skuWeight"]')))
driver.find_element(By.XPATH, '//*[@id="skuWeight"]').clear()
driver.find_element(By.XPATH, '//*[@id="skuWeight"]').send_keys("100")
wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'))).click()
time.sleep(0.5)

# 批量设置“库存”
driver.find_element(By.XPATH, '//*[@id="mercadoSkuAdd"]/table/thead/tr/th[8]/span[2]/a').click()
wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="num2"]')))
driver.find_element(By.XPATH, '//*[@id="num2"]').clear()
driver.find_element(By.XPATH, '//*[@id="num2"]').send_keys("50")
wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="skuListBatchEdit"]/div[2]/div/div[3]/button[1]'))).click()
time.sleep(0.5)

#图片

upload_tasks = [
    {
        "button_xpath": '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[1]/dt/div[1]/button',
        "menu_xpath":   '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[1]/dt/div[1]/ul/li[1]/a',
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\3mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg"
            
        ]
    },
    {
        "button_xpath": '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[2]/dt/div[1]/button',
        "menu_xpath":   '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[2]/dt/div[1]/ul/li[1]/a',
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\4mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg"
        ]
    },
    {
        "button_xpath": '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[3]/dt/div[1]/button',
        "menu_xpath":   '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[3]/dt/div[1]/ul/li[1]/a',
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\6mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg"
        ]
    },
    {
        "button_xpath": '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[4]/dt/div[1]/button',
        "menu_xpath":   '/html/body/form/div/div[11]/div[2]/table/tbody/tr[2]/td[2]/div/dl[4]/dt/div[1]/ul/li[1]/a',
        "image_paths": [
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\选项\8mm.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图1.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图2.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图3.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图4.jpg",
            r"\\Desktop-inv4qoc\图片数据\BTFBES 店铺图片\黑胆石\HDS3\主图5.jpg"
        ]
    }
]

# 逐个上传
for task in upload_tasks:
    upload_img_in_one_slot(task['button_xpath'], task['menu_xpath'], task['image_paths'])

# 附属信息
warranty_select = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="warrantyType"]')))
Select(warranty_select).select_by_index(3)  # 下标从0开始，第4个是3
time.sleep(0.2)

# 等待并点击按钮
button = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/form/div/div[13]/div[2]/button')))
button.click()
time.sleep(0.2)

# 再点下拉菜单中的第1项
menu_item = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/form/div/div[13]/div[2]/ul/li[1]/a')))
menu_item.click()
time.sleep(0.2)


input("流程结束，按回车关闭浏览器...")

driver.quit()
