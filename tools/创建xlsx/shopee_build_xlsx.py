from __future__ import annotations
import os, re, logging
from pathlib import Path
import pandas as pd, pymysql
from openpyxl import Workbook

DATA_DIR = Path(r"C:\Users\Administrator\Documents\Mecrado\Automation\数据")
SHOPEE_PRODUCTS_XLSX = Path(os.getenv("SHOPEE_PRODUCTS_XLSX", DATA_DIR / "shopee_products.xlsx"))
SHOPEE_FOLDER_TXT = Path(r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\创建xlsx\txt文件\shopee_folders.txt")
LOG_FILE = Path(os.getenv("SHOPEE_BUILD_LOG", DATA_DIR / "shopee_build.log"))
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s: %(message)s")

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

def build(lines, prod, sku, img):
    wb = Workbook()
    ws_p = wb.active
    ws_p.title = "shopee_product"
    ws_p.append(["product_id", "title", "desc", *[f"img{n}" for n in range(1, 11)]])
    ws_i = wb.create_sheet("shopee_images")
    ws_i.append(["product_id", "sku_code", "size", "color", "img_path"])

    prod = prod.copy()
    prod["sku_folder_norm"] = prod.sku_folder.apply(norm)
    prod_norm = {r.sku_folder_norm: r for r in prod.itertuples()}
    prod_id = {r.folder_id: r for r in prod.itertuples()}
    sg, ig = sku.groupby("folder_id"), img.groupby("folder_id")
    pid = 10001

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        name = Path(raw).name
        key_norm = norm(name)
        key_id = name if name.isdigit() else None
        pf = None
        if key_id and key_id in prod_id:
            pf = prod_id[key_id]
        elif key_norm in prod_norm:
            pf = prod_norm[key_norm]

        if pf is None:
            logging.error(f"Folder not found: {raw}")
            ws_p.append([pid, name, "", *[""] * 10])
            ws_i.append([pid, "", "", "", ""])
            pid += 1
            continue
        pics = []
        if pf.folder_id in ig.groups:
            g = ig.get_group(pf.folder_id)
            pics = (g[g.img_role == "main"].file_path.tolist() +
                    g[g.img_role == "detail"].file_path.tolist())[:10]
        else:
            logging.warning(f"No images for folder {pf.folder_id} ({raw})")
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
            uniq = gsku.drop_duplicates("sku_code")
            if uniq.empty:
                logging.warning(f"No SKUs for folder {pf.folder_id} ({raw})")
                ws_i.append([pid, "", "", "", ""])
            else:
                for row in uniq.itertuples():
                    ws_i.append([
                        pid,
                        row.sku_code,
                        row.size_desc,
                        row.color_desc,
                        color_img.get(row.color_desc, ""),
                    ])
        else:
            logging.warning(f"No SKUs for folder {pf.folder_id} ({raw})")
            ws_i.append([pid, "", "", "", ""])

        pid += 1
    return wb

def main():
    prod, sku, img = fetch()

    if SHOPEE_FOLDER_TXT.exists():
        lines = [x for x in SHOPEE_FOLDER_TXT.read_text(encoding="utf-8-sig").splitlines()]
    else:
        lines = prod.sku_folder.tolist()        

    build(lines, prod, sku, img).save(SHOPEE_PRODUCTS_XLSX)

if __name__ == "__main__":
    main()
