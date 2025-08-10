import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Network Performance Analysis",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: Transaction Analysis⛓")

st.info(
    "📊Charts initially display data for a default time range. Select a custom range to view results for your desired period."

)

st.info(
    "⏳On-chain data retrieval may take a few moments. Please wait while the results load."
)

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
timeframe = st.selectbox("Select Time Frame", ["month", "week", "day"])
start_date = st.date_input("Start Date", value=pd.to_datetime("2025-01-01"))
end_date = st.date_input("End Date", value=pd.to_datetime("2025-07-31"))

# --- Query Functions ---
@st.cache_data
def load_main_data(timeframe, start_date, end_date):
    query = f"""
    SELECT date_trunc('{timeframe}', block_timestamp) AS "Date",
           COUNT(DISTINCT tx_id) AS "TXs Count",
           tx_succeeded AS "TX Success"
    FROM AXELAR.CORE.FACT_TRANSACTIONS
    WHERE block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1, 3
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_success_rate(start_date, end_date):
    query = f"""
    WITH TAB1 AS (
        SELECT COUNT(DISTINCT tx_id) AS "Succeeded TXs Count"
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
          AND tx_succeeded = 'TRUE'
    ),
    TAB2 AS (
        SELECT COUNT(DISTINCT tx_id) AS "Total TXs Count"
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
    )
    SELECT ROUND((("Succeeded TXs Count"/"Total TXs Count")*100),2) AS "Success Rate"
    FROM TAB1, TAB2
    """
    return pd.read_sql(query, conn).iloc[0, 0]

@st.cache_data
def load_total_txs(start_date, end_date):
    query = f"""
    SELECT COUNT(DISTINCT tx_id) AS "TXs Count"
    FROM axelar.core.fact_transactions
    WHERE block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    """
    return pd.read_sql(query, conn).iloc[0, 0]

@st.cache_data
def load_tps_data(timeframe, start_date, end_date):
    query = f"""
    WITH tab1 AS (
        SELECT block_timestamp::date AS date,
               COUNT(DISTINCT tx_id)/86400 AS TPS
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true'
          AND block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1
    )
    SELECT date_trunc('{timeframe}', date) AS "Date",
           ROUND(AVG(tps), 2) AS TPS
    FROM tab1
    GROUP BY 1
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_correlation_data(start_date, end_date):
    query = f"""
    WITH tab1 AS (
        SELECT block_timestamp::date AS date,
               COUNT(DISTINCT tx_id) AS total_tx_count
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1
    ),
    tab2 AS (
        SELECT block_timestamp::date AS date,
               COUNT(DISTINCT tx_id) AS false_tx_count
        FROM axelar.core.fact_transactions
        WHERE block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
          AND tx_succeeded = 'false'
        GROUP BY 1
    )
    SELECT ROUND(CORR(total_tx_count, false_tx_count), 2) AS cc
    FROM tab1 LEFT JOIN tab2 ON tab1.date = tab2.date
    """
    return pd.read_sql(query, conn).iloc[0, 0]

@st.cache_data
def load_hour_day_data(start_date, end_date):
    query = f"""
    SELECT DATE_PART('hour', block_timestamp) AS "Hour",
           CASE WHEN DAYOFWEEK(block_timestamp)=0 THEN 7 
                ELSE DAYOFWEEK(block_timestamp) END || ' - ' || DAYNAME(block_timestamp) AS "Day Name",
           COUNT(DISTINCT tx_id) AS "TXs Count"
    FROM axelar.core.fact_transactions
    WHERE block_timestamp::date >= '{start_date}'
      AND block_timestamp::date <= '{end_date}'
    GROUP BY 1, 2
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

# --- Load Data ---
df = load_main_data(timeframe, start_date, end_date)
success_rate = load_success_rate(start_date, end_date)
total_txs = load_total_txs(start_date, end_date)
tps_df = load_tps_data(timeframe, start_date, end_date)
correlation = load_correlation_data(start_date, end_date)
df_hour_day = load_hour_day_data(start_date, end_date)

# --- Row 1: Metrics ---
col1, col2 = st.columns(2)
col1.metric("Current Success Rate of Transactions", f"{success_rate}%")
col2.metric("Total Transactions Count", f"{total_txs:,}")

# --- Row 2: Bar Chart ---
fig_bar = px.bar(df, x="Date", y="TXs Count", color="TX Success",
                 title="Number of Transactions Based on Success Over Time")
st.plotly_chart(fig_bar)

# --- Row 3: Normalized Bar + Pie Chart ---
col3, col4 = st.columns(2)
df_percent = df.copy()
monthly_total = df_percent.groupby("Date")["TXs Count"].transform("sum")
df_percent["Percentage"] = df_percent["TXs Count"] / monthly_total * 100
fig_normalized = px.bar(df_percent, x="Date", y="Percentage", color="TX Success",
                        title="Normalized Transactions by Success (%)", barmode="stack")
col3.plotly_chart(fig_normalized)

summary = df.groupby("TX Success")["TXs Count"].sum().reset_index()
fig_pie = px.pie(summary, names="TX Success", values="TXs Count",
                 title="Success vs Failed Transactions (Total)")
col4.plotly_chart(fig_pie)

# --- Row 4: Scatter Plot for TPS ---
fig_tps = px.scatter(tps_df, x="Date", y="TPS", size="TPS",
                     color="TPS", color_continuous_scale="Viridis",
                     title="Transaction per Second (TPS) Over Time",
                     labels={"TPS": "Transactions Per Second"})
st.plotly_chart(fig_tps)

# --- Row 5: Correlation Coefficient ---
st.metric("Effect of Increasing the Number of Transactions on the Number of Failed Transactions",
          f"{correlation:.2f}")

# --- Row 6: Heatmap ---
heatmap_data = df_hour_day.pivot_table(index="Day Name", columns="Hour", values="TXs Count", fill_value=0)
fig_heatmap = px.imshow(heatmap_data, aspect="auto",
                        title="Time Pattern of Axelar Network Transactions",
                        labels=dict(x="Hour", y="Day Name", color="TXs Count"))
st.plotly_chart(fig_heatmap)

# --- Row 7: Two Bar Charts (Hours & Days) ---
col5, col6 = st.columns(2)
hourly_summary = df_hour_day.groupby("Hour")["TXs Count"].sum().reset_index()
fig_hourly = px.bar(hourly_summary, x="Hour", y="TXs Count",
                    title="Total Number of Transactions on Different Hours of the Day")
col5.plotly_chart(fig_hourly)

daily_summary = df_hour_day.groupby("Day Name")["TXs Count"].sum().reset_index()
fig_daily = px.bar(daily_summary, x="Day Name", y="TXs Count",
                   title="Total Number of Transactions on Different Days of the Week")
col6.plotly_chart(fig_daily)

# --- Row 8: Peak Activity ---
peak = df_hour_day.loc[df_hour_day["TXs Count"].idxmax()]
peak_hour = int(peak["Hour"])
peak_day = peak["Day Name"]
peak_count = int(peak["TXs Count"])

st.metric("Peak Activity Period", f"{peak_day}, Hour {peak_hour}", delta=f"{peak_count:,} TXs")
