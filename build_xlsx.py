"""
auto_build.py   v2025‑07‑22
----------------------------------------------------------
• 读取 product_folder / sku / image_asset 三表
• 若提供 txt 文件，则仅处理该列表里的文件夹
• 生成 products.xlsx 及 images.xlsx

用法：
    python auto_build.py folders.txt   # 处理 txt 中列出的文件夹
    python auto_build.py               # 走默认筛选条件
"""

from __future__ import annotations
import os, sys, re, json, time, argparse
import pandas as pd, pymysql
from openai import OpenAI

# ───────────── 进度条 ────────────────────────────────────────────────────
try:
    from tqdm import tqdm                                           
except ImportError:                                                
    class tqdm:                                                   
        def __init__(self, iterable=None, total=None, **kw):
            self._iter = iterable or range(total or 0)
            self.i, self.n = 0, total or len(self._iter)
        def __iter__(self):
            for obj in self._iter:
                yield obj
                self.i += 1
                width, filled = 50, int(self.i / self.n * 50)
                bar = "█" * filled + "-" * (width - filled)
                pct = self.i / self.n * 100
                sys.stdout.write(f"\r[{bar}] {self.i}/{self.n} {pct:5.1f}%")
                sys.stdout.flush()
            print()
# ────────────────────────────────────────────────────────────────────────

# ========================= 必填参数 =====================================
DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

DEEPSEEK_API_KEY = "sk-c73cba2525b74adbb76c271fc7080857"
GPT_MODEL        = "deepseek-chat"

# —— option_tag 过滤开关 ("qty" / "noqty" / "all") ————————————————
# * "qty"  ：优先 qty；若无 qty 则用 noqty；都没有跳过
# * "noqty": 仅用 noqty；不存在则跳过
# * "all"  ：qty 和 noqty 都输出
OPTION_TAG = "qty"
# =======================================================================

# ---------------- 常量：价格计算 ----------------------------------------
FF, COMMISSION, ACOS_RATE = 4.2, 0.08, 0.35
GROSS_MARGIN, TARGET_REV_RMB = 0.20, 0.0
RMB_TO_USD, MIN_PRICE_USD = 0.13927034, 3.0
# -----------------------------------------------------------------------

# =======================================================================
#                            Util 函数
# =======================================================================

def db():
    return pymysql.connect(**DB_CONF)


# ――――――――― 解析 txt 中的文件夹绝对路径 → 三元组 ―――――――――――――――――――――
def parse_folder_path(path: str):
    """
    传入形如：
      \\Desktop-inv4qoc\\图片数据\\整理图库\\RT\\风格4\\RT76
    返回：("RT", "风格4", "RT76")
    匹配失败返回 None
    """
    m = re.search(r"整理图库\\([^\\]+)\\([^\\]+)\\([^\\]+)$", path.strip())
    return m.groups() if m else None


# ――――――――― 根据 txt/全部两种模式读取数据 ――――――――――――――――――――――――――――
def load_data(folders: list[tuple[str, str, str]] | None = None):
    """
    folders: [(folder_code, style_name, sku_folder), ...]  or None
    """
    conn = db()
    try:
        # ————— product_folder ————————————————————————————
        base_sql = """
            SELECT pf.id AS folder_id, pf.folder_code, pf.style_name, pf.sku_folder
            FROM   product_folder pf
            WHERE  1=1
        """
        params: list[str] = []

        if folders:                                             # 仅过滤 txt 列表
            conds = []
            for fc, sn, sf in folders:
                conds.append("(pf.folder_code=%s AND pf.style_name=%s AND pf.sku_folder=%s)")
                params += [fc, sn, sf]
            base_sql += " AND (" + " OR ".join(conds) + ")"

        else:                                                   # ↓↓↓ 可按需调整默认筛选 ↓↓↓
            base_sql += """
              AND pf.folder_code = 'MN-玛瑙'
              AND pf.style_name  = '风格1'
            """

        prod = pd.read_sql(base_sql, conn, params=params)

        # ————— sku ——————————————————————————————————————————
        sku = pd.read_sql(
            "SELECT sku_code, product_name, cost_price, weight_kg, folder_id FROM sku",
            conn,
        )

        # ————— image_asset ———————————————————————————————
        img_sql = """
            SELECT ia.folder_id,
                   ia.file_path,
                   ia.img_role,
                   ia.option_tag,
                   ia.sku_code
            FROM   image_asset ia
            WHERE  ia.img_role <> 'option'
               OR ia.img_role  = 'option'      -- 全量拉取 option 图，后续再做回退逻辑
        """
        img = pd.read_sql(img_sql, conn)
    finally:
        conn.close()

    # 统一 SKU 大写
    sku["sku_code"] = sku.sku_code.str.upper()
    img["sku_code"] = img.sku_code.str.upper()
    return prod, sku, img


