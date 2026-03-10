"""
Retail analytics dashboard (Flask). Uses the UCI Online Retail dataset to show
revenue trends, geography, top products, and customer RFM segments with
per-customer lookup and recommendations.
Run: python dashboard_web.py  then open http://localhost:5000
"""
from pathlib import Path
from datetime import timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from flask import Flask, render_template_string, request

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "Online Retail.xlsx"
app = Flask(__name__)

# --------------- Data loading (unchanged) ---------------
def load_and_clean():
    df = pd.read_excel(DATA_FILE, engine="openpyxl")
    df = df.drop_duplicates()
    req = ["CustomerID", "Description", "InvoiceNo", "StockCode", "InvoiceDate", "Quantity", "UnitPrice", "Country"]
    df = df.dropna(subset=[c for c in req if c in df.columns])
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["CustomerID"] = df["CustomerID"].astype(int)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df

def get_return_rate():
    df = pd.read_excel(DATA_FILE, engine="openpyxl")
    inv = df["InvoiceNo"].astype(str)
    total = df["InvoiceNo"].nunique()
    cancel = df.loc[inv.str.startswith("C"), "InvoiceNo"].nunique()
    return (cancel / total * 100) if total else 0.0

def compute_rfm(clean):
    ref = clean["InvoiceDate"].max() + timedelta(days=1)
    rfm = clean.groupby("CustomerID").agg(
        Recency=("InvoiceDate", lambda x: (ref - x.max()).days),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("Revenue", "sum"),
    ).reset_index()
    rfm["R_Score"] = pd.qcut(rfm["Recency"], q=4, labels=[4,3,2,1], duplicates="drop")
    rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), q=4, labels=[1,2,3,4], duplicates="drop")
    rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"), q=4, labels=[1,2,3,4], duplicates="drop")
    rfm["R_Score"] = rfm["R_Score"].astype(int)
    rfm["F_Score"] = rfm["F_Score"].astype(int)
    rfm["M_Score"] = rfm["M_Score"].astype(int)
    def seg(row):
        r,f,m = row["R_Score"], row["F_Score"], row["M_Score"]
        if r>=4 and f>=3 and m>=3: return "Champions"
        if r>=3 and f>=2 and m>=2: return "Loyal"
        if r>=3 and (f<=2 or m<=2): return "Potential loyal"
        if r==2 and f>=2 and m>=2: return "At risk"
        if r<=2 and f>=3 and m>=3: return "Can't lose"
        if r<=2 and f<=2 and m>=2: return "Hibernating"
        if r<=2 and f<=2 and m<=2: return "Lost"
        if r>=3 and f<=1 and m<=1: return "New"
        if r<=1: return "Lost"
        return "Other"
    rfm["Segment"] = rfm.apply(seg, axis=1)
    return rfm

RECOMMENDATIONS = {
    "Champions": "Retain & reward — VIP programme, early access, loyalty offers.",
    "Loyal": "Retain — keep engaged to avoid slipping to At risk.",
    "At risk": "Win-back urgently — personalised offer, we miss you campaign.",
    "Can't lose": "Win-back urgently — high value; personal outreach, strong incentive.",
    "Hibernating": "Re-engage — win-back email, targeted offer.",
    "Potential loyal": "Nurture — second-purchase offer, recommendations.",
    "Lost": "Low-cost re-engage — simple win-back; avoid heavy discount.",
    "New": "Onboard — welcome series, first repeat incentive.",
    "Other": "Review — assess next best action.",
}

clean = None
rfm_df = None
return_rate = 0.0

def init_data():
    global clean, rfm_df, return_rate
    if clean is None and DATA_FILE.exists():
        clean = load_and_clean()
        rfm_df = compute_rfm(clean)
        try:
            return_rate = get_return_rate()
        except Exception:
            return_rate = 0.0

@app.before_request
def ensure_data():
    init_data()

