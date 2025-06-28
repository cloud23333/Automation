# -*- coding: utf-8 -*-
"""
build_product_and_image_excel.py
------------------------------------------------
• 读取 MySQL(product_folder / sku / image_asset)
• 计算 global_price = 计算器逻辑(最高成本价)
• DeepSeek-GPT 生成 title / desc
• 导出 products.xlsx, images.xlsx
"""

import os, json, re, time
import pandas as pd, pymysql
from openai import OpenAI

# =============== 可 调 参 数 ==================================================
DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

ROOT_PATH = r"D:\图片录入测试"  # 拼绝对路径
DEEPSEEK_API_KEY = "sk-c73cba2525b74adbb76c271fc7080857"  # ← 换成真实 key
GPT_MODEL = "deepseek-chat"

# 价格计算器常量 —— 若要调整只改这里
FF = 4.2  # Fulfillment Fee
COMMISSION = 0.08  # 平台佣金
GROSS_MARGIN = 0.25  # 目标毛利率 (25%)
TARGET_REVENUE_RMB = 0.0  # 若有固定额外营收目标(¥)，填数，否则 0
RMB_TO_USD = 0.13927034  # 汇率
MIN_PRICE_USD = 3.0  # 美金最低售价
# ============================================================================


# ---------- 数据库 ------------------------------------------------------------
def db():
    return pymysql.connect(**DB_CONF)


def load_data():
    conn = db()
    try:
        prod = pd.read_sql(
            "SELECT id folder_id,folder_code,style_name,sku_folder "
            "FROM product_folder",
            conn,
        )
        sku = pd.read_sql(
            "SELECT sku_code,product_name,cost_price,weight_kg,folder_id " "FROM sku",
            conn,
        )
        img = pd.read_sql(
            "SELECT folder_id,file_path,img_role,option_tag,sku_code "
            "FROM image_asset",
            conn,
        )
        return prod, sku, img
    finally:
        conn.close()


# ---------- DeepSeek GPT ------------------------------------------------------
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def _strip_fence(txt: str) -> str:
    return re.sub(r"^```[\s\S]*?\n|\n?```$", "", txt.strip())


def gpt_title_desc(names: list[str], tries: int = 3) -> tuple[str, str]:
    sys = "You are an e-commerce copywriter."
    user = (
        "Generate an English title (≤55 chars) and description (≤300 chars) for "
        "hematite beads listed below.\nProducts: "
        + "; ".join(names[:20])
        + '\nReturn JSON: {"title":"...", "desc":"..."}'
    )
    for i in range(tries):
        try:
            rsp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
                stream=False,
            )
            data = json.loads(_strip_fence(rsp.choices[0].message.content))
            return data.get("title", "")[:80], data.get("desc", "")[:300]
        except Exception as e:
            print(f"[GPT] attempt {i+1}/{tries} failed: {e}")
            time.sleep(1.5)
    return "", ""


# ---------- 价格计算器 ---------------------------------------------------------
def calc_price_usd(max_cost_rmb: float) -> float:
    """由最高成本价(¥)得到最终 USD 售价"""
    pc = max_cost_rmb
    if pc == 0:
        return MIN_PRICE_USD
    # 公式同 GUI 逻辑
    p1 = (pc + FF) / (1 - GROSS_MARGIN - COMMISSION)
    p2 = (TARGET_REVENUE_RMB + pc + FF) / (1 - COMMISSION)
    price_rmb = max(p1, p2)
    price_usd = max(MIN_PRICE_USD, round(price_rmb * RMB_TO_USD, 2))
    return price_usd


# ---------- 生成 products.xlsx -------------------------------------------------
def make_products(prod_df, sku_df):
    rows = []
    next_id = 10001
    for _, pf in prod_df.iterrows():
        subset = sku_df[sku_df.folder_id == pf.folder_id]
        if subset.empty:
            continue
        price_usd = calc_price_usd(subset.cost_price.max())
        title, desc = gpt_title_desc(subset.product_name.dropna().unique().tolist())

        rows.append(
            dict(
                id=next_id,
                title=title,
                desc=desc,
                global_price=price_usd,
                category="Beads(珠子)",
                attribute="Generic",
                attr_value="Beads",
                folder_id=pf.folder_id,
            )
        )
        next_id += 1

    df = pd.DataFrame(rows)
    df.to_excel("products.xlsx", index=False)
    print(f"[OK] products.xlsx 生成 {len(df)} 行")
    return df


# ---------- 生成 images.xlsx ---------------------------------------------------
def make_images(prod_df: pd.DataFrame, img_df: pd.DataFrame):
    img_df["abs_path"] = img_df.file_path.apply(
        lambda p: os.path.join(ROOT_PATH, p).replace("\\", "/")
    )
    grp = img_df.groupby("folder_id")

    out_rows = []
    img_idx = 1
    for _, pr in prod_df.iterrows():
        fid = pr.folder_id
        if fid not in grp.groups:
            continue
        g = grp.get_group(fid)
        main = g[g.img_role == "main"].abs_path.tolist()
        detail = g[g.img_role == "detail"].abs_path.tolist()
        size = g[g.img_role == "size"].abs_path.tolist()
        opts = g[g.img_role == "option"]

        for _, r in opts.iterrows():
            pics = [r.abs_path] + main + detail + size
            pics = pics[:10]
            row = {
                "id": img_idx,
                "product_id": pr.id,
                "size": "",
                "pack": "",
                "color": "",
                "sku": r.sku_code or "",
            }
            for i, p in enumerate(pics, 1):
                row[f"img_path{i}"] = p
            out_rows.append(row)
            img_idx += 1

    df = pd.DataFrame(out_rows)
    df.to_excel("images.xlsx", index=False)
    print(f"[OK] images.xlsx   生成 {len(df)} 行")


# ---------- 主程 --------------------------------------------------------------
if __name__ == "__main__":
    prod, sku, img = load_data()
    prod_out = make_products(prod, sku)
    make_images(prod_out, img)
    print("✅ 全部完成")