# ――――――――――――――― GPT 辅助函数 ―――――――――――――――――――――――――――――――――――――
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

    sys_msg = "You are an e‑commerce copywriter."
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


def calc_price_usd(max_cost_rmb: float | None) -> float:
    pc = max_cost_rmb or 0
    p1 = (pc + FF) / (1 - GROSS_MARGIN - COMMISSION - ACOS_RATE)
    p2 = (TARGET_REV_RMB + pc + FF) / (1 - COMMISSION - ACOS_RATE)
    price_rmb = max(p1, p2)
    return max(MIN_PRICE_USD, round(price_rmb * RMB_TO_USD, 2))

# =======================================================================
#                       生成 products.xlsx
# =======================================================================

def make_products(prod_df: pd.DataFrame, sku_df: pd.DataFrame, img_df: pd.DataFrame):
    rows, next_id = {}, 10001
    for pf in tqdm(prod_df.itertuples(), total=len(prod_df), desc="GPT generating"):

        # ——— ① 取当前文件夹全部 option 图
        opt_all = img_df[
            (img_df.folder_id == pf.folder_id) &
            (img_df.img_role  == "option")    &
            (img_df.sku_code.notnull())
        ]

        # ——— ② 先 qty → 再 noqty → 否则 None
        opt_qty    = opt_all[opt_all.option_tag == "qty"]
        opt_noqty  = opt_all[opt_all.option_tag == "noqty"]
        if OPTION_TAG == "qty":
            opts = opt_qty if len(opt_qty) else opt_noqty
        elif OPTION_TAG == "noqty":
            opts = opt_noqty
        else:                     # "all"
            opts = opt_all

        if opts.empty:
            print(f"\n[⚠] Folder {pf.folder_id}: 无符合条件的选项图，跳过")
            continue

        # ——— ③ 关联 SKU
        opt_skus = opts.sku_code.unique()
        subset   = sku_df[sku_df.sku_code.isin(opt_skus)]
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


# =======================================================================
#                       生成 images.xlsx
# =======================================================================

def make_images(prod_df: pd.DataFrame, img_df: pd.DataFrame):
    grp = img_df.groupby("folder_id")

    out_rows, img_idx = [], 1
    for pr in tqdm(prod_df.itertuples(), total=len(prod_df), desc="Images assembling"):
        fid = pr.folder_id
        if fid not in grp.groups:
            continue

        g = grp.get_group(fid)
        main   = g[g.img_role == "main"  ].file_path.tolist()
        detail = g[g.img_role == "detail"].file_path.tolist()
        size   = g[g.img_role == "size"  ].file_path.tolist()

        # ——— 选项图优先级：qty → noqty → all ———
        opt_qty   = g[(g.img_role == "option") & (g.option_tag == "qty"  )]
        opt_noqty = g[(g.img_role == "option") & (g.option_tag == "noqty")]
        if OPTION_TAG == "qty":
            opts = opt_qty if len(opt_qty) else opt_noqty
        elif OPTION_TAG == "noqty":
            opts = opt_noqty
        else:                     # "all"
            opts = g[g.img_role == "option"]

        if opts.empty:
            continue

        for r in opts.itertuples():
            pics = [r.file_path] + main + detail + size
            pics = pics[:10]                       # 系统最多接收 10 张

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


# =======================================================================
#                               主入口
# =======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build products.xlsx & images.xlsx from DB or txt list")
    parser.add_argument("txt", nargs="?", help="txt file with folder paths")
    args = parser.parse_args()

    folder_tuples: list[tuple[str, str, str]] | None = None
    if args.txt:
        if not os.path.isfile(args.txt):
            sys.exit(f"[ERR] txt 文件不存在: {args.txt}")
        with open(args.txt, "r", encoding="utf-8") as f:
            folder_tuples = []
            for ln in f:
                if not ln.strip():
                    continue
                t = parse_folder_path(ln)
                if t:
                    folder_tuples.append(t)
                else:
                    print(f"[WARN] 无法解析路径: {ln.strip()}")
        if not folder_tuples:
            sys.exit("[ERR] txt 中无有效文件夹路径被解析")

    print(f"[INFO] OPTION_TAG = {OPTION_TAG}")
    prod_df, sku_df, img_df = load_data(folder_tuples)
    if prod_df.empty:
        sys.exit("[ERR] 未找到任何 product_folder 记录，请检查筛选条件")
    products_out = make_products(prod_df, sku_df, img_df)
    make_images(products_out, img_df)
    print("✅ 全部完成")


if __name__ == "__main__":
    main()
