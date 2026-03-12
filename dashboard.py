"""
2-page Streamlit dashboard: Business Overview + Customer RFM Analysis.
Data: Online Retail.xlsx (same folder as this file).
Run locally: streamlit run dashboard.py --server.port 8502
Deploy: Push to GitHub, then deploy on share.streamlit.io (one link for everyone).
"""
import sys
import os
from pathlib import Path
from datetime import timedelta

# Only auto-launch Streamlit when run as "python dashboard.py" on your PC (not when "streamlit run dashboard.py" is used on Cloud)
if __name__ == "__main__":
    if "streamlit" not in sys.modules:
        import subprocess
        _script = Path(__file__).resolve()
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(_script), "--server.port", "8502"],
            cwd=str(_script.parent),
        )
        print("\n  Dashboard: http://localhost:8502\n")
        sys.exit(0)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "Online Retail.xlsx"

st.set_page_config(page_title="Retail Analytics", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Show something immediately so the page is never blank (helps on Streamlit Cloud)
st.sidebar.title("📊 Retail Analytics")
st.sidebar.caption("RFM dashboard · Data: UCI Online Retail")

if not DATA_FILE.exists():
    st.error(f"Data file not found. Put **Online Retail.xlsx** in the same folder as `dashboard.py`.")
    st.info(f"Expected path: `{DATA_FILE}`")
    st.stop()

st.sidebar.divider()
page = st.sidebar.radio("Page", ["Business Overview", "Customer RFM Analysis"], index=0)

# Sidebar image: analytics/data theme (free Unsplash)
st.sidebar.image(
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=80",
    caption="Data-driven decisions",
    use_container_width=True,
)

st.markdown("""
<style>
  /* Main area: warmer, less white - soft blue-grey tint */
  .stApp { background: linear-gradient(180deg, #e8eef7 0%, #dbe4f0 25%, #e2eaf4 60%, #edf1f7 100%); }
  /* Blocks/cards: subtle background so content isn't on raw white */
  .stPlotlyChart, [data-testid="stExpander"] { background: #fff; border-radius: 12px; padding: 12px; box-shadow: 0 1px 8px rgba(30,58,95,0.08); }
  div[data-testid="stExpander"] > div { background: #ffffff !important; border-radius: 10px !important; }
  /* Sidebar */
  [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #2d5a87 50%, #1a365d 100%); }
  [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0 !important; }
  [data-testid="stSidebar"] label { color: #e2e8f0 !important; }
  [data-testid="stSidebar"] .stCaptionContainer { color: #94a3b8 !important; }
  /* Hero banner */
  .hero-banner { background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 50%, #6366f1 100%); color: white; padding: 1.25rem 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 14px rgba(30,58,95,0.25); }
  .hero-banner h1 { color: white !important; margin: 0 !important; font-size: 1.75rem !important; }
  .hero-banner p { color: rgba(255,255,255,0.95) !important; margin: 0.35rem 0 0 0 !important; font-size: 0.95rem !important; }
  /* Section headers */
  .section-head { color: #1e3a5f; font-weight: 700; padding-left: 12px; border-left: 4px solid #3b82f6; margin: 1.5rem 0 0.75rem 0; }
  /* Callouts */
  .callout { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 4px solid #2563eb; padding: 1rem 1.25rem; border-radius: 0 10px 10px 0; margin: 1rem 0; font-size: 0.95rem; }
  .callout-success { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-left-color: #059669; }
  .metric-card { background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 1rem 1.5rem; border-radius: 12px; margin: 0.5rem 0; box-shadow: 0 2px 10px rgba(30,58,95,0.2); }
  /* Table container: card style, no harsh white */
  .stDataFrame { background: #fff !important; border-radius: 10px !important; box-shadow: 0 1px 6px rgba(0,0,0,0.06) !important; }
</style>
""", unsafe_allow_html=True)

loading_placeholder = st.empty()
with loading_placeholder.container():
    st.info("⏳ **Loading data…** First load may take 1–2 minutes. Please wait.")

@st.cache_data
def load_and_clean():
    df = pd.read_excel(DATA_FILE, engine="openpyxl")
    df = df.drop_duplicates()
    req = ["CustomerID", "Description", "InvoiceNo", "StockCode", "InvoiceDate", "Quantity", "UnitPrice", "Country"]
    df = df.dropna(subset=[c for c in req if c in df.columns])
    inv = df["InvoiceNo"].astype(str)
    df = df.loc[~inv.str.startswith("C", na=False)]
    df = df.loc[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["CustomerID"] = df["CustomerID"].astype(int)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df


@st.cache_data
def get_return_rate():
    df = pd.read_excel(DATA_FILE, engine="openpyxl")
    inv = df["InvoiceNo"].astype(str)
    total = df["InvoiceNo"].nunique()
    cancel = df.loc[inv.str.startswith("C", na=False), "InvoiceNo"].nunique()
    return (cancel / total * 100) if total else 0.0


@st.cache_data
def compute_rfm(clean):
    ref = clean["InvoiceDate"].max() + timedelta(days=1)
    rfm = clean.groupby("CustomerID").agg(
        Recency=("InvoiceDate", lambda x: (ref - x.max()).days),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("Revenue", "sum"),
    ).reset_index()
    rfm["R_Score"] = pd.qcut(rfm["Recency"], q=4, labels=[4, 3, 2, 1], duplicates="drop")
    rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), q=4, labels=[1, 2, 3, 4], duplicates="drop")
    rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"), q=4, labels=[1, 2, 3, 4], duplicates="drop")
    rfm["R_Score"] = rfm["R_Score"].astype(int)
    rfm["F_Score"] = rfm["F_Score"].astype(int)
    rfm["M_Score"] = rfm["M_Score"].astype(int)

    def segment_name(row):
        r, f, m = row["R_Score"], row["F_Score"], row["M_Score"]
        if r >= 4 and f >= 3 and m >= 3: return "Champions"
        if r >= 3 and f >= 2 and m >= 2: return "Loyal"
        if r >= 3 and (f <= 2 or m <= 2): return "Potential loyal"
        if r == 2 and f >= 2 and m >= 2: return "At risk"
        if r <= 2 and f >= 3 and m >= 3: return "Can't lose"
        if r <= 2 and f <= 2 and m >= 2: return "Hibernating"
        if r <= 2 and f <= 2 and m <= 2: return "Lost"
        if r >= 3 and f <= 1 and m <= 1: return "New"
        if r <= 1: return "Lost"
        return "Other"

    rfm["Segment"] = rfm.apply(segment_name, axis=1)
    return rfm


