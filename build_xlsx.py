from __future__ import annotations
import os, sys, re, json, time, argparse
import pandas as pd, pymysql
from openai import OpenAI
from tqdm import tqdm

DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
    autocommit=False,
)

DEEPSEEK_API_KEY = "sk-c73cba2525b74adbb76c271fc7080857"
GPT_MODEL = "deepseek-chat"
OPTION_TAG = "qty"

FF, COMMISSION, ACOS_RATE = 4.2, 0.08, 0.35
GROSS_MARGIN, TARGET_REV_RMB = 0.20, 0.0
RMB_TO_USD, MIN_PRICE_USD = 0.13927034, 4.0

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def db():
    return pymysql.connect(**DB_CONF)


def parse_folder_path(path: str):
    m = re.search(r"整理图库\\([^\\]+)\\([^\\]+)\\([^\\]+)$", path.strip())
    return m.groups() if m else None


def load_data(folders: list[tuple[str, str, str]] | None = None):
    conn = db()
    try:
        base_sql = """
            SELECT pf.id AS folder_id, pf.folder_code, pf.style_name, pf.sku_folder
            FROM   product_folder pf
            WHERE  1=1
        """
        params: list[str] = []
        if folders:
            conds = []
            for fc, sn, sf in folders:
                conds.append(
                    "(pf.folder_code=%s AND pf.style_name=%s AND pf.sku_folder=%s)"
                )
                params += [fc, sn, sf]
            base_sql += " AND (" + " OR ".join(conds) + ")"
        else:
            base_sql += """
              AND pf.folder_code = 'MN-玛瑙'
              AND pf.style_name  = '风格1'
            """
        prod = pd.read_sql(base_sql, conn, params=params)
        sku = pd.read_sql(
            "SELECT sku_code, product_name, cost_price, weight_kg, folder_id, "
            "qty_desc, color_desc, size_desc, material_desc FROM sku",
            conn,
        )
        img = pd.read_sql(
            "SELECT folder_id, file_path, img_role, option_tag, sku_code "
            "FROM image_asset",
            conn,
        )
    finally:
        conn.close()
    sku["sku_code"] = sku.sku_code.str.upper()
    img["sku_code"] = img.sku_code.str.upper()
    return prod, sku, img


def _clean_title(t: str) -> str:
    t = re.sub(r"[#\\/+%^*<>$@~`|]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:55]


def _num_range(vals):
    nums = []
    for v in vals:
        m = re.search(r"\d+", str(v))
        if m:
            nums.append(int(m.group()))
    if not nums:
        return ""
    mn, mx = min(nums), max(nums)
    return f"{mn}-{mx}" if mn != mx else str(mn)


def _strip_fence(txt: str) -> str:
    return re.sub(r"^```[\s\S]*?\n|\n?```$", "", txt.strip())


def gpt_title_desc(
    names,
    qty_set,
    size_set,
    color_set,
    weight_set,
    material_set,
    tries=3,
):
    qty_txt = _num_range(qty_set)
    size_txt = _num_range(size_set)
    weight_txt = _num_range(weight_set)
    color_txt = ", ".join(sorted(list(color_set))[:1])
    mat_txt = ", ".join(sorted(list(material_set))[:1])

    hint_parts = []
    if qty_txt:
        hint_parts.append(f"{qty_txt}pcs")
    elif weight_txt:
        hint_parts.append(f"{weight_txt}g")
    if size_txt:
        hint_parts.append(f"{size_txt}mm")
    if mat_txt:
        hint_parts.append(mat_txt)
    if color_txt:
        hint_parts.append(color_txt)

    prefix = ", ".join(hint_parts)

    sys_msg = "You are an e‑commerce copywriter."
    user_msg = (
        "Create a concise English product title (≤55 chars incl. spaces) and an English "
        "bullet‑style description. "
        "TITLE must contain: " + prefix + ", product name. "
        "DESCRIPTION template:\n"
        "• Key material & finish\n"
        "• Exact size or weight & pack qty\n"
        "• Suitable DIY uses\n"
        "• Advantage or assurance\n"
        "End with: Add to cart today.\n"
        "No extra symbols, keep punctuation minimal. "
        'Return JSON: {"title":"...", "desc":"..."}  '
        "Products: " + "; ".join(names[:20])
    )

    for _ in range(tries):
        try:
            rsp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.5,
            )
            data = json.loads(_strip_fence(rsp.choices[0].message.content))
            title = _clean_title(data.get("title", ""))
            desc_raw = data.get("desc", "")[:1000]
            desc = re.sub(r"\s+\n", "\n", desc_raw).strip()
            return title, desc
        except Exception:
            time.sleep(1.5)
    return "", ""


