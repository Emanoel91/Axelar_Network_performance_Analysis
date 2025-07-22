import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from utils import run_query, date_trunc_mapping

st.set_page_config(page_title="User Analysis", layout="wide")
st.title("User Analysis")

# --- Filters ---
timeframe = st.selectbox("Select Time Frame", ["day", "week", "month"])
start_date = st.date_input("Start Date", datetime(2022, 1, 1))
end_date = st.date_input("End Date", datetime.today())

date_trunc_col = date_trunc_mapping(timeframe)

# --- Query 1: Total Users ---
query_total_users = f"""
SELECT COUNT(DISTINCT tx_from) AS "Total Users"
FROM axelar.core.fact_transactions
WHERE tx_succeeded='true'
  AND block_timestamp::date >= '{start_date}'
  AND block_timestamp::date <= '{end_date}'
"""
total_users = run_query(query_total_users).iloc[0]["Total Users"]

# --- Query 2: Median Number of User Transactions ---
query_median_tx = f"""
WITH tab1 AS (
    SELECT tx_from, COUNT(DISTINCT tx_id) AS tx_count
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
)
SELECT ROUND(MEDIAN(tx_count)) AS "Median Number of User Transactions"
FROM tab1
"""
median_tx = run_query(query_median_tx).iloc[0]["Median Number of User Transactions"]

# --- Query 3: User Growth Percentages ---
query_growth = """
WITH tab1 AS (
    SELECT COUNT(DISTINCT tx_from) AS User1d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date -1
),
tab2 AS (
    SELECT COUNT(DISTINCT tx_from) AS User2d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date -2
),
tab3 AS (
    SELECT COUNT(DISTINCT tx_from) AS User7d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date -8
),
tab4 AS (
    SELECT COUNT(DISTINCT tx_from) AS User30d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date -31
),
tab5 AS (
    SELECT COUNT(DISTINCT tx_from) AS User365d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date -366
)
SELECT
    ROUND(((User1d-User2d)/User2d)*100,2) AS "User Change (1D)",
    ROUND(((User1d-User7d)/User7d)*100,2) AS "User Change (7D)",
    ROUND(((User1d-User30d)/User30d)*100,2) AS "User Change (30D)",
    ROUND(((User1d-User365d)/User365d)*100,2) AS "User Change (1Y)"
FROM tab1, tab2, tab3, tab4, tab5
"""
user_growth = run_query(query_growth).iloc[0]

# --- Row 1 ---
col1, col2 = st.columns(2)
col1.metric("Total Axelar Network Users", f"{total_users:,}")
col2.metric("Median Number of User Transactions", f"{median_tx:,}")

# --- Row 2 ---
col3, col4 = st.columns(2)
col3.metric("User Growth Percentage: 1D", f"{user_growth['User Change (1D)']:.2f}%", delta=f"{user_growth['User Change (1D)']:.2f}%")
col4.metric("User Growth Percentage: 7D", f"{user_growth['User Change (7D)']:.2f}%", delta=f"{user_growth['User Change (7D)']:.2f}%")

# --- Row 3 ---
col5, col6 = st.columns(2)
col5.metric("User Growth Percentage: 30D", f"{user_growth['User Change (30D)']:.2f}%", delta=f"{user_growth['User Change (30D)']:.2f}%")
col6.metric("User Growth Percentage: 1Y", f"{user_growth['User Change (1Y)']:.2f}%", delta=f"{user_growth['User Change (1Y)']:.2f}%")

# --- Query 4: Axelar Users Over Time ---
query_users_over_time = f"""
WITH tab1 AS (
    SELECT {date_trunc_col} AS "Date", COUNT(DISTINCT tx_from) AS "Total Users"
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
),
tab2 AS (
    WITH tab10 AS (
        SELECT tx_from, MIN(block_timestamp::date) AS first_tx
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true'
          AND block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1
    )
    SELECT {date_trunc_col} AS "Date", COUNT(DISTINCT tx_from) AS "New Users"
    FROM tab10
    GROUP BY 1
)
SELECT tab1."Date", "Total Users", COALESCE("New Users",0) AS "New Users", "Total Users" - COALESCE("New Users",0) AS "Active Users"
FROM tab1
LEFT JOIN tab2 ON tab1."Date" = tab2."Date"
ORDER BY tab1."Date"
"""
df_users_over_time = run_query(query_users_over_time)

st.markdown("#### Axelar Users Over Time")
chart4 = alt.Chart(df_users_over_time).mark_bar().encode(
    x="Date:T",
    y="New Users:Q",
    color=alt.value("#1f77b4")
).properties(height=400)
st.altair_chart(chart4, use_container_width=True)

# --- Query 5: Growth of Axelar Network Users Over Time ---
query_growth_over_time = f"""
WITH tab10 AS (
    SELECT tx_from, MIN(block_timestamp::date) AS first_tx
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
)
SELECT {date_trunc_col} AS "Date", COUNT(DISTINCT tx_from) AS "New Users",
       SUM(COUNT(DISTINCT tx_from)) OVER (ORDER BY {date_trunc_col}) AS "Total Users"
FROM tab10
GROUP BY 1
ORDER BY 1
"""
df_growth_over_time = run_query(query_growth_over_time)

col7, col8 = st.columns(2)
with col7:
    st.markdown("#### Growth of Axelar Network Users")
    chart5 = alt.Chart(df_growth_over_time).mark_bar().encode(
        x="Date:T",
        y="Total Users:Q",
        color=alt.value("#2ca02c")
    ).properties(height=400)
    st.altair_chart(chart5, use_container_width=True)

# --- Query 6: Distribution of Users Based on TXs Count ---
query_tx_distribution = f"""
WITH tab1 AS (
    SELECT tx_from, COUNT(DISTINCT tx_id) AS tx_count
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
)
SELECT tx_count AS "TXs Count", COUNT(DISTINCT tx_from) AS "Users Count"
FROM tab1
GROUP BY 1
ORDER BY 1
"""
df_tx_distribution = run_query(query_tx_distribution)

with col8:
    st.markdown("#### Users by TXs Count")
    chart6 = alt.Chart(df_tx_distribution).mark_bar().encode(
        x="TXs Count:Q",
        y="Users Count:Q",
        color=alt.value("#ff7f0e")
    ).properties(height=400)
    st.altair_chart(chart6, use_container_width=True)

# --- Query 7: Distribution of Users by Days of Activity ---
query_activity_distribution = f"""
WITH tab1 AS (
    SELECT tx_from,
           COUNT(DISTINCT block_timestamp::date) AS active_days,
           CASE
               WHEN COUNT(DISTINCT block_timestamp::date) = 1 THEN 'n=1'
               WHEN COUNT(DISTINCT block_timestamp::date) > 1 AND COUNT(DISTINCT block_timestamp::date) <= 7 THEN '1<n<=7'
               WHEN COUNT(DISTINCT block_timestamp::date) > 7 AND COUNT(DISTINCT block_timestamp::date) <= 30 THEN '7<n<=30'
               ELSE 'n>30'
           END AS "Class"
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
)
SELECT "Class", COUNT(DISTINCT tx_from) AS "Users Count"
FROM tab1
GROUP BY 1
"""
df_activity_distribution = run_query(query_activity_distribution)

st.markdown("#### Users by Active Days")
chart7 = alt.Chart(df_activity_distribution).mark_arc(innerRadius=50).encode(
    theta="Users Count:Q",
    color="Class:N",
    tooltip=["Class", "Users Count"]
).properties(height=400)
st.altair_chart(chart7, use_container_width=True)
