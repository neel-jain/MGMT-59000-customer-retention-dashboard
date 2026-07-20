"""
Customer Growth & Retention Intelligence Dashboard
====================================================
An interactive Streamlit dashboard built on NR_dataset.xlsx that helps
commercial and marketing teams:

  1. Spot potential and emerging growth opportunities within the existing
     customer base.
  2. Detect early warning signs of customer decline or reduced engagement.
  3. Turn both of the above into concrete, data-driven recommendations that
     support commercial/marketing strategy and revenue optimization.

Core fields used: label, purchaseamount, customerregion, productcategory,
retailchannel, customerid, transactiondate.
(CustomerSatisfaction is also used as a supporting signal for early-warning
detection, since it is one of the strongest available predictors of churn.)

Author: Data Analyst (generated with Claude)
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Customer Growth & Retention Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY_COLOR = "#4C6FFF"
LABEL_COLORS = {
    "Growth": "#2E9E5B",
    "Promising": "#4C6FFF",
    "Stable": "#F2A93B",
    "Decline": "#E05252",
    "Unclassified": "#9AA0AC",
}

# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------
DATA_PATH = Path(__file__).parent / "NR_dataset.xlsx"


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Standardize column names to the field names referenced in the brief
    df = df.rename(
        columns={
            "CustomerID": "customerid",
            "TransactionID": "transactionid",
            "TransactionDate": "transactiondate",
            "ProductCategory": "productcategory",
            "PurchaseAmount": "purchaseamount",
            "CustomerAgeGroup": "customeragegroup",
            "CustomerGender": "customergender",
            "CustomerRegion": "customerregion",
            "CustomerSatisfaction": "customersatisfaction",
            "RetailChannel": "retailchannel",
        }
    )

    df["label"] = df["label"].fillna("Unclassified")
    df["transactiondate"] = pd.to_datetime(df["transactiondate"])
    df["purchaseamount"] = pd.to_numeric(df["purchaseamount"], errors="coerce")
    df = df.dropna(subset=["purchaseamount", "transactiondate"])

    return df


df_raw = load_data(DATA_PATH)

MAX_DATE = df_raw["transactiondate"].max()
MIN_DATE = df_raw["transactiondate"].min()

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.title("🔎 Filters")
st.sidebar.caption("Filters apply to every tab in the dashboard.")

date_range = st.sidebar.date_input(
    "Transaction date range",
    value=(MIN_DATE.date(), MAX_DATE.date()),
    min_value=MIN_DATE.date(),
    max_value=MAX_DATE.date(),
)

region_opts = sorted(df_raw["customerregion"].dropna().unique().tolist())
channel_opts = sorted(df_raw["retailchannel"].dropna().unique().tolist())
category_opts = sorted(df_raw["productcategory"].dropna().unique().tolist())
label_opts = [l for l in ["Growth", "Promising", "Stable", "Decline", "Unclassified"] if l in df_raw["label"].unique()]

sel_regions = st.sidebar.multiselect("Customer region", region_opts, default=region_opts)
sel_channels = st.sidebar.multiselect("Retail channel", channel_opts, default=channel_opts)
sel_categories = st.sidebar.multiselect("Product category", category_opts, default=category_opts)
sel_labels = st.sidebar.multiselect("Customer segment (label)", label_opts, default=label_opts)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = MIN_DATE.date(), MAX_DATE.date()

mask = (
    (df_raw["transactiondate"].dt.date >= start_date)
    & (df_raw["transactiondate"].dt.date <= end_date)
    & (df_raw["customerregion"].isin(sel_regions))
    & (df_raw["retailchannel"].isin(sel_channels))
    & (df_raw["productcategory"].isin(sel_categories))
    & (df_raw["label"].isin(sel_labels))
)
df = df_raw[mask].copy()

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Showing **{len(df):,}** of **{len(df_raw):,}** transactions "
    f"({df['customerid'].nunique()} of {df_raw['customerid'].nunique()} customers)."
)

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.title("📈 Customer Growth & Retention Intelligence Dashboard")
st.caption(
    "Identify growth opportunities, catch early warning signs of decline, "
    "and turn both into concrete commercial actions."
)

if df.empty:
    st.warning("No transactions match the current filter selection. Please broaden your filters.")
    st.stop()

# ----------------------------------------------------------------------------
# SHARED HELPER METRICS
# ----------------------------------------------------------------------------
total_revenue = df["purchaseamount"].sum()
total_txns = len(df)
unique_customers = df["customerid"].nunique()
aov = df["purchaseamount"].mean()
has_satisfaction = "customersatisfaction" in df.columns
avg_satisfaction = df["customersatisfaction"].mean() if has_satisfaction else np.nan

label_summary = (
    df.groupby("label")
    .agg(
        revenue=("purchaseamount", "sum"),
        transactions=("purchaseamount", "count"),
        customers=("customerid", "nunique"),
        avg_order_value=("purchaseamount", "mean"),
        avg_satisfaction=("customersatisfaction", "mean") if has_satisfaction else ("purchaseamount", "mean"),
    )
    .reindex(label_opts)
    .dropna(how="all")
    .reset_index()
)
label_summary["revenue_share"] = label_summary["revenue"] / total_revenue

# Customer-level rollup (recency, frequency, monetary + dominant label)
customer_rollup = (
    df.groupby("customerid")
    .agg(
        total_spend=("purchaseamount", "sum"),
        transactions=("purchaseamount", "count"),
        avg_order_value=("purchaseamount", "mean"),
        last_purchase=("transactiondate", "max"),
        first_purchase=("transactiondate", "min"),
        region=("customerregion", lambda x: x.mode().iat[0]),
        channel=("retailchannel", lambda x: x.mode().iat[0]),
        top_category=("productcategory", lambda x: x.mode().iat[0]),
        avg_satisfaction=("customersatisfaction", "mean") if has_satisfaction else ("purchaseamount", "mean"),
        label=("label", lambda x: x.mode().iat[0]),
    )
    .reset_index()
)
customer_rollup["recency_days"] = (MAX_DATE - customer_rollup["last_purchase"]).dt.days

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------
tab_overview, tab_growth, tab_warning, tab_reco = st.tabs(
    ["🏠 Overview", "🚀 Growth Opportunities", "⚠️ Early Warning Signs", "🎯 Strategic Recommendations"]
)

# =============================================================================
# TAB 1 — OVERVIEW
# =============================================================================
with tab_overview:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Revenue", f"${total_revenue:,.0f}")
    c2.metric("Transactions", f"{total_txns:,}")
    c3.metric("Active Customers", f"{unique_customers:,}")
    c4.metric("Avg Order Value", f"${aov:,.2f}")
    if has_satisfaction:
        c5.metric("Avg Satisfaction", f"{avg_satisfaction:.2f} / 5")
    else:
        c5.metric("Avg Satisfaction", "n/a")

    st.markdown("### Revenue trend")
    weekly = (
        df.set_index("transactiondate")
        .resample("W-MON")["purchaseamount"]
        .sum()
        .reset_index()
        .rename(columns={"transactiondate": "week", "purchaseamount": "revenue"})
    )
    fig_trend = px.line(
        weekly, x="week", y="revenue", markers=True,
        labels={"week": "Week starting", "revenue": "Revenue ($)"},
    )
    fig_trend.update_traces(line_color=PRIMARY_COLOR, line_width=3)
    fig_trend.update_layout(height=320, margin=dict(t=10, b=10))
    st.plotly_chart(fig_trend, use_container_width=True)

    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown("### Customer segments (label)")
        fig_pie = px.pie(
            label_summary, names="label", values="revenue",
            color="label", color_discrete_map=LABEL_COLORS, hole=0.45,
        )
        fig_pie.update_traces(textinfo="label+percent")
        fig_pie.update_layout(height=340, margin=dict(t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        st.markdown("### Revenue by region & channel")
        rc = df.groupby(["customerregion", "retailchannel"])["purchaseamount"].sum().reset_index()
        fig_rc = px.bar(
            rc, x="customerregion", y="purchaseamount", color="retailchannel",
            barmode="group", labels={"purchaseamount": "Revenue ($)", "customerregion": "Region", "retailchannel": "Channel"},
        )
        fig_rc.update_layout(height=340, margin=dict(t=10, b=10))
        st.plotly_chart(fig_rc, use_container_width=True)

    st.markdown("### Top product categories by revenue")
    top_cats = (
        df.groupby("productcategory")["purchaseamount"].sum()
        .sort_values(ascending=False).head(10).reset_index()
    )
    fig_cats = px.bar(
        top_cats, x="purchaseamount", y="productcategory", orientation="h",
        labels={"purchaseamount": "Revenue ($)", "productcategory": "Category"},
        color_discrete_sequence=[PRIMARY_COLOR],
    )
    fig_cats.update_layout(height=380, margin=dict(t=10, b=10), yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig_cats, use_container_width=True)

# =============================================================================
# TAB 2 — GROWTH OPPORTUNITIES
# =============================================================================
with tab_growth:
    st.markdown(
        "This view highlights **where the existing customer base is expanding**, "
        "so commercial teams can double down with cross-sell, upsell, and loyalty investments."
    )

    growth_labels = [l for l in ["Growth", "Promising"] if l in df["label"].unique()]
    df_growth = df[df["label"].isin(growth_labels)]

    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Growth + Promising Revenue", f"${df_growth['purchaseamount'].sum():,.0f}",
               f"{df_growth['purchaseamount'].sum() / total_revenue:.0%} of total")
    g2.metric("Growth + Promising Customers", f"{df_growth['customerid'].nunique():,}")
    g3.metric("Avg Order Value (this group)", f"${df_growth['purchaseamount'].mean():,.2f}" if len(df_growth) else "n/a")
    if has_satisfaction and len(df_growth):
        g4.metric("Avg Satisfaction (this group)", f"{df_growth['customersatisfaction'].mean():.2f} / 5")
    else:
        g4.metric("Avg Satisfaction (this group)", "n/a")

    st.markdown("### Revenue & customer count by segment")
    fig_seg = go.Figure()
    fig_seg.add_bar(
        x=label_summary["label"], y=label_summary["revenue"], name="Revenue ($)",
        marker_color=[LABEL_COLORS.get(l, "#999") for l in label_summary["label"]],
    )
    fig_seg.update_layout(height=340, margin=dict(t=10, b=10), yaxis_title="Revenue ($)")
    st.plotly_chart(fig_seg, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Category affinity: Growth/Promising vs. rest")
        if len(df_growth):
            cat_growth = df_growth.groupby("productcategory")["purchaseamount"].sum()
            cat_other = df[~df["label"].isin(growth_labels)].groupby("productcategory")["purchaseamount"].sum()
            cat_compare = pd.concat(
                [cat_growth.rename("Growth/Promising"), cat_other.rename("Other segments")], axis=1
            ).fillna(0)
            cat_compare["total"] = cat_compare.sum(axis=1)
            cat_compare = cat_compare.sort_values("total", ascending=False).head(8).drop(columns="total")
            fig_affinity = px.bar(
                cat_compare.reset_index().melt(id_vars="productcategory", var_name="Segment", value_name="Revenue"),
                x="Revenue", y="productcategory", color="Segment", orientation="h", barmode="group",
                color_discrete_map={"Growth/Promising": "#2E9E5B", "Other segments": "#9AA0AC"},
            )
            fig_affinity.update_layout(height=380, margin=dict(t=10, b=10), yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(fig_affinity, use_container_width=True)
        else:
            st.info("No Growth/Promising transactions in current filter.")

    with col_b:
        st.markdown("### Region × Channel opportunity map")
        opp = df_growth.groupby(["customerregion", "retailchannel"])["purchaseamount"].sum().reset_index()
        if len(opp):
            fig_heat = px.density_heatmap(
                opp, x="retailchannel", y="customerregion", z="purchaseamount",
                color_continuous_scale="Greens", labels={"purchaseamount": "Revenue ($)"},
            )
            fig_heat.update_layout(height=380, margin=dict(t=10, b=10))
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("No Growth/Promising transactions in current filter.")

    st.markdown("### Top high-potential customers")
    st.caption("Highest-spending customers currently labeled Growth or Promising — prioritize for upsell/loyalty offers.")
    top_customers = (
        customer_rollup[customer_rollup["label"].isin(growth_labels)]
        .sort_values("total_spend", ascending=False)
        .head(10)
    )
    display_cols = ["customerid", "label", "region", "channel", "top_category",
                     "transactions", "total_spend", "avg_order_value"]
    if has_satisfaction:
        display_cols.append("avg_satisfaction")
    st.dataframe(
        top_customers[display_cols].rename(columns={
            "customerid": "Customer ID", "label": "Segment", "region": "Region",
            "channel": "Channel", "top_category": "Top Category", "transactions": "Transactions",
            "total_spend": "Total Spend ($)", "avg_order_value": "Avg Order Value ($)",
            "avg_satisfaction": "Avg Satisfaction",
        }).style.format({"Total Spend ($)": "${:,.2f}", "Avg Order Value ($)": "${:,.2f}", "Avg Satisfaction": "{:.1f}"}),
        use_container_width=True, hide_index=True,
    )

# =============================================================================
# TAB 3 — EARLY WARNING SIGNS
# =============================================================================
with tab_warning:
    st.markdown(
        "This view surfaces **customers and segments showing signs of disengagement or decline**, "
        "so retention efforts can be targeted before revenue is lost."
    )

    decline_df = df[df["label"] == "Decline"] if "Decline" in df["label"].unique() else df.iloc[0:0]
    revenue_at_risk = decline_df["purchaseamount"].sum()

    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Revenue at Risk (Decline)", f"${revenue_at_risk:,.0f}",
               f"{revenue_at_risk / total_revenue:.0%} of total" if total_revenue else "n/a")
    w2.metric("Customers in Decline", f"{decline_df['customerid'].nunique():,}")
    if has_satisfaction and len(decline_df):
        w3.metric("Avg Satisfaction (Decline)", f"{decline_df['customersatisfaction'].mean():.2f} / 5")
    else:
        w3.metric("Avg Satisfaction (Decline)", "n/a")
    recency_threshold = int(customer_rollup["recency_days"].quantile(0.75)) if len(customer_rollup) else 0
    at_risk_recency = customer_rollup[customer_rollup["recency_days"] >= recency_threshold]
    w4.metric("Customers Inactive ≥ Top Quartile Recency", f"{len(at_risk_recency):,}")

    col_a, col_b = st.columns(2)

    with col_a:
        if has_satisfaction:
            st.markdown("### Satisfaction by segment")
            sat_by_label = df.groupby("label")["customersatisfaction"].mean().reindex(label_opts).dropna().reset_index()
            fig_sat = px.bar(
                sat_by_label, x="label", y="customersatisfaction", color="label",
                color_discrete_map=LABEL_COLORS, labels={"customersatisfaction": "Avg Satisfaction (1-5)", "label": "Segment"},
            )
            fig_sat.update_layout(height=340, margin=dict(t=10, b=10), showlegend=False)
            fig_sat.add_hline(y=3, line_dash="dot", line_color="gray", annotation_text="Neutral (3.0)")
            st.plotly_chart(fig_sat, use_container_width=True)

    with col_b:
        st.markdown("### Decline concentration by region")
        if len(decline_df):
            dec_region = decline_df.groupby("customerregion")["purchaseamount"].sum().reset_index()
            fig_dec_region = px.bar(
                dec_region, x="customerregion", y="purchaseamount",
                labels={"purchaseamount": "Revenue at risk ($)", "customerregion": "Region"},
                color_discrete_sequence=["#E05252"],
            )
            fig_dec_region.update_layout(height=340, margin=dict(t=10, b=10))
            st.plotly_chart(fig_dec_region, use_container_width=True)
        else:
            st.info("No Decline-labeled transactions in current filter.")

    st.markdown("### Recency, frequency & satisfaction — full customer view")
    st.caption(
        f"Customers with recency ≥ {recency_threshold} days since last purchase (top quartile), "
        + ("or satisfaction ≤ 2, " if has_satisfaction else "")
        + "or labeled Decline, are flagged as churn risks."
    )
    flag_cond = customer_rollup["recency_days"] >= recency_threshold
    flag_cond |= customer_rollup["label"] == "Decline"
    if has_satisfaction:
        flag_cond |= customer_rollup["avg_satisfaction"] <= 2
    flagged = customer_rollup[flag_cond].sort_values(["label", "recency_days"], ascending=[True, False])

    flag_display_cols = ["customerid", "label", "region", "channel", "recency_days",
                          "transactions", "total_spend"]
    if has_satisfaction:
        flag_display_cols.append("avg_satisfaction")
    st.dataframe(
        flagged[flag_display_cols].rename(columns={
            "customerid": "Customer ID", "label": "Segment", "region": "Region", "channel": "Channel",
            "recency_days": "Days Since Last Purchase", "transactions": "Transactions",
            "total_spend": "Total Spend ($)", "avg_satisfaction": "Avg Satisfaction",
        }).style.format({"Total Spend ($)": "${:,.2f}", "Avg Satisfaction": "{:.1f}"}),
        use_container_width=True, hide_index=True,
    )

# =============================================================================
# TAB 4 — STRATEGIC RECOMMENDATIONS
# =============================================================================
with tab_reco:
    st.markdown(
        "Recommendations below are generated directly from the filtered data — "
        "adjust the sidebar filters to regenerate insights for a specific region, channel, or time window."
    )

    insights = []

    # 1. Growth opportunity: best-performing region/channel combo among Growth+Promising
    if len(df_growth):
        best_combo = (
            df_growth.groupby(["customerregion", "retailchannel"])["purchaseamount"]
            .sum().idxmax()
        )
        best_combo_rev = df_growth.groupby(["customerregion", "retailchannel"])["purchaseamount"].sum().max()
        insights.append((
            "🚀 Growth",
            f"**{best_combo[0]} region via {best_combo[1]}** generates the most revenue "
            f"(${best_combo_rev:,.0f}) among Growth/Promising customers. "
            f"Prioritize marketing spend and inventory availability here to accelerate momentum."
        ))

    # 2. Category cross-sell opportunity
    if len(df_growth):
        top_growth_cat = df_growth.groupby("productcategory")["purchaseamount"].sum().idxmax()
        insights.append((
            "🚀 Growth",
            f"**{top_growth_cat}** is the top-selling category among Growth/Promising customers. "
            f"Consider bundling complementary products or launching a loyalty tier around this category "
            f"to increase basket size."
        ))

    # 3. Revenue at risk
    if revenue_at_risk > 0:
        insights.append((
            "⚠️ Retention",
            f"**${revenue_at_risk:,.0f} in revenue is tied to Decline-labeled customers** "
            f"({revenue_at_risk / total_revenue:.0%} of filtered revenue). "
            f"Launch a targeted win-back or retention offer for this group before further attrition."
        ))

    # 4. Low satisfaction segment
    if has_satisfaction and len(decline_df):
        low_sat_share = (decline_df["customersatisfaction"] <= 2).mean()
        insights.append((
            "⚠️ Retention",
            f"**{low_sat_share:.0%} of Decline-segment transactions have satisfaction ≤ 2/5.** "
            f"Low satisfaction is a leading indicator here — route these accounts to customer success "
            f"for proactive outreach before renewal or next expected purchase."
        ))

    # # 5. Regional decline concentration
    # if len(decline_df):
    #     worst_region = decline_df.groupby("customerregion")["purchaseamount"].sum().idxmax()
    #     insights.append((
    #         "⚠️ Retention",
    #         f"**{worst_region} region has the highest revenue at risk** from Decline-labeled customers. "
    #         f"Investigate local service quality, delivery times, or competitor activity in this region."
    #     ))

    # 6. Inactivity / recency
    # if len(at_risk_recency):
    #     insights.append((
    #         "⚠️ Retention",
    #         f"**{len(at_risk_recency)} customers** have gone ≥ {recency_threshold} days without a purchase "
    #         f"(top quartile of recency). Trigger a re-engagement campaign (e.g. personalized discount or "
    #         f"replenishment reminder) for this group."
    #     ))

    # 7. Channel strategy
    channel_rev = df.groupby("retailchannel")["purchaseamount"].sum()
    if len(channel_rev) > 1:
        lead_channel = channel_rev.idxmax()
        lag_channel = channel_rev.idxmin()
        insights.append((
            "🎯 Strategy",
            f"**{lead_channel}** outperforms **{lag_channel}** "
            f"(\${channel_rev.max():,.0f} vs \${channel_rev.min():,.0f}). "
            f"Evaluate whether underperformance in {lag_channel} is a channel-experience issue "
            f"or a customer-mix issue, and pilot a targeted promotion there."
        ))

    # 8. Stable segment nudge
    stable_df = df[df["label"] == "Stable"] if "Stable" in df["label"].unique() else df.iloc[0:0]
    if len(stable_df):
        insights.append((
            "🎯 Strategy",
            f"**{stable_df['customerid'].nunique()} Stable customers** "
            f"(${stable_df['purchaseamount'].sum():,.0f} revenue) show flat but steady engagement. "
            f"These are strong candidates for upsell testing since they are not yet at risk but also not "
            f"actively growing — small, well-timed incentives could shift them into the Growth segment."
        ))

    if not insights:
        st.info("Not enough data in the current filter selection to generate recommendations. Try broadening the filters.")
    else:
        for tag, text in insights:
            st.markdown(f"**{tag}** — {text}")
            st.markdown("")

    st.markdown("---")
    st.markdown("### Segment summary reference table")
    st.dataframe(
        label_summary.rename(columns={
            "label": "Segment", "revenue": "Revenue ($)", "transactions": "Transactions",
            "customers": "Customers", "avg_order_value": "Avg Order Value ($)",
            "avg_satisfaction": "Avg Satisfaction", "revenue_share": "Revenue Share",
        }).style.format({
            "Revenue ($)": "${:,.2f}", "Avg Order Value ($)": "${:,.2f}",
            "Avg Satisfaction": "{:.2f}", "Revenue Share": "{:.0%}",
        }),
        use_container_width=True, hide_index=True,
    )

st.markdown("---")
st.caption("Built with Streamlit · Data source: NR_dataset.xlsx · Fields used: label, purchaseamount, customerregion, productcategory, retailchannel, customerid, transactiondate (satisfaction used as a supporting signal).")
