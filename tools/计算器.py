from decimal import Decimal, ROUND_UP, ROUND_HALF_UP, getcontext
import tkinter as tk
from ttkbootstrap import Window, Style
from ttkbootstrap.constants import *
import ttkbootstrap as tb
from bisect import bisect_left
from tkinter import messagebox

getcontext().prec = 28

CONFIG = {
    "COMMISSION":   Decimal("0.08"),
    "ACOS":         Decimal("0.30"),
    "DAILY_AD":     Decimal("0.05"),
    "GROSS_MARGIN": Decimal("0.20"),
    "TARGET_REV":   Decimal("0.00"),
    "RMB_TO_USD":   Decimal("0.13927034"),
    "MIN_PRICE_USD":Decimal("3.00"),
    "PRICE_99":     False
}

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

TABLE_INT = {
    r: ( [int(Decimal(str(w))*Decimal(10)) for w,_ in lst],
         [Decimal(str(c)) for _,c in lst] )
    for r,lst in SHIPPING_TABLE.items()
}

def ceil_to_100g_units(weight_kg: Decimal) -> int:
    units = (weight_kg * Decimal(10))
    return int(units.to_integral_value(rounding=ROUND_UP))

def units_to_kg(units: int) -> Decimal:
    return (Decimal(units) / Decimal(10)).quantize(Decimal("0.1"))

def get_shipping_cost(weight_kg: Decimal, region: str):
    if region not in TABLE_INT:
        raise ValueError(f"未知地区: {region}")
    limits, costs = TABLE_INT[region]
    u = ceil_to_100g_units(weight_kg)
    idx = bisect_left(limits, u)
    if idx >= len(limits):
        max_kg = limits[-1] / 10
        raise ValueError(f"重量超出{region}阶梯上限（≤{max_kg} kg），请补充表格")
    return units_to_kg(limits[idx]), costs[idx]

def price_calc(cost_rmb: Decimal, weight_kg: Decimal, region: str):
    bill_w, ship_cost = get_shipping_cost(weight_kg, region)
    cm, ac, da, gm = CONFIG["COMMISSION"], CONFIG["ACOS"], CONFIG["DAILY_AD"], CONFIG["GROSS_MARGIN"]
    denom1 = Decimal(1) - gm - cm - ac - da
    denom2 = Decimal(1) - cm - ac - da
    if denom1 <= 0 or denom2 <= 0:
        raise ValueError(f"费率设置不合理：denom1={denom1}, denom2={denom2}")
    price_profit = (cost_rmb + ship_cost) / denom1
    price_gm     = (CONFIG["TARGET_REV"] + cost_rmb + ship_cost) / denom2
    price_rmb    = max(price_profit, price_gm)
    usd = price_rmb * CONFIG["RMB_TO_USD"]
    if usd < CONFIG["MIN_PRICE_USD"]:
        usd = CONFIG["MIN_PRICE_USD"]
    usd = usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if CONFIG["PRICE_99"]:
        cents = usd - usd.to_integral_value()
        if cents != Decimal("0.99"):
            usd = (usd.to_integral_value() + Decimal("0.99"))
    platform_fee = usd / CONFIG["RMB_TO_USD"] * cm
    ad_fee = usd / CONFIG["RMB_TO_USD"] * (ac + da)
    return {
        "region": region,
        "bill_w": bill_w,
        "ship_cost": ship_cost,
        "price_rmb": price_rmb.quantize(Decimal("0.01")),
        "price_usd": usd,
        "platform_fee_rmb": platform_fee.quantize(Decimal("0.01")),
        "ad_fee_rmb": ad_fee.quantize(Decimal("0.01"))
    }

