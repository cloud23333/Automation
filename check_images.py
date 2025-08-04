from __future__ import annotations
import sys, os, argparse
import pandas as pd

DEFAULT_XLSX = r"C:\Users\Administrator\Documents\Mecrado\Automation\数据\images.xlsx"


def load_df(path: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, dtype=str)
    except Exception as e:
        sys.exit(f"[ERR] 读取 {path} 失败: {e}")
    for col in ("product_id", "size", "pack", "color"):
        if col not in df.columns:
            sys.exit(f"[ERR] 列缺失: {col}")
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df


def validate(df: pd.DataFrame) -> pd.DataFrame:
    r1 = df["color"] == ""
    r2 = df.duplicated(subset=["product_id", "color"], keep=False) & ~r1
    r3 = df.duplicated(subset=["product_id", "size", "pack", "color"], keep=False)
    r4 = pd.Series(False, index=df.index)

    for pid, grp in df.groupby("product_id"):
        sizes = grp["size"].unique()
        packs = grp["pack"].unique()
        colors = grp["color"].unique()
        expected = len(sizes) * len(packs) * len(colors)
        actual = grp[["size", "pack", "color"]].drop_duplicates().shape[0]
        if expected != actual:
            r4.loc[grp.index] = True

    df["R1_no_color"] = r1
    df["R2_dup_color"] = r2
    df["R3_dup_combo"] = r3
    df["R4_miss_combo"] = r4
    return df


def main():
    ap = argparse.ArgumentParser(description="Validate images.xlsx")
    ap.add_argument("xlsx", nargs="?", default=DEFAULT_XLSX, help="路径")
    args = ap.parse_args()

    xlsx_path = args.xlsx
    if not os.path.isfile(xlsx_path):
        sys.exit(f"[ERR] 文件不存在: {xlsx_path}")

    df = load_df(xlsx_path)
    df = validate(df)

    print("=== Validation Summary ===")
    print(f"总行数            : {len(df)}")
    print(f"缺色行 (R1)       : {df['R1_no_color'].sum()}")
    print(f"颜色重复行 (R2)   : {df['R2_dup_color'].sum()}")
    print(f"组合重复行 (R3)   : {df['R3_dup_combo'].sum()}")
    print(f"组合缺失行 (R4)   : {df['R4_miss_combo'].sum()}")

    viol_mask = df.filter(like="R").any(axis=1)
    if viol_mask.any():
        out_path = os.path.splitext(xlsx_path)[0] + "_violations.xlsx"
        df[viol_mask].to_excel(out_path, index=False)
        print(f"\n⚠️  发现违规 {viol_mask.sum()} 行，详情已导出: {out_path}")
    else:
        print("\n✅  全部通过，无违规行。")


if __name__ == "__main__":
    main()
