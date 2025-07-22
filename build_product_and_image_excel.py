# -*- coding: utf-8 -*-
"""
build_product_and_image_excel.py  ·  带 GPT 进度条
--------------------------------------------------
• 读取 MySQL(product_folder / sku / image_asset)
• 计算 global_price（不再对 SKU 做 *n 倍处理）
• DeepSeek-GPT 生成 title / desc，并实时显示进度
• 导出 products.xlsx、images.xlsx
"""
import os, json, re, time, sys
import pandas as pd, pymysql
from openai import OpenAI

# ───────────── 进度条 ─────────────────────────────────────────────────────────
try:
    from tqdm import tqdm
except ImportError:                # 若用户未安装 tqdm，则退化为普通打印
    class tqdm:                    # noqa: D401
        def __init__(self, iterable=None, total=None, **kw):
            self._iter = iterable or range(total or 0)
            self.i, self.n = 0, total or len(self._iter)
        def __iter__(self):
            for obj in self._iter:
                yield obj
                self.i += 1
                width = 50
                filled = int(self.i / self.n * width)
                bar = "█" * filled + "-" * (width - filled)
                pct = self.i / self.n * 100
                sys.stdout.write(f"\r[{bar}] {self.i}/{self.n} {pct:5.1f}%")
                sys.stdout.flush()
            print()
# ──────────────────────────────────────────────────────────────────────────────

# ===================== 必填参数 =================================================
DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

ROOT_PATH       = r"D:\图片录入测试"
DEEPSEEK_API_KEY = "sk-c73cba2525b74adbb76c271fc7080857"     # ← 改成你的 Key
GPT_MODEL        = "deepseek-chat"

# ====== option_tag 过滤开关 =====================================================
OPTION_TAG = "qty"                 # "qty" / "noqty" / "all"
# ==============================================================================

# ---- 价格计算常量 -------------------------------------------------------------
FF = 4.2
COMMISSION = 0.08
ACOS_RATE = 0.35
GROSS_MARGIN = 0.20
TARGET_REV_RMB = 0.0
RMB_TO_USD = 0.13927034
MIN_PRICE_USD = 3.0
# ==============================================================================


def _tag_sql(alias: str = "ia") -> str:
    if OPTION_TAG in (None, "", "all"):
        return ""
    return f"AND {alias}.option_tag = '{OPTION_TAG}'"


def db():
    return pymysql.connect(**DB_CONF)


def load_data():
    conn = db()
    try:
        prod = pd.read_sql(
            f"""
            SELECT pf.id AS folder_id, pf.folder_code, pf.style_name, pf.sku_folder
            FROM product_folder pf
            WHERE pf.folder_code = 'CCB-电镀塑料'
              AND pf.style_name  = '风格1'
              AND EXISTS (
                  SELECT 1 FROM image_asset ia
                  WHERE ia.folder_id = pf.id
                    AND ia.img_role  = 'option'
                    {_tag_sql('ia')}
              )
            """,
            conn,
        )

        sku = pd.read_sql(
            "SELECT sku_code, product_name, cost_price, weight_kg, folder_id FROM sku",
            conn,
        )

        img = pd.read_sql(
            f"""
            SELECT folder_id, file_path, img_role, option_tag, sku_code
            FROM image_asset
            WHERE img_role <> 'option'
            OR (img_role = 'option'
                {"AND option_tag = '%s'" % OPTION_TAG if OPTION_TAG not in (None, "", "all") else ""}
            )
            """,
            conn,
        )
    finally:
        conn.close()

    sku["sku_code"] = sku.sku_code.str.upper()
    img["sku_code"] = img.sku_code.str.upper()
    return prod, sku, img


# -------------------- GPT ------------------------------------------------------
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def _strip_fence(txt: str) -> str:
    return re.sub(r"^```[\s\S]*?\n|\n?```$", "", txt.strip())


