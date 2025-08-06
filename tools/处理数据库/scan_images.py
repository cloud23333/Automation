import os, logging, pandas as pd, pymysql
from os.path import abspath, join, normpath, relpath, splitext
from typing import Optional, Tuple, Dict, Set
import datetime

EXCEL_PATH = (
    r"\\Desktop-inv4qoc\图片数据\Temu_半托项目组\倒表格\数据\JST_DATA\Single.xlsx"
)

Mid_pic_folder = r"\\Desktop-inv4qoc\图片数据\1重点图：图片备份\新品临时安置"
Final_pic_folder = r"\\Desktop-inv4qoc\图片数据\整理图库"
ROOT_PATH = Final_pic_folder

DB_CFG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "temu_gallery",
    "charset": "utf8mb4",
    "autocommit": False,
}

IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff")
OPTION_TAG_MAP = {"带数量": "qty", "不带数量": "noqty"}


def db():
    return pymysql.connect(**DB_CFG)


def truncate_tables():
    conn, cur = db(), None
    try:
        cur = conn.cursor()
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("TRUNCATE sku")
        cur.execute("TRUNCATE image_asset")
        cur.execute("TRUNCATE product_folder")
        cur.execute("TRUNCATE option_tag_dict")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
    finally:
        if cur:
            cur.close()
        conn.close()


def normalize_sku(raw: Optional[str]) -> str:
    if raw is None:
        return ""
    return raw.strip().replace("_", "*").replace(" ", "").replace("=", "/").lower()


def ensure_folder(
    cur,
    cache: Dict[Tuple[str, str, str], int],
    folder_code: str,
    style_name: str,
    sku_folder: str,
) -> int:
    key = (folder_code, style_name, sku_folder)
    folder_id = cache.get(key)
    if folder_id:
        return folder_id
    cur.execute(
        "SELECT id FROM product_folder WHERE folder_code=%s AND style_name=%s AND sku_folder=%s",
        key,
    )
    row = cur.fetchone()
    if row:
        folder_id = row[0]
    else:
        cur.execute(
            "INSERT INTO product_folder(folder_code,style_name,sku_folder) VALUES (%s,%s,%s)",
            key,
        )
        folder_id = cur.lastrowid
    cache[key] = folder_id
    return folder_id


def ensure_option_tags(cur):
    cur.execute(
        "CREATE TABLE IF NOT EXISTS option_tag_dict(tag_code VARCHAR(32) PRIMARY KEY,tag_name VARCHAR(64) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    cur.executemany(
        "INSERT IGNORE INTO option_tag_dict(tag_code,tag_name) VALUES (%s,%s)",
        [(code, zh) for zh, code in OPTION_TAG_MAP.items()],
    )


def import_sku(logger: logging.Logger):
    df = pd.read_excel(
        EXCEL_PATH,
        usecols=[
            "商品编码",
            "商品名称",
            "成本价",
            "重量",
            "数量(pcs)",
            "颜色",
            "尺寸规格(mm)",
            "材质",
        ],
        dtype={"商品编码": str},
    )
    df["material_desc"] = (
        df["材质"].fillna("").str.strip().replace({"": None, "/": None})
    )
    df["成本价"] = pd.to_numeric(df["成本价"], errors="coerce").fillna(0.0)
    df["重量"] = pd.to_numeric(df["重量"], errors="coerce").fillna(0.0)

    def clean_txt(x):
        if pd.isna(x):
            return None
        x = str(x).strip()
        return None if x in ["", "/"] else x

    df["qty_desc"] = df["数量(pcs)"].apply(clean_txt)
    df["color_desc"] = df["颜色"].apply(clean_txt)
    df["size_desc"] = df["尺寸规格(mm)"].apply(clean_txt)

    conn, cur = db(), None
    try:
        cur = conn.cursor()
        data = [
            (
                normalize_sku(r["商品编码"]),
                str(r["商品名称"]).strip() if pd.notna(r["商品名称"]) else "",
                float(r["成本价"]),
                float(r["重量"]),
                r["qty_desc"],
                r["color_desc"],
                r["size_desc"],
            )
            for _, r in df.iterrows()
            if normalize_sku(r["商品编码"])
        ]
        cur.executemany(
            """
            INSERT INTO sku
              (sku_code, product_name, cost_price, weight_kg, qty_desc, color_desc, size_desc)
            VALUES
              (%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              product_name = VALUES(product_name),
              cost_price   = VALUES(cost_price),
              weight_kg    = VALUES(weight_kg),
              qty_desc     = VALUES(qty_desc),
              color_desc   = VALUES(color_desc),
              size_desc    = VALUES(size_desc)
            """,
            data,
        )
        conn.commit()
        logger.info("SKU 导入/更新 %d 行", len(data))
    finally:
        if cur:
            cur.close()
        conn.close()


