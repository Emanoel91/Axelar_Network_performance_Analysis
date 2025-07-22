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

# --- New Query 9: Distribution of Users by Fee Paid ---
@st.cache_data
def load_distribution_fee_paid(start_date, end_date):
    
    query = f"""
    with tab1 as (select tx_from, sum(fee)/pow(10,6), case 
when (sum(fee)/pow(10,6))<=0.01 then 'V<=0.01 AXL'
when (sum(fee)/pow(10,6))>0.01 and (sum(fee)/pow(10,6))<0.1 then '0.01<V<=0.1 AXL'
when (sum(fee)/pow(10,6))>0.1 and (sum(fee)/pow(10,6))<1 then '0.1<V<=1 AXL'
when (sum(fee)/pow(10,6))>1 and (sum(fee)/pow(10,6))<10 then '1<V<=10 AXL'
when (sum(fee)/pow(10,6))>10 and (sum(fee)/pow(10,6))<100 then '10<V<=100 AXL'
when (sum(fee)/pow(10,6))>100 and (sum(fee)/pow(10,6))<1000 then '100<V<=1k AXL'
else 'V>1k AXL' end as "Class"
from axelar.core.fact_transactions
where block_timestamp::date>={start_date} and block_timestamp::date<={end_date}
group by 1)

select "Class", count(distinct tx_from) as "Users Count"
from tab1
group by 1
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

# --- Row 3: User Growth Percentage (30D, 1Y) ---
col5, col6 = st.columns(2)
with col5:
    display_growth_metric("User Growth Percentage: 30D", user_growth["User Change (30D)"])
with col6:
    display_growth_metric("User Growth Percentage: 1Y", user_growth["User Change (1Y)"])

# --- Row 4: Axelar Users Over Time (Stacked Bar + Line) ---
st.markdown("---")
st.markdown("<h4 style='font-size:16px;'>Axelar Users Over Time</h4>", unsafe_allow_html=True)

fig1 = go.Figure()
fig1.add_trace(go.Bar(
    x=users_over_time_df['Date'],
    y=users_over_time_df['New Users'],
    name='New Users',
    marker_color='rgb(26, 118, 255)'
))
fig1.add_trace(go.Bar(
    x=users_over_time_df['Date'],
    y=users_over_time_df['Active Users'],
    name='Active Users',
    marker_color='rgb(55, 83, 109)'
))
fig1.add_trace(go.Scatter(
    x=users_over_time_df['Date'],
    y=users_over_time_df['Total Users'],
    name='Total Users',
    mode='lines+markers',
    line=dict(color='rgb(255, 0, 0)', width=2)
))

fig1.update_layout(
    barmode='stack',
    xaxis=dict(title='Date'),
    yaxis=dict(title='Number of Users'),
    legend=dict(x=0, y=1.2, orientation='h')
)

st.plotly_chart(fig1, use_container_width=True)

# --- Row 5: Two charts side by side ---
col7, col8 = st.columns(2)

with col7:
    st.markdown("<h4 style='font-size:16px;'>Growth of Axelar Network Users Over Time</h4>", unsafe_allow_html=True)
    fig2 = px.bar(
        growth_over_time_df, 
        x='Date', 
        y='Total Users', 
        labels={'Date': 'Date', 'Total Users': 'Total Users'}
    )
    st.plotly_chart(fig2, use_container_width=True)

with col8:
    st.markdown("<h4 style='font-size:16px;'>Distribution of Users Based on the TXs Count</h4>", unsafe_allow_html=True)
    fig3 = px.pie(
        distribution_txs_df,
        names='TXs Count',
        values='Users Count',
        color='TXs Count',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig3.update_layout(legend_title_font=dict(size=12), legend_font=dict(size=10))
    st.plotly_chart(fig3, use_container_width=True)

# --- Row 6: Pie Chart (Days Activity) ---
st.markdown("---")
st.markdown("<h4 style='font-size:16px;'>Distribution of Users Based on the Number of Days of Activity</h4>", unsafe_allow_html=True)

fig4 = px.pie(
    distribution_days_df,
    names='Class',
    values='Users Count',
    color='Class',
    color_discrete_map={
        'n=1': 'lightblue',
        '1<n<=7': 'orange',
        '7<n<=30': 'green',
        'n>30': 'purple'
    }
)
st.plotly_chart(fig4, use_container_width=True)

# --- Row 7: Pie Chart (Fee Paid) ---
st.markdown("---")
st.markdown("<h4 style='font-size:16px;'>Distribution of Users Based on Total Fees Paid</h4>", unsafe_allow_html=True)

if not distribution_fee_df.empty:
    fig5 = px.pie(
        distribution_fee_df,
        names='Class',
        values='Users Count',
        color='Class',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No data available for fee distribution in the selected period.")