def gpt_title_desc(names, folder_id, tries=3):
    merged = " ".join(names)
    pcs_hint = weight_hint = ""

    m = re.search(r"(\d+)\s*(pcs?|Pc|颗|个|色|colors?)", merged, re.I)
    if m:
        pcs_hint = (
            f"\nEach pack actually contains **{m.group(1)} pcs**, "
            "this exact number MUST appear in the title."
        )
    m = re.search(r"(\d+)\s*(g|克|grams?)", merged, re.I)
    if m:
        weight_hint = (
            f"\nNet weight per pack is **{m.group(1)} g**, "
            "make sure this number is included in the title."
        )

    sys_msg = "You are an e-commerce copywriter."
    user_msg = (
        "English title must contain the exact pcs quantity or weight in grams "
        "(if present), plus the main size(s) and the material. Do NOT invent numbers."
        + pcs_hint + weight_hint
        + "\nGenerate an English title (≤55 chars) and description (≤300 chars) "
        "for the jewelry beads listed below.\nProducts: "
        + "; ".join(names[:20])
        + '\nReturn JSON: {"title":"...", "desc":"..."}'
    )

    for i in range(1, tries + 1):
        try:
            rsp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "system", "content": sys_msg},
                          {"role": "user", "content": user_msg}],
                temperature=0.7,
            )
            data = json.loads(_strip_fence(rsp.choices[0].message.content))
            return data.get("title", "")[:55], data.get("desc", "")[:300]
        except Exception as e:
            print(f"[GPT-retry] Folder {folder_id} attempt {i}/{tries} failed: {e}")
            time.sleep(1.5)
    return "", ""


def calc_price_usd(max_cost_rmb):
    pc = max_cost_rmb or 0
    # 公式里分母多减一个ACOS费率
    p1 = (pc + FF) / (1 - GROSS_MARGIN - COMMISSION - ACOS_RATE)
    p2 = (TARGET_REV_RMB + pc + FF) / (1 - COMMISSION - ACOS_RATE)
    price_rmb = max(p1, p2)
    return max(MIN_PRICE_USD, round(price_rmb * RMB_TO_USD, 2))


# -------------------- 生成 products.xlsx ---------------------------------------
def make_products(prod_df, sku_df, img_df):
    rows, next_id = {}, 10001
    for pf in tqdm(prod_df.itertuples(), total=len(prod_df), desc="GPT generating"):
        tag_mask = True if OPTION_TAG == "all" else (img_df.option_tag == OPTION_TAG)
        opt_skus = img_df[
            (img_df.folder_id == pf.folder_id) &
            (img_df.img_role == "option") &
            tag_mask &
            (img_df.sku_code.notnull())
        ].sku_code.unique()

        if not len(opt_skus):
            print(f"\n[⚠] Folder {pf.folder_id}: no option images")
            continue

        subset = sku_df[sku_df.sku_code.isin(opt_skus)]
        if subset.empty:
            print(f"\n[⚠] Folder {pf.folder_id}: SKUs missing in sku table")
            continue

        price_usd = calc_price_usd(subset.cost_price.max())
        names = subset.product_name.dropna().unique().tolist()
        title, desc = gpt_title_desc(names, pf.folder_id)

        print(f"\n[GPT] Folder {pf.folder_id} → {title[:40]}")

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
    print(f"\n[OK] products.xlsx 生成 {len(df)} 行")
    return df


# -------------------- 生成 images.xlsx -----------------------------------------
def make_images(prod_df, img_df):
    img_df["abs_path"] = img_df.file_path.apply(
        lambda p: os.path.join(ROOT_PATH, p).replace("\\", "\\")
    )
    grp = img_df.groupby("folder_id")

    out_rows, img_idx = [], 1
    for pr in tqdm(prod_df.itertuples(), total=len(prod_df), desc="Images assembling"):
        fid = pr.folder_id
        if fid not in grp.groups:
            continue

        g = grp.get_group(fid)
        main   = g[g.img_role == "main"].abs_path.tolist()
        detail = g[g.img_role == "detail"].abs_path.tolist()
        size   = g[g.img_role == "size"].abs_path.tolist()

        tag_mask = True if OPTION_TAG == "all" else (g.option_tag == OPTION_TAG)
        opts = g[(g.img_role == "option") & tag_mask]

        for r in opts.itertuples():
            pics = [r.abs_path] + main + detail + size
            pics = pics[:10]

            row = dict(
                id=img_idx,
                product_id=pr.id,
                size="",
                pack="2",
                color="",
                sku=r.sku_code,
            )
            for i, p in enumerate(pics, 1):
                row[f"img_path{i}"] = p
            out_rows.append(row)
            img_idx += 1

    pd.DataFrame(out_rows).to_excel("images.xlsx", index=False)
    print(f"[OK] images.xlsx   生成 {len(out_rows)} 行")


# -------------------- 主程 ------------------------------------------------------
if __name__ == "__main__":
    print(f"[INFO] OPTION_TAG = {OPTION_TAG}")
    prod_df, sku_df, img_df = load_data()
    products_out = make_products(prod_df, sku_df, img_df)
    make_images(products_out, img_df)
    print("✅ 全部完成")
