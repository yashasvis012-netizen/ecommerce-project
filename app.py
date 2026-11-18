"""E-Commerce Sales & Customer Insights - interactive dashboard.   Run: streamlit run app.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analysis as an

ROOT = Path(__file__).parent
NAVY, TEAL, AMBER, CORAL, PLUM, SLATE = "#14213D", "#1B6F8A", "#E0A030", "#C8553D", "#6C5B7B", "#8AA1B1"
COLORS = [TEAL, AMBER, "#2A9D8F", CORAL, PLUM, SLATE]
SEGMENT_COLORS = {"Champions": "#1B6F8A", "Loyal Customers": "#2A9D8F", "Potential Loyalists": "#7FB7BE",
                  "Needs Attention": "#E0A030", "At Risk": "#E08A30", "Cannot Lose Them": "#C8553D",
                  "Hibernating": "#8AA1B1"}

st.set_page_config(page_title="E-Commerce Analytics", page_icon="📊", layout="wide")
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; }}
.block-container {{ padding-top: 1.4rem; max-width: 1400px; }}
#MainMenu, footer {{ visibility: hidden; }}
.banner {{ background: {NAVY}; color: #fff; padding: 1.4rem 1.8rem; border-radius: 10px; margin-bottom: 1.1rem;
          border-bottom: 4px solid {AMBER}; }}
.banner h1 {{ color: #fff; font-size: 1.7rem; margin: 0 0 .25rem 0; padding: 0; font-weight: 600; }}
.banner p {{ color: #C9D3E0; margin: 0; font-size: .95rem; }}
.kpi {{ background: #fff; border-radius: 8px; padding: .9rem 1.1rem; border-left: 5px solid {TEAL};
       box-shadow: 0 1px 3px rgba(20,33,61,.12); margin-bottom: .6rem; }}
.kpi-label {{ color: #5B6B7C; font-size: .86rem; }}
.kpi-value {{ color: {NAVY}; font-size: 1.65rem; font-weight: 600; line-height: 1.25; }}
.kpi-delta {{ font-size: .78rem; font-weight: 500; }}
.up {{ color: #1E8E5A; }} .down {{ color: {CORAL}; }}
.small-kpi .kpi-value {{ font-size: 1.2rem; }}
h3 {{ color: {NAVY}; font-weight: 600; }}
</style>""", unsafe_allow_html=True)


# ---------- helpers ----------
@st.cache_data(show_spinner="Preparing data...")
def load_data():
    if not an.CLEAN_PATH.exists():                      # first run: build everything automatically
        import data_cleaning
        import generate_data
        if not (ROOT / "data.csv").exists():
            generate_data.main()
        data_cleaning.main()
    return an.load_clean()


def inr(x):
    x = float(x)
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.2f} L"
    if abs(x) >= 1e3:
        return f"₹{x / 1e3:.1f}K"
    return f"₹{x:,.0f}"


def card(label, value, delta=None, accent=TEAL, small=False):
    d = ""
    if delta is not None and not np.isnan(delta):
        d = f'<div class="kpi-delta {"up" if delta >= 0 else "down"}">{delta:+.1f}% vs previous period</div>'
    st.markdown(f'<div class="kpi {"small-kpi" if small else ""}" style="border-left-color:{accent}">'
                f'<div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{d}</div>',
                unsafe_allow_html=True)


def style(fig, height=360, money_axis=None):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), colorway=COLORS,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="IBM Plex Sans, Segoe UI, sans-serif", color=NAVY),
                      legend=dict(orientation="h", y=-0.2, x=0), hoverlabel=dict(font_size=13))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(20,33,61,.08)")
    if money_axis:
        fig.update_layout(**{money_axis: dict(tickprefix="₹", tickformat="~s", gridcolor="rgba(20,33,61,.08)")})
    return fig


def delta(cur, prev):
    return (cur - prev) / prev * 100 if prev else np.nan


# ---------- data + sidebar filters ----------
df_all = load_data()
st.sidebar.markdown("### Filters")
dmin, dmax = df_all["order_date"].min().date(), df_all["order_date"].max().date()
picked = st.sidebar.date_input("Order date range", value=(dmin, dmax), min_value=dmin, max_value=dmax)
if not (isinstance(picked, (tuple, list)) and len(picked) == 2):
    st.info("Pick both a start date and an end date to update the dashboard.")
    st.stop()
