import os, time
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
from selenium.common.exceptions import TimeoutException
import common, config


def _open_uploader(driver, button_xpath, menu_xpath, retries=3):
    for _ in range(retries):
        try:
            btn = common.wait_click(driver, button_xpath)
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            btn.click()
            common.wait_click(driver, menu_xpath).click()
        except Exception:
            time.sleep(config.SLEEP_SHORT)

        for _ in range(20):
            handles = findwindows.find_windows(
                title_re="打开|Open", class_name="#32770"
            )
            if handles:
                dlg = (
                    Application(backend="win32")
                    .connect(handle=handles[0])
                    .window(handle=handles[0])
                )
                dlg.wait("ready", timeout=10)
                return dlg
            time.sleep(0.3)

    raise TimeoutException("文件对话框未弹出，已重试多次")


def _upload_in_dialog(dlg, paths):
    dirpath = os.path.dirname(paths[0])
    dlg["Edit"].set_edit_text(dirpath)
    send_keys("{ENTER}")
    time.sleep(config.SLEEP_SHORT)
    if len(paths) == 1:
        dlg["Edit"].set_edit_text(os.path.basename(paths[0]))
    else:
        dlg["Edit"].set_edit_text(" ".join(f'"{os.path.basename(p)}"' for p in paths))
    dlg["Button"].click()
    time.sleep(2)


def upload_img_in_one_slot(driver, button_xpath, menu_xpath, img_list):
    img_list = [p for p in img_list if os.path.exists(p)]
    if not img_list:
        return
    done = set()
    for p in img_list:
        d = os.path.dirname(p)
        if d in done:
            continue
        group = [x for x in img_list if os.path.dirname(x) == d]
        dlg = _open_uploader(driver, button_xpath, menu_xpath)
        _upload_in_dialog(dlg, group)
        done.add(d)
