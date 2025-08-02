#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_images.py ─ 校验 images.xlsx 的 size / pack / color 规则
固定路径已写在 DEFAULT_XLSX，可用命令行参数临时覆盖
"""
from __future__ import annotations
import sys, os, argparse
import pandas as pd

# === 1. 在这里改成你的实际文件地址 ================================
DEFAULT_XLSX = (
    r"C:\Users\Administrator\Documents\Mecrado\Automation\数据\images.xlsx"
)
# ===================================================================

def load_df(path: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, dtype=str)
    except Exception as e:
        sys.exit(f"[ERR] 读取 {path} 失败: {e}")
    # 统一空值表示
    for col in ("product_id", "size", "pack", "color"):
        if col not in df.columns:
            sys.exit(f"[ERR] 列缺失: {col}")
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df

def validate(df: pd.DataFrame) -> pd.DataFrame:
    # R1 缺色
    r1 = df["color"] == ""
    # R2 同 product_id 颜色重复
    r2 = df.duplicated(subset=["product_id", "color"], keep=False) & ~r1
    # R3 同 product_id (size,pack,color) 重复
    r3 = df.duplicated(subset=["product_id", "size", "pack", "color"], keep=False)
    df["R1_no_color"]  = r1
    df["R2_dup_color"] = r2
    df["R3_dup_combo"] = r3
    return df

def main():
    ap = argparse.ArgumentParser(description="Validate images.xlsx")
    ap.add_argument("xlsx", nargs="?", default=DEFAULT_XLSX,
                    help="路径 (默认: %(default)s)")
    args = ap.parse_args()

    xlsx_path = args.xlsx
    if not os.path.isfile(xlsx_path):
        sys.exit(f"[ERR] 文件不存在: {xlsx_path}")

    df = load_df(xlsx_path)
    df = validate(df)

    total = len(df)
    r1_cnt = df["R1_no_color"].sum()
    r2_cnt = df["R2_dup_color"].sum()
    r3_cnt = df["R3_dup_combo"].sum()

    print("=== Validation Summary ===")
    print(f"总行数            : {total}")
    print(f"缺色行 (R1)       : {r1_cnt}")
    print(f"颜色重复行 (R2)   : {r2_cnt}")
    print(f"组合重复行 (R3)   : {r3_cnt}")

    viol_mask = df[["R1_no_color", "R2_dup_color", "R3_dup_combo"]].any(axis=1)
    if viol_mask.any():
        out_path = os.path.splitext(xlsx_path)[0] + "_violations.xlsx"
        df[viol_mask].to_excel(out_path, index=False)
        print(f"\n⚠️  发现违规 {viol_mask.sum()} 行，详情已导出: {out_path}")
    else:
        print("\n✅  全部通过，无违规行。")

if __name__ == "__main__":
    main()
