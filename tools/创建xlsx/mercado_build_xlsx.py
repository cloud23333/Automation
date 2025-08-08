from __future__ import annotations
import os, sys, re, json, time
import pandas as pd, pymysql
from openai import OpenAI
from tqdm import tqdm
from sqlalchemy import create_engine, text

ENGINE = create_engine(
    "mysql+pymysql://root:123456@localhost/temu_gallery?charset=utf8mb4",
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)

TXT_PATH = r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\创建xlsx\txt文件\mercado_folders.txt"
OUT_DIR = r"C:\Users\Administrator\Documents\Mecrado\Automation\数据"

MAX_DESC_LEN = 3500

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

FF, COMMISSION, ACOS_RATE = 4.2, 0.08, 0.350
GROSS_MARGIN, TARGET_REV_RMB = 0.20, 0.0
RMB_TO_USD, MIN_PRICE_USD = 0.13927034, 4.0

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

_name_cache: dict[str, str] = {}


def db():
    return pymysql.connect(**DB_CONF)


def parse_folder_path(path: str):
    m = re.search(r"整理图库\\([^\\]+)\\([^\\]+)\\([^\\]+)$", path.strip())
    return m.groups() if m else None


def load_data(folders: list[tuple[str, str, str]] | None = None):
    with ENGINE.begin() as conn:
        base_sql = """
            SELECT pf.id AS folder_id, pf.folder_code, pf.style_name, pf.sku_folder
            FROM product_folder pf
            WHERE 1=1
        """
        params = {}
        if folders:
            conds = []
            for i, (fc, sn, sf) in enumerate(folders):
                conds.append(f"(pf.folder_code=:fc{i} AND pf.style_name=:sn{i} AND pf.sku_folder=:sf{i})")
                params.update({f"fc{i}": fc, f"sn{i}": sn, f"sf{i}": sf})
            base_sql += " AND (" + " OR ".join(conds) + ")"
        else:
            base_sql += " AND pf.folder_code = 'MN-玛瑙' AND pf.style_name = '风格1'"

        prod = pd.read_sql(text(base_sql), conn, params=params)
        sku = pd.read_sql(
            text("""
                SELECT sku_code, product_name, cost_price, weight_kg, folder_id,
                       qty_desc, color_desc, size_desc, material_desc
                FROM sku
            """),
            conn,
        )
        img = pd.read_sql(
            text("""
                SELECT folder_id, file_path, img_role, option_tag, sku_code
                FROM image_asset
            """),
            conn,
        )

    sku["sku_code"] = sku.sku_code.str.upper()
    img["sku_code"] = img.sku_code.str.upper()
    return prod, sku, img


def _clean_title(t: str) -> str:
    t = re.sub(r"[#\\/+%^*<>$@~|]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = t[:55]
    t = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", "", t)
    return t.strip()


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
    txt = txt.strip()
    if txt.startswith(""):
        txt = re.sub(r"^[^\n]*\n?", "", txt)
    if txt.endswith(""):
        txt = txt[:-3]
    return txt.strip()


_color_cache: dict[str, str] = {}

def translate_colors(colors: list[str]) -> list[str]:
    todo = [c for c in colors if c not in _color_cache]
    if todo:
        joined = " | ".join(todo)
        rsp = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a translator."},
                {"role": "user", "content": "Translate these Chinese color names to standard concise English color terms only, keep order, separated by ' | ': " + joined},
            ],
            temperature=0,
        )
        out_raw = rsp.choices[0].message.content or ""
        outs = [x.strip() for x in out_raw.split("|")]
        if len(outs) < len(todo):
            outs += todo[len(outs):]
        for zh, en in zip(todo, outs):
            _color_cache[zh] = en or zh
    return [_color_cache.get(c, c) for c in colors]

def build_color_map_for_folder(sku_df: pd.DataFrame, folder_id: int) -> dict:
    sub = sku_df[sku_df.folder_id == folder_id][["size_desc","color_desc"]].dropna()
    sub = sub.loc[(sub.size_desc != "/")]
    sub = sub.assign(size_val=pd.to_numeric(sub.size_desc, errors="coerce")).dropna(subset=["size_val"])
    if sub.empty:
        return {}
    min_size = sub.size_val.min()
    base = sub[sub.size_val == min_size]
    colors = base.color_desc.dropna().astype(str).unique().tolist()
    if not colors:
        return {}
    colors_en = translate_colors(colors)
    return dict(zip(colors, colors_en))


