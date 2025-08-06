from __future__ import annotations
import os
import shutil
from pathlib import Path
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = Path(__file__).resolve().parents[1]
DRIVER_DIR = BASE_DIR / "drivers"
DEFAULT_DRIVER_NAME = "chromedriver.exe" if os.name == "nt" else "chromedriver"
DEFAULT_DRIVER_PATH = DRIVER_DIR / DEFAULT_DRIVER_NAME

def ensure_chromedriver(path: str | Path | None = None) -> str:
    driver_path = Path(path or os.getenv("CHROME_DRIVER_PATH", DEFAULT_DRIVER_PATH))
    driver_path.parent.mkdir(parents=True, exist_ok=True)

    if not driver_path.exists():
        downloaded = ChromeDriverManager().install()
        shutil.copy(downloaded, driver_path)
        if os.name != "nt":
            driver_path.chmod(0o755)
    return str(driver_path)