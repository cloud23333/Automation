import tkinter as tk
from tkinter import messagebox
import math

# ─── 固定参数 ──────────────────────────────────────────────────
COMMISSION    = 0.08     # 平台佣金率
ACOS          = 0.3     # 推广费率
DAILY_AD      = 0.05     # 日常广告费率 ← 新增
GROSS_MARGIN  = 0.20     # 目标毛利率
TARGET_REV    = 0.0      # 目标净利润 (RMB)
RMB_TO_USD    = 0.13927034
MIN_PRICE_USD = 3.0
# ────────────────────────────────────────────────────────────

SHIPPING_TABLE = {
    "Brazil": [
        (0.1, 1), (0.2, 1), (0.3, 1), (0.4, 1.5), (0.5, 1.5),
        (0.6, 3), (0.7, 3), (0.8, 3), (0.9, 5), (1.0, 5),
        (1.5, 10), (2.0, 20), (3.0, 30), (4.0, 40),
        (5.0, 52.44), (6.0, 79.67), (7.0, 97.90), (8.0, 111.26),
        (9.0, 124.62), (10.0, 137.98), (11.0, 151.35), (12.0, 164.71),
        (13.0, 178.07), (14.0, 191.43), (15.0, 204.79)
    ],
    "Mexico": [
        (0.1, 1), (0.2, 1), (0.3, 1), (0.4, 1.5), (0.5, 1.5),
        (0.6, 3), (0.7, 3), (0.8, 3), (0.9, 5), (1.0, 5),
        (1.5, 10), (2.0, 20), (3.0, 30), (4.0, 40),
        (5.0, 60.33), (6.0, 76.23), (7.0, 92.12), (8.0, 108.01),
        (9.0, 123.90), (10.0, 139.79), (11.0, 155.69), (12.0, 171.58),
        (13.0, 187.47), (14.0, 203.36), (15.0, 219.25)
    ]
}

# ─── 计算工具函数 ──────────────────────────────────────────────
def ceil_to_100g(weight_kg: float) -> float:
    """不足 100 g 向上取整到 0.1 kg"""
    return math.ceil(weight_kg * 10) / 10

def get_shipping_cost(weight_kg: float, region: str) -> float:
    table = SHIPPING_TABLE.get(region)
    if not table:
        raise ValueError(f"未知地区: {region}")
    w = ceil_to_100g(weight_kg)
    for max_w, cost in table:
        if w <= max_w:
            return cost
    raise ValueError("重量超出阶梯表上限，请补充表格")

def compute_price(product_cost: float, weight_kg: float, region: str) -> tuple:
    ship_cost = get_shipping_cost(weight_kg, region)
    # 分母里再扣 DAILY_AD
    denom1 = 1 - GROSS_MARGIN - COMMISSION - ACOS - DAILY_AD
    denom2 = 1 - COMMISSION - ACOS - DAILY_AD
    if denom1 <= 0 or denom2 <= 0:
        raise ValueError("公式分母 ≤0，请检查费率设置")

    price_profit = (product_cost + ship_cost) / denom1
    price_gm     = (TARGET_REV + product_cost + ship_cost) / denom2
    price_rmb    = max(price_profit, price_gm)
    price_usd    = max(MIN_PRICE_USD, price_rmb * RMB_TO_USD)
    return ceil_to_100g(weight_kg), ship_cost, price_usd

# ─── GUI 回调 ─────────────────────────────────────────────────
def calculate(event=None):
    try:
        cost   = float(entry_cost.get())
        weight = float(entry_weight.get())
        if weight <= 0:
            raise ValueError("重量必须大于 0")

        results = []
        for region in ("Brazil", "Mexico"):
            bill_w, ship_cost, price_usd = compute_price(cost, weight, region)
            results.append(f"[{region}] 建议售价 {price_usd:.2f} USD  | "
                           f"计费重 {bill_w:.1f} kg | 运费 {ship_cost:.2f} RMB")

        label_result.config(text="\n".join(results))
    except Exception as e:
        label_result.config(text="PriceUSD = （输入错误）")
        messagebox.showerror("输入错误", f"请检查输入内容：\n{e}")

# ─── Tkinter UI ───────────────────────────────────────────────
root = tk.Tk()
root.title("售价计算器（成本 & 重量）")
root.geometry("500x260")
root.attributes("-topmost", True)

tk.Label(root, text="产品成本 (RMB)").pack(pady=(12,2))
entry_cost = tk.Entry(root)
entry_cost.insert(0, "1.2")
entry_cost.pack()

tk.Label(root, text="商品重量 (kg)").pack(pady=(10,2))
entry_weight = tk.Entry(root)
entry_weight.insert(0, "0.12")
entry_weight.pack()

btn = tk.Button(root, text="计算 PriceUSD", command=calculate)
btn.pack(pady=15)

label_result = tk.Label(root, text="", fg="blue", font=("Arial", 12),
                        wraplength=480, justify="left")
label_result.pack()

entry_cost.bind("<Return>", calculate)
entry_weight.bind("<Return>", calculate)
btn.bind("<Return>", calculate)

root.mainloop()
