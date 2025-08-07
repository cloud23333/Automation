# Automation

Utilities and scripts to automate product listing and data preparation for e-commerce platforms such as Mercado and Shopee.

## Features
- Upload products to Mercado and Shopee with Selenium-based scripts.
- Helpers for building spreadsheets and cleaning databases.
- Automatic ChromeDriver download and caching.

## Requirements
- Python 3.11+
- Google Chrome
- Windows environment for GUI automation
- Python packages: `selenium`, `pandas`, `pywinauto`, `openpyxl`, `webdriver-manager`

## Installation
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install selenium pandas pywinauto openpyxl webdriver-manager
   ```
3. Place the necessary Excel files inside the `数据/` directory.

## Repository Layout
- `src/` – automation scripts
  - `单文件-自动上新/` – single-file Mercado uploader
  - `多模块-自动上新/` – modular upload framework for Mercado and Shopee
- `tools/` – utilities for generating spreadsheets and processing databases
- `数据/` – input spreadsheets (`mercado_products.xlsx`, `mercado_images.xlsx`, `shopee_products.xlsx`)

## Preparing Data
The scripts expect product and image information in Excel format. Place the files mentioned above in `数据/` before running any automation.

## ChromeDriver
On first execution the required ChromeDriver is downloaded to `drivers/` and reused on subsequent runs. To specify a custom driver path, set `CHROME_DRIVER_PATH` before launching a script:

```bash
export CHROME_DRIVER_PATH=/path/to/chromedriver      # Linux/macOS
set CHROME_DRIVER_PATH=C:\path\to\chromedriver.exe # Windows
```

## Usage
Example: run the single-file Mercado upload script:

```bash
python src/单文件-自动上新/mercado_自动上新.py
```

## Troubleshooting
- **Missing dependencies** – install the packages listed above.
- **ChromeDriver mismatch** – download a driver version compatible with your Chrome browser.
- **Excel path errors** – verify that data files exist under `数据/` and that paths inside scripts are correct.
- **Timeouts or element not found** – increase wait times or check network stability.
