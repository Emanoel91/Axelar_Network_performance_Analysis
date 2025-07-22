import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: User Analysis")

# --- Snowflake Connection ---
conn = snowflake.connector.connect(
    user=st.secrets["snowflake"]["user"],
    password=st.secrets["snowflake"]["password"],
    account=st.secrets["snowflake"]["account"],
    warehouse="SNOWFLAKE_LEARNING_WH",
    database="AXELAR",
    schema="PUBLIC"
)

# --- Time Frame & Period Selection ---
timeframe = st.selectbox("Select Time Frame", ["day", "week", "month"])
start_date = st.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
end_date = st.date_input("End Date", value=pd.to_datetime("today"))

# --- Helper function for date truncation based on timeframe ---
def truncate_date(date_col, timeframe):
    if timeframe == "day":
        return f"block_timestamp::date"
    elif timeframe == "week":
        return f"date_trunc('week', block_timestamp)"
    elif timeframe == "month":
        return f"date_trunc('month', block_timestamp)"
    else:
        return "block_timestamp::date"

date_col = truncate_date("block_timestamp", timeframe)

# --- Query Functions ---

@st.cache_data
def load_total_users(start_date, end_date):
    query = f"""
    SELECT COUNT(DISTINCT tx_from) AS "Total Users"
    FROM axelar.core.fact_transactions
    WHERE tx_succeeded='true'
      AND block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    """
    return pd.read_sql(query, conn).iloc[0, 0]

