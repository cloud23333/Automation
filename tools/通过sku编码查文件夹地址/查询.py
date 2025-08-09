from __future__ import annotations
import os, pandas as pd
from sqlalchemy import create_engine, text, bindparam

DB_URL = "mysql+pymysql://root:123456@localhost/temu_gallery?charset=utf8mb4"
TXT_PATH = r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\通过sku编码查文件夹地址\txt\sku编码.txt"
ROOT = r"\\Desktop-inv4qoc\图片数据\整理图库"
OUT = r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\通过sku编码查文件夹地址\xlsx\sku_folders.xlsx"

SQL_FROM_SKU = """
SELECT s.sku_code, pf.folder_code, pf.style_name, pf.sku_folder
FROM sku s
JOIN product_folder pf ON pf.id = s.folder_id
WHERE s.sku_code IN :skus
"""

SQL_FROM_IMAGE = """
SELECT ia.sku_code, pf.folder_code, pf.style_name, pf.sku_folder
FROM image_asset ia
JOIN product_folder pf ON pf.id = ia.folder_id
WHERE ia.sku_code IN :skus
"""

def load_skus(path: str) -> list[str]:
    skus = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                skus.append(s)
    return sorted(set(skus))

def query_folders(engine, skus: list[str]) -> pd.DataFrame:
    if not skus:
        return pd.DataFrame(columns=["sku_code","folder_code","style_name","sku_folder"])
    with engine.begin() as conn:
        params = {"skus": bindparam("skus", expanding=True)}
        df1 = pd.read_sql(text(SQL_FROM_SKU).bindparams(params["skus"]), conn, params={"skus": skus})
        df2 = pd.read_sql(text(SQL_FROM_IMAGE).bindparams(params["skus"]), conn, params={"skus": skus})
    df = pd.concat([df1, df2], ignore_index=True)
    df.drop_duplicates(subset=["sku_code","folder_code","style_name","sku_folder"], inplace=True)
    return df

def add_folder_path(df: pd.DataFrame) -> pd.DataFrame:
    df["folder_path"] = df.apply(
        lambda r: os.path.join(ROOT, str(r["folder_code"]), str(r["style_name"]), str(r["sku_folder"] or "")),
        axis=1,
    )
    return df

if __name__ == "__main__":
    engine = create_engine(DB_URL, pool_recycle=3600, future=True)
    skus = load_skus(TXT_PATH)
    df = query_folders(engine, skus)
    df = add_folder_path(df)
    df = df[["sku_code","folder_code","style_name","sku_folder","folder_path"]].sort_values(["sku_code"])
    df.to_excel(OUT, index=False)
    print(f"已生成: {OUT}")
