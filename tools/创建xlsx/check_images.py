from __future__ import annotations
import sys, os, argparse, datetime as dt
import pandas as pd
from itertools import product

DEFAULT_XLSX = r"C:\Users\Administrator\Documents\Mecrado\Automation\数据\mercado.xlsx"

REQ_COLS = ("product_id", "size", "pack", "color")

def read_sheet(path: str, sheet_opt: str|int|None) -> pd.DataFrame:
    try:
        if sheet_opt is not None:
            return pd.read_excel(path, sheet_name=sheet_opt, dtype=str, keep_default_na=False)
        try:
            return pd.read_excel(path, sheet_name="images", dtype=str, keep_default_na=False)
        except Exception:
            return pd.read_excel(path, sheet_name=1, dtype=str, keep_default_na=False)
    except Exception as e:
        sys.exit(f"[ERR] 读取 {path} 失败: {e}")

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
    for col in REQ_COLS:
        if col not in df.columns:
            sys.exit(f"[ERR] 列缺失: {col}")
    df["product_id"] = df["product_id"].astype(str).str.strip()
    df["size"] = df["size"].astype(str).str.strip()
    df["pack"] = df["pack"].astype(str).str.strip()
    df["color"] = df["color"].astype(str).str.strip()
    df["color_norm"] = df["color"].where(df["color"] != "", None)
    if df["color_norm"].notna().any():
        df["color_norm"] = df["color_norm"].str.casefold().str.strip().str.title()
    df["color_eff"] = df["color_norm"].fillna("")
    return df

def find_missing_combos(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid, g in df.groupby("product_id", sort=False):
        sizes = sorted(g["size"].unique().tolist())
        packs = sorted(g["pack"].unique().tolist())
        colors = sorted([c for c in g["color_eff"].unique().tolist() if c != ""])
        if not colors:
            continue
        have = g[["size","pack","color_eff"]].drop_duplicates()
        have_tuples = set(map(tuple, have.values.tolist()))
        for s, p, c in product(sizes, packs, colors):
            if (s, p, c) not in have_tuples:
                rows.append({"product_id": pid, "size": s, "pack": p, "color": c})
    return pd.DataFrame(rows)

def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    r1 = df["color"].eq("")
    r2 = df.duplicated(subset=["product_id","size","color_eff"], keep=False) & ~r1
    r3 = df.duplicated(subset=["product_id","size","pack","color_eff"], keep=False)
    miss = find_missing_combos(df)
    r4 = pd.Series(False, index=df.index)
    if not miss.empty:
        key = df.assign(color_eff=df["color_eff"])[["product_id","size","pack","color_eff"]]
        mk = pd.merge(
            key,
            miss.rename(columns={"color":"color_eff"}),
            how="left",
            on=["product_id","size","pack","color_eff"],
            indicator=True
        )["_merge"].eq("both")
        r4.loc[mk[mk].index] = True
    out = df.copy()
    out["R1_no_color"] = r1
    out["R2_dup_color"] = r2
    out["R3_dup_combo"] = r3
    out["R4_miss_combo"] = r4
    return out, miss

def main():
    ap = argparse.ArgumentParser(description="Validate images sheet in Excel")
    ap.add_argument("xlsx", nargs="?", default=DEFAULT_XLSX, help="路径")
    ap.add_argument("--sheet", help="工作表名或索引", default=None)
    ap.add_argument("--strict", action="store_true", help="有违规则退出非零码")
    args = ap.parse_args()

    xlsx_path = args.xlsx
    if not os.path.isfile(xlsx_path):
        sys.exit(f"[ERR] 文件不存在: {xlsx_path}")

    sheet_opt = None
    if args.sheet is not None:
        try:
            sheet_opt = int(args.sheet)
        except ValueError:
            sheet_opt = args.sheet

    df = read_sheet(xlsx_path, sheet_opt)
    df = normalize(df)
    vdf, miss = validate(df)

    print("=== Validation Summary ===")
    print(f"总行数            : {len(vdf)}")
    print(f"缺色行 (R1)       : {int(vdf['R1_no_color'].sum())}")
    print(f"颜色重复行 (R2)   : {int(vdf['R2_dup_color'].sum())}")
    print(f"组合重复行 (R3)   : {int(vdf['R3_dup_combo'].sum())}")
    print(f"组合缺失行 (R4)   : {int(vdf['R4_miss_combo'].sum())}")
    viol_mask = vdf.filter(like="R").any(axis=1)
    if viol_mask.any() or (not miss.empty):
        ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = os.path.splitext(xlsx_path)[0] + f"_violations_{ts}.xlsx"
        with pd.ExcelWriter(out_path, engine="openpyxl") as w:
            vdf[viol_mask].to_excel(w, index=False, sheet_name="violations")
            if not miss.empty:
                miss.to_excel(w, index=False, sheet_name="missing_combos")
        print(f"\n⚠️  发现违规 {int(viol_mask.sum())} 行，详情已导出: {out_path}")
        if args.strict:
            sys.exit(2)
    else:
        print("\n✅  全部通过，无违规行。")

if __name__ == "__main__":
    main()
