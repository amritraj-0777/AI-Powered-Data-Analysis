# Retail Analytics Dashboard

A single-page analytics report built with **Flask** and **Plotly** (and a **Streamlit** version), using the UCI Online Retail dataset. The dashboard tells the full story from raw data and cleaning through business overview, customer RFM segments, and actionable recommendations.

## What’s in it

- **Data & cleaning** — Where the data comes from, cleaning steps (dropping cancellations and invalid rows), and baseline stats
- **At a glance** — Total revenue, customers, orders, AOV, and monthly revenue trend
- **Business overview** — Revenue by month, by country (top 15), top 15 products, correlation heatmap, month×country heatmap, and segment bubble chart
- **Customer RFM** — Look up any customer by ID; see segment, recommendation, and purchase profile
- **Insights** — Revenue by segment, recommended actions per segment

## Tech stack

- Python 3, Flask, Pandas, Plotly, OpenPyXL

## How to run

1. **Get the data**  
   Download the [Online Retail](https://archive.ics.uci.edu/ml/datasets/Online+Retail) dataset from the UCI Machine Learning Repository (Excel file). Place `Online Retail.xlsx` in the project root (same folder as `dashboard_web.py`).

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   Or run `RUN_WEBSITE.bat` (Windows), which will install Flask, pandas, openpyxl, and plotly if needed.

3. **Start the app**
   ```bash
   python dashboard_web.py
   ```
   Or double-click `RUN_WEBSITE.bat`. Then open **http://localhost:5000** in your browser.

## Project structure

| File / folder      | Purpose |
|--------------------|--------|
| `dashboard_web.py` | Flask app: single-page report, data loading, RFM, charts |
| `dashboard.py`     | Streamlit version of the dashboard |
| `RUN_WEBSITE.bat`  | One-click run for Flask app (Windows) |
| `requirements.txt` | Python dependencies |
| `Online Retail.xlsx` | Dataset (not in repo; add locally) |

## Dataset

[UCI Machine Learning Repository — Online Retail](https://archive.ics.uci.edu/ml/datasets/Online+Retail)  
UK-based online retail, 2010–2011, transaction-level data.

## License

MIT (or your choice). Dataset is from UCI and subject to its own terms.
