# -*- coding: utf-8 -*-
"""
build_product_and_image_excel.py
------------------------------------------------
• 读取 MySQL(product_folder / sku / image_asset)
• 按最高成本价计算 global_price，若结果仍是 3 USD (MIN_PRICE_USD)，
  就把成本价成倍放大（×2, ×3 …）直至售价 > 3 USD
• DeepSeek-GPT 生成 title / desc —— 件数 pcs 或克重 g 都会 × 倍并写进标题
• 导出 products.xlsx、images.xlsx
  - products.xlsx：每个产品 1 行，含最终售价
  - images.xlsx ：option 图逐行，sku 写入时才附 *n（n > 1）
"""
import os, json, re, time
import pandas as pd, pymysql
from openai import OpenAI

# ===================== 可调参数 =================================================
DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

ROOT_PATH = r"D:\图片录入测试"  # 图片根目录
DEEPSEEK_API_KEY = "sk-c73cba2525b74adbb76c271fc7080857"  # ← 改成你的 Key
GPT_MODEL = "deepseek-chat"

# ====== option_tag 过滤开关 =====================================================
#   "qty"   → 只处理带数量图
#   "noqty" → 只处理不带数量图
#   None / "all" → 两种都处理
OPTION_TAG = "qty"
# ==============================================================================

# ---- 价格计算常量 -------------------------------------------------------------
FF = 4.2  # Fulfillment Fee
COMMISSION = 0.08  # 平台佣金
GROSS_MARGIN = 0.30  # 目标毛利率 (= 1 - 40%)
TARGET_REV_RMB = 0.0  # 固定额外营收 (若有)
RMB_TO_USD = 0.13927034
MIN_PRICE_USD = 3.0
# ==============================================================================


# -------------------- 工具：生成 SQL 片段 --------------------------------------
def _tag_sql(alias: str = "ia") -> str:
    """返回 SQL 的 option_tag 过滤片段；不需过滤则为空串"""
    if OPTION_TAG in (None, "", "all"):
        return ""
    return f"AND {alias}.option_tag = '{OPTION_TAG}'"


# -------------------- 数据库 ----------------------------------------------------
def db():
    return pymysql.connect(**DB_CONF)


def load_data():
    """一次性读出三张表，并把 sku_code 统一转大写，避免大小写不一致"""
    conn = db()
    try:
        # ① product_folder：至少有一张指定 tag 的 option 图
        prod = pd.read_sql(
            f"""
            SELECT pf.id   AS folder_id,
                   pf.folder_code,
                   pf.style_name,
                   pf.sku_folder
            FROM product_folder pf
            WHERE pf.folder_code = '碎石'
              AND pf.style_name  = '风格1'
              AND EXISTS (
                  SELECT 1
                  FROM image_asset ia
                  WHERE ia.folder_id = pf.id
                    AND ia.img_role  = 'option'
                    {_tag_sql('ia')}
              )
            """,
            conn,
        )

        # ② sku：全部读取
        sku = pd.read_sql(
            """
            SELECT sku_code, product_name, cost_price, weight_kg, folder_id
            FROM sku
            """,
            conn,
        )

        # ③ image_asset：main/detail/size 全部读；option 只读指定 tag
        img = pd.read_sql(
            f"""
            SELECT folder_id, file_path, img_role, option_tag, sku_code
            FROM image_asset
            WHERE img_role <> 'option'
            OR (img_role = 'option' {"AND option_tag = '%s'" % OPTION_TAG if OPTION_TAG not in (None, "", "all") else ""}
            )
            """,
            conn,
        )
    finally:
        conn.close()

    sku["sku_code"] = sku.sku_code.str.upper()
    img["sku_code"] = img.sku_code.str.upper()

    return prod, sku, img


# -------------------- GPT 客户端 ------------------------------------------------
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def _strip_fence(txt: str) -> str:
    """去掉 ```json ...``` 围栏（GPT 有时会包围起来）"""
    return re.sub(r"^```[\s\S]*?\n|\n?```$", "", txt.strip())


