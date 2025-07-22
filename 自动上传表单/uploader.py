import time
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
import pyperclip
import logging

def get_open_dialog():
    handles = findwindows.find_windows(title_re="打开|Open", class_name="#32770")
    if not handles:
        raise RuntimeError("未找到文件对话框！")
    return Application().connect(handle=handles[0]).window(handle=handles[0])

def upload_images_dialog(paths):
    dlg = get_open_dialog()
    paths_str = '"{}"'.format('" "'.join(paths))
    pyperclip.copy(paths_str)
    dlg["Edit"].click_input()
    send_keys('^v')
    time.sleep(0.5)
    dlg["Button"].click()
    time.sleep(2)
