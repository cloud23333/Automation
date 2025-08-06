import os, csv
from pathlib import Path
from itertools import zip_longest

# === 1. 基本参数 =========================================================
ROOT_PATH = r"\\Desktop-inv4qoc\图片数据\整理图库"   # ← 修改成你的根目录

# 如果想固定列顺序，把大类写在这里；否则按文件夹名字顺序
FIXED_ORDER = []          # 例: ["HDS", "ABS", "BGX", ...]

CSV_NAME = "给小廖的.csv"

cat2styles = {}

# 先确定大类顺序：若给了 FIXED_ORDER 就用它；否则按文件夹自然排序
categories = FIXED_ORDER or sorted(
    d.name for d in os.scandir(ROOT_PATH) if d.is_dir()
)

for cat in categories:
    cat_path = Path(ROOT_PATH, cat)
    if not cat_path.is_dir():
        continue  # FIXED_ORDER 里可能列了不存在的目录，自动跳过

    # 遍历第二层目录得到风格列表，保持文件系统顺序
    styles = [
        p.name for p in os.scandir(cat_path)
        if p.is_dir()
    ]
    # 如需去重并保持顺序：
    seen = set()
    styles = [s for s in styles if not (s in seen or seen.add(s))]
    cat2styles[cat] = styles

if not cat2styles:
    raise SystemExit("❌ 未找到任何大类目录，请检查 ROOT_PATH 设置。")

# === 3. 纵向排列并按行拼接 ===============================================
lists = [cat2styles.get(cat, []) for cat in categories]
max_len = max(len(lst) for lst in lists)
rows = zip_longest(*lists, fillvalue="")

# === 4. 写 CSV ============================================================
csv_path = Path(CSV_NAME)
with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(categories)   # 第一行：大类列标题
    writer.writerows(rows)

print(f"✅ 已生成 {csv_path.resolve()}")