start, end = pd.Timestamp(picked[0]), pd.Timestamp(picked[1])
cats = st.sidebar.multiselect("Product category", sorted(df_all["category"].unique()), placeholder="All categories")
states = st.sidebar.multiselect("State", sorted(df_all["state"].unique()), placeholder="All states")
pool = df_all[df_all["state"].isin(states)] if states else df_all
cities = st.sidebar.multiselect("City", sorted(pool["city"].unique()), placeholder="All cities")
st.sidebar.caption("Leave a filter empty to include everything. KPIs count Delivered and Shipped orders; "
                   "Cancelled and Returned orders appear in the status analysis.")

base = df_all
if cats:
    base = base[base["category"].isin(cats)]
if states:
    base = base[base["state"].isin(states)]
if cities:
    base = base[base["city"].isin(cities)]
df = base[(base["order_date"] >= start) & (base["order_date"] <= end)]
if df.empty:
    st.warning("No orders match these filters. Widen the date range or clear a filter.")
    st.stop()
span = (end - start).days + 1
prev = base[(base["order_date"] >= start - pd.Timedelta(days=span)) & (base["order_date"] < start)]

# ---------- header + KPIs ----------
st.markdown(f'<div class="banner"><h1>E-Commerce Sales &amp; Customer Insights</h1>'
            f'<p>{len(df):,} orders from {start:%d %b %Y} to {end:%d %b %Y}. All amounts in Indian rupees.</p></div>',
            unsafe_allow_html=True)
k = an.kpis(df)
kp = an.kpis(prev) if not prev.empty else {}
c = st.columns(5)
with c[0]: card("Total revenue", inr(k["revenue"]), delta(k["revenue"], kp.get("revenue")), TEAL)
with c[1]: card("Total orders", f"{k['orders']:,}", delta(k["orders"], kp.get("orders")), AMBER)
with c[2]: card("Total customers", f"{k['customers']:,}", delta(k["customers"], kp.get("customers")), "#2A9D8F")
with c[3]: card("Total profit", inr(k["profit"]), delta(k["profit"], kp.get("profit")), CORAL)
with c[4]: card("Average order value", inr(k["aov"]), delta(k["aov"], kp.get("aov")), PLUM)
c = st.columns(4)
with c[0]: card("Profit margin", f"{k['margin_pct']:.1f}%", accent=CORAL, small=True)
with c[1]: card("Repeat customers", f"{k['repeat_rate_pct']:.1f}%", accent="#2A9D8F", small=True)
with c[2]: card("Cancellation rate", f"{k['cancel_rate_pct']:.1f}%", accent=AMBER, small=True)
with c[3]: card("Return rate", f"{k['return_rate_pct']:.1f}%", accent=SLATE, small=True)

tab_overview, tab_products, tab_geo, tab_customers, tab_data = st.tabs(
    ["Overview", "Products", "Geography", "Customers", "Data quality"])

# ---------- Overview ----------
with tab_overview:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Monthly revenue and profit")
        m = an.monthly_trend(df)
        fig = go.Figure()
        fig.add_bar(x=m["month"], y=m["revenue"], name="Revenue", marker_color=TEAL)
        fig.add_scatter(x=m["month"], y=m["profit"], name="Profit", mode="lines+markers", line=dict(color=AMBER, width=3))
        fig.add_scatter(x=m["month"], y=m["revenue_ma3"], name="3-month average revenue", mode="lines",
                        line=dict(color=CORAL, width=2, dash="dot"))
        st.plotly_chart(style(fig, 380, "yaxis"))
    with right:
        st.subheader("Yearly summary")
        y = an.yearly_summary(df)
        y["year"] = y["year"].astype(str)
        fig = px.bar(y, x="year", y=["revenue", "profit"], barmode="group", labels={"value": "", "variable": ""})
        st.plotly_chart(style(fig, 380, "yaxis"))
    a, b, c3 = st.columns(3)
    with a:
        st.subheader("Sales by category")
        cp = an.category_performance(df)
        fig = px.bar(cp, x="revenue", y="category", orientation="h", text=cp["revenue"].map(inr),
                     labels={"revenue": "", "category": ""})
        fig.update_traces(marker_color=TEAL, textposition="outside", cliponaxis=False)
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(style(fig, 340))
    with b:
        st.subheader("Payment methods")
        pm = an.payment_analysis(df)
        fig = px.pie(pm, names="payment_method", values="orders", hole=0.55)
        fig.update_traces(textinfo="percent", sort=False)
        st.plotly_chart(style(fig, 340))
    with c3:
        st.subheader("Order status")
        stt = an.status_analysis(df)
        fig = px.bar(stt, x="order_status", y="orders", text="orders", color="order_status",
                     color_discrete_map={"Delivered": "#2A9D8F", "Shipped": TEAL, "Cancelled": CORAL, "Returned": AMBER},
                     labels={"order_status": "", "orders": ""})
        fig.update_layout(showlegend=False)
        st.plotly_chart(style(fig, 340))
    lost = stt[stt["order_status"].isin(["Cancelled", "Returned"])]["order_value"].sum()
    st.caption(f"Cancelled and returned orders represent {inr(lost)} of order value that did not turn into revenue.")

