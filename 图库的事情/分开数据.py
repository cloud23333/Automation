import pandas as pd

df = pd.read_excel(r"D:\下载\商品资料_20250801171534_99677783_1.xlsx")

# 需要同时检查的列
cols = ['数量(pcs)', '颜色', '尺寸规格(mm)']

# ▸ 定义“有值”条件：既不是 NaN，也不是空字符串/全空白
non_empty = lambda x: pd.notna(x) and str(x).strip() != ''

# ▸ 每行是否这 3 列都满足 non_empty
mask_complete = df[cols].applymap(non_empty).all(axis=1)

# ▸ 分出两个 DataFrame
df_full     = df[mask_complete].copy()      # 三列都填了
df_missing  = df[~mask_complete].copy() 


df_full.to_excel('好的.xlsx')
df_missing.to_excel('没好.xlsx')