from __future__ import annotations
import os, sys, re, json, time
import pandas as pd
from sqlalchemy import create_engine, text
from openai import OpenAI
from tqdm import tqdm

TXT_PATH = r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\创建xlsx\txt文件\mercado_folders.txt"
OUT_DIR = r"C:\Users\Administrator\Documents\Mecrado\Automation\数据"
OUT_XLSX = "mercado.xlsx"

MAX_DESC_LEN = 3500

DB_CONF = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
)

DEEPSEEK_API_KEY = "sk-c73cba2525b74adbb76c271fc7080857"
GPT_MODEL = "deepseek-chat"
OPTION_TAG = "qty"

FF, COMMISSION, ACOS_RATE = 4.2, 0.08, 0.350
GROSS_MARGIN, TARGET_REV_RMB = 0.20, 0.0
RMB_TO_USD, MIN_PRICE_USD = 0.13927034, 4.0

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

_name_cache: dict[str, str] = {}
_title_cache: dict[str, tuple[str,str]] = {}

def engine():
    url = f"mysql+pymysql://{DB_CONF['user']}:{DB_CONF['password']}@{DB_CONF['host']}/{DB_CONF['database']}?charset={DB_CONF['charset']}"
    return create_engine(url, pool_pre_ping=True)

def parse_folder_path(path: str):
    m = re.search(r"整理图库\\([^\\]+)\\([^\\]+)\\([^\\]+)$", path.strip())
    return m.groups() if m else None

def load_data(folders: list[tuple[str, str, str]] | None = None):
    eng = engine()
    with eng.connect() as conn:
        base_sql = """
            SELECT pf.id AS folder_id, pf.folder_code, pf.style_name, pf.sku_folder
            FROM product_folder pf
            WHERE 1=1
        """
        if folders:
            tuples = [(fc, sn, sf) for fc, sn, sf in folders]
            parts = []
            params = {}
            for i, (fc, sn, sf) in enumerate(tuples):
                parts.append(f"(:fc{i}, :sn{i}, :sf{i})")
                params[f"fc{i}"] = fc
                params[f"sn{i}"] = sn
                params[f"sf{i}"] = sf
            base_sql += " AND (pf.folder_code, pf.style_name, pf.sku_folder) IN (" + ",".join(parts) + ")"
            prod = pd.read_sql(text(base_sql), conn, params=params)
        else:
            base_sql += " AND pf.folder_code = :fc AND pf.style_name = :sn"
            prod = pd.read_sql(text(base_sql), conn, params={"fc": "MN-玛瑙", "sn": "风格1"})

        sku = pd.read_sql(
            text("SELECT sku_code, product_name, cost_price, weight_kg, folder_id, qty_desc, color_desc, size_desc, material_desc FROM sku"),
            conn,
        )
        img = pd.read_sql(
            text("SELECT folder_id, file_path, img_role, option_tag, sku_code FROM image_asset"),
            conn,
        )
    sku["sku_code"] = sku.sku_code.str.upper()
    img["sku_code"] = img.sku_code.str.upper()
    return prod, sku, img

def _clean_title(t: str) -> str:
    t = re.sub(r"[#\\/+%^*<>$@~|]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = t[:60]
    t = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", "", t)
    return t.strip()

def _num_range(vals):
    nums = []
    for v in vals:
        m = re.search(r"\d+(\.\d+)?", str(v))
        if m:
            s = m.group()
            try:
                f = float(s)
                nums.append(f)
            except:
                pass
    if not nums:
        return ""
    mn, mx = min(nums), max(nums)
    if mn.is_integer() and mx.is_integer():
        mn, mx = int(mn), int(mx)
    return f"{mn}-{mx}" if mn != mx else f"{mn}"

def _strip_fence(txt: str) -> str:
    s = txt.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        if s.endswith("```"):
            s = s[: -3]
    return s.strip()

def _extract_json(s: str) -> dict:
    s = _strip_fence(s)
    m = re.search(r"\{[\s\S]*\}\s*$", s)
    if not m:
        raise ValueError("no json")
    frag = m.group(0)
    return json.loads(frag)

def translate_names(names: list[str]) -> list[str]:
    todo = [n for n in names if n not in _name_cache]
    if todo:
        joined = " | ".join(todo)
        rsp = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a translator."},
                {
                    "role": "user",
                    "content": "Translate the following Chinese product names to concise natural English, keep the order, separate each with ' | ' only: " + joined,
                },
            ],
            temperature=0,
        )
        out_raw = rsp.choices[0].message.content or ""
        outs = [x.strip() for x in out_raw.split("|")]
        if len(outs) < len(todo):
            outs += todo[len(outs):]
        for zh, en in zip(todo, outs):
            _name_cache[zh] = en or zh
    return [_name_cache.get(n, n) for n in names]