# ---------- Products ----------
with tab_products:
    metric = st.radio("Rank products by", ["Revenue", "Profit", "Units sold"], horizontal=True)
    col, label = {"Revenue": ("revenue", "Revenue"), "Profit": ("profit", "Profit"), "Units sold": ("units", "Units sold")}[metric]
    left, right = st.columns(2)
    with left:
        st.subheader(f"Top 10 products by {metric.lower()}")
        tp = an.top_products(df, 10, col)
        fig = px.bar(tp, x=col, y="product_name", orientation="h", color="category", labels={col: label, "product_name": ""})
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(style(fig, 420, "xaxis" if col != "units" else None))
    with right:
        st.subheader("Where revenue comes from")
        pp = an.product_performance(df)
        fig = px.treemap(pp, path=[px.Constant("All sales"), "category", "product_name"], values="revenue",
                         color="margin_pct", color_continuous_scale=["#C8553D", "#F2E3B3", "#1B6F8A"],
                         labels={"margin_pct": "Margin %"})
        st.plotly_chart(style(fig, 420))
    st.subheader("Category performance")
    cp = an.category_performance(df)
    fig = px.bar(cp, x="category", y="margin_pct", text=cp["margin_pct"].map(lambda v: f"{v:.1f}%"),
                 labels={"category": "", "margin_pct": "Profit margin (%)"})
    fig.update_traces(marker_color=AMBER, textposition="outside")
    st.plotly_chart(style(fig, 300))
    show = cp.rename(columns={"category": "Category", "revenue": "Revenue", "profit": "Profit", "orders": "Orders",
                              "units": "Units", "margin_pct": "Margin %", "aov": "Avg order value",
                              "revenue_share_pct": "Revenue share %"})
    st.dataframe(show.round(2), hide_index=True)

# ---------- Geography ----------
with tab_geo:
    sr, cr = an.regional(df, "state"), an.regional(df, "city")
    left, right = st.columns(2)
    with left:
        st.subheader("Revenue by state")
        fig = px.bar(sr, x="revenue", y="state", orientation="h", labels={"revenue": "", "state": ""})
        fig.update_traces(marker_color=TEAL)
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(style(fig, 440, "xaxis"))
    with right:
        st.subheader("Top 15 cities by revenue")
        fig = px.bar(cr.head(15), x="revenue", y="city", orientation="h", color="state", labels={"revenue": "", "city": ""})
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(style(fig, 440, "xaxis"))
    st.subheader("State and city breakdown")
    fig = px.treemap(cr, path=[px.Constant("India"), "state", "city"], values="revenue", color="aov",
                     color_continuous_scale="Teal", labels={"aov": "Avg order value"})
    st.plotly_chart(style(fig, 380))
    st.dataframe(sr.round(2).rename(columns={"state": "State", "revenue": "Revenue", "profit": "Profit", "orders": "Orders",
                                             "customers": "Customers", "aov": "Avg order value",
                                             "revenue_share_pct": "Revenue share %"}), hide_index=True)

