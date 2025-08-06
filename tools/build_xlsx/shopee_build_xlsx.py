from __future__ import annotations
import os, re
from pathlib import Path
import pandas as pd, pymysql
from openpyxl import Workbook

DATA_DIR = Path(r"C:\Users\Administrator\Documents\Mecrado\Automation\数据")
SHOPEE_PRODUCTS_XLSX = Path(os.getenv("SHOPEE_PRODUCTS_XLSX", DATA_DIR / "shopee_products.xlsx"))
SHOPEE_FOLDER_TXT = Path(r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\build_xlsx\txt文件\shopee_folders.txt")

DB = dict(host="localhost", user="root", password="123456", database="temu_gallery",
          charset="utf8mb4", autocommit=False)

def db():
    return pymysql.connect(**DB)

def to_str_id(col: pd.Series) -> pd.Series:
    return pd.to_numeric(col, errors="coerce").astype("Int64").astype(str)

def fetch():
    conn = db()
    try:
        p = pd.read_sql("SELECT id AS folder_id, sku_folder FROM product_folder", conn)
        s = pd.read_sql("SELECT sku_code, folder_id, color_desc, size_desc FROM sku", conn)
        i = pd.read_sql("SELECT folder_id, sku_code, file_path, img_role FROM image_asset", conn)
    finally:
        conn.close()
    p["folder_id"] = to_str_id(p.folder_id)
    s["folder_id"] = to_str_id(s.folder_id)
    i["folder_id"] = to_str_id(i.folder_id)
    s["sku_code"] = s.sku_code.str.lower()
    i["sku_code"] = i.sku_code.str.lower()
    return p, s, i

def norm(txt: str) -> str:
    return re.sub(r"\s+", "", txt or "").lower()

def build(prod, sku, img):
    wb = Workbook()
    ws_p = wb.active
    ws_p.title = "shopee_product"
    ws_p.append(["product_id", "title", "desc", *[f"img{n}" for n in range(1, 11)]])
    ws_i = wb.create_sheet("shopee_images")
    ws_i.append(["product_id", "sku_code", "size", "color", "img_path"])

    sg, ig = sku.groupby("folder_id"), img.groupby("folder_id")
    pid = 10001

    for pf in prod.itertuples():
        pics = []
        if pf.folder_id in ig.groups:
            g = ig.get_group(pf.folder_id)
            pics = (g[g.img_role == "main"].file_path.tolist() +
                    g[g.img_role == "detail"].file_path.tolist())[:10]
        ws_p.append([pid, pf.sku_folder, pf.sku_folder, *pics, *[""] * (10 - len(pics))])

        color_img = {}
        if pf.folder_id in ig.groups:
            opt = ig.get_group(pf.folder_id)
            opt = opt[opt.img_role == "option"].merge(
                sku[["sku_code", "color_desc"]], on="sku_code", how="left")
            for r in opt.itertuples():
                if r.color_desc and r.color_desc not in color_img:
                    color_img[r.color_desc] = r.file_path

        if pf.folder_id in sg.groups:
            gsku = sg.get_group(pf.folder_id).copy()
            sizes = sorted(gsku.size_desc.astype(str).unique(), key=lambda x: (len(x), x))
            base_size = sizes[0]
            base_colors = gsku[gsku.size_desc.astype(str) == base_size].color_desc.unique().tolist()

            for size in sizes:
                for color in base_colors:
                    subset = gsku[(gsku.size_desc.astype(str) == size) & (gsku.color_desc == color)]
                    if subset.empty:
                        subset = gsku[(gsku.size_desc.astype(str) == base_size) & (gsku.color_desc == color)]
                    if subset.empty:
                        continue
                    row = subset.iloc[0]
                    ws_i.append([pid, row.sku_code, size, color, color_img.get(color, "")])

        pid += 1
    return wb

def main():
    prod, sku, img = fetch()

    if SHOPEE_FOLDER_TXT.exists():
        raw = SHOPEE_FOLDER_TXT.read_text(encoding="utf-8-sig").splitlines()
        want = {norm(Path(x.strip()).name) for x in raw if x.strip()}
        want_id = {w for w in want if w.isdigit()}
        prod["sku_folder_norm"] = prod.sku_folder.apply(norm)
        prod = prod[prod.sku_folder_norm.isin(want) | prod.folder_id.isin(want_id)]

    sku = sku[sku.folder_id.isin(prod.folder_id.unique())]
    img = img[img.folder_id.isin(prod.folder_id.unique())]

    build(prod, sku, img).save(SHOPEE_PRODUCTS_XLSX)

if __name__ == "__main__":
    main()
