import streamlit as st
import pandas as pd
import altair as alt
from utils import run_query

st.set_page_config(page_title="User Analysis", layout="wide")
st.title("User Analysis")

# --- Filters ---
col1, col2, col3 = st.columns(3)
time_frame = col1.selectbox("Select Time Frame", ["day", "week", "month"])
start_date = col2.date_input("Start Date", pd.to_datetime("2022-01-01"))
end_date = col3.date_input("End Date", pd.to_datetime("today"))

date_trunc_col = f"date_trunc('{time_frame}', block_timestamp)"

# ====================== Row 1: Total Users & Median TXs ======================
query_total_users = f"""
SELECT COUNT(DISTINCT tx_from) AS "Total Users"
FROM axelar.core.fact_transactions
WHERE tx_succeeded = 'true'
  AND block_timestamp::date >= '{start_date}'
  AND block_timestamp::date <= '{end_date}'
"""
total_users = run_query(query_total_users)["Total Users"][0]

query_median_tx = f"""
WITH tab1 AS (
    SELECT tx_from, COUNT(DISTINCT tx_id) AS tx_count
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
)
SELECT ROUND(median(tx_count)) AS "Median TX Count" FROM tab1
"""
median_tx = run_query(query_median_tx)["Median TX Count"][0]

col1, col2 = st.columns(2)
col1.metric("Total number of Axelar network users", f"{total_users:,}")
col2.metric("Median Number of User Transactions", f"{median_tx:,}")

# ====================== Row 2 & 3: User Growth % ======================
query_user_growth = """
WITH tab1 AS (
    SELECT COUNT(DISTINCT tx_from) AS User1d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date - 1
),
tab2 AS (
    SELECT COUNT(DISTINCT tx_from) AS User2d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date - 2
),
tab3 AS (
    SELECT COUNT(DISTINCT tx_from) AS User7d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date - 8
),
tab4 AS (
    SELECT COUNT(DISTINCT tx_from) AS User30d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date - 31
),
tab5 AS (
    SELECT COUNT(DISTINCT tx_from) AS User365d
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true' AND block_timestamp::date = current_date - 366
)
SELECT 
    ROUND(((User1d-User2d)/NULLIF(User2d,0))*100,2) AS "User Change (1D)",
    ROUND(((User1d-User7d)/NULLIF(User7d,0))*100,2) AS "User Change (7D)",
    ROUND(((User1d-User30d)/NULLIF(User30d,0))*100,2) AS "User Change (30D)",
    ROUND(((User1d-User365d)/NULLIF(User365d,0))*100,2) AS "User Change (1Y)"
FROM tab1, tab2, tab3, tab4, tab5
"""
user_growth = run_query(query_user_growth).iloc[0]

def display_growth_metric(col, label, value):
    delta_color = "normal"
    arrow = "▲" if value > 0 else "▼"
    delta_color = "green" if value > 0 else "red"
    col.metric(label, f"{value}%", delta=f"{arrow} {value}%", delta_color=delta_color)

col1, col2 = st.columns(2)
display_growth_metric(col1, "User Growth Percentage: 1D", user_growth["User Change (1D)"])
display_growth_metric(col2, "User Growth Percentage: 7D", user_growth["User Change (7D)"])

col1, col2 = st.columns(2)
display_growth_metric(col1, "User Growth Percentage: 30D", user_growth["User Change (30D)"])
display_growth_metric(col2, "User Growth Percentage: 1Y", user_growth["User Change (1Y)"])

# ====================== Row 4: Axelar Users Over Time ======================
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
SELECT tab1."Date", 
       "Total Users", 
       COALESCE("New Users",0) AS "New Users", 
       "Total Users" - COALESCE("New Users",0) AS "Active Users"
