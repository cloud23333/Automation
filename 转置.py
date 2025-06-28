import pandas as pd
from pathlib import PureWindowsPath

TXT_FILE = r"D:\下载\转置.txt"       # 先把那段文本粘到这个文件
OUT_XLSX = "links_horizontal.xlsx"

rows, group = [], []

with open(TXT_FILE, encoding="utf-8") as f:
    for line in f:
        l = line.strip()
        if not l:                         # 遇到空行 ⇒ 完成一个分段
            if group:
                rows.append(group.copy())
                group.clear()
            continue
        group.append(l)

# 收尾
if group:
    rows.append(group)

# ➜ 写入 DataFrame；顺便抽出尺寸 mm 当作额外字段
df = pd.DataFrame(rows, columns=["sku_img", "main1", "main2", "main3", "main4", "main5"])
df.insert(
    0,
    "size",
    df["sku_img"].apply(lambda p: PureWindowsPath(p).stem.replace("mm", ""))
)

df.to_excel(OUT_XLSX, index=False)        # 直接得到横向表格
print(f"已生成：{OUT_XLSX}")
