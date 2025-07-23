import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: Block Analysis🧱")

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
           round(AVG(tx_count)) AS "Average TX per Block"
    FROM axelar.core.fact_blocks
    WHERE block_timestamp::date >= current_date - 1
    """
    return pd.read_sql(query, conn).iloc[0]

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
    LIMIT 5
    """
    return pd.read_sql(query, conn)


# --- Load Data ----------------------------------------------------------------------------------------
blocks_stats_filtered = load_blocks_stats_filtered(start_date, end_date)
blocks_stats_last24h = load_blocks_stats_last24h()
blocks_over_time = load_blocks_over_time(start_date, end_date, timeframe)
block_distribution = load_block_distribution(start_date, end_date)
top_blocks = load_top_blocks(start_date, end_date)

# --- Row Data ------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Number of Blocks Generated", f"{blocks_stats_filtered['Blocks Count']:,}")
col2.metric("Avg Txn Count per Block", f"{blocks_stats_filtered['Average TX per Block']:.0f}")
col3.metric("Number of Blocks Generated (Last 24h)", f"{blocks_stats_last24h['Blocks Count']:,}")
col4.metric("Avg Txn Count per Block (Last 24h)", f"{blocks_stats_last24h['Average TX per Block']:.2f}")

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

# --- Row 3 ---
col1, col2 = st.columns([1, 1])

# --- Left: Table for Top 5 Blocks ---
with col1:
    st.markdown("### 🧱 5 Blocks Created with the Highest Number of Transactions")
    st.dataframe(
        top_blocks.style.set_table_styles(
            [{'selector': 'thead th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]}]
        ).background_gradient(cmap='Blues', subset=["# of Transactions"])
    )

# --- Right: Pie Chart for Block Distribution ---
fig_pie = px.pie(
    block_distribution,
    names="Class",
    values="Block Count",
    title="Distribution of Blocks Based on the TXs Count",
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Set3
)
col2.plotly_chart(fig_pie, use_container_width=True)
