from pathlib import Path
import os

WAIT_SEC = 15
SLEEP_SHORT = 0.3
ATTR_TIMEOUT = 3

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "数据"

MERCADO_XLSX = Path(os.getenv("MERCADO_XLSX", DATA_DIR / "mercado.xlsx"))

SHOPEE_PRODUCTS_XLSX = Path(
    os.getenv("SHOPEE_PRODUCTS_XLSX", DATA_DIR / "shopee_products.xlsx")
)


USERNAME = os.getenv("MERCADO_USERNAME", "Cloud23333")
PASSWORD = os.getenv("MERCADO_PASSWORD", "Dzj9876543")
