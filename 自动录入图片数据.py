import os, datetime, pymysql

# ----------------- 基本配置 -----------------
DB_CFG = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
)

ROOT = r"D:\图片录入测试"           # 根目录
URL_PREFIX = "/images/"            # 存到数据库的前缀
IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")
VID_EXT = (".mp4", ".mov", ".avi", ".wmv", ".webm", ".mkv")

# 目录名 ↔ option_tag 字典（可随时追加）
OPTION_TAGS = {
    "qty":   "带数量",
    "noqty": "不带数量",
    # "500Pcs": "带 500 粒",  # 需要时再放开
}

# ----------------- 数据库工具 -----------------
def db_conn():
    return pymysql.connect(**DB_CFG, autocommit=False)

def file_ctime(path):
    try:
        ts = os.path.getctime(path)
    except Exception:
        ts = os.path.getmtime(path)
    return datetime.datetime.fromtimestamp(ts)

def ensure_style(cur, style_code, style_name, ctime, cache):
    if style_code in cache:
        return cache[style_code]

    cur.execute("SELECT style_id FROM style WHERE style_code=%s", (style_code,))
    row = cur.fetchone()
    if row:
        sid = row[0]
    else:
        cur.execute(
            "INSERT INTO style(style_code, style_name, created_at) VALUES (%s,%s,%s)",
            (style_code, style_name, ctime),
        )
        sid = cur.lastrowid
    cache[style_code] = sid
    return sid

def ensure_sku(cur, sku_code, cache):
    if sku_code in cache:
        return True
    cur.execute("SELECT 1 FROM sku WHERE sku_code=%s", (sku_code,))
    found = bool(cur.fetchone())
    if not found:
        print(f"[SKIP] 数据库不存在 sku_code: {sku_code}")
        return False  # 不存在，直接跳过
    cache.add(sku_code)
    return True

def ensure_binding(cur, sku_code, style_id, cache):
    key = (sku_code, style_id)
    if key in cache:
        return
    cur.execute(
        "INSERT IGNORE INTO sku_style(sku_code, style_id) VALUES (%s,%s)", key
    )
    cache.add(key)

def ensure_option_tag(cur, tag_code, tag_name, cache):
    if tag_code in cache:
        return
    cur.execute("INSERT IGNORE INTO option_tag_dict(tag_code,tag_name) VALUES (%s,%s)",
                (tag_code, tag_name))
    cache.add(tag_code)

# ----------------- 主逻辑 -----------------
def main():
    conn = db_conn()
    rows = []
    seen = set()           # 去重 (style_id, media_url)
    sku_cache, bind_cache = set(), set()
    style_cache, tag_cache = {}, set()

    try:
        with conn.cursor() as cur:
            for pf in os.listdir(ROOT):                # 产品文件夹
                pf_path = os.path.join(ROOT, pf)
                if not os.path.isdir(pf_path):
                    continue

                for sf in os.listdir(pf_path):         # Style 文件夹
                    sf_path = os.path.join(pf_path, sf)
                    if not os.path.isdir(sf_path):
                        continue
                    style_id = ensure_style(cur, sf, sf, file_ctime(sf_path), style_cache)

                    for sku_dir in os.listdir(sf_path):  # SKU 文件夹
                        sku_path = os.path.join(sf_path, sku_dir)
                        if not os.path.isdir(sku_path):
                            continue

                        sku_code = sku_dir.replace("^", "*")
                        ensure_sku(cur, sku_code, sku_cache)
                        ensure_binding(cur, sku_code, style_id, bind_cache)

                        # ------ 根目录文件：main/size/detail/video ------
                        for fn in sorted(os.listdir(sku_path)):
                            fp = os.path.join(sku_path, fn)
                            if os.path.isdir(fp) or not _is_media(fn):
                                continue
                            _collect_media(
                                rows, seen, style_id, sku_code, fp,
                                infer_role(fn), None
                            )

                        # ------ 选项图子目录 ------
                        opt_root = os.path.join(sku_path, "选项图")
                        if os.path.isdir(opt_root):
                            for sub in os.listdir(opt_root):
                                tag_code = sub  # 直接用文件夹名
                                tag_name = OPTION_TAGS.get(sub, sub)
                                ensure_option_tag(cur, tag_code, tag_name, tag_cache)

                                sub_path = os.path.join(opt_root, sub)
                                if not os.path.isdir(sub_path):
                                    continue
                                for fn in sorted(os.listdir(sub_path)):
                                    fp = os.path.join(sub_path, fn)
                                    if not _is_media(fn):
                                        continue
                                    _collect_media(
                                        rows, seen, style_id, sku_code, fp,
                                        "option", tag_code
                                    )

            # ------- 批量插入 -------
            if rows:
                cur.executemany(
                    """
                    INSERT IGNORE INTO style_media
                    (style_id, owner_sku, media_type, img_role, option_tag,
                     media_url, sort_order)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    rows
                )
            conn.commit()
    finally:
        conn.close()

# ----------------- 辅助函数 -----------------
def _is_media(fn):
    lower = fn.lower()
    return lower.endswith(IMG_EXT) or lower.endswith(VID_EXT)

def infer_role(fn):
    """根据文件名推断 main / size / detail / video"""
    lower = fn.lower()
    if lower.endswith(VID_EXT):
        return "video"
    if "尺寸图" in fn:
        return "size"
    if "详情图" in fn:
        return "detail"
    return "main"

def _collect_media(rows, seen, style_id, sku_code, abs_path, role, tag):
    rel_path = os.path.relpath(abs_path, ROOT).replace("\\", "/")
    media_url = URL_PREFIX + rel_path
    key = (style_id, media_url)
    if key in seen:
        return
    seen.add(key)

    media_type = "video" if abs_path.lower().endswith(VID_EXT) else "image"
    sort_order = _extract_number(os.path.basename(abs_path))

    rows.append((
        style_id, sku_code, media_type, role, tag, media_url, sort_order
    ))

def _extract_number(filename):
    num = "".join(ch for ch in filename if ch.isdigit())
    try:
        return int(num) if num else 0
    except ValueError:
        return 0

# ----------------- 入口 -----------------
if __name__ == "__main__":
    main()