def translate_names(names: list[str]) -> list[str]:
    todo = [n for n in names if n not in _name_cache]
    if todo:
        prompt = " | ".join(todo)
        rsp = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a translator."},
                {
                    "role": "user",
                    "content": "Translate the following Chinese product names to concise natural English, keep the order, separate each with ' | ' only: "
                    + prompt,
                },
            ],
            temperature=0,
        )
        outs = [x.strip() for x in rsp.choices[0].message.content.split("|")]
        for zh, en in zip(todo, outs):
            _name_cache[zh] = en or zh
    return [_name_cache.get(n, n) for n in names]


def gpt_title_desc(
    names,
    qty_set,
    size_set,
    color_set,
    weight_set,
    material_set,
    tries=3,
):
    parts = []
    qty_txt = _num_range(qty_set)
    size_txt = _num_range(size_set)
    weight_txt = _num_range(weight_set)
    color_txt = ", ".join(sorted(list(color_set))[:1])
    mat_txt = ", ".join(sorted(list(material_set))[:1])
    if qty_txt:
        parts.append(f"{qty_txt}pcs")
    elif weight_txt:
        parts.append(f"{weight_txt}g")
    if size_txt:
        parts.append(f"{size_txt}mm")
    if mat_txt:
        parts.append(mat_txt)
    if color_txt:
        parts.append(color_txt)
    prefix = ", ".join(parts)
    if prefix:
        title_rule = f"TITLE must contain: {prefix}, product name."
    else:
        title_rule = "TITLE must contain the product name."
    sys_msg = "You are an e-commerce copywriter."
    user_msg = (
        "Create a concise English product title (≤55 chars incl. spaces) and an "
        "detailed English bullet-style description.\n"
        f"{title_rule}\n"
        "DESCRIPTION requirements:\n"
        "• 10-12 bullets, each ≤35 words.\n"
        "• Cover: material & finish, exact size/weight & pack qty, DIY use cases, "
        "creative project ideas, benefits, quality assurance, shipping info, "
        "storage/care tips, brand story, plus a call-to-action.\n"
        "Finish with: Add to cart today.\n"
        "No emojis, minimal punctuation.\n"
        'Return JSON: {"title":"...", "desc":"..."}\n'
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
            content = _strip_fence(rsp.choices[0].message.content)
            try:
                data = json.loads(content)
                title = _clean_title(data.get("title", ""))
                desc = re.sub(r"\s+\n", "\n", str(data.get("desc", "")))[
                    :MAX_DESC_LEN
                ].strip()
                if title:
                    return title, desc
            except Exception:
                pass
        except Exception:
            time.sleep(1.5)
    fallback_name = names[0] if names else "Beads"
    qty_txt = _num_range(qty_set) or ""
    size_txt = _num_range(size_set) or ""
    prefix = " ".join(
        [f"{size_txt}mm" if size_txt else "", f"{qty_txt}pcs" if qty_txt else ""]
    ).strip()
    title = _clean_title(f"{prefix} {fallback_name}".strip()) or fallback_name
    desc = (
        "Jewelry-making beads. Ideal for DIY crafts and decorations. Add to cart today."
    )
    return title, desc


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
        names_raw = subset.product_name.dropna().unique().tolist() or [pf.sku_folder]
        names = translate_names(names_raw)
        fallback_name = names[0]
        title, desc_gpt = gpt_title_desc(
            names, qty_set, size_set, color_set, weight_set, mat_set
        )

        def fmt(v):
            try:
                f = float(v)
                return str(int(f)) if f.is_integer() else str(f)
            except Exception:
                return str(v)

        pairs_df = (
            subset[["size_desc", "qty_desc"]]
            .dropna()
            .loc[lambda d: (d.size_desc != "/") & (d.qty_desc != "/")]
            .assign(size_val=lambda d: pd.to_numeric(d.size_desc, errors="coerce"))
            .sort_values("size_val", ignore_index=True)
        )
        mapping_lines = [
            f"{fmt(r.size_desc)}mm-{fmt(r.qty_desc)}pcs" for _, r in pairs_df.iterrows()
        ]
        mapping_text = "\n".join(dict.fromkeys(mapping_lines))
        full_desc = f"{desc_gpt.strip()}\n\nAvailable packs:\n{mapping_text}"
        rows[next_id] = dict(
            id=next_id,
            title=title,
            desc=full_desc,
            global_price=price_usd,
            category="Beads",
            attribute="Generic",
            attr_value="Beads",
            folder_id=pf.folder_id,
            folder_name=pf.sku_folder,
        )
        next_id += 1
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.to_excel(
        r"C:\Users\Administrator\Documents\Mecrado\Automation\数据\mercado_products.xlsx",
        index=False,
    )
    return df


def make_images(prod_df: pd.DataFrame, img_df: pd.DataFrame, sku_df: pd.DataFrame):
    attr_map = (
        sku_df[["sku_code", "qty_desc", "color_desc", "size_desc", "folder_id"]]
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
        opt_g = g[g.img_role == "option"]
        if opt_g.empty:
            continue
        sizes_all = (
            sku_df.loc[sku_df.folder_id == fid, "size_desc"]
            .dropna()
            .astype(str)
            .loc[lambda s: s != "/"]
        )
        if sizes_all.empty:
            continue
        sizes_all = pd.to_numeric(sizes_all, errors="coerce").dropna().sort_values().astype(str).tolist()
        sz_map = (
            sku_df[sku_df.folder_id == fid][["sku_code","size_desc","color_desc","qty_desc"]]
            .dropna(subset=["size_desc"])
        )
        sz_map = sz_map.assign(size_val=pd.to_numeric(sz_map["size_desc"], errors="coerce")).dropna(subset=["size_val"])
        if sz_map.empty:
            continue
        min_size = sz_map["size_val"].min()
        base_skus = sz_map[sz_map["size_val"] == min_size]
        base_skus = base_skus[base_skus["color_desc"].notna()]
        base_colors_zh = base_skus["color_desc"].astype(str).unique().tolist()
        if not base_colors_zh:
            continue
        colors_en = translate_colors(base_colors_zh)
        color_cn2en = dict(zip(base_colors_zh, colors_en))
        base_opt = opt_g.merge(
            sku_df[["sku_code","color_desc","size_desc"]], on="sku_code", how="left"
        )
        base_opt = base_opt.assign(
            size_val=pd.to_numeric(base_opt["size_desc"], errors="coerce")
        )
        base_opt = base_opt[base_opt["size_val"] == min_size]
        color2optpath = {}
        for r in base_opt.itertuples():
            cz = str(getattr(r, "color_desc") or "")
            if cz and cz not in color2optpath:
                color2optpath[cz] = r.file_path
        size_color_opt = {}
        tmp = opt_g.merge(
            sku_df[["sku_code","color_desc","size_desc"]], on="sku_code", how="left"
        )
        for r in tmp.itertuples():
            sz = str(getattr(r, "size_desc") or "")
            cz = str(getattr(r, "color_desc") or "")
            if sz and cz:
                size_color_opt[(sz, cz)] = r.file_path
        prod_rows = []
        for sz in sizes_all:
            for cz in base_colors_zh:
                opt_path = size_color_opt.get((sz, cz), color2optpath.get(cz, None))
                pics = ([opt_path] if opt_path else []) + main + detail + size_pic
                pics = pics[:10]
                matched_sku = (
                    sku_df[(sku_df.folder_id == fid) & (sku_df.size_desc.astype(str) == sz) & (sku_df.color_desc.astype(str) == cz)]
                )
                if matched_sku.empty:
                    matched_sku = sku_df[(sku_df.folder_id == fid) & (sku_df.size_desc.astype(str) == sz)]
                sku_code = matched_sku.iloc[0]["sku_code"] if not matched_sku.empty else ""
                qty = matched_sku.iloc[0]["qty_desc"] if not matched_sku.empty else ""
                row = dict(
                    id=img_idx,
                    product_id=pr.id,
                    size=sz,
                    pack="2",
                    color=color_cn2en.get(cz, cz),
                    qty=str(qty) if pd.notna(qty) else "",
                    sku=sku_code,
                )
                for i, p in enumerate(pics, 1):
                    row[f"img_path{i}"] = p
                prod_rows.append(row)
                img_idx += 1
        df_prod = pd.DataFrame(prod_rows)
        df_prod = df_prod.drop_duplicates(subset=["product_id","size","pack","color"], keep="first")
        out_rows.extend(df_prod.to_dict(orient="records"))
    df = pd.DataFrame(out_rows)
    if not df.empty:
        chk = (
            df.groupby("product_id")
            .apply(lambda g: len(g[["size", "pack", "color"]].drop_duplicates()) != len(g))
            .reset_index(name="mismatch")
        )
        bad_ids = chk[chk.mismatch].product_id.tolist()
        if bad_ids:
            df[df.product_id.isin(bad_ids)].to_excel(os.path.join(OUT_DIR, "variant_mismatch.xlsx"), index=False)
    out_path = os.path.join(OUT_DIR, "mercado_images.xlsx")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_excel(out_path, index=False)


def main():
    folder_tuples: list[tuple[str, str, str]] | None = None
    if not os.path.isfile(TXT_PATH):
        sys.exit(f"[ERR] txt 文件不存在: {TXT_PATH}")
    with open(TXT_PATH, "r", encoding="utf-8") as f:
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