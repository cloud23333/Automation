import pandas as pd

df = pd.read_excel(r"D:\下载\555444.xlsx")


cols = ["数量(pcs)", "颜色", "尺寸规格(mm)"]


non_empty = lambda x: pd.notna(x) and str(x).strip() != ""


mask_complete = df[cols].applymap(non_empty).all(axis=1)

df_full = df[mask_complete].copy()
df_missing = df[~mask_complete].copy()


df_full.to_excel("好的.xlsx")
df_missing.to_excel("没好.xlsx")
