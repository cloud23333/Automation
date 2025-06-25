import os
import fitz  # PyMuPDF
from pyzbar.pyzbar import decode
from PIL import Image
import re
from tkinter import Tk, filedialog, messagebox


def safe_filename(s):
    s = re.sub(r"[^A-Za-z0-9_-]", "", s)
    return s


def pdf_to_image(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def extract_barcode(img):
    results = decode(img)
    if not results:
        return None
    return results[0].data.decode("utf-8")


def process_pdf(pdf_path):
    img = pdf_to_image(pdf_path)
    barcode = extract_barcode(img)

    if barcode:
        if barcode.startswith("GF"):
            barcode = barcode[-15:]
        else:
            barcode = barcode[-22:]

        safe_barcode = safe_filename(barcode)
        if not safe_barcode:
            print(f"{os.path.basename(pdf_path)} 条码内容全部非法，无法命名")
            return
        new_pdf_path = os.path.join(os.path.dirname(pdf_path), f"{safe_barcode}.pdf")
        if os.path.abspath(pdf_path) == os.path.abspath(new_pdf_path):
            print(f"文件已经是目标文件名，无需重命名")
        else:
            os.rename(pdf_path, new_pdf_path)
            print(f"{os.path.basename(pdf_path)} -> {safe_barcode}.pdf")
    else:
        print(f"{os.path.basename(pdf_path)} 未识别到条码")


def main():
    root = Tk()
    root.withdraw()

    pdf_paths = filedialog.askopenfilenames(
        title="选择PDF文件（可多选）", filetypes=[("PDF Files", "*.pdf")]
    )
    if not pdf_paths:
        messagebox.showinfo("未选择", "未选择任何文件，程序结束。")
        return

    for pdf_path in pdf_paths:
        process_pdf(pdf_path)

    messagebox.showinfo("完成", "全部文件处理完成！")


if __name__ == "__main__":
    main()