def calc_price_usd(max_cost_rmb: float | None) -> float:
    pc = max_cost_rmb or 0
    p1 = (pc + FF) / (1 - GROSS_MARGIN - COMMISSION - ACOS_RATE)
    p2 = (TARGET_REV_RMB + pc + FF) / (1 - COMMISSION - ACOS_RATE)
    price_rmb = max(p1, p2)
    return max(MIN_PRICE_USD, round(price_rmb * RMB_TO_USD, 2))


def make_products(prod_df: pd.DataFrame, sku_df: pd.DataFrame, img_df: pd.DataFrame):
    rows, next_id = {}, 10001
    for pf in tqdm(prod_df.itertuples(), total=len(prod_df), desc="GPT generating"):
        opt_all = img_df[
            (img_df.folder_id == pf.folder_id)
            & (img_df.img_role == "option")
            & (img_df.sku_code.notnull())
        ]
        opt_qty = opt_all[opt_all.option_tag == "qty"]
        opt_noqty = opt_all[opt_all.option_tag == "noqty"]
        opts = (
            opt_qty
            if OPTION_TAG == "qty" and len(opt_qty)
            else opt_noqty if OPTION_TAG == "noqty" else opt_all
        )
        if opts.empty:
            continue
        opt_skus = opts.sku_code.unique()
        subset = sku_df[sku_df.sku_code.isin(opt_skus)]
        if subset.empty:
            continue

        qty_set = {q for q in subset.qty_desc.dropna().unique() if q and q != "/"}
        size_set = {s for s in subset.size_desc.dropna().unique() if s}
        color_set = {c for c in subset.color_desc.dropna().unique() if c}
        mat_set = {m for m in subset.material_desc.dropna().unique() if m}
        weight_set = {int(w * 1000) for w in subset.weight_kg.dropna().unique() if w}

        price_usd = calc_price_usd(subset.cost_price.max())
        names = subset.product_name.dropna().unique().tolist()
        title, desc = gpt_title_desc(
            names, qty_set, size_set, color_set, weight_set, mat_set
        )

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
    return df


def make_images(prod_df: pd.DataFrame, img_df: pd.DataFrame, sku_df: pd.DataFrame):
    attr_map = (
        sku_df[["sku_code", "qty_desc", "color_desc", "size_desc"]]
        .set_index("sku_code")
        .to_dict(orient="index")
    )
    grp = img_df.groupby("folder_id")
    out_rows, img_idx = [], 1
    for pr in tqdm(prod_df.itertuples(), total=len(prod_df), desc="Images assembling"):
        fid = pr.folder_id
        if fid not in grp.groups:
            continue
        g = grp.get_group(fid)
        main = g[g.img_role == "main"].file_path.tolist()
        detail = g[g.img_role == "detail"].file_path.tolist()
        size_pic = g[g.img_role == "size"].file_path.tolist()
        opt_qty = g[(g.img_role == "option") & (g.option_tag == "qty")]
        opt_noqty = g[(g.img_role == "option") & (g.option_tag == "noqty")]
        opts = (
            opt_qty
            if OPTION_TAG == "qty" and len(opt_qty)
            else opt_noqty if OPTION_TAG == "noqty" else g[g.img_role == "option"]
        )
        if opts.empty:
            continue
        for r in opts.itertuples():
            pics = [r.file_path] + main + detail + size_pic
            pics = pics[:10]
            attr = attr_map.get(r.sku_code, {})
            row = dict(
                id=img_idx,
                product_id=pr.id,
                size=attr.get("size_desc", "") or "",
                pack="2",
                color=attr.get("color_desc", "") or "",
                qty=attr.get("qty_desc", "") or "",
                sku=r.sku_code,
            )
            for i, p in enumerate(pics, 1):
                row[f"img_path{i}"] = p
            out_rows.append(row)
            img_idx += 1
    df = pd.DataFrame(out_rows)
    chk = (
        df.groupby("product_id")
        .apply(lambda g: len(g[["size", "pack", "color"]].drop_duplicates()) != len(g))
        .reset_index(name="mismatch")
    )
    bad_ids = chk[chk.mismatch].product_id.tolist()
    if bad_ids:
        df[df.product_id.isin(bad_ids)].to_excel("variant_mismatch.xlsx", index=False)
    df.to_excel("images.xlsx", index=False)


def main():
    parser = argparse.ArgumentParser(description="Build products.xlsx & images.xlsx")
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
    prod_df, sku_df, img_df = load_data(folder_tuples)
    if prod_df.empty:
        sys.exit("[ERR] 未找到任何 product_folder 记录")
    products_out = make_products(prod_df, sku_df, img_df)
    make_images(products_out, img_df, sku_df)
    print("✅ 全部完成")


if __name__ == "__main__":
    main()
