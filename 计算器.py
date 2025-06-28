import tkinter as tk
from tkinter import messagebox


def calculate_price(event=None):
    try:
        productCost = float(entry_cost.get())
        FF = 4.2
        Commission = 0.08
        grossMargin = float(entry_margin.get())
        targetRevenue = float(entry_revenue.get())

        RMBUSD = 0.13927034

        Price_fixed_profit = (productCost + FF) / (1 - grossMargin - Commission)
        Price_fixed_grossMargin = (targetRevenue + productCost + FF) / (1 - Commission)
        Price = max(Price_fixed_profit, Price_fixed_grossMargin)

        PriceUSD = max(3, Price * RMBUSD)

        label_result.config(text=f"PriceUSD = {PriceUSD:.2f}")
    except Exception as e:
        label_result.config(text="PriceUSD = （输入错误）")
        messagebox.showerror("输入错误", f"请检查输入内容：{e}")


root = tk.Tk()
root.title("PriceUSD 计算器")
root.geometry("350x300")

root.attributes("-topmost", True)  # 添加窗口置顶

tk.Label(root, text="productCost (人民币)").pack(pady=5)
entry_cost = tk.Entry(root)
entry_cost.insert(0, "1.2")
entry_cost.pack(pady=2)

tk.Label(root, text="grossMargin (毛利率 0.0~1.0)").pack(pady=5)
entry_margin = tk.Entry(root)
entry_margin.insert(0, "0.6")
entry_margin.pack(pady=2)

tk.Label(root, text="targetRevenue (目标营收)").pack(pady=5)
entry_revenue = tk.Entry(root)
entry_revenue.insert(0, "8")
entry_revenue.pack(pady=2)

btn = tk.Button(root, text="计算 PriceUSD", command=calculate_price)
btn.pack(pady=12)

label_result = tk.Label(root, text="PriceUSD = ", fg="blue", font=("Arial", 16, "bold"))
label_result.pack(pady=8)

entry_cost.bind("<Return>", calculate_price)
entry_margin.bind("<Return>", calculate_price)
entry_revenue.bind("<Return>", calculate_price)
btn.bind("<Return>", calculate_price)

root.mainloop()