@st.cache_data
def load_median_user_tx(start_date, end_date):
    query = f"""
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
    return pd.read_sql(query, conn).iloc[0, 0]

@st.cache_data
def load_user_growth():
    query = """
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
        ROUND((((User1d-User2d)/User2d)*100), 2) AS "User Change (1D)", 
        ROUND((((User1d-User7d)/User7d)*100), 2) AS "User Change (7D)", 
        ROUND((((User1d-User30d)/User30d)*100), 2) AS "User Change (30D)", 
        ROUND((((User1d-User365d)/User365d)*100), 2) AS "User Change (1Y)" 
    FROM tab1, tab2, tab3, tab4, tab5
    """
    return pd.read_sql(query, conn).iloc[0]

@st.cache_data
def load_users_over_time(start_date, end_date, timeframe):
    date_trunc_col = truncate_date("block_timestamp", timeframe)
    query = f"""
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
        GROUP BY 1
    )
    SELECT date_trunc('{timeframe}', first_tx) AS "Date", COUNT(DISTINCT tx_from) AS "New Users"
    FROM tab10
    where first_tx::date >= '{start_date}'
          AND first_tx::date <= '{end_date}'
    GROUP BY 1
)
SELECT tab1."Date" AS "Date", "Total Users", COALESCE("New Users",0) AS "New Users", "Total Users" - COALESCE("New Users",0) AS "Active Users"
FROM tab1
LEFT JOIN tab2 ON tab1."Date" = tab2."Date"
ORDER BY tab1."Date"
"""
    return pd.read_sql(query, conn)

@st.cache_data
def load_growth_over_time(start_date, end_date, timeframe):
    query = f"""
    WITH tab10 AS (
        SELECT tx_from, MIN(block_timestamp::date) AS first_tx
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true'
          AND block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1
    )
    SELECT date_trunc('month', first_tx) AS "Date", COUNT(DISTINCT tx_from) AS "New Users",
           SUM(COUNT(DISTINCT tx_from)) OVER (ORDER BY date_trunc('month', first_tx)) AS "Total Users"
    FROM tab10
    WHERE first_tx::date >= '2022-01-01'
    GROUP BY 1
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_distribution_txs_count(start_date, end_date):
    query = f"""
    WITH tab1 AS (
        SELECT tx_from,
               CASE 
                   WHEN COUNT(DISTINCT tx_id) = 1 THEN 'n=1 Txn'
                   WHEN COUNT(DISTINCT tx_id) > 1 AND COUNT(DISTINCT tx_id) <= 10 THEN '1<n<=10 Txns'
                   WHEN COUNT(DISTINCT tx_id) > 10 AND COUNT(DISTINCT tx_id) <= 100 THEN '10<n<=100 Txns'
                   WHEN COUNT(DISTINCT tx_id) > 100 AND COUNT(DISTINCT tx_id) <= 1000 THEN '100<n<=1k Txns'
                   WHEN COUNT(DISTINCT tx_id) > 1000 AND COUNT(DISTINCT tx_id) <= 10000 THEN '1k<n<=10k Txns'
                   WHEN COUNT(DISTINCT tx_id) > 10000 AND COUNT(DISTINCT tx_id) <= 100000 THEN '10k<n<=100k Txns'
                   WHEN COUNT(DISTINCT tx_id) > 100000 AND COUNT(DISTINCT tx_id) <= 1000000 THEN '100k<n<=1m Txns'
                   WHEN COUNT(DISTINCT tx_id) > 1000000 THEN 'n>1m Txns'
               END AS tx_count
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded = 'true'
          AND block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1
    )
    SELECT tx_count AS "TXs Count", COUNT(DISTINCT tx_from) AS "Users Count"
    FROM tab1
    GROUP BY 1
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_distribution_days_activity(start_date, end_date):
    query = f"""
    WITH tab1 AS (
        SELECT tx_from, COUNT(DISTINCT block_timestamp::date) AS day_count,
            CASE  
                WHEN COUNT(DISTINCT block_timestamp::date) = 1 THEN 'n=1'
                WHEN COUNT(DISTINCT block_timestamp::date) > 1 AND COUNT(DISTINCT block_timestamp::date) <= 7 THEN '1<n<=7'
                WHEN COUNT(DISTINCT block_timestamp::date) > 7 AND COUNT(DISTINCT block_timestamp::date) <= 30 THEN '7<n<=30'
                ELSE 'n>30' 
            END AS "Class"
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
          AND tx_succeeded='true'
        GROUP BY 1
    )
    SELECT "Class", COUNT(DISTINCT tx_from) AS "Users Count"
    FROM tab1
    GROUP BY 1
    ORDER BY "Class"
    """
    return pd.read_sql(query, conn)

# --- کوئری ۸: توزیع کاربران بر اساس مجموع Fee پرداخت شده ---
@st.cache_data
def load_distribution_fee_paid(start_date, end_date):
    query = f"""
    WITH tab1 as (
        SELECT tx_from, SUM(fee)/pow(10,6) as total_fee, 
        CASE  
            WHEN (SUM(fee)/pow(10,6))<=0.01 THEN 'V<=0.01 AXL' 
            WHEN (SUM(fee)/pow(10,6))>0.01 AND (SUM(fee)/pow(10,6))<0.1 THEN '0.01<V<=0.1 AXL' 
            WHEN (SUM(fee)/pow(10,6))>0.1 AND (SUM(fee)/pow(10,6))<1 THEN '0.1<V<=1 AXL' 
            WHEN (SUM(fee)/pow(10,6))>1 AND (SUM(fee)/pow(10,6))<10 THEN '1<V<=10 AXL' 
            WHEN (SUM(fee)/pow(10,6))>10 AND (SUM(fee)/pow(10,6))<100 THEN '10<V<=100 AXL' 
            WHEN (SUM(fee)/pow(10,6))>100 AND (SUM(fee)/pow(10,6))<1000 THEN '100<V<=1k AXL' 
            ELSE 'V>1k AXL' 
        END as "Class" 
        FROM axelar.core.fact_transactions 
        WHERE tx_succeeded='true'
          AND block_timestamp::date >= '{start_date}' 
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1
    )  
    SELECT "Class", COUNT(DISTINCT tx_from) as "Users Count" 
    FROM tab1 
    GROUP BY 1
    ORDER BY "Class"
    """
    return pd.read_sql(query, conn)

# --- کوئری ۹: جدول کاربران برتر ---
@st.cache_data
def load_top_users(start_date, end_date):
    query = f"""
    SELECT tx_from as "👨‍💻User", 
           MIN(block_timestamp::date) as "📅Creation Date",  
           COUNT(DISTINCT tx_id) as "⛓Transactions Count", 
           COUNT(DISTINCT block_timestamp::date) as "📋# of Days of Activity", 
           ROUND((SUM(fee)/pow(10,6)),2) as "💸Total Fee Paid ($AXL)", 
           ROUND(AVG(gas_used),2) as "💨Average Gas Used" 
    FROM axelar.core.fact_transactions 
    WHERE tx_succeeded='true' 
      AND block_timestamp::date >= '{start_date}' 
      AND block_timestamp::date <= '{end_date}'
      AND fee_denom='uaxl' 
    GROUP BY 1 
    ORDER BY 3 DESC  
    LIMIT 1000
    """
    return pd.read_sql(query, conn)

# --- Load Data ---
total_users = load_total_users(start_date, end_date)
median_user_tx = load_median_user_tx(start_date, end_date)
user_growth = load_user_growth()

users_over_time_df = load_users_over_time(start_date, end_date, timeframe)
growth_over_time_df = load_growth_over_time(start_date, end_date, timeframe)
distribution_txs_df = load_distribution_txs_count(start_date, end_date)
distribution_days_df = load_distribution_days_activity(start_date, end_date)
distribution_fee_df = load_distribution_fee_paid(start_date, end_date)
top_users_df = load_top_users(start_date, end_date)

# --- Layout: Summary Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Users", total_users)
col2.metric("Median Number of User Transactions", median_user_tx)
col3.metric("User Growth (1D)", f"{user_growth['User Change (1D)']} %")

# --- Layout: Users Over Time Line Chart ---
fig_users = px.line(users_over_time_df, x="Date", y=["Total Users", "New Users", "Active Users"],
                    title="Users Over Time", labels={"value": "Users", "variable": "Category"})
st.plotly_chart(fig_users, use_container_width=True)

# --- Layout: Growth Over Time Bar Chart ---
fig_growth = px.bar(growth_over_time_df, x="Date", y=["New Users", "Total Users"], barmode='group',
                    title="User Growth Over Time")
st.plotly_chart(fig_growth, use_container_width=True)

# --- Layout: Distribution of Users Based on Number of Transactions ---
fig_dist_tx = px.bar(distribution_txs_df, x="TXs Count", y="Users Count",
                     title="Distribution of Users Based on Number of Transactions")
st.plotly_chart(fig_dist_tx, use_container_width=True)

# --- Layout: Distribution of Users Based on Number of Days of Activity ---
fig_dist_days = px.bar(distribution_days_df, x="Class", y="Users Count",
                       title="Distribution of Users Based on Number of Days of Activity")
col_left, col_right = st.columns(2)
with col_left:
    st.plotly_chart(fig_dist_days, use_container_width=True)

# --- Layout: Distribution of Users Based on Amount of Fee Paid (Pie Chart) ---
fig_fee = px.pie(distribution_fee_df, names="Class", values="Users Count",
                 title="Distribution of Users Based on the Amount of Fee Paid")
with col_right:
    st.plotly_chart(fig_fee, use_container_width=True)

# --- Layout: Top 1000 Users Table ---
st.markdown("### 🔎Axelar Network User Tracking: Top 1000 Users")
st.dataframe(top_users_df, use_container_width=True)
