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
def load_fee_metrics(start_date, end_date):
    query = f"""
    SELECT 
        ROUND(SUM(fee)/pow(10,6)) AS "Fee Amount", 
        ROUND(AVG(fee)/pow(10,6),3) AS "Average Fee per TX",
        ROUND(MEDIAN(fee)/pow(10,6),3) AS "Median Fee per TX", 
        ROUND(MAX(fee)/pow(10,6),3) AS "Max Fee"
    FROM axelar.core.fact_transactions
    WHERE block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
      AND fee_denom='uaxl'
      AND tx_succeeded='true'
    """
    return pd.read_sql(query, conn).iloc[0]


# --- Load Data ----------------------------------------------------------------------------------------
fee_metrics = load_fee_metrics(start_date, end_date)


# --- Row Data ------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Fees Paid on the Axelar Network", f"{fee_metrics['Fee Amount']:,} AXL")
col2.metric("Average Fee Paid per Transaction", f"{fee_metrics['Average Fee per TX']} AXL")
col3.metric("Median Transaction Fees", f"{fee_metrics['Median Fee per TX']} AXL")
col4.metric("Maximum Fee Paid in One Transaction", f"{fee_metrics['Max Fee']} AXL")