FROM tab1
LEFT JOIN tab2 ON tab1."Date" = tab2."Date"
ORDER BY tab1."Date"
"""
df_users_over_time = run_query(query_users_over_time)
st.markdown("#### Axelar Users Over Time")

df_stacked = df_users_over_time.melt(
    id_vars=["Date", "Total Users"], 
    value_vars=["New Users", "Active Users"], 
    var_name="User Type", 
    value_name="Count"
)

bars = alt.Chart(df_stacked).mark_bar().encode(
    x=alt.X("Date:T", title="Date"),
    y=alt.Y("Count:Q", title="Number of Users"),
    color=alt.Color("User Type:N", scale=alt.Scale(scheme="category10"))
)

line = alt.Chart(df_users_over_time).mark_line(color="black", strokeWidth=2).encode(
    x="Date:T",
    y="Total Users:Q",
    tooltip=["Date:T", "Total Users:Q"]
)

chart4 = alt.layer(bars, line).resolve_scale(y='shared').properties(height=400)
st.altair_chart(chart4, use_container_width=True)

# ====================== Row 5: Growth & Distribution ======================
query_growth_users = f"""
WITH tab10 AS (
    SELECT tx_from, MIN(block_timestamp::date) AS first_tx
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
    GROUP BY 1
)
SELECT {date_trunc_col} AS "Date",
       COUNT(DISTINCT tx_from) AS "New Users",
       SUM(COUNT(DISTINCT tx_from)) OVER (ORDER BY {date_trunc_col}) AS "Total Users"
FROM tab10
WHERE first_tx::date >= '{start_date}' AND first_tx::date <= '{end_date}'
GROUP BY 1 ORDER BY 1
"""
df_growth_users = run_query(query_growth_users)
st.markdown("##### Growth of Axelar Network Users Over Time")
chart5 = alt.Chart(df_growth_users).mark_bar().encode(
    x="Date:T",
    y="Total Users:Q",
    tooltip=["Date:T", "Total Users:Q"]
).properties(height=400)
st.altair_chart(chart5, use_container_width=True)

query_dist_txs = f"""
WITH tab1 AS (
    SELECT tx_from, COUNT(DISTINCT tx_id) AS tx_count
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
)
SELECT tx_count AS "TXs Count", COUNT(DISTINCT tx_from) AS "Users Count"
FROM tab1 GROUP BY 1 ORDER BY 1
"""
df_dist_txs = run_query(query_dist_txs)
st.markdown("##### Distribution of Users Based on the TXs Count")
chart6 = alt.Chart(df_dist_txs).mark_bar().encode(
    x="TXs Count:Q",
    y="Users Count:Q",
    tooltip=["TXs Count:Q", "Users Count:Q"]
).properties(height=400)
st.altair_chart(chart6, use_container_width=True)

# ====================== Row 6: Pie chart ======================
query_days_activity = f"""
WITH tab1 AS (
    SELECT tx_from, COUNT(DISTINCT block_timestamp::date) AS active_days,
           CASE
               WHEN COUNT(DISTINCT block_timestamp::date) = 1 THEN 'n=1'
               WHEN COUNT(DISTINCT block_timestamp::date) > 1 AND COUNT(DISTINCT block_timestamp::date) <= 7 THEN '1<n<=7'
               WHEN COUNT(DISTINCT block_timestamp::date) > 7 AND COUNT(DISTINCT block_timestamp::date) <= 30 THEN '7<n<=30'
               ELSE 'n>30'
           END AS "Class"
    FROM axelar.core.fact_transactions
    WHERE block_timestamp::date >= '{start_date}' AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
)
SELECT "Class", COUNT(DISTINCT tx_from) AS "Users Count"
FROM tab1 GROUP BY 1
"""
df_days_activity = run_query(query_days_activity)
st.markdown("##### Distribution of Users Based on the Number of Days of Activity")
pie = alt.Chart(df_days_activity).mark_arc().encode(
    theta="Users Count:Q",
    color="Class:N",
    tooltip=["Class:N", "Users Count:Q"]
).properties(height=400)
st.altair_chart(pie, use_container_width=True)