def chart_layout(fig, height=420):
    """Apply attractive, consistent layout to Plotly figures."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, system-ui, sans-serif", size=12),
        title_font_size=18,
        margin=dict(l=60, r=40, t=50, b=60),
        height=height,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,0.8)",
    )
    return fig

# --------------- Base template: single-page, anchor nav, smooth scroll ---------------
BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Retail Analytics · From Data to Decisions</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body { font-family: 'Inter', system-ui, sans-serif; margin: 0; padding: 0; background: #f8fafc; color: #1e293b; line-height: 1.7; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 0 24px 48px; }
    .nav { background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%); padding: 16px 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); position: sticky; top: 0; z-index: 100; }
    .nav-inner { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .nav a { color: #e2e8f0; text-decoration: none; padding: 10px 18px; border-radius: 10px; font-weight: 500; transition: all 0.2s; }
    .nav a:hover { background: rgba(255,255,255,0.12); color: white; }
    .nav .brand { font-weight: 700; font-size: 1.1rem; margin-right: 24px; }
    .hero { background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 56px 40px; border-radius: 20px; margin: 32px 0 40px; text-align: center; box-shadow: 0 10px 40px rgba(30,58,95,0.3); }
    .hero h1 { margin: 0 0 16px 0; font-size: 2rem; font-weight: 700; }
    .hero p { margin: 0; opacity: 0.95; font-size: 1.05rem; max-width: 680px; margin-left: auto; margin-right: auto; line-height: 1.6; }
    .section { background: white; padding: 36px 40px; border-radius: 16px; margin-bottom: 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); scroll-margin-top: 80px; }
    .section h2 { margin: 0 0 24px 0; color: #1e3a5f; font-size: 1.5rem; font-weight: 600; }
    .section h3 { margin: 28px 0 14px 0; color: #334155; font-size: 1.15rem; font-weight: 600; }
    .writeup { color: #475569; font-size: 1rem; margin-bottom: 24px; }
    .writeup p { margin: 0 0 16px 0; }
    .writeup .step { margin: 20px 0; padding-left: 20px; border-left: 3px solid #cbd5e1; }
    .writeup .step strong { color: #1e293b; }
    .cards { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 28px; }
    .card { background: linear-gradient(145deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 24px 28px; border-radius: 14px; min-width: 160px; box-shadow: 0 4px 14px rgba(30,58,95,0.25); transition: transform 0.2s; }
    .card:hover { transform: translateY(-2px); }
    .card h3 { margin: 0 0 8px 0; font-size: 13px; font-weight: 500; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px; }
    .card .val { font-size: 24px; font-weight: 700; }
    .chart-wrap { margin: 28px 0; border-radius: 12px; overflow: hidden; }
    .chart-caption { font-size: 0.9rem; color: #64748b; margin-top: -16px; margin-bottom: 24px; }
    .cust-form { display: flex; align-items: center; gap: 16px; margin: 24px 0; flex-wrap: wrap; }
    .cust-form select { padding: 12px 20px; font-size: 16px; border-radius: 10px; border: 2px solid #e2e8f0; min-width: 140px; font-family: inherit; }
    .cust-form button { padding: 12px 28px; background: linear-gradient(135deg, #1e3a5f, #2d5a87); color: white; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: 600; }
    .cust-form button:hover { opacity: 0.95; }
    .info-box { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 5px solid #1e3a5f; padding: 20px 24px; margin: 24px 0; border-radius: 0 12px 12px 0; }
    .profile-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; margin: 24px 0; }
    .insight-list { margin: 20px 0; padding-left: 24px; }
    .insight-list li { margin: 12px 0; color: #475569; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } }
    .footer { margin-top: 48px; padding: 24px 0; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 0.9rem; }
    .footer p { margin: 0; }
  </style>
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a href="/" class="brand">📊 Retail Analytics</a>
      <a href="#data-story">Data</a>
      <a href="#glance">At a glance</a>
      <a href="#overview">Business overview</a>
      <a href="#customer-rfm">Customer RFM</a>
      <a href="#insights">Insights</a>
    </div>
  </nav>
  <div class="wrap">
    {{ body_content | safe }}
  </div>
  <footer class="footer">
    <div class="wrap">
      <p>Built as a portfolio project. Data: UCI Machine Learning Repository, Online Retail dataset (UK-based, 2010–2011). Metrics use cleaned transactions only (cancellations excluded).</p>
    </div>
  </footer>
  <script>
    if (window.location.search.indexOf('customer=') !== -1) {
      var el = document.getElementById('customer-rfm');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  </script>
</body>
</html>
"""