def classify(parts: Tuple[str, ...], fname: str) -> Tuple[str, Optional[str]]:
    if len(parts) > 3:
        tag = next((v for k, v in OPTION_TAG_MAP.items() if k in parts), None)
        return "option", tag
    if "详情图" in fname:
        return "detail", None
    if "尺寸图" in fname:
        return "size", None
    return "main", None


def scan_and_link(logger: logging.Logger):
    conn, cur = db(), None
    try:
        cur = conn.cursor()
        ensure_option_tags(cur)
        cur.execute("SELECT sku_code FROM sku")
        sku_set: Set[str] = {row[0] for row in cur.fetchall()}

        folder_cache: Dict[Tuple[str, str, str], int] = {}
        cnt_option = cnt_link = 0
        not_found_skus: Set[str] = set()

        for root, _, files in os.walk(ROOT_PATH):
            rel_dir = relpath(root, ROOT_PATH)
            if rel_dir == ".":
                continue
            parts = tuple(rel_dir.split(os.sep))
            if len(parts) < 3:
                continue
            folder_id = ensure_folder(cur, folder_cache, *parts[:3])

            for fn in files:
                if not fn.lower().endswith(IMG_EXT):
                    continue

                role, tag = classify(parts, fn)
                abs_path = normpath(abspath(join(root, fn))).replace("/", "\\")

                ctime = os.path.getctime(abs_path)
                created = datetime.datetime.fromtimestamp(ctime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                sku_code = normalize_sku(splitext(fn)[0]) if role == "option" else None
                if sku_code and sku_code not in sku_set:
                    not_found_skus.add(sku_code)
                    sku_code = None

                cur.execute(
                    """
                    INSERT INTO image_asset(
                        folder_id, file_path, img_role,
                        option_tag, sku_code, file_created
                    ) VALUES (%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                      img_role     = VALUES(img_role),
                      option_tag   = VALUES(option_tag),
                      sku_code     = VALUES(sku_code),
                      file_created = VALUES(file_created)
                    """,
                    (folder_id, abs_path, role, tag, sku_code, created),
                )

                if cur.rowcount and role == "option":
                    cnt_option += 1

                if sku_code:
                    cur.execute(
                        """
                        UPDATE sku SET folder_id=%s
                        WHERE sku_code=%s AND (folder_id IS NULL OR folder_id<>%s)
                        """,
                        (folder_id, sku_code, folder_id),
                    )
                    if cur.rowcount:
                        cnt_link += 1

        conn.commit()
        logger.info("IMG 新增/更新选项图 %d 张", cnt_option)
        logger.info("MAP SKU ↔ folder 绑定 %d 条", cnt_link)
        if not_found_skus:
            logger.warning("以下 sku_code 不存在于 sku 表:")
            for s in sorted(not_found_skus):
                logger.warning("  %s", s)
    finally:
        if cur:
            cur.close()
        conn.close()


def init_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("gallery_import")


def main():
    logger = init_logger()
    truncate_tables()
    import_sku(logger)
    scan_and_link(logger)
    logger.info("✅ import_gallery 完成")


if __name__ == "__main__":
    main()
