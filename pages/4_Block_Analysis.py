import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: Gas Fee Analysis💨")

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
def load_blocks_stats_filtered(start_date, end_date):
    query = f"""
    SELECT COUNT(DISTINCT fact_blocks_id) AS "Blocks Count",
           ROUND(AVG(tx_count)) AS "Average TX per Block"
    FROM axelar.core.fact_blocks
    WHERE block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    """
    return pd.read_sql(query, conn).iloc[0]

@st.cache_data
def load_blocks_stats_last24h():
    query = """
    SELECT COUNT(DISTINCT fact_blocks_id) AS "Blocks Count",
           AVG(tx_count) AS "Average TX per Block"
    FROM axelar.core.fact_blocks
    WHERE block_timestamp::date >= current_date - 1
    """
    return pd.read_sql(query, conn).iloc[0]


# --- Load Data ----------------------------------------------------------------------------------------
blocks_stats_filtered = load_blocks_stats_filtered(start_date, end_date)
blocks_stats_last24h = load_blocks_stats_last24h()

# --- Row Data ------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Number of Blocks Generated", f"{blocks_stats_filtered['Blocks Count']:,}")
col2.metric("Avg Txn Count per Block", f"{blocks_stats_filtered['Average TX per Block']:.0f}")
col3.metric("Number of Blocks Generated (Last 24h)", f"{blocks_stats_last24h['Blocks Count']:,}")
col4.metric("Avg Txn Count per Block (Last 24h)", f"{blocks_stats_last24h['Average TX per Block']:.2f}")