def render(body_content):
    return render_template_string(BASE, body_content=body_content)

# --------------- Single page: all sections, storytelling from start to finish ---------------
@app.route("/")
def index():
    if not DATA_FILE.exists() or clean is None:
        return "Data not loaded.", 500
    total_rev = clean["Revenue"].sum()
    n_cust = clean["CustomerID"].nunique()
    n_orders = clean["InvoiceNo"].nunique()
    aov_val = clean.groupby("InvoiceNo")["Revenue"].sum().mean()
    clean_t = clean.copy()
    clean_t["YearMonth"] = clean_t["InvoiceDate"].dt.to_period("M").astype(str)
    trends = clean_t.groupby("YearMonth").agg(Revenue=("Revenue", "sum")).reset_index()
    fig_glance = px.area(trends, x="YearMonth", y="Revenue", title="Monthly revenue trend")
    fig_glance.update_layout(yaxis_tickformat="£,.0f", xaxis_tickangle=-45, showlegend=False)
    chart_glance = pio.to_html(chart_layout(fig_glance, 360), full_html=False, include_plotlyjs=False)
    fig_t = px.line(trends, x="YearMonth", y="Revenue", title="Revenue trend by month", markers=True)
    fig_t.update_layout(yaxis_tickformat="£,.0f", xaxis_tickangle=-45)
    chart_trend = pio.to_html(chart_layout(fig_t), full_html=False, include_plotlyjs=False)
    order_val = clean.groupby("InvoiceNo").agg(OrderRev=("Revenue", "sum")).reset_index()
    order_val = order_val.merge(clean[["InvoiceNo", "Country"]].drop_duplicates(), on="InvoiceNo", how="left")
    geo = order_val.groupby("Country").agg(Revenue=("OrderRev", "sum")).reset_index().sort_values("Revenue", ascending=False).head(15)
    fig_g = px.bar(geo, x="Country", y="Revenue", title="Revenue by country (top 15)", color="Revenue", color_continuous_scale="Blues")
    fig_g.update_layout(showlegend=False, xaxis_tickangle=-45, yaxis_tickformat="£,.0f")
    chart_geo = pio.to_html(chart_layout(fig_g), full_html=False, include_plotlyjs=False)
    top_p = clean.groupby(["StockCode", "Description"]).agg(Revenue=("Revenue", "sum")).reset_index().nlargest(15, "Revenue")
    top_p["Desc"] = top_p["Description"].fillna("").astype(str).str[:42]
    fig_p = px.bar(top_p, x="Revenue", y="Desc", orientation="h", title="Top 15 products by revenue", color="Revenue", color_continuous_scale="Teal")
    fig_p.update_layout(showlegend=False, xaxis_tickformat="£,.0f", yaxis=dict(autorange="reversed"))
    chart_products = pio.to_html(chart_layout(fig_p, 460), full_html=False, include_plotlyjs=False)

    # Correlation heatmap (Quantity, UnitPrice, Revenue)
    corr = clean[["Quantity", "UnitPrice", "Revenue"]].corr()
    fig_heat = go.Figure(data=go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index,
        colorscale="RdBu", zmin=-1, zmax=1,
        text=corr.round(2).values, texttemplate="%{text}", textfont={"size": 14},
        hoverongaps=False,
    ))
    fig_heat.update_layout(title="Correlation heatmap: Quantity, UnitPrice, Revenue", xaxis_title="", yaxis_title="", height=380)
    chart_heat = pio.to_html(chart_layout(fig_heat, 380), full_html=False, include_plotlyjs=False)

    # Revenue by month x country (top 8 countries) heatmap
    top_countries = geo.head(8)["Country"].tolist()
    order_val2 = clean.groupby("InvoiceNo").agg(OrderRev=("Revenue", "sum")).reset_index()
    order_val2 = order_val2.merge(clean[["InvoiceNo", "Country", "InvoiceDate"]].drop_duplicates(), on="InvoiceNo", how="left")
    order_val2["YearMonth"] = order_val2["InvoiceDate"].dt.to_period("M").astype(str)
    month_country = order_val2[order_val2["Country"].isin(top_countries)].groupby(["YearMonth", "Country"]).agg(Revenue=("OrderRev", "sum")).reset_index()
    pivot_mc = month_country.pivot(index="Country", columns="YearMonth", values="Revenue").fillna(0)
    fig_heat2 = go.Figure(data=go.Heatmap(
        z=pivot_mc.values, x=pivot_mc.columns, y=pivot_mc.index,
        colorscale="Blues", colorbar_title="Revenue (£)",
        hoverongaps=False,
    ))
    fig_heat2.update_layout(title="Revenue by month and country (top 8)", xaxis_title="Month", yaxis_title="Country", height=400)
    fig_heat2.update_layout(yaxis=dict(autorange="reversed"), xaxis_tickangle=-45)
    chart_heat2 = pio.to_html(chart_layout(fig_heat2, 400), full_html=False, include_plotlyjs=False)

    # Segment bubble: Recency (avg) vs Monetary (total), size = number of customers
    seg_bubble = rfm_df.groupby("Segment").agg(
        Recency_avg=("Recency", "mean"),
        Monetary_total=("Monetary", "sum"),
        Customers=("CustomerID", "count"),
    ).reset_index()
    fig_bubble = px.scatter(seg_bubble, x="Recency_avg", y="Monetary_total", size="Customers", color="Segment",
                            title="Customer segments: Recency vs total revenue (bubble size = customer count)",
                            hover_data={"Recency_avg": ":.0f", "Monetary_total": ":,.0f", "Customers": True}, size_max=55)
    fig_bubble.update_layout(xaxis_title="Avg. recency (days since last purchase)", yaxis_title="Total revenue (£)", yaxis_tickformat="£,.0f", height=440)
    chart_bubble = pio.to_html(chart_layout(fig_bubble, 440), full_html=False, include_plotlyjs=False)

    n_products = clean["StockCode"].nunique()
    n_countries = clean["Country"].nunique()
    date_min = clean["InvoiceDate"].min().strftime("%Y-%m-%d")
    date_max = clean["InvoiceDate"].max().strftime("%Y-%m-%d")

    customer_country = clean.groupby("CustomerID")["Country"].first().reset_index()
    rfm_country = rfm_df.merge(customer_country, on="CustomerID", how="left")
    customer_ids = sorted(rfm_country["CustomerID"].unique().tolist())
    selected_id = request.args.get("customer", type=int)
    if selected_id not in customer_ids:
        selected_id = customer_ids[0] if customer_ids else None
    customer_data = None
    chart_customer_products = ""
    chart_customer_cat = ""
    if selected_id is not None:
        cust = rfm_country[rfm_country["CustomerID"] == selected_id].iloc[0]
        segment = cust["Segment"]
        rec_text = RECOMMENDATIONS.get(segment, "Review segment and define action.")
        co = clean[clean["CustomerID"] == selected_id]
        if not co.empty:
            country = co["Country"].iloc[0]
            first_p = co["InvoiceDate"].min().strftime("%Y-%m-%d")
            last_p = co["InvoiceDate"].max().strftime("%Y-%m-%d")
            total_rev_c = co["Revenue"].sum()
            n_txn = co["InvoiceNo"].nunique()
            aov_c = total_rev_c / n_txn if n_txn else 0
            customer_data = type("C", (), {
                "id": selected_id, "segment": segment, "recommendation": rec_text,
                "country": country, "first_purchase": first_p, "last_purchase": last_p,
                "total_rev": f"£{total_rev_c:,.2f}", "aov": f"£{aov_c:,.2f}", "n_txn": n_txn,
                "recency": int(cust["Recency"]), "frequency": int(cust["Frequency"]), "monetary": f"£{cust['Monetary']:,.2f}"
            })()
            prod_df = co.groupby("Description").agg(Revenue=("Revenue", "sum")).reset_index().sort_values("Revenue", ascending=False).head(12)
            prod_df["Desc"] = prod_df["Description"].fillna("").astype(str).str[:40]
            fig_top = px.bar(prod_df, x="Revenue", y="Desc", orientation="h", color="Revenue", color_continuous_scale="Viridis")
            fig_top.update_layout(showlegend=False, xaxis_tickformat="£,.0f", yaxis=dict(autorange="reversed"))
            chart_customer_products = pio.to_html(chart_layout(fig_top, 400), full_html=False, include_plotlyjs=False)
            co2 = co.copy()
            co2["Category"] = co2["Description"].str.split().str[0].fillna("Other")
            cat_df = co2.groupby("Category")["Revenue"].sum().reset_index().sort_values("Revenue", ascending=False).head(10)
            fig_cat = px.pie(cat_df, values="Revenue", names="Category", title="Spend by category (first word)", color_discrete_sequence=px.colors.qualitative.Set3)
            fig_cat.update_traces(textposition="inside", textinfo="percent+label")
            chart_customer_cat = pio.to_html(chart_layout(fig_cat, 400), full_html=False, include_plotlyjs=False)
    options_html = "".join(f'<option value="{c}" {"selected" if selected_id == c else ""}>{c}</option>' for c in customer_ids)
    cust_section = ""
    if customer_data:
        cust_section = f"""
    <div class="info-box">
      <strong>Customer {customer_data.id}</strong> is in segment <strong>{customer_data.segment}</strong>. Next step: {customer_data.recommendation}
    </div>
    <div class="profile-grid">
      <div class="card"><h3>Country</h3><div class="val" style="font-size:16px;">{customer_data.country}</div></div>
      <div class="card"><h3>First purchase</h3><div class="val" style="font-size:14px;">{customer_data.first_purchase}</div></div>
      <div class="card"><h3>Last purchase</h3><div class="val" style="font-size:14px;">{customer_data.last_purchase}</div></div>
      <div class="card"><h3>Total revenue</h3><div class="val">{customer_data.total_rev}</div></div>
      <div class="card"><h3>AOV</h3><div class="val">{customer_data.aov}</div></div>
      <div class="card"><h3>Transactions</h3><div class="val">{customer_data.n_txn}</div></div>
    </div>
    <h3>Top products purchased</h3>
    <div class="chart-wrap">{chart_customer_products}</div>
    <h3>Spend by category</h3>
    <div class="chart-wrap">{chart_customer_cat}</div>
    <p><small>RFM: Recency {customer_data.recency} days · Frequency {customer_data.frequency} · Monetary {customer_data.monetary}</small></p>
    """
    else:
        cust_section = "<p>Select a customer above and click View to see their segment and recommendation.</p>"
    seg_summary = rfm_df.groupby("Segment").agg(
        Customers=("CustomerID", "count"),
        Total_Revenue=("Monetary", "sum"),
    ).reset_index()
    total_rev_rfm = rfm_df["Monetary"].sum()
    seg_summary["SharePct"] = (seg_summary["Total_Revenue"] / total_rev_rfm * 100).round(1)
    seg_summary = seg_summary.sort_values("Total_Revenue", ascending=False)
    fig_seg = px.bar(seg_summary, x="Segment", y="Total_Revenue", color="Total_Revenue", title="Revenue by customer segment",
                     color_continuous_scale="Viridis", text="SharePct")
    fig_seg.update_traces(texttemplate="%{text}%", textposition="outside")
    fig_seg.update_layout(showlegend=False, yaxis_tickformat="£,.0f", xaxis_tickangle=-30)
    chart_seg = pio.to_html(chart_layout(fig_seg), full_html=False, include_plotlyjs=False)
    fig_pie = px.pie(seg_summary, values="Total_Revenue", names="Segment", title="Revenue share by segment", color_discrete_sequence=px.colors.qualitative.Set3)
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    chart_pie = pio.to_html(chart_layout(fig_pie, 420), full_html=False, include_plotlyjs=False)

    body = f"""
    <div class="hero">
      <h1>Retail Analytics: From Data to Decisions</h1>
      <p>Home and business overview in one scroll: from where the data comes from and how it was cleaned, through the big-picture numbers and where the money comes from, to customer segments and what to do next. Use the menu above to jump to any section.</p>
    </div>

    <div class="section" id="data-story">
      <h2>Step 1 — The data and how it was prepared</h2>
      <div class="writeup">
        <p><strong>Where the data comes from.</strong> The analysis uses the UCI Machine Learning Repository's Online Retail dataset: transaction-level records from a UK-based online retailer covering roughly one year (December 2010–December 2011). Each row is a line item: product, quantity, price, invoice number, customer ID, country, and date.</p>
        <p><strong>Why cleaning matters for business.</strong> Raw data always needs a clean baseline before any metric or segment can be trusted. Cleaning included dropping cancellations and invalid rows so that every number in this report reflects real, valid sales. The following cleaning steps were applied:</p>
        <div class="writeup step"><strong>Duplicates removed.</strong> Exact duplicate rows were dropped so that the same line item is not counted twice.</div>
        <div class="writeup step"><strong>Missing key fields removed.</strong> Rows without a valid CustomerID, Description, InvoiceNo, StockCode, InvoiceDate, Quantity, UnitPrice, or Country were dropped. Without CustomerID, a customer cannot be segmented; without price and quantity, revenue cannot be computed.</div>
        <div class="writeup step"><strong>Cancellations excluded.</strong> In the source data, cancelled orders are indicated by invoice numbers starting with "C". Those invoices were removed from the analysis. Revenue, order counts, and averages in this report therefore reflect only completed sales. The return/cancel rate is still calculated separately from the raw data so the business knows how often orders are reversed.</div>
        <div class="writeup step"><strong>Invalid quantities and prices removed.</strong> Rows with zero or negative quantity or unit price were dropped. They would distort revenue and average order value.</div>
        <p>After cleaning, the dataset contains <strong>{n_orders:,}</strong> orders from <strong>{n_cust:,}</strong> customers, <strong>{n_products:,}</strong> unique products (SKUs), and <strong>{n_countries}</strong> countries. The date range runs from <strong>{date_min}</strong> to <strong>{date_max}</strong>. That is the baseline for every insight below.</p>
      </div>
      <h3>Correlation heatmap: transaction fields</h3>
      <div class="chart-wrap">{chart_heat}</div>
      <p class="chart-caption">How Quantity, UnitPrice, and Revenue relate. Strong positive correlation between Quantity and Revenue is expected; UnitPrice can be negative or weak if high-price low-quantity items balance low-price high-quantity ones. Use this to spot data quirks and to justify which metrics to track.</p>
      <h3>Revenue by month and country (top 8)</h3>
      <div class="chart-wrap">{chart_heat2}</div>
      <p class="chart-caption">Where and when revenue happens. Darker cells show stronger months for each country. Helps planning (seasonality by geography) and resource allocation (which markets to support in which periods).</p>
    </div>

    <div class="section" id="glance">
      <h2>Step 2 — At a glance: the big picture</h2>
      <div class="writeup">
        <p>The next question is: what do the overall numbers look like? The cards below summarise total revenue, number of customers, number of orders, and average order value (AOV). These four metrics answer "how big is this business over the period?" and set the context for everything that follows.</p>
        <p><strong>What the trend chart shows.</strong> The area chart plots monthly revenue. It reveals seasonality (e.g. peaks and dips across the year), the effect of the late-2011 period, and the drop in December—which is a partial month in the data, so the dip is expected. For the business, this view supports planning: when to stock up, when to run promotions, and how to set targets by month.</p>
      </div>
      <div class="cards">
        <div class="card"><h3>Total revenue</h3><div class="val">£{total_rev/1e6:.2f}M</div></div>
        <div class="card"><h3>Customers</h3><div class="val">{n_cust:,}</div></div>
        <div class="card"><h3>Orders</h3><div class="val">{n_orders:,}</div></div>
        <div class="card"><h3>Avg order value</h3><div class="val">£{aov_val:,.2f}</div></div>
      </div>
      <h3>Revenue over time (monthly)</h3>
      <div class="chart-wrap">{chart_glance}</div>
      <p class="chart-caption">Hover for exact values. This baseline trend is the starting point for understanding where revenue comes from by geography and product.</p>
    </div>

    <div class="section" id="overview">
      <h2>Step 3 — Business overview: where does the money come from?</h2>
      <div class="writeup">
        <p>Once the baseline is clear, the next step is to break down where the money actually comes from. That drives three decisions: how to plan by time, where to focus by geography, and which products to prioritise.</p>
        <div class="writeup step"><strong>Revenue trend by month (again, for context).</strong> The line chart below repeats the monthly view with a different style. It reinforces seasonality and trend. For finance and operations, this supports budgeting and inventory planning; for marketing, it highlights when demand is highest so campaigns can be timed accordingly.</div>
        <div class="writeup step"><strong>Revenue by country.</strong> The bar chart shows which countries generate the most revenue (top 15). Typically, one or two markets dominate. The business implication: concentration is a strength (you know where to invest in fulfilment and marketing) but also a risk (over-reliance on one geography). Expansion or diversification strategies should start from this picture.</div>
        <div class="writeup step"><strong>Top products by revenue.</strong> The horizontal bar chart lists the top 15 products by total revenue. These SKUs drive a large share of sales. For assortment and merchandising: protect availability on these lines. For promotions: use them as anchors or cross-sell from them. For procurement: ensure supply and margin are healthy on these items.</div>
        <p>The return/cancel rate below is from the raw data (invoices starting with "C") so the business sees how often orders are reversed. All other metrics in this report use cleaned transactions only.</p>
      </div>
      <div class="cards">
        <div class="card"><h3>Total revenue</h3><div class="val">£{total_rev/1e6:.2f}M</div></div>
        <div class="card"><h3>Customers</h3><div class="val">{n_cust:,}</div></div>
        <div class="card"><h3>Orders</h3><div class="val">{n_orders:,}</div></div>
        <div class="card"><h3>AOV</h3><div class="val">£{aov_val:,.2f}</div></div>
        <div class="card"><h3>Return/cancel rate</h3><div class="val">{return_rate:.1f}%</div></div>
      </div>
      <h3>Revenue trend (monthly)</h3>
      <div class="chart-wrap">{chart_trend}</div>
      <p class="chart-caption">Use this view to align planning and campaigns with actual demand patterns.</p>
      <h3>Revenue by country (top 15)</h3>
      <div class="chart-wrap">{chart_geo}</div>
      <p class="chart-caption">Identifies the markets that matter most for revenue—and where concentration risk or growth opportunity lies.</p>
      <h3>Top 15 products by revenue</h3>
      <div class="chart-wrap">{chart_products}</div>
      <p class="chart-caption">These products should be at the centre of assortment, availability, and promotion decisions.</p>
      <h3>Segment bubble: Recency vs revenue (bubble size = customer count)</h3>
      <div class="chart-wrap">{chart_bubble}</div>
      <p class="chart-caption">Each bubble is a customer segment. Left = more recent buyers; vertical = total revenue from that segment; size = number of customers. Champions sit bottom-left (recent, high value); At risk / Can't lose sit top-right (older, high value)—priority for win-back.</p>
    </div>

    <div class="section" id="customer-rfm">
      <h2>Step 4 — Customer RFM: who to retain, who to win back</h2>
      <div class="writeup">
        <p><strong>What RFM is and why it matters.</strong> RFM stands for Recency (how long since the last purchase), Frequency (how many orders in the period), and Monetary (how much the customer spent in total). These three dimensions are used to assign every customer to a segment—Champions, Loyal, At risk, Can't lose, Hibernating, Lost, New, Potential loyal, or Other. Each segment gets a clear recommendation: retain, win-back, nurture, or re-engage.</p>
        <p><strong>How the segments were built.</strong> For each customer, Recency was computed as days since the most recent order; Frequency as number of distinct invoices; Monetary as sum of revenue. Each metric was scored (e.g. quartiles) and combined into rules. For example: high recency, high frequency, and high monetary define Champions; high recency but low frequency and low monetary might be New; low recency but high frequency and high monetary are At risk or Can't lose—valuable customers who have gone quiet and need urgent attention.</p>
        <p><strong>How to use this section.</strong> The dropdown below lets you select any customer by ID. After clicking View, the page shows that customer's segment, the recommended next step, their profile (country, first and last purchase, total revenue, AOV, transaction count), and charts of what they bought and how spend breaks down by category. Marketing can use it to plan segment-level campaigns; support or account management can use it when a high-value customer gets in touch—so the right message and offer are applied to the right customer.</p>
      </div>
      <form method="get" action="/#customer-rfm" class="cust-form">
        <label for="customer"><strong>Select Customer ID:</strong></label>
        <select name="customer" id="customer" onchange="this.form.submit()">
          {options_html}
        </select>
        <button type="submit">View</button>
      </form>
      {cust_section}
    </div>

    <div class="section" id="insights">
      <h2>Step 5 — Insights and what to do next</h2>
      <div class="writeup">
        <p>When revenue is summed by segment, the story becomes clear: a small set of segments holds most of the revenue. Champions and Loyal together explain the majority of sales. At risk and Can't lose are fewer in number but still valuable—they are customers who used to buy a lot and have gone quiet. The business impact: if the business can only do one thing, it should focus retention and win-back on those four segments. Lost and Hibernating may respond to low-cost re-engagement; New and Potential loyal are where second-purchase and onboarding efforts pay off.</p>
        <p>The bar chart below shows total revenue by segment; the pie chart shows revenue share. Together they answer: where is the money, and where should effort go first?</p>
      </div>
      <div class="two-col">
        <div>
          <h3>Revenue by segment</h3>
          <div class="chart-wrap">{chart_seg}</div>
        </div>
        <div>
          <h3>Revenue share by segment</h3>
          <div class="chart-wrap">{chart_pie}</div>
        </div>
      </div>
      <p class="chart-caption">Use the Customer RFM section above to look up any customer and see their recommended action.</p>
      <h3>What to do with each segment</h3>
      <ul class="insight-list">
        <li><strong>Champions and Loyal:</strong> Retain and reward—VIP programme, early access, loyalty offers. Protecting this base protects most of the revenue.</li>
        <li><strong>At risk and Can't lose:</strong> Win-back urgently. Personal outreach and a strong "we miss you" offer; these customers are worth the cost.</li>
        <li><strong>Hibernating:</strong> Re-engage with win-back emails and a targeted offer before they move to Lost.</li>
        <li><strong>Potential loyal and New:</strong> Nurture with a second-purchase incentive and onboarding so they climb into Loyal.</li>
        <li><strong>Lost:</strong> Low-cost re-engagement only; avoid heavy discount. Prioritise effort on At risk and Can't lose first.</li>
      </ul>
      <div class="writeup">
        <p><strong>Summary.</strong> The report has walked from raw data to cleaned baseline, to overall metrics and trend, to geography and products, to customer segments and per-customer lookup, and finally to actionable recommendations by segment. Each step is designed to add value: clean data for trust, trends for planning, geography and products for resource allocation, and RFM for targeting the right message to the right customer and protecting the revenue that matters most.</p>
      </div>
    </div>
    """
    return render(body)

if __name__ == "__main__":
    if not DATA_FILE.exists():
        print(f"ERROR: Put 'Online Retail.xlsx' in: {BASE_DIR}")
    else:
        print("Loading data (one time, may take 1-2 min)...")
        init_data()
        print("Done. Open in browser:  http://localhost:5000")
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
