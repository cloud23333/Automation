# -*- coding: utf-8 -*-
"""
build_product_and_image_excel.py
------------------------------------------------
• 读取 MySQL(product_folder / sku / image_asset)
• 按最高成本价计算 global_price，若结果仍是 3 USD (MIN_PRICE_USD)，
  就把成本价成倍放大（×2, ×3 …）直至售价 > 3 USD
• DeepSeek-GPT 生成 title / desc
• 导出 products.xlsx、images.xlsx
  - products.xlsx：每个链接 1 行，含最终售价
  - images.xlsx  ：option 图逐行，sku 在写表格时才附 *n（n > 1）
"""

import os, json, re, time
import pandas as pd, pymysql
from openai import OpenAI

# ===================== 可 调 参 数 =============================================
DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

ROOT_PATH = r"D:\图片录入测试"  # 拼绝对路径
DEEPSEEK_API_KEY = "sk-c73cba2525b74adbb76c271fc7080857"
GPT_MODEL = "deepseek-chat"

# 价格计算常量
FF = 4.2  # Fulfillment Fee
COMMISSION = 0.08  # 平台佣金
GROSS_MARGIN = 0.6  # 目标毛利率 (40 %)
TARGET_REVENUE_RMB = 0.0  # 若需固定额外营收，填数，否则 0
RMB_TO_USD = 0.13927034  # 汇率
MIN_PRICE_USD = 3.0  # 平台最低售价
# ==============================================================================


# -------------------- 数据库 ----------------------------------------------------
def db():
    return pymysql.connect(**DB_CONF)


def load_data():
    """一次性读出三张表"""
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


# -------------------- GPT ------------------------------------------------------
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def _strip_fence(txt: str) -> str:
    """去掉 ```json …``` 围栏"""
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
            )
            data = json.loads(_strip_fence(rsp.choices[0].message.content))
            return data.get("title", "")[:80], data.get("desc", "")[:300]
        except Exception as e:
            print(f"[GPT] attempt {i+1}/{tries} failed: {e}")
            time.sleep(1.5)
    return "", ""


# -------------------- 价格公式 --------------------------------------------------
def calc_price_usd(max_cost_rmb: float) -> float:
    """
    由最高成本价(¥)得到最终 USD 售价
    同 GUI 逻辑：
        p1 = (成本+FF) / (1-毛利率-佣金)
        p2 = (目标营收+成本+FF) / (1-佣金)
        取 max(p1, p2)
    """
    pc = max_cost_rmb
    if pc == 0:
        return MIN_PRICE_USD
    p1 = (pc + FF) / (1 - GROSS_MARGIN - COMMISSION)
    p2 = (TARGET_REVENUE_RMB + pc + FF) / (1 - COMMISSION)
    price_rmb = max(p1, p2)
    price_usd = max(MIN_PRICE_USD, round(price_rmb * RMB_TO_USD, 2))
    return price_usd


# -------------------- 选倍数 ----------------------------------------------------
def choose_multiplier(max_cost_rmb: float, max_try: int = 10) -> tuple[int, float]:
    """
    若 calc_price_usd 成果仍 = MIN_PRICE_USD，则把成本价乘 2、3、4…
    直到售价跳出 3USD，返回 (倍数, 对应售价)
    """
    multiplier = 1
    while multiplier <= max_try:
        price = calc_price_usd(max_cost_rmb * multiplier)
        if price > MIN_PRICE_USD:
            return multiplier, price
        multiplier += 1
    # 若全部失败，返回最后一次结果
    return multiplier, calc_price_usd(max_cost_rmb * multiplier)


# -------------------- 生成 products.xlsx ---------------------------------------
def make_products(
    prod_df: pd.DataFrame, sku_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict[int, int]]:
    """
    返回：
        products_df
        folder_multi: {folder_id: multiplier}
    """
    rows, folder_multi = [], {}
    next_id = 10001

    for _, pf in prod_df.iterrows():
        subset = sku_df[sku_df.folder_id == pf.folder_id]
        if subset.empty:
            continue

        # 1) 选倍数 & 售价
        mult, price_usd = choose_multiplier(subset.cost_price.max())
        folder_multi[pf.folder_id] = mult

        # 2) GPT 生成标题/描述
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
    return df, folder_multi


# -------------------- 生成 images.xlsx -----------------------------------------
def make_images(
    prod_df: pd.DataFrame, img_df: pd.DataFrame, folder_multi: dict[int, int]
) -> None:
    """
    • 查询/分组仍用原始 sku_code
    • 写 Excel 行时，根据 folder_id 的 multiplier 决定是否附 *n
    """
    img_df["abs_path"] = img_df.file_path.apply(
        lambda p: os.path.join(ROOT_PATH, p).replace("\\", "/")
    )
    grp = img_df.groupby("folder_id")

    out_rows, img_idx = [], 1
    for _, pr in prod_df.iterrows():
        fid = pr.folder_id
        if fid not in grp.groups:
            continue

        mult = folder_multi.get(fid, 1)
        g = grp.get_group(fid)

        main = g[g.img_role == "main"].abs_path.tolist()
        detail = g[g.img_role == "detail"].abs_path.tolist()
        size = g[g.img_role == "size"].abs_path.tolist()
        opts = g[g.img_role == "option"]

        for _, r in opts.iterrows():
            pics = [r.abs_path] + main + detail + size
            pics = pics[:10]  # 平台 ≤10 张

            row = dict(
                id=img_idx,
                product_id=pr.id,
                size="",
                pack="",
                color="",
                sku=(f"{r.sku_code}*{mult}" if mult > 1 else r.sku_code),
            )
            for i, p in enumerate(pics, 1):
                row[f"img_path{i}"] = p
            out_rows.append(row)
            img_idx += 1

    pd.DataFrame(out_rows).to_excel("images.xlsx", index=False)
    print(f"[OK] images.xlsx   生成 {len(out_rows)} 行")


# -------------------- 主程 ------------------------------------------------------
if __name__ == "__main__":
    prod_df, sku_df, img_df = load_data()
    products_out, folder_multi = make_products(prod_df, sku_df)
    make_images(products_out, img_df, folder_multi)
    print("✅ 全部完成")
