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

@st.cache_data
def load_monthly_fees(start_date, end_date, timeframe):
    date_col = truncate_date("block_timestamp", timeframe)
    query = f"""
        SELECT 
            {date_col} AS "Date",
            SUM(fee)/pow(10,6) AS "Fee Amount",
            AVG(fee)/pow(10,6) AS "Average Fee per TX",
            MEDIAN(fee)/pow(10,6) AS "Median Fee per TX",
            MAX(fee)/pow(10,6) AS "Max Fee",
            SUM(SUM(fee)/pow(10,6)) OVER (ORDER BY {date_col} ASC) AS "Total Fee"
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
          AND fee_denom = 'uaxl'
          AND tx_succeeded = 'true'
        GROUP BY 1
        ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_current_gas_usage():
    query = """
        SELECT 
            ROUND(AVG(gas_used)) AS "Current Gas Used",
            ROUND(AVG(gas_wanted)) AS "Current Gas Wanted"
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date = CURRENT_DATE - 1
          AND fee_denom = 'uaxl'
          AND tx_succeeded = 'true'
    """
    return pd.read_sql(query, conn).iloc[0]

@st.cache_data
def load_average_gas_usage(start_date, end_date):
    query = f"""
        SELECT 
            AVG(gas_used) AS "Average Gas Used",
            AVG(gas_wanted) AS "Average Gas Wanted"
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
          AND fee_denom = 'uaxl'
          AND tx_succeeded = 'true'
    """
    return pd.read_sql(query, conn).iloc[0]
    
# --- Load Data ----------------------------------------------------------------------------------------
current_gas = load_current_gas_usage()
average_gas = load_average_gas_usage(start_date, end_date)
fee_metrics = load_fee_metrics(start_date, end_date)
monthly_fees = load_monthly_fees(start_date, end_date, timeframe)

# --- Row Data ------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Fees Paid on the Axelar Network", f"{fee_metrics['Fee Amount']:,} AXL")
col2.metric("Average Fee Paid per Transaction", f"{fee_metrics['Average Fee per TX']} AXL")
col3.metric("Median Transaction Fees", f"{fee_metrics['Median Fee per TX']} AXL")
col4.metric("Maximum Fee Paid in One Transaction", f"{fee_metrics['Max Fee']} AXL")

# --- Row 2: Charts ---
col1, col2 = st.columns(2)

# Chart 1: Column (Fee Amount) + Line (Total Fee)
fig1 = go.Figure()
fig1.add_bar(x=monthly_fees["Date"], y=monthly_fees["Fee Amount"], name="Fee Amount (AXL)", yaxis="y1")
fig1.add_trace(go.Scatter(x=monthly_fees["Date"], y=monthly_fees["Total Fee"], name="Total Fee (AXL)", yaxis="y2", mode='lines', line=dict(color='red')))

fig1.update_layout(
    title="Total Transaction Fees Paid Over Time",
    xaxis=dict(title="Date"),
    yaxis=dict(title="AXL", side="left"),
    yaxis2=dict(title="AXL", overlaying="y", side="right"),
    legend=dict(x=0.1, y=1.1, orientation="h")
)
col1.plotly_chart(fig1, use_container_width=True)

# Chart 2: Line Chart (Average vs Median Fee per TX)
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=monthly_fees["Date"], y=monthly_fees["Average Fee per TX"], mode='lines', name="Average Fee per TX (AXL)", yaxis="y1"))
fig2.add_trace(go.Scatter(x=monthly_fees["Date"], y=monthly_fees["Median Fee per TX"], mode='lines', name="Median Fee per TX (AXL)", yaxis="y2"))

fig2.update_layout(
    title="Average & Median Transaction Fees Over Time",
    xaxis=dict(title="Date"),
    yaxis=dict(title="AXL", side="left"),
    yaxis2=dict(title="AXL", overlaying="y", side="right"),
    legend=dict(x=0.1, y=1.1, orientation="h")
)
col2.plotly_chart(fig2, use_container_width=True)

# --- Row 3: Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Gas Used (Current Date)", f"{current_gas['Current Gas Used']:,}")
col2.metric("Current Gas Wanted (Current Date)", f"{current_gas['Current Gas Wanted']:,}")
col3.metric("Average Gas Used (Selected Period)", f"{average_gas['Average Gas Used']:.2f}")
col4.metric("Average Gas Wanted (Selected Period)", f"{average_gas['Average Gas Wanted']:.2f}")