# -------------------- GPT 生成标题/描述 ----------------------------------------
def gpt_title_desc(names: list[str], mult: int, tries: int = 3) -> tuple[str, str]:
    """
    • names 已经过 adjust_qty() 乘倍
    • 若抓到 pcs 或 g，都在 prompt 里给 GPT 明确提示
    """
    merged = " ".join(names)

    # (1) 件数提示
    pcs_hint = ""
    m_pcs = re.search(r"(\d+)\s*(pcs?|PCS?|Pc|pc|颗|个|色|colors?|Colors?)", merged)
    if m_pcs:
        pcs_hint = (
            f"\nEach pack actually contains **{m_pcs.group(1)} pcs**, "
            "this exact number MUST appear in the title."
        )

    # (2) 克重提示
    weight_hint = ""
    m_g = re.search(r"(\d+)\s*(g|G|克|grams?)", merged)
    if m_g:
        weight_hint = (
            f"\nNet weight per pack is **{m_g.group(1)} g**, "
            "make sure this number is included in the title."
        )

    sys = "You are an e-commerce copywriter."
    user = (
        "English title must contain the exact pcs quantity or weight in grams "
        "(if present), plus the main size(s) and the material. Do NOT invent "
        "numbers."
        + pcs_hint
        + weight_hint
        + "\nGenerate an English title (≤55 chars) and description (≤300 chars) "
        "for the jewelry beads listed below.\nProducts: "
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
            return data.get("title", "")[:55], data.get("desc", "")[:300]
        except Exception as e:
            print(f"[GPT] attempt {i+1}/{tries} failed: {e}")
            time.sleep(1.5)
    return "", ""


# -------------------- 价格公式 --------------------------------------------------
def calc_price_usd(max_cost_rmb: float) -> float:
    pc = max_cost_rmb or 0
    p1 = (pc + FF) / (1 - GROSS_MARGIN - COMMISSION)
    p2 = (TARGET_REV_RMB + pc + FF) / (1 - COMMISSION)
    price_rmb = max(p1, p2)
    return max(MIN_PRICE_USD, round(price_rmb * RMB_TO_USD, 2))


# -------------------- 选倍数 ----------------------------------------------------
def choose_multiplier(max_cost_rmb: float, max_try: int = 10) -> tuple[int, float]:
    multiplier = 1
    while multiplier <= max_try:
        price = calc_price_usd(max_cost_rmb * multiplier)
        if price > MIN_PRICE_USD:
            return multiplier, price
        multiplier += 1
    return multiplier, calc_price_usd(max_cost_rmb * multiplier)


# -------------------- 数量 / 克重 放大 ------------------------------------------
_qty_pat = re.compile(
    r"(\d+)\s*(pcs?|PCS?|Pc|pc|颗|个|色|colors?|Colors?|g|G|克|grams?)"
)


def adjust_qty(name: str, mult: int) -> str:
    """把与 pcs / 克 等单位连用的数字 × mult；尺寸 mm 不动"""

    def _repl(m):
        num = int(m.group(1)) * mult
        return f"{num}{m.group(2)}"

    return _qty_pat.sub(_repl, name)


# -------------------- 生成 products.xlsx ---------------------------------------
def make_products(
    prod_df: pd.DataFrame, sku_df: pd.DataFrame, img_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict[int, int]]:
    rows, folder_multi = {}, {}
    next_id = 10001

    for _, pf in prod_df.iterrows():
        # 1) option 图里的 SKU
        tag_mask = (
            True
            if OPTION_TAG in (None, "", "all")
            else (img_df.option_tag == OPTION_TAG)
        )

        opt_skus = img_df[
            (img_df.folder_id == pf.folder_id)
            & (img_df.img_role == "option")
            & tag_mask
            & (img_df.sku_code.notnull())
        ].sku_code.unique()

        if not len(opt_skus):
            print(f"[⚠] folder {pf.folder_id}: 没有 option 图或 sku_code 为空")
            continue

        subset = sku_df[sku_df.sku_code.isin(opt_skus)]
        if subset.empty:
            print(f"[⚠] folder {pf.folder_id}: option 图里的 SKU 不在 sku 表")
            continue

        # 2) 选倍数 & 售价
        mult, price_usd = choose_multiplier(subset.cost_price.max())
        folder_multi[pf.folder_id] = mult

        # 3) 调整数量后再交 GPT
        names = subset.product_name.dropna().unique().tolist()
        if mult > 1:
            names = [adjust_qty(n, mult) for n in names]

        title, desc = gpt_title_desc(names, mult)

        rows[next_id] = dict(
            id=next_id,
            title=title,
            desc=desc,
            global_price=price_usd,
            category="Beads(珠子)",
            attribute="Generic",
            attr_value="Beads",
            folder_id=pf.folder_id,
            folder_name=pf.sku_folder,
        )
        next_id += 1

    df = pd.DataFrame.from_dict(rows, orient="index")
    df.to_excel("products.xlsx", index=False)
    print(f"[OK] products.xlsx 生成 {len(df)} 行")
    return df, folder_multi


# -------------------- 生成 images.xlsx -----------------------------------------
def make_images(
    prod_df: pd.DataFrame, img_df: pd.DataFrame, folder_multi: dict[int, int]
) -> None:
    img_df["abs_path"] = img_df.file_path.apply(
        lambda p: os.path.join(ROOT_PATH, p).replace("\\", "\\")
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

        tag_mask = (
            True if OPTION_TAG in (None, "", "all") else (g.option_tag == OPTION_TAG)
        )
        opts = g[(g.img_role == "option") & tag_mask]

        for _, r in opts.iterrows():
            pics = [r.abs_path] + main + detail + size
            pics = pics[:10]

            row = dict(
                id=img_idx,
                product_id=pr.id,
                size="",
                pack="2",
                color="",
                sku=f"{r.sku_code}*{mult}" if mult > 1 else r.sku_code,
            )
            for i, p in enumerate(pics, 1):
                row[f"img_path{i}"] = p
            out_rows.append(row)
            img_idx += 1

    out_rows = sorted(out_rows, key=lambda r: (r["product_id"], r["sku"]))
    pd.DataFrame(out_rows).to_excel("images.xlsx", index=False)
    print(f"[OK] images.xlsx   生成 {len(out_rows)} 行")


# -------------------- 主程 ------------------------------------------------------
if __name__ == "__main__":
    prod_df, sku_df, img_df = load_data()
    products_out, folder_multi = make_products(prod_df, sku_df, img_df)
    make_images(products_out, img_df, folder_multi)
    print("✅ 全部完成")
