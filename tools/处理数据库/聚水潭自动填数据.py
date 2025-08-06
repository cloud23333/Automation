import re
import pandas as pd
from pathlib import Path
import numpy as np

src_path = Path(r"C:\Users\Administrator\Documents\Mecrado\Automation\没好.xlsx")
df = pd.read_excel(src_path)

key_cols = ["数量(pcs)", "颜色", "尺寸规格(mm)"]
for col in key_cols:
    if col not in df.columns:
        df[col] = np.nan

qty_name_pat = re.compile(r"(\d+)\s*(?:pcs|颗|个)", re.I)
qty_code_pat = re.compile(r"-(\d+)\s*pcs",               re.I)
size_pat      = re.compile(r"(\d+(?:\.\d+)?)\s*mm",      re.I)

def safe_text(val) -> str:
    return "" if pd.isna(val) else str(val)

def extract_size(text):
    m = size_pat.search(safe_text(text))
    return float(m.group(1)) if m else None

def extract_qty(row):
    name = safe_text(row["商品名称"])
    code = safe_text(row["款式编码"])
    m = qty_name_pat.search(name)
    if m:
        return int(m.group(1))
    m = qty_code_pat.search(code)
    if m:
        return int(m.group(1))
    return None

# ────────── 4. 仅填空白单元格 ──────────
for idx, row in df.iterrows():
    # 尺寸规格(mm)
    if pd.isna(row["尺寸规格(mm)"]):
        size = extract_size(row["商品名称"]) or extract_size(row["款式编码"])
        if size is not None:
            df.at[idx, "尺寸规格(mm)"] = size

    # 数量(pcs)
    if pd.isna(row["数量(pcs)"]):
        qty = extract_qty(row)
        if qty is not None:
            df.at[idx, "数量(pcs)"] = qty

# ────────── 5. 剔除已完整数据行 ──────────
df = df[df[key_cols].isna().any(axis=1)].reset_index(drop=True)

# ────────── 6. 保存 ──────────
out_path = src_path.with_stem(src_path.stem + "_filled")
df.to_excel(out_path, index=False)
print(f"已保存：{out_path}")
