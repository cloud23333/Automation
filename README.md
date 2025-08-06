# Automation

## Purpose
Scripts and utilities for automating product uploads and data preparation for e-commerce platforms such as Mercado and Shopee.

## Prerequisites
- Python 3.11+
- Google Chrome with a matching ChromeDriver in your PATH
- Packages: `selenium`, `pandas`, `pywinauto`, `openpyxl`
- Windows environment for GUI automation

## Setup
1. Clone this repository.
2. Install the required packages:
   ```bash
   pip install selenium pandas pywinauto openpyxl
   ```
3. Place the necessary Excel files inside the `数据/` directory.
4. Ensure ChromeDriver is accessible from the command line.

## Folder Structure
- `src/` – core automation scripts for uploading products
- `tools/` – helper utilities for building spreadsheets and processing databases
- `数据/` – spreadsheet inputs (`mercado_products.xlsx`, `mercado_images.xlsx`, `shopee_products.xlsx`)

## Data Requirements
The automation scripts expect product and image information in Excel spreadsheets located in `数据/`. Typical files include:
- `mercado_products.xlsx` and `mercado_images.xlsx` for Mercado uploads
- `shopee_products.xlsx` for Shopee listings

## Example Usage
Run a single-file Mercado upload script:
```bash
python src/单文件-自动上新/mercado_自动上新.py
```

## Troubleshooting
- **Missing dependencies** – install the packages listed above.
- **ChromeDriver mismatch** – download a driver version compatible with your Chrome browser.
- **Excel path errors** – verify that data files exist under `数据/` and that paths inside scripts are correct.
- **Timeouts or element not found** – increase wait times or check network stability.
