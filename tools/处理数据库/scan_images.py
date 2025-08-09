import os, logging, pandas as pd, re, datetime
from os.path import abspath, join, normpath, relpath, splitext
from typing import Optional, Tuple, Dict, Set, List
from sqlalchemy import create_engine, text

EXCEL_PATH = (
    r"\\Desktop-inv4qoc\图片数据\Temu_半托项目组\倒表格\数据\JST_DATA\Single.xlsx"
)
Final = r"\\Desktop-inv4qoc\图片数据\整理图库"
Mid = r"\\Desktop-inv4qoc\图片数据\美工摄影的-美工区\新品临时安置"
ROOT_PATH = Final
OUT_XLSX = r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\处理数据库\图库诊断\folder_health.xlsx"

ENGINE = create_engine(
    "mysql+pymysql://root:123456@localhost/temu_gallery?charset=utf8mb4",
    pool_recycle=3600,
    future=True,
)

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
OPTION_TAG_MAP = {"带数量": "qty", "不带数量": "noqty"}

_re_dotzero = re.compile(r"\.0$")


def init_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("gallery_import")


def normalize_sku(raw: Optional[str]) -> str:
    if raw is None:
        return ""
    return raw.strip().replace("_", "*").replace(" ", "").replace("=", "/").lower()