# ---------- Customers ----------
with tab_customers:
    beh = an.customer_behaviour(df)
    c = st.columns(4)
    with c[0]: card("Repeat purchase rate", f"{beh['repeat_rate_pct']:.1f}%", accent="#2A9D8F", small=True)
    with c[1]: card("Orders per customer", f"{beh['avg_orders_per_customer']:.2f}", accent=TEAL, small=True)
    with c[2]: card("Days between orders", f"{beh['avg_days_between_orders']:.0f}", accent=AMBER, small=True)
    with c[3]: card("Revenue from top 20% of customers", f"{beh['top20_revenue_share_pct']:.0f}%", accent=CORAL, small=True)
    seg = an.rfm(df)
    if seg.empty:
        st.info("Customer segmentation needs at least 5 customers in the current selection. Widen your filters.")
    else:
        ss = an.segment_summary(seg)
        left, right = st.columns(2)
        with left:
            st.subheader("Customers by segment")
            fig = px.bar(ss, x="customers", y="segment", orientation="h", color="segment",
                         color_discrete_map=SEGMENT_COLORS, text="customers", labels={"segment": "", "customers": ""})
            fig.update_layout(showlegend=False, yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(style(fig, 360))
        with right:
            st.subheader("Revenue share by segment")
            fig = px.pie(ss, names="segment", values="revenue", hole=0.55, color="segment", color_discrete_map=SEGMENT_COLORS)
            fig.update_traces(textinfo="percent")
            st.plotly_chart(style(fig, 360))
        left, right = st.columns(2)
        with left:
            st.subheader("Frequency vs. spend")
            fig = px.scatter(seg, x="frequency", y="monetary", color="segment", color_discrete_map=SEGMENT_COLORS,
                             hover_data=["customer_name", "recency_days"], labels={"frequency": "Orders", "monetary": "Total spend"})
            st.plotly_chart(style(fig, 360, "yaxis"))
        with right:
            st.subheader("Orders per customer")
            fig = px.histogram(beh["orders_per_customer"].to_frame("orders"), x="orders", nbins=25, labels={"orders": "Orders", "count": "Customers"})
            fig.update_traces(marker_color=TEAL)
            fig.update_layout(yaxis_title="Customers")
            st.plotly_chart(style(fig, 360))
        st.subheader("Segment summary")
        st.dataframe(ss.round(2).rename(columns={"segment": "Segment", "customers": "Customers", "revenue": "Revenue",
                                                 "avg_orders": "Avg orders", "avg_recency_days": "Avg days since last order",
                                                 "revenue_share_pct": "Revenue share %", "customer_share_pct": "Customer share %"}),
                     hide_index=True)
    st.subheader("New and returning customers by month")
    nr = an.new_vs_returning(df)
    fig = px.bar(nr, x="month", y="customers", color="customer_type", barmode="stack",
                 color_discrete_map={"New": AMBER, "Returning": TEAL}, labels={"month": "", "customers": "Customers", "customer_type": ""})
    st.plotly_chart(style(fig, 320))
    st.caption("A customer counts as new in their first order month within the selected data.")

# ---------- Data quality ----------
with tab_data:
    report_path = ROOT / "cleaning_report.json"
    if report_path.exists():
        rep = json.loads(report_path.read_text(encoding="utf-8"))
        c = st.columns(4)
        with c[0]: card("Raw rows", f"{rep['raw_rows']:,}", accent=SLATE, small=True)
        with c[1]: card("Clean rows", f"{rep['final_rows']:,}", accent=TEAL, small=True)
        with c[2]: card("Duplicates removed", f"{rep['exact_duplicates_removed'] + rep['duplicate_order_ids_removed']:,}", accent=CORAL, small=True)
        with c[3]: card("Values imputed", f"{sum(rep['imputed'].values()):,}", accent=AMBER, small=True)
        st.markdown("**Cleaning steps and what they fixed**")
        st.json(rep, expanded=False)
    st.subheader("Filtered orders")
    st.dataframe(df.assign(order_date=df["order_date"].dt.strftime("%Y-%m-%d")).drop(columns=["is_revenue_order"]).head(2000), hide_index=True)
    st.download_button("Download filtered data (CSV)", df.to_csv(index=False).encode("utf-8"), "filtered_orders.csv", "text/csv")
