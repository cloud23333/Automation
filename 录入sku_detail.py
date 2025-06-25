import pandas as pd, pymysql, pathlib, re

xlsx = r"\\Desktop-inv4qoc\图片数据\Temu_半托项目组\倒表格\数据\JST_DATA\Single.xlsx"
if not pathlib.Path(xlsx).is_file():
    raise FileNotFoundError(f"文件未找到: {xlsx}")


def no_chinese(s):
    return not re.search(r"[\u4e00-\u9fa5]", str(s))


df = pd.read_excel(xlsx, engine="openpyxl", dtype={"款式编码": str})
df = df[["款式编码", "商品名称", "成本价", "重量"]]
df["款式编码"] = df["款式编码"].astype(str).str.strip().str.replace(" ", "")
df = df[df["款式编码"].apply(lambda x: bool(x) and no_chinese(x))]
df["成本价"] = pd.to_numeric(df["成本价"], errors="coerce").fillna(0)
df["重量"] = pd.to_numeric(df["重量"], errors="coerce").fillna(0)
df = df.drop_duplicates(subset=["款式编码"], keep="first")

data = [
    (r["款式编码"], r["商品名称"], float(r["成本价"]), float(r["重量"]))
    for _, r in df.iterrows()
]
all_sku = {r[0] for r in data}

db = dict(
    host="localhost",
    user="root",
    password="123456",
    database="temu_gallery",
    charset="utf8mb4",
)

con = pymysql.connect(**db)
try:
    with con.cursor() as cur:
        # 补齐 sku
        cur.execute("SELECT sku_code FROM sku WHERE sku_code IN %s", (tuple(all_sku),))
        exist = {r[0] for r in cur.fetchall()}
        missing = all_sku - exist
        if missing:
            cur.executemany(
                "INSERT INTO product_folder(title) VALUES (NULL)", [() for _ in missing]
            )
            cur.execute("SELECT LAST_INSERT_ID()")
            pid_start = cur.fetchone()[0] - len(missing) + 1
            cur.executemany(
                "INSERT INTO sku(sku_code,product_id) VALUES (%s,%s)",
                [(sku, pid_start + i) for i, sku in enumerate(missing)],
            )
    con.commit()
    with con.cursor() as cur:
        # 查询已存在 sku_detail
        cur.execute(
            "SELECT sku_code FROM sku_detail WHERE sku_code IN %s", (tuple(all_sku),)
        )
        existed_detail = {r[0] for r in cur.fetchall()}
    # 过滤掉已存在的
    data_to_insert = [row for row in data if row[0] not in existed_detail]
    if data_to_insert:
        with con.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO sku_detail(sku_code,product_name,cost_price,weight)
                VALUES (%s,%s,%s,%s)
                """,
                data_to_insert,
            )
        con.commit()
finally:
    con.close()