def truncate_tables(conn):
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    conn.execute(text("TRUNCATE sku"))
    conn.execute(text("TRUNCATE image_asset"))
    conn.execute(text("TRUNCATE product_folder"))
    conn.execute(text("TRUNCATE option_tag_dict"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def ensure_option_tags(conn):
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS option_tag_dict(tag_code VARCHAR(32) PRIMARY KEY,tag_name VARCHAR(64) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
    )
    rows = [{"code": code, "zh": zh} for zh, code in OPTION_TAG_MAP.items()]
    if rows:
        conn.execute(
            text(
                "INSERT IGNORE INTO option_tag_dict(tag_code,tag_name) VALUES (:code,:zh)"
            ),
            rows,
        )


def ensure_folder(
    conn,
    cache: Dict[Tuple[str, str, str], int],
    folder_code: str,
    style_name: str,
    sku_folder: str,
) -> int:
    key = (folder_code, style_name, sku_folder)
    folder_id = cache.get(key)
    if folder_id:
        return folder_id
    row = conn.execute(
        text(
            "SELECT id FROM product_folder WHERE folder_code=:a AND style_name=:b AND sku_folder=:c"
        ),
        {"a": folder_code, "b": style_name, "c": sku_folder},
    ).first()
    if row:
        folder_id = int(row[0])
    else:
        res = conn.execute(
            text(
                "INSERT INTO product_folder(folder_code,style_name,sku_folder) VALUES (:a,:b,:c)"
            ),
            {"a": folder_code, "b": style_name, "c": sku_folder},
        )
        folder_id = (
            res.lastrowid
            if res.lastrowid is not None
            else int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar_one())
        )
    cache[key] = folder_id
    return folder_id


def _clean_cell(x):
    if pd.isna(x):
        return None
    x = str(x).strip()
    return None if x in ("", "/") else x


def import_sku(conn, logger: logging.Logger):
    df = pd.read_excel(EXCEL_PATH, sheet_name=0).rename(
        columns=lambda x: str(x).strip()
    )
    if "商品编码" not in df.columns:
        raise ValueError("Excel 缺少列：商品编码")
    df["商品编码"] = (
        df["商品编码"].astype(str).str.strip().str.replace(_re_dotzero, "", regex=True)
    )
    use = [
        "商品编码",
        "商品名称",
        "成本价",
        "重量",
        "数量(pcs)",
        "颜色",
        "尺寸规格(mm)",
        "材质",
    ]
    df = df[[c for c in use if c in df.columns]].copy()
    df["material_desc"] = (
        df.get("材质", "").fillna("").str.strip().replace({"": None, "/": None})
    )
    df["成本价"] = pd.to_numeric(df.get("成本价", 0), errors="coerce").fillna(0.0)
    df["重量"] = pd.to_numeric(df.get("重量", 0), errors="coerce").fillna(0.0)
    df["qty_desc"] = (
        df.get("数量(pcs)", None).apply(_clean_cell)
        if "数量(pcs)" in df.columns
        else None
    )
    df["color_desc"] = (
        df.get("颜色", None).apply(_clean_cell) if "颜色" in df.columns else None
    )
    df["size_desc"] = (
        df.get("尺寸规格(mm)", None).apply(_clean_cell)
        if "尺寸规格(mm)" in df.columns
        else None
    )
    rows: List[dict] = []
    nt = df[
        [
            "商品编码",
            "商品名称",
            "成本价",
            "重量",
            "qty_desc",
            "color_desc",
            "size_desc",
        ]
    ].itertuples(index=False, name=None)
    for sku_code, name, cost, weight, qty, color, size in nt:
        sku_code_n = normalize_sku(sku_code)
        if not sku_code_n:
            continue
        rows.append(
            {
                "sku_code": sku_code_n,
                "product_name": (name.strip() if isinstance(name, str) else ""),
                "cost_price": float(cost),
                "weight_kg": float(weight),
                "qty_desc": qty,
                "color_desc": color,
                "size_desc": size,
            }
        )
    if rows:
        conn.execute(
            text(
                """
                INSERT INTO sku
                  (sku_code, product_name, cost_price, weight_kg, qty_desc, color_desc, size_desc)
                VALUES (:sku_code,:product_name,:cost_price,:weight_kg,:qty_desc,:color_desc,:size_desc)
                ON DUPLICATE KEY UPDATE
                  product_name=VALUES(product_name),
                  cost_price=VALUES(cost_price),
                  weight_kg=VALUES(weight_kg),
                  qty_desc=VALUES(qty_desc),
                  color_desc=VALUES(color_desc),
                  size_desc=VALUES(size_desc)
                """
            ),
            rows,
        )
    logger.info("SKU 导入/更新 %d 行", len(rows))


def classify(parts: Tuple[str, ...], fname: str) -> Tuple[str, Optional[str]]:
    if len(parts) > 3:
        for zh, code in OPTION_TAG_MAP.items():
            if zh in parts:
                return "option", code
    if "详情图" in fname:
        return "detail", None
    if "尺寸图" in fname:
        return "size", None
    return "main", None


def _walk_dirs(root: str):
    stack = [root]
    while stack:
        d = stack.pop()
        with os.scandir(d) as it:
            subs = []
            files = []
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    subs.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(entry)
            yield d, files
            stack.extend(subs)


def scan_and_link(conn, logger: logging.Logger):
    ensure_option_tags(conn)
    sku_set: Set[str] = {
        row[0] for row in conn.execute(text("SELECT sku_code FROM sku")).all()
    }
    folder_cache: Dict[Tuple[str, str, str], int] = {}
    not_found_skus: Set[str] = set()
    to_image_rows: List[dict] = []
    to_link_rows: Set[Tuple[int, str]] = set()
    cnt_option = 0
    for dir_path, entries in _walk_dirs(ROOT_PATH):
        rel_dir = relpath(dir_path, ROOT_PATH)
        if rel_dir == ".":
            continue
        parts = tuple(rel_dir.split(os.sep))
        if len(parts) < 3:
            continue
        folder_id = ensure_folder(conn, folder_cache, *parts[:3])
        for e in entries:
            name = e.name
            ext = splitext(name)[1].lower()
            if ext not in IMG_EXT:
                continue
            role, tag = classify(parts, name)
            abs_path = normpath(abspath(join(dir_path, name))).replace("/", "\\")
            try:
                st = e.stat()
                created = datetime.datetime.fromtimestamp(st.st_ctime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                created = None
            sku_code = normalize_sku(splitext(name)[0]) if role == "option" else None
            if sku_code and sku_code not in sku_set:
                not_found_skus.add(sku_code)
                sku_code = None
            to_image_rows.append(
                {
                    "folder_id": folder_id,
                    "file_path": abs_path,
                    "img_role": role,
                    "option_tag": tag,
                    "sku_code": sku_code,
                    "file_created": created,
                }
            )
            if role == "option":
                cnt_option += 1
            if sku_code:
                to_link_rows.add((folder_id, sku_code))
    if to_image_rows:
        B = 1000
        for i in range(0, len(to_image_rows), B):
            conn.execute(
                text(
                    """
                    INSERT INTO image_asset(
                        folder_id, file_path, img_role, option_tag, sku_code, file_created
                    ) VALUES (:folder_id,:file_path,:img_role,:option_tag,:sku_code,:file_created)
                    ON DUPLICATE KEY UPDATE
                      img_role=VALUES(img_role),
                      option_tag=VALUES(option_tag),
                      sku_code=VALUES(sku_code),
                      file_created=VALUES(file_created)
                    """
                ),
                to_image_rows[i : i + B],
            )
    if to_link_rows:
        conn.execute(
            text(
                """
                UPDATE sku s
                JOIN (
                  SELECT :folder_id AS folder_id, :sku_code AS sku_code
                ) t ON s.sku_code=t.sku_code
                SET s.folder_id=t.folder_id
                WHERE s.folder_id IS NULL OR s.folder_id<>t.folder_id
                """
            ),
            [{"folder_id": fid, "sku_code": code} for fid, code in to_link_rows],
        )
    logger.info("IMG 新增/更新选项图 %d 张", cnt_option)


def export_health_xlsx(engine, root_path: str, out_xlsx: str, logger: logging.Logger):
    q_vh = """
        SELECT vh.folder_id, vh.folder_code, vh.style_name, vh.sku_folder,
               vh.main_cnt, vh.size_cnt, vh.option_cnt,
               vh.qty_option_cnt, vh.noqty_option_cnt, vh.bad_sku_cnt,
               vh.has_few_keyimg, vh.has_bad_option, vh.has_bad_sku
        FROM v_folder_health vh
    """
    q_badopt = """
        SELECT ia.folder_id, ia.file_path, ia.sku_code
        FROM image_asset ia
        WHERE ia.img_role='option' AND (ia.sku_code IS NULL OR ia.sku_code='')
    """
    with engine.connect() as ro:
        df_vh = pd.read_sql(text(q_vh), ro)
        df_badopt = pd.read_sql(text(q_badopt), ro)
    df_vh["文件夹地址"] = df_vh.apply(
        lambda r: os.path.join(
            root_path, str(r["folder_code"]), str(r["style_name"]), str(r["sku_folder"])
        ).replace("/", "\\"),
        axis=1,
    )
    not_good = df_vh[
        (df_vh["has_few_keyimg"] == 1)
        | (df_vh["has_bad_option"] == 1)
        | (df_vh["has_bad_sku"] == 1)
        | (df_vh["size_cnt"] != 1)
    ].copy()
    not_good = not_good.merge(df_badopt, how="left", on="folder_id")
    not_good = not_good.assign(
        大类=not_good["folder_code"],
        风格=not_good["style_name"],
        SKU文件夹=not_good["sku_folder"],
        主图数=not_good["main_cnt"],
        尺寸图数=not_good["size_cnt"],
        选项图数=not_good["option_cnt"],
        带数量张数=not_good["qty_option_cnt"],
        不带数量张数=not_good["noqty_option_cnt"],
        坏SKU张数=not_good["bad_sku_cnt"],
        **{
            "主+尺寸<5": not_good["has_few_keyimg"],
            "选项图有问题": not_good["has_bad_option"],
            "有坏SKU": not_good["has_bad_sku"],
            "问题选项图路径": not_good["file_path"],
            "记录的SKU": not_good["sku_code"],
            "文件夹地址": not_good["文件夹地址"],
        }
    )[
        [
            "大类",
            "风格",
            "SKU文件夹",
            "文件夹地址",
            "主图数",
            "尺寸图数",
            "选项图数",
            "带数量张数",
            "不带数量张数",
            "坏SKU张数",
            "主+尺寸<5",
            "选项图有问题",
            "有坏SKU",
            "问题选项图路径",
            "记录的SKU",
        ]
    ].sort_values(
        by=["大类", "风格", "SKU文件夹", "问题选项图路径"], na_position="last"
    )
    good = df_vh[
        (df_vh["has_few_keyimg"] == 0)
        & (df_vh["has_bad_option"] == 0)
        & (df_vh["has_bad_sku"] == 0)
        & (df_vh["size_cnt"] == 1)
    ].copy()
    good = good.assign(
        大类=good["folder_code"],
        风格=good["style_name"],
        SKU文件夹=good["sku_folder"],
        主图数=good["main_cnt"],
        尺寸图数=good["size_cnt"],
        选项图数=good["option_cnt"],
        带数量张数=good["qty_option_cnt"],
        不带数量张数=good["noqty_option_cnt"],
        坏SKU张数=good["bad_sku_cnt"],
        文件夹地址=good["文件夹地址"],
    )[
        [
            "大类",
            "风格",
            "SKU文件夹",
            "文件夹地址",
            "主图数",
            "尺寸图数",
            "选项图数",
            "带数量张数",
            "不带数量张数",
            "坏SKU张数",
        ]
    ].sort_values(
        by=["大类", "风格", "SKU文件夹"]
    )
    os.makedirs(os.path.dirname(out_xlsx), exist_ok=True)
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        good.to_excel(w, sheet_name="Good", index=False)
        not_good.to_excel(w, sheet_name="not Good", index=False)
    logger.info("报表已导出: %s", out_xlsx)


def main():
    logger = init_logger()
    with ENGINE.begin() as conn:
        truncate_tables(conn)
        import_sku(conn, logger)
        scan_and_link(conn, logger)
    export_health_xlsx(ENGINE, ROOT_PATH, OUT_XLSX, logger)
    logger.info("✅ import_gallery 完成")


if __name__ == "__main__":
    main()