def gpt_title_desc(names, qty_set, size_set, color_set, weight_set, material_set, tries=3):
    qty_txt = _num_range(qty_set)
    size_txt = _num_range(size_set)
    weight_txt = _num_range(weight_set)
    color_txt = ", ".join(sorted(list(color_set))[:1])
    mat_txt = ", ".join(sorted(list(material_set))[:1])
    parts = []
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
    title_rule = f"TITLE must contain: {prefix}, product name." if prefix else "TITLE must contain the product name."
    key = "|".join(names[:20]) + "||" + title_rule
    if key in _title_cache:
        return _title_cache[key]
    sys_msg = "You are an e-commerce copywriter."
    user_msg = (
        "Create a concise English product title (≤55 chars incl. spaces) and a detailed English bullet-style description.\n"
        f"{title_rule}\n"
        "DESCRIPTION requirements:\n"
        "• 10-12 bullets, each ≤35 words.\n"
        "• Cover: material & finish, exact size/weight & pack qty, DIY use cases, creative project ideas, benefits, quality assurance, shipping info, storage/care tips, brand story, plus a call-to-action.\n"
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
            content = rsp.choices[0].message.content or ""
            data = _extract_json(content)
            title = _clean_title(str(data.get("title", "")))
            desc = re.sub(r"\s+\n", "\n", str(data.get("desc", "")))[:MAX_DESC_LEN].strip()
            if title:
                _title_cache[key] = (title, desc)
                return title, desc
        except:
            time.sleep(1.2)
    fallback_name = names[0] if names else "Beads"
    qty_txt = _num_range(qty_set) or ""
    size_txt = _num_range(size_set) or ""
    pre = " ".join([f"{size_txt}mm" if size_txt else "", f"{qty_txt}pcs" if qty_txt else ""]).strip()
    title = _clean_title(f"{pre} {fallback_name}".strip()) or fallback_name
    desc = "Jewelry-making beads. Ideal for DIY crafts and decorations. Add to cart today."
    _title_cache[key] = (title, desc)
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
        opt_all = img_df[(img_df.folder_id == pf.folder_id) & (img_df.img_role == "option") & (img_df.sku_code.notnull())]
        opt_qty = opt_all[opt_all.option_tag == "qty"]
        opt_noqty = opt_all[opt_all.option_tag == "noqty"]
        opts = opt_qty if OPTION_TAG == "qty" and len(opt_qty) else opt_noqty if OPTION_TAG == "noqty" and len(opt_noqty) else opt_all
        if opts.empty:
            continue
        opt_skus = opts.sku_code.unique()
        subset = sku_df[sku_df.sku_code.isin(opt_skus)]
        if subset.empty:
            continue
        qty_set = {q for q in subset.qty_desc.dropna().unique() if q and q != "/"}
        size_set = {s for s in subset.size_desc.dropna().unique() if s and s != "/"}
        color_set = {c for c in subset.color_desc.dropna().unique() if c and c != "/"}
        mat_set = {m for m in subset.material_desc.dropna().unique() if m and m != "/"}
        weight_set = {round(float(w) * 1000, 2) for w in subset.weight_kg.dropna().unique() if w}
        price_usd = calc_price_usd(subset.cost_price.max())
        names_raw = subset.product_name.dropna().unique().tolist() or [pf.sku_folder]
        names = translate_names(names_raw)
        title, desc_gpt = gpt_title_desc(names, qty_set, size_set, color_set, weight_set, mat_set)
        def fmt(v):
            try:
                f = float(v)
                return str(int(f)) if f.is_integer() else str(f)
            except:
                return str(v)
        pairs_df = (
            subset[["size_desc", "qty_desc"]]
            .dropna()
            .loc[lambda d: (d.size_desc != "/") & (d.qty_desc != "/")]
            .assign(size_val=lambda d: pd.to_numeric(d.size_desc, errors="coerce"))
            .sort_values("size_val", ignore_index=True)
        )
        mapping_lines = [f"{fmt(r.size_desc)}mm-{fmt(r.qty_desc)}pcs" for _, r in pairs_df.iterrows()]
        mapping_text = "\n".join(dict.fromkeys(mapping_lines))
        full_desc = (desc_gpt or "").strip()
        if mapping_text:
            full_desc = f"{full_desc}\n\nAvailable packs:\n{mapping_text}"
        rows[next_id] = dict(
            id=next_id,
            title=title,
            desc=full_desc[:MAX_DESC_LEN],
            global_price=price_usd,
            category="Beads",
            attribute="Generic",
            attr_value="Beads",
            folder_id=pf.folder_id,
            folder_name=pf.sku_folder,
        )
        next_id += 1
    df = pd.DataFrame.from_dict(rows, orient="index")
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
        opts = opt_qty if OPTION_TAG == "qty" and len(opt_qty) else opt_noqty if OPTION_TAG == "noqty" and len(opt_noqty) else g[g.img_role == "option"]
        if opts.empty:
            continue
        for r in opts.itertuples():
            pics = [r.file_path] + main + detail + size_pic
            pics = pics[:10]
            attr = attr_map.get(r.sku_code, {}) or {}
            row = dict(
                id=img_idx,
                product_id=pr.id,
                size=(attr.get("size_desc") or ""),
                pack="2",
                color=(attr.get("color_desc") or ""),
                qty=(attr.get("qty_desc") or ""),
                sku=r.sku_code,
            )
            for i, p in enumerate(pics, 1):
                row[f"img_path{i}"] = p
            out_rows.append(row)
            img_idx += 1
    df = pd.DataFrame(out_rows)
    return df

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
    if products_out.empty:
        sys.exit("[ERR] 未生成任何产品行")
    images_out = make_images(products_out, img_df, sku_df)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, OUT_XLSX)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        products_out.to_excel(writer, index=False, sheet_name="products")
        images_out.to_excel(writer, index=False, sheet_name="images")
    print("✅ 全部完成")

if __name__ == "__main__":
    main()