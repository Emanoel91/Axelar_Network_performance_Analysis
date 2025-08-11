import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Network Performance Analysis",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: Block Analysis🧱")

st.info("📊Charts initially display data for a default time range. Select a custom range to view results for your desired period.")
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Sidebar Footer Slightly Left-Aligned ------------------------------------------------------------------------------------------------------------------
st.sidebar.markdown(
    """
    <style>
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        width: 250px;
        font-size: 13px;
        color: gray;
        margin-left: 5px; # -- MOVE LEFT
        text-align: left;  
    }
    .sidebar-footer img {
        width: 16px;
        height: 16px;
        vertical-align: middle;
        border-radius: 50%;
        margin-right: 5px;
    }
    .sidebar-footer a {
        color: gray;
        text-decoration: none;
    }
    </style>

    <div class="sidebar-footer">
        <div>
            <a href="https://x.com/axelar" target="_blank">
                <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar Logo">
                Powered by Axelar
            </a>
        </div>
        <div style="margin-top: 5px;">
            <a href="https://x.com/0xeman_raz" target="_blank">
                <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" alt="Eman Raz">
                Built by Eman Raz
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Snowflake Connection -----------------------------------------------------------------------------------------------------------------------------
conn = snowflake.connector.connect(
    user=st.secrets["snowflake"]["user"],
    password=st.secrets["snowflake"]["password"],
    account=st.secrets["snowflake"]["account"],
    warehouse="SNOWFLAKE_LEARNING_WH",
    database="AXELAR",
    schema="PUBLIC"
)

# --- Time Frame & Period Selection ---
timeframe = st.selectbox("Select Time Frame", ["month", "week", "day"])
start_date = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
end_date = st.date_input("End Date", value=pd.to_datetime("2025-07-31"))

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

# --- Row (1) ---------------------------------------------------------------------------------------------------------------------
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

blocks_stats_filtered = load_blocks_stats_filtered(start_date, end_date)

@st.cache_data
def load_blocks_stats_last24h():
    query = """
    SELECT COUNT(DISTINCT fact_blocks_id) AS "Blocks Count",
           round(AVG(tx_count)) AS "Average TX per Block"
    FROM axelar.core.fact_blocks
    WHERE block_timestamp::date >= current_date - 1
    """
    return pd.read_sql(query, conn).iloc[0]

blocks_stats_last24h = load_blocks_stats_last24h()

# --- Row 1: Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Number of Blocks Generated", f"{blocks_stats_filtered['Blocks Count']:,}")
col2.metric("Avg Txn Count per Block", f"{blocks_stats_filtered['Average TX per Block']:.0f}")
col3.metric("Number of Blocks Generated (Last 24h)", f"{blocks_stats_last24h['Blocks Count']:,}")
col4.metric("Avg Txn Count per Block (Last 24h)", f"{blocks_stats_last24h['Average TX per Block']:.2f}")

# --- Row (2) ---------------------------------------------------------------------------------------------------------------------

@st.cache_data
def load_blocks_over_time(start_date, end_date, timeframe):
    date_col = truncate_date("block_timestamp", timeframe)
    query = f"""
    SELECT {date_col} AS "Date",
           COUNT(DISTINCT fact_blocks_id) AS "Blocks Count",
           ROUND(AVG(tx_count)) AS "Average TX per Block",
           COUNT(DISTINCT validator_hash) AS "Validator Count",
           SUM(COUNT(DISTINCT fact_blocks_id)) OVER (ORDER BY {date_col} ASC) AS "Total Blocks Count"
    FROM axelar.core.fact_blocks
    WHERE block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

blocks_over_time = load_blocks_over_time(start_date, end_date, timeframe)

# --- Row 2 ---
col1, col2 = st.columns(2)

# --- Chart 1: Generated Blocks Over Time (bar + line) ---
fig_blocks = go.Figure()
fig_blocks.add_bar(
    x=blocks_over_time["Date"],
    y=blocks_over_time["Blocks Count"],
    name="Blocks Count",
    yaxis="y1"
)
fig_blocks.add_trace(go.Scatter(
    x=blocks_over_time["Date"],
    y=blocks_over_time["Total Blocks Count"],
    name="Total Blocks Count",
    yaxis="y2",
    mode="lines+markers"
))
fig_blocks.update_layout(
    title="Generated Blocks Over Time",
    xaxis=dict(title=" "),
    yaxis=dict(title="Blocks Count", side="left"),
    yaxis2=dict(title="Total Blocks Count", overlaying="y", side="right"),
    barmode="group"
)
col1.plotly_chart(fig_blocks, use_container_width=True)

# --- Chart 2: Average Transaction per Block (line) ---
fig_avg_tx = go.Figure()
fig_avg_tx.add_trace(go.Scatter(
    x=blocks_over_time["Date"],
    y=blocks_over_time["Average TX per Block"],
    mode="lines+markers",
    name="Average TX per Block"
))
fig_avg_tx.update_layout(
    title="Average Transaction per Block Over Time",
    xaxis=dict(title=" "),
    yaxis=dict(title="Txn count")
)
col2.plotly_chart(fig_avg_tx, use_container_width=True)

# --- Row (3) ---------------------------------------------------------------------------------------------------------------------
@st.cache_data
def load_block_distribution(start_date, end_date):
    query = f"""
    WITH tab1 AS (
        SELECT block_id,
               CASE 
                   WHEN tx_count <= 5 THEN 'n<=5 TXs'
                   WHEN tx_count > 5 AND tx_count <= 10 THEN '5<n<=10 TXs'
                   WHEN tx_count > 10 AND tx_count <= 20 THEN '10<n<=20 TXs'
                   WHEN tx_count > 20 AND tx_count <= 50 THEN '20<n<=50 TXs'
                   WHEN tx_count > 50 AND tx_count <= 100 THEN '50<n<=100 TXs'
                   ELSE 'n>100 TXs'
               END AS "Class"
        FROM axelar.core.fact_blocks
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
    )
    SELECT "Class", COUNT(DISTINCT block_id) AS "Block Count"
    FROM tab1
    GROUP BY 1
    """
    return pd.read_sql(query, conn)

block_distribution = load_block_distribution(start_date, end_date)

@st.cache_data
def load_top_blocks(start_date, end_date):
    query = f"""
    SELECT block_id AS "Block Number",
           fact_blocks_id AS "Block ID",
           tx_count AS "# of Transactions",
           block_timestamp::date AS "Block Creation Date"
    FROM axelar.core.fact_blocks
    WHERE block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    ORDER BY 3 DESC
    LIMIT 10
    """
    return pd.read_sql(query, conn)

top_blocks = load_top_blocks(start_date, end_date)

# --- Row 3 ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("<h4 style='font-size:18px;'>🧱 10 Blocks with the Highest Number of Transactions</h4>", unsafe_allow_html=True)
    st.dataframe(top_blocks, use_container_width=True)

with col2:
    fig_pie = px.pie(block_distribution,
                     values='Block Count',
                     names='Class',
                     title='Distribution of Blocks Based on the TXs Count')
    st.plotly_chart(fig_pie, use_container_width=True)
