import pandas as pd

xl = pd.ExcelFile(
    r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\管理在售\数据\各站点在售商品.xlsx"
)
df_site = xl.parse(0)
df_check = xl.parse(1)

site_skus = {str(x).strip() for x in df_site.values.ravel() if pd.notna(x)}

check_skus = set(df_check["sku编码"].astype(str).str.strip())

missing = sorted(check_skus - site_skus)

print(f"共 {len(missing)} 个缺失 SKU：")

pd.DataFrame({"缺失SKU": missing}).to_excel(
    r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\管理在售\数据\missing_skus.xlsx",
    index=False,
)
