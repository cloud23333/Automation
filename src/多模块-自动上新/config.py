from pathlib import Path
import os

WAIT_SEC = 15
SLEEP_SHORT = 0.3
ATTR_TIMEOUT = 3

# Project directories
_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _ROOT / "数据"

# Excel file locations
Mercado_PRODUCTS_XLSX = _DATA_DIR / "mercado_products.xlsx"
Mercado_IMAGES_XLSX = _DATA_DIR / "mercado_images.xlsx"


Shopee_products = _DATA_DIR / "shopee_products.xlsx"


USERNAME = os.getenv("Cloud23333")
PASSWORD = os.getenv("Dzj9876543")