with st.spinner("Preparing data (reading Excel & computing RFM)…"):
    try:
        clean = load_and_clean()
        rfm_df = compute_rfm(clean)
    except Exception as e:
        loading_placeholder.empty()
        st.error("Error loading data")
        st.code(str(e))
        st.stop()

loading_placeholder.empty()

# --------------- PAGE 1: Business Overview ---------------
if page == "Business Overview":
    st.markdown("""
    <div class="hero-banner">
      <h1>📈 Business Overview</h1>
      <p>Revenue at a glance · Where the money comes from · Trends, geography & top products</p>
    </div>
    """, unsafe_allow_html=True)

    # Main content image: retail/analytics theme
    img_col1, img_col2, img_col3 = st.columns([1, 2, 1])
    with img_col2:
        st.image(
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
            caption="Retail analytics · UCI Online Retail",
            use_container_width=True,
        )

    total_rev = clean["Revenue"].sum()
    n_cust = clean["CustomerID"].nunique()
    n_orders = clean["InvoiceNo"].nunique()
    aov = clean.groupby("InvoiceNo")["Revenue"].sum().mean()
    try:
        return_rate = get_return_rate()
    except Exception:
        return_rate = 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Revenue", f"£{total_rev/1e6:.2f}M")
    c2.metric("Customers", f"{n_cust:,}")
    c3.metric("Orders", f"{n_orders:,}")
    c4.metric("AOV", f"£{aov:,.2f}")
    c5.metric("Return/Cancel rate", f"{return_rate:.1f}%")

    st.markdown('<p class="callout"><strong>💡 At a glance:</strong> Use these numbers to track performance and spot trends. Revenue and AOV drive planning; return rate highlights fulfilment quality.</p>', unsafe_allow_html=True)

    st.markdown('<p class="section-head">📊 Revenue trend (monthly)</p>', unsafe_allow_html=True)
    clean_t = clean.copy()
    clean_t["YearMonth"] = clean_t["InvoiceDate"].dt.to_period("M").astype(str)
    trends = clean_t.groupby("YearMonth").agg(Revenue=("Revenue", "sum"), Orders=("InvoiceNo", "nunique")).reset_index()
    fig_t = px.line(trends, x="YearMonth", y="Revenue", title="Revenue trend (monthly)", markers=True)
    fig_t.update_layout(yaxis_tickformat="£,.0f", xaxis_tickangle=-45)
    st.plotly_chart(fig_t, use_container_width=True)

    st.markdown('<p class="section-head">🌍 Geography & products</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        order_val = clean.groupby("InvoiceNo").agg(OrderRev=("Revenue", "sum")).reset_index()
        order_val = order_val.merge(clean[["InvoiceNo", "Country"]].drop_duplicates(), on="InvoiceNo", how="left")
        geo = order_val.groupby("Country").agg(Revenue=("OrderRev", "sum")).reset_index().sort_values("Revenue", ascending=False).head(15)
        fig_g = px.bar(geo, x="Country", y="Revenue", title="Revenue by country (top 15)", color="Revenue", color_continuous_scale="Blues")
        fig_g.update_layout(showlegend=False, xaxis_tickangle=-45, yaxis_tickformat="£,.0f")
        st.plotly_chart(fig_g, use_container_width=True)

    with col2:
        top_p = clean.groupby(["StockCode", "Description"]).agg(Revenue=("Revenue", "sum")).reset_index().nlargest(15, "Revenue")
        top_p["Desc"] = top_p["Description"].fillna("").astype(str).str[:40]
        fig_p = px.bar(top_p, x="Revenue", y="Desc", orientation="h", title="Top 15 products by revenue", color="Revenue", color_continuous_scale="Teal")
        fig_p.update_layout(showlegend=False, xaxis_tickformat="£,.0f", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_p, use_container_width=True)

    with st.expander("Geographic table (revenue, orders, AOV by country)"):
        geo_full = order_val.groupby("Country").agg(Revenue=("OrderRev", "sum"), Orders=("InvoiceNo", "nunique")).reset_index()
        geo_full["AvgOrderValue"] = geo_full["Revenue"] / geo_full["Orders"]
        geo_full = geo_full.sort_values("Revenue", ascending=False).reset_index(drop=True)
        geo_full.insert(0, "Rank", range(1, len(geo_full) + 1))
        st.dataframe(
            geo_full.style.format({"Revenue": "£{:,.2f}", "AvgOrderValue": "£{:,.2f}"}),
            use_container_width=True,
            hide_index=True,
        )

# --------------- PAGE 2: Customer RFM Analysis ---------------
else:
    st.markdown("""
    <div class="hero-banner">
      <h1>🎯 Customer RFM Analysis</h1>
      <p>Recency · Frequency · Monetary · Segment any customer and see the next best action</p>
    </div>
    """, unsafe_allow_html=True)

    customer_country = clean.groupby("CustomerID")["Country"].first().reset_index()
    rfm_country = rfm_df.merge(customer_country, on="CustomerID", how="left")
    customer_ids = sorted(rfm_country["CustomerID"].astype(str).tolist())

    search = st.sidebar.text_input("Search Customer ID", placeholder="e.g. 12347")
    options = [c for c in customer_ids if search in c] if search else customer_ids
    if not options:
        options = customer_ids
    selected_str = st.sidebar.selectbox("Select customer", options, key="cust_sel")
    try:
        selected_id = int(selected_str)
    except (ValueError, TypeError):
        selected_id = int(customer_ids[0]) if customer_ids else None

    if selected_id is None:
        st.info("No customer selected.")
        st.stop()

    cust = rfm_country[rfm_country["CustomerID"] == selected_id].iloc[0]
    segment = cust["Segment"]

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
    rec_text = RECOMMENDATIONS.get(segment, "Review segment and define action.")

    st.markdown(f'<p class="callout callout-success"><strong>👤 Customer {selected_id}</strong> · Segment: <strong>{segment}</strong><br><strong>Recommendation:</strong> {rec_text}</p>', unsafe_allow_html=True)

    cust_orders = clean[clean["CustomerID"] == selected_id]
    if cust_orders.empty:
        st.warning("No transaction detail for this customer.")
        st.stop()

    country = cust_orders["Country"].iloc[0]
    first_p = cust_orders["InvoiceDate"].min()
    last_p = cust_orders["InvoiceDate"].max()
    total_rev_c = cust_orders["Revenue"].sum()
    n_txn = cust_orders["InvoiceNo"].nunique()
    aov_c = total_rev_c / n_txn if n_txn else 0

    st.divider()
    st.markdown('<p class="section-head">📋 Customer profile</p>', unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    p1.metric("Country", country)
    p2.metric("First purchase", first_p.strftime("%Y-%m-%d"))
    p3.metric("Last purchase", last_p.strftime("%Y-%m-%d"))
    f1, f2, f3 = st.columns(3)
    f1.metric("Total revenue", f"£{total_rev_c:,.2f}")
    f2.metric("AOV", f"£{aov_c:,.2f}")
    f3.metric("Transactions", n_txn)

    st.markdown('<p class="section-head">🛒 Top products purchased</p>', unsafe_allow_html=True)
    prod_df = cust_orders.groupby("Description").agg(Revenue=("Revenue", "sum"), Qty=("Quantity", "sum")).reset_index().sort_values("Revenue", ascending=False).head(12)
    prod_df["Desc"] = prod_df["Description"].fillna("").astype(str).str[:40]
    fig_top = px.bar(prod_df, x="Revenue", y="Desc", orientation="h", color="Revenue", color_continuous_scale="Viridis")
    fig_top.update_layout(showlegend=False, xaxis_tickformat="£,.0f", yaxis=dict(autorange="reversed"), height=400)
    st.plotly_chart(fig_top, use_container_width=True)

    st.markdown('<p class="section-head">🥧 Spend by product category</p>', unsafe_allow_html=True)
    cust_copy = cust_orders.copy()
    cust_copy["Category"] = cust_copy["Description"].str.split().str[0].fillna("Other")
    cat_df = cust_copy.groupby("Category")["Revenue"].sum().reset_index().sort_values("Revenue", ascending=False).head(10)
    fig_cat = px.pie(cat_df, values="Revenue", names="Category", color_discrete_sequence=px.colors.qualitative.Set3)
    fig_cat.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_cat, use_container_width=True)

    with st.expander("RFM scores"):
        st.write(f"**Recency:** {int(cust['Recency'])} days | **Frequency:** {int(cust['Frequency'])} | **Monetary:** £{cust['Monetary']:,.2f}")
        st.write(f"R_Score={int(cust['R_Score'])}, F_Score={int(cust['F_Score'])}, M_Score={int(cust['M_Score'])}")
