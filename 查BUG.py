"""
调试脚本：找出为何 product_folder.title = BGX22 查不到选项图
会逐步打印：
  1) product_folder 列表（确认有没有 BGX22）
  2) BGX22 的 id
  3) 该 id 下的 SKU 列表
  4) 这些 SKU 与 style 关联情况
  5) style_media 表里 img_role / option_tag 分布
  6) 该文件夹的所有 style_media 明细
运行后把终端输出整体复制给我即可
"""

import pymysql, pandas as pd

DB = dict(host="localhost", user="root", password="123456",
          database="temu_gallery", charset="utf8mb4",
          cursorclass=pymysql.cursors.DictCursor)

FOLDER_TITLE = "BGX22"    # ← 如有需要再改


def show(df, title, head=20):
    print(f"\n=== {title} (共 {len(df)} 行, 预览 {head}) ===")
    if len(df):
        print(df.head(head).to_string(index=False))
    else:
        print("＜空＞")


with pymysql.connect(**DB) as conn, conn.cursor() as cur:
    # 1) 所有 product_folder
    cur.execute("SELECT id, title FROM product_folder ORDER BY id")
    df_pf = pd.DataFrame(cur.fetchall())
    show(df_pf, "product_folder 列表")

    # 2) 找 BGX22 的 id
    cur.execute("SELECT id, title FROM product_folder WHERE title=%s", (FOLDER_TITLE,))
    pf_row = cur.fetchone()
    if not pf_row:
        print(f"\n❌ 没找到 title = '{FOLDER_TITLE}' 的 product_folder！")
        exit()

    folder_id = pf_row["id"]
    print(f"\n✅ 找到 BGX22 的 folder_id = {folder_id}")

    # 3) 该文件夹下全部 SKU
    cur.execute("SELECT sku_code FROM sku WHERE product_id=%s", (folder_id,))
    df_sku = pd.DataFrame(cur.fetchall())
    show(df_sku, f"folder_id={folder_id} 的 SKU 列表")
    if df_sku.empty:
        print("❌ 文件夹里没有任何 SKU，问题就出在插入 sku 时！")
        exit()

    sku_list = tuple(df_sku["sku_code"])
    # 4) 这些 SKU 在 sku_style 是否有绑定
    cur.execute("""
        SELECT ss.sku_code, ss.style_id
        FROM sku_style ss
        WHERE ss.sku_code IN %s
    """, (sku_list,))
    df_bind = pd.DataFrame(cur.fetchall())
    show(df_bind, "SKU ⇌ Style 绑定情况")
    if df_bind.empty:
        print("❌ 这些 SKU 没有绑定任何 Style，检查 Python 的 ensure_binding()!")
        exit()

    style_id_list = tuple(df_bind["style_id"].unique())

    # 5) style_media 的角色 / tag 分布
    cur.execute("""
        SELECT img_role, option_tag, COUNT(*) AS cnt
        FROM style_media
        WHERE style_id IN %s
          AND owner_sku IN %s
        GROUP BY img_role, option_tag
    """, (style_id_list, sku_list))
    df_stats = pd.DataFrame(cur.fetchall())
    show(df_stats, "style_media 角色 & option_tag 分布", head=100)

    # 6) 明细记录（限制 50 行）
    cur.execute("""
        SELECT owner_sku, img_role, option_tag, media_url
        FROM style_media
        WHERE style_id IN %s
          AND owner_sku IN %s
        ORDER BY owner_sku, img_role, option_tag
        LIMIT 50
    """, (style_id_list, sku_list))
    df_detail = pd.DataFrame(cur.fetchall())
    show(df_detail, "style_media 明细（前 50 行）", head=50)