class App:
    def __init__(self):
        self.win = Window(title="售价计算器（成本 & 重量）", themename="cosmo")
        self.win.geometry("720x460")
        self.style = Style()
        self.build_ui()

    def build_ui(self):
        header = tb.Frame(self.win, padding=16)
        header.pack(fill=X)
        tb.Label(header, text="售价计算器", font=("", 16, "bold")).pack(side=LEFT)
        self.theme_var = tk.StringVar(value="cosmo")
        themes = ["cosmo","flatly","darkly","cyborg","morph","superhero","journal","minty"]
        tb.Combobox(header, values=themes, textvariable=self.theme_var, width=12).pack(side=RIGHT, padx=6)
        tb.Button(header, text="切换主题", bootstyle=INFO, command=self.switch_theme).pack(side=RIGHT)

        body = tb.Frame(self.win, padding=12)
        body.pack(fill=BOTH, expand=YES)

        card_left = tb.Labelframe(body, text="输入", padding=16, bootstyle=PRIMARY)
        card_left.pack(side=LEFT, fill=Y)
        tb.Label(card_left, text="产品成本 (RMB)").grid(row=0, column=0, sticky=W, pady=(0,6))
        self.ent_cost = tb.Entry(card_left, width=18)
        self.ent_cost.insert(0, "1.20")
        self.ent_cost.grid(row=0, column=1, sticky=EW, padx=(8,0), pady=(0,6))

        tb.Label(card_left, text="商品重量 (kg)").grid(row=1, column=0, sticky=W, pady=6)
        self.ent_weight = tb.Entry(card_left, width=18)
        self.ent_weight.insert(0, "0.12")
        self.ent_weight.grid(row=1, column=1, sticky=EW, padx=(8,0), pady=6)

        btn_row = tb.Frame(card_left)
        btn_row.grid(row=2, column=0, columnspan=2, pady=(10,0), sticky=EW)
        tb.Button(btn_row, text="计算价格", bootstyle=(SUCCESS, OUTLINE), command=self.calculate).pack(side=LEFT)
        tb.Button(btn_row, text="复制结果", bootstyle=SECONDARY, command=self.copy_result).pack(side=LEFT, padx=8)
        tb.Button(btn_row, text="重置", bootstyle=WARNING, command=self.reset).pack(side=LEFT)

        for i in range(2):
            card_left.grid_columnconfigure(i, weight=1)

        card_right = tb.Labelframe(body, text="结果", padding=16, bootstyle=INFO)
        card_right.pack(side=LEFT, fill=BOTH, expand=YES, padx=(12,0))

        self.result_box = tb.Text(card_right, height=10, wrap="word")
        self.result_box.pack(fill=BOTH, expand=YES)
        self.summary = tb.Label(card_right, text="", bootstyle=SUCCESS, anchor=W, justify=LEFT)
        self.summary.pack(fill=X, pady=(8,0))

        self.ent_cost.bind("<Return>", self.calculate)
        self.ent_weight.bind("<Return>", self.calculate)

        footer = tb.Frame(self.win, padding=8)
        footer.pack(fill=X, side=BOTTOM)
        tb.Label(footer, text="提示：主题可切换，结果支持复制", bootstyle=SECONDARY).pack(side=LEFT)

    def switch_theme(self):
        theme = self.theme_var.get() or "cosmo"
        try:
            self.style.theme_use(theme)
        except:
            self.style.theme_use("cosmo")

    def calculate(self, *_):
        try:
            cost = Decimal(self.ent_cost.get().strip())
            weight = Decimal(self.ent_weight.get().strip())
            if cost < 0:
                raise ValueError("成本必须≥0")
            if weight <= 0:
                raise ValueError("重量必须>0")
            rows = []
            for region in ("Brazil", "Mexico"):
                r = price_calc(cost, weight, region)
                rows.append(
                    f"[{r['region']}] 建议售价：{r['price_usd']} USD\n"
                    f"  计费重：{r['bill_w']} kg    运费：{r['ship_cost']} RMB\n"
                    f"  估算平台费：{r['platform_fee_rmb']} RMB    广告费：{r['ad_fee_rmb']} RMB\n"
                )
            self.result_box.delete("1.0", tk.END)
            self.result_box.insert(tk.END, "\n".join(rows))
            self.summary.config(text="已计算完成 ✓")
        except Exception as e:
            self.summary.config(text="计算失败 ✗")
            messagebox.showerror("输入错误", f"请检查输入内容：\n{e}")

    def copy_result(self):
        s = self.result_box.get("1.0", tk.END).strip()
        if not s:
            return
        self.win.clipboard_clear()
        self.win.clipboard_append(s)
        self.summary.config(text="结果已复制到剪贴板")

    def reset(self):
        self.ent_cost.delete(0, tk.END)
        self.ent_weight.delete(0, tk.END)
        self.ent_cost.insert(0, "1.20")
        self.ent_weight.insert(0, "0.12")
        self.result_box.delete("1.0", tk.END)
        self.summary.config(text="")

if __name__ == "__main__":
    App().win.mainloop()
