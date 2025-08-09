from pathlib import Path
import os

WAIT_SEC = 15
SLEEP_SHORT = 0.3
ATTR_TIMEOUT = 3

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "数据"

MERCADO_XLSX = Path(
    os.getenv(
        "MERCADO_XLSX",
        Path(r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\创建xlsx\xlsx文件\mercado\mercado.xlsx")
    )
)

SHOPEE_PRODUCTS_XLSX = Path(
    os.getenv(
        "SHOPEE_PRODUCTS_XLSX",
        Path(r"C:\Users\Administrator\Documents\Mecrado\Automation\tools\创建xlsx\xlsx文件\Shopee\shopee_products.xlsx")
    )
)

USERNAME = os.getenv("MERCADO_USERNAME", "Cloud23333")
PASSWORD = os.getenv("MERCADO_PASSWORD", "Dzj9876543")
