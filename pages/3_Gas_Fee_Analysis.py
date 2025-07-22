import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: Gas Fee Analysis")

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

# --- Query Functions ---------------------------------------------------------------------------------------
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


# --- Load Data ----------------------------------------------------------------------------------------
total_users = load_total_users(start_date, end_date)
median_user_tx = load_median_user_tx(start_date, end_date)


# --- Row Data ------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
col1, col2 = st.columns(2)
col1.metric("Total number of Axelar network users", f"{total_users:,}")
col2.metric("Median Number of User Transactions", f"{median_user_tx}")

# --- Helper function to show growth with correct delta_color ---
def display_growth_metric(label, value):
    if value > 0:
        st.metric(label=label, value=f"{value}%", delta=f"▲ {value}%", delta_color="normal")
    elif value < 0:
        st.metric(label=label, value=f"{value}%", delta=f"▼ {abs(value)}%", delta_color="inverse")
    else:
        st.metric(label=label, value=f"{value}%", delta="0%", delta_color="off")

# --- Row 2: User Growth Percentage (1D, 7D) ---
col3, col4 = st.columns(2)
with col3:
    display_growth_metric("User Growth Percentage: 1D", user_growth["User Change (1D)"])
with col4:
    display_growth_metric("User Growth Percentage: 7D", user_growth["User Change (7D)"])


