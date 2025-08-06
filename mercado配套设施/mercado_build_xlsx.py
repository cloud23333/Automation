from __future__ import annotations
import os, re, json, time, sys, argparse
import pandas as pd, pymysql
from openpyxl import Workbook

DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

def db():
    return pymysql.connect(**DB_CONF)

def fetch_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    conn = db()
    try:
        prod = pd.read_sql(
            "SELECT id AS folder_id, folder_code, style_name, sku_folder "
            "FROM product_folder", conn
        )
        sku = pd.read_sql(
            "SELECT sku_code, product_name, cost_price, weight_kg, folder_id, "
            "qty_desc, color_desc, size_desc, material_desc "
            "FROM sku", conn
        )
        img = pd.read_sql(
            "SELECT folder_id, file_path, img_role, option_tag, sku_code "
            "FROM image_asset", conn
        )
    finally:
        conn.close()
    sku["sku_code"] = sku.sku_code.str.upper()
    img["sku_code"] = img.sku_code.str.upper()
    return prod, sku, img

def first_in_color(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(["color_desc"])

def build_workbook(prod: pd.DataFrame, sku: pd.DataFrame, img: pd.DataFrame):
    wb = Workbook()
    ws_prod = wb.active
    ws_prod.title = "products"
    ws_prod.append([
        "product_id","material","title","description",
        *[f"img{i}" for i in range(1,10)],
        "sku_imgs","video","price","weight_g","stock_qty"
    ])
    ws_var = wb.create_sheet("variants")
    ws_var.append(["product_id","sku_code","color","size"])

    img_grp = img.groupby("folder_id")
    sku_grp = sku.groupby("folder_id")
    pid = 10001
    for pf in prod.itertuples():
        if pf.folder_id not in sku_grp.groups or pf.folder_id not in img_grp.groups:
            continue
        g_sku = sku_grp.get_group(pf.folder_id)
        g_img = img_grp.get_group(pf.folder_id)
        main_imgs = g_img[g_img.img_role=="main"].file_path.tolist()[:9]
        detail_imgs = g_img[g_img.img_role=="detail"].file_path.tolist()
        imgs = (main_imgs + detail_imgs)[:9]
        opt_imgs = g_img[g_img.img_role == "option"]
        opt_imgs = opt_imgs[opt_imgs.sku_code.isin(g_sku.sku_code)]
        if not opt_imgs.empty:
            opt_imgs = opt_imgs.merge(
                g_sku[["sku_code", "color_desc"]], on="sku_code", how="left"
            )
            color_imgs = opt_imgs.drop_duplicates(["color_desc"]).file_path.tolist()
        else:
            color_imgs = []
        sku_imgs = ";".join(color_imgs)
        material = ", ".join(filter(None,g_sku.material_desc.dropna().unique()[:1])) or "Unknown"
        title = pf.sku_folder
        desc = pf.sku_folder
        price = round((g_sku.cost_price.max() or 0)*1.5,2)
        weight = int((g_sku.weight_kg.mean() or 0)*1000)
        stock = 100
        row = [
            pid, material, title, desc,
            *imgs, *[""]*(9-len(imgs)),
            sku_imgs,"",price,weight,stock
        ]
        ws_prod.append(row)
        for r in g_sku.itertuples():
            ws_var.append([pid,r.sku_code,r.color_desc,r.size_desc])
        pid += 1
    return wb

def main():
    out = r"shopee_output.xlsx"
    prod, sku, img = fetch_data()
    wb = build_workbook(prod, sku, img)
    wb.save(out)
    print("saved:",out)

if __name__ == "__main__":
    main()
