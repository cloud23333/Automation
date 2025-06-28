import math, re, pymysql

# ---------- 数据库连接 --------------------------------------------------------
DB = dict(host="localhost", user="root", password="123456",
          database="temu_gallery", charset="utf8mb4", autocommit=False)

def db():                       # 取得连接
    return pymysql.connect(**DB)

# ---------- 价格计算 ----------------------------------------------------------
def compute_global_price(costs):
    """最高成本 ×2.5 向上取 0.1 元"""
    if not costs:
        return None
    max_cost = max(map(float, costs))
    return math.ceil(max_cost * 2.5 * 10) / 10

# ---------- SKU → Diameter / Length / Color ----------------------------------
diam_pat   = re.compile(r'(\d+(?:\.\d+)?)\s*mm', re.I)   # 3mm / 4.5MM
length_pat = re.compile(r'-(\d+)(?:PCS|X)?', re.I)       # -2 / -2PCS
color_pat  = re.compile(r'([A-Za-z]+)$')                 # 末尾字母串

def parse_attrs(sku):
    diam  = diam_pat.search(sku)
    leng  = length_pat.search(sku)
    color = color_pat.search(sku)
    return (
        diam.group(1)  if diam  else None,
        leng.group(1)  if leng  else None,
        color.group(1) if color else None,
    )

# ---------- 主流程 ------------------------------------------------------------
def main():
    conn = db()
    cur  = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # ① 找需要入队的 folder
        cur.execute("""
            SELECT pf.id folder_id, pf.folder_code, pf.style_name, pf.sku_folder
              FROM product_folder pf
             WHERE NOT EXISTS (SELECT 1 FROM listing_queue l WHERE l.folder_id = pf.id)
               AND EXISTS  (SELECT 1 FROM image_asset ia
                              WHERE ia.folder_id = pf.id AND ia.img_role='option')
        """)
        folders = cur.fetchall()
        if not folders:
            print("没有新的文件夹需要入队")
            return

        for f in folders:
            fid = f["folder_id"]

            # ② 选项图 + 成本
            cur.execute("""
               SELECT DISTINCT ia.sku_code, ia.option_tag,
                               s.cost_price,  s.weight_kg
                 FROM image_asset ia
                 JOIN sku s ON ia.sku_code = s.sku_code
                WHERE ia.folder_id=%s
                  AND ia.img_role='option'
                  AND ia.sku_code IS NOT NULL
            """, (fid,))
            rows = cur.fetchall()
            if not rows:
                print(f"[跳过] {f['sku_folder']}：无选项图或SKU")
                continue

            gp = compute_global_price([r["cost_price"] for r in rows if r["cost_price"]])
            if gp is None:
                print(f"[跳过] {f['sku_folder']}：成本缺失")
                continue

            # ③ 插 listing_queue
            title = f"{f['folder_code']} {f['style_name']} {f['sku_folder']}"
            cur.execute("""
                INSERT INTO listing_queue
                       (folder_id,title,description,global_price,
                        category,attribute,attr_value)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (fid, title, f"{title} 自动上新", gp,
                  "Beads", "Generic", "Hematite"))
            qid = cur.lastrowid

            # ④ 插 listing_queue_variant
            ok_cnt = 0
            for r in rows:
                diam, leng, col = parse_attrs(r["sku_code"])
                if not all([diam, leng, col]):
                    print(f"⚠️ 解析失败跳过 SKU {r['sku_code']}")
                    continue

                # 选优先“带数量”的选项图
                cur.execute("""
                    SELECT file_path, option_tag
                      FROM image_asset
                     WHERE folder_id=%s
                       AND img_role='option'
                       AND sku_code=%s
                     ORDER BY (option_tag='qty') DESC
                     LIMIT 1
                """, (fid, r["sku_code"]))
                img = cur.fetchone() or {}

                cur.execute("""
                    INSERT INTO listing_queue_variant
                       (queue_id, sku_code, diameter_mm, length_mm, color,
                        cost_price, weight_kg, option_img, option_tag)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                      diameter_mm=VALUES(diameter_mm),
                      length_mm  =VALUES(length_mm),
                      color      =VALUES(color),
                      cost_price =VALUES(cost_price),
                      weight_kg  =VALUES(weight_kg),
                      option_img =VALUES(option_img),
                      option_tag =VALUES(option_tag)
                """, (qid, r["sku_code"], diam, leng, col,
                      r["cost_price"], r["weight_kg"],
                      img.get("file_path"), img.get("option_tag")))
                ok_cnt += 1

            print(f"[OK] 入队 {title} → ¥{gp}（写入 {ok_cnt}/{len(rows)} 变体）")

        conn.commit()
    finally:
        cur.close()
        conn.close()

# --------- 入口 --------------------------------------------------------------
if __name__ == "__main__":
    main()
