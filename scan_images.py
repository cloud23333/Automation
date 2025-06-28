# -*- coding: utf-8 -*-
"""
import_gallery.py  –  Excel → SKU & 图库扫描
------------------------------------------------
1. Excel 三列：商品编码 / 成本价 / 重量   → sku
2. 扫描目录：深度 >3 为选项图(option)
   • 归一 ^ → *、× → X
   • 同路径冲突则 update img_role / option_tag / sku_code
"""

import os, pandas as pd, pymysql
from os.path import abspath, join, normpath

# === 路径 & 数据库账号 ========================================================
EXCEL_PATH = (
    r"\\Desktop-inv4qoc\图片数据\Temu_半托项目组\倒表格\数据\JST_DATA\Single.xlsx"
)
ROOT_PATH = r"D:\图片录入测试"

DB_CFG = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)
# ============================================================================

IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff")

# 中文关键字 → tag_code
OPTION_TAG_MAP = {
    "带数量": "qty",
    "不带数量": "noqty",
}


# ---------- 工具 -------------------------------------------------------------
def normalize_sku(raw: str) -> str:
    """SKU 编码标准化"""
    return (
        ""
        if raw is None
        else (raw.strip().upper().replace("_", "*").replace(" ", ""))
    )


def db():  # 连接
    return pymysql.connect(**DB_CFG)


# ---------- product_folder ---------------------------------------------------
def ensure_folder(cur, folder_code, style_name, sku_folder) -> int:
    cur.execute(
        "SELECT id FROM product_folder "
        "WHERE folder_code=%s AND style_name=%s AND sku_folder=%s",
        (folder_code, style_name, sku_folder),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO product_folder(folder_code,style_name,sku_folder) "
        "VALUES (%s,%s,%s)",
        (folder_code, style_name, sku_folder),
    )
    return cur.lastrowid


# ---------- option_tag_dict --------------------------------------------------
def ensure_option_tags(cur):
    cur.execute(
        """CREATE TABLE IF NOT EXISTS option_tag_dict(
                     tag_code VARCHAR(32) PRIMARY KEY,
                     tag_name VARCHAR(64) NOT NULL
                   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    for zh, code in OPTION_TAG_MAP.items():
        cur.execute(
            "INSERT IGNORE INTO option_tag_dict(tag_code,tag_name) VALUES (%s,%s)",
            (code, zh),
        )


# ---------- ① Excel → sku ----------------------------------------------------
def import_sku():
    df = pd.read_excel(
        EXCEL_PATH,
        usecols=["商品编码", "商品名称", "成本价", "重量"],
        dtype={"商品编码": str},
    )
    df["成本价"] = pd.to_numeric(df["成本价"], errors="coerce").fillna(0.0)
    df["重量"] = pd.to_numeric(df["重量"], errors="coerce").fillna(0.0)

    conn, cur = db(), None
    try:
        cur = conn.cursor()
        for _, r in df.iterrows():
            sku = normalize_sku(r["商品编码"])
            if not sku:
                continue
            name = str(r["商品名称"]).strip() if pd.notna(r["商品名称"]) else ""
            cost = float(r["成本价"])
            wt = float(r["重量"])
            cur.execute(
                """
                INSERT INTO sku (sku_code, product_name, cost_price, weight_kg)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                product_name = VALUES(product_name),
                cost_price   = VALUES(cost_price),
                weight_kg    = VALUES(weight_kg)
                """,
                (sku, name, cost, wt),
            )
        conn.commit()
        print(f"[SKU] 导入/更新 {len(df)} 行")
    finally:
        if cur:
            cur.close()
        conn.close()


# ---------- ② 扫描图库 -------------------------------------------------------
def classify(parts, fname):
    """返回 (img_role, option_tag)"""
    if len(parts) > 3:  # 深度>3 为选项图
        tag = next((v for k, v in OPTION_TAG_MAP.items() if k in parts), None)
        return "option", tag
    if "详情图" in fname:
        return "detail", None
    if "尺寸图" in fname:
        return "size", None
    return "main", None


def scan_and_link():
    conn, cur = db(), None
    cnt_option = cnt_link = 0
    try:
        cur = conn.cursor()
        ensure_option_tags(cur)

        for root, _, files in os.walk(ROOT_PATH):
            rel_dir = os.path.relpath(root, ROOT_PATH)
            if rel_dir == ".":  # 跳过根目录
                continue
            parts = rel_dir.split(os.sep)
            if len(parts) < 3:  # 需 ≥ BXG/风格/SKU
                continue

            folder_id = ensure_folder(cur, *parts[:3])

            for fn in files:
                if not fn.lower().endswith(IMG_EXT):
                    continue
                role, tag = classify(parts, fn)
                file_path = normpath(abspath(join(root, fn)))
                file_path = file_path.replace("/", "\\")
                sku_code = (
                    normalize_sku(os.path.splitext(fn)[0]) if role == "option" else None
                )

                # 插入/更新 image_asset
                cur.execute(
                    """
                    INSERT INTO image_asset(folder_id,file_path,img_role,option_tag,sku_code)
                    VALUES (%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                      img_role   = VALUES(img_role),
                      option_tag = VALUES(option_tag),
                      sku_code   = VALUES(sku_code)
                """,
                    (folder_id, file_path, role, tag, sku_code),
                )
                if cur.rowcount and role == "option":
                    cnt_option += 1

                # 选项图 → 回填 sku.folder_id
                if sku_code:
                    cur.execute(
                        """
                        UPDATE sku SET folder_id=%s
                        WHERE sku_code=%s AND (folder_id IS NULL OR folder_id<>%s)
                    """,
                        (folder_id, sku_code, folder_id),
                    )
                    if cur.rowcount:
                        cnt_link += 1

        conn.commit()
        print(f"[IMG] 新增/更新选项图 {cnt_option} 张")
        print(f"[MAP] SKU ↔ folder 绑定 {cnt_link} 条")
    finally:
        if cur:
            cur.close()
        conn.close()


# ---------- 主入口 ------------------------------------------------------------
if __name__ == "__main__":
    import_sku()
    scan_and_link()
    print("✅ import_gallery 完成")
