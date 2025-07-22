import streamlit as st
import pandas as pd
import snowflake.connector

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
        GROUP BY tx_from
    )
    SELECT ROUND(MEDIAN(tx_count)) AS "Median Number of User Transactions"
    FROM tab1
    """
    return pd.read_sql(query, conn).iloc[0, 0]

@st.cache_data
def load_user_growth():
    query = f"""
    WITH tab1 AS (
        SELECT COUNT(DISTINCT tx_from) AS User1d
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true' 
          AND block_timestamp::date = CURRENT_DATE - 1
    ),
    tab2 AS (
        SELECT COUNT(DISTINCT tx_from) AS User2d
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true' 
          AND block_timestamp::date = CURRENT_DATE - 2
    ),
    tab3 AS (
        SELECT COUNT(DISTINCT tx_from) AS User7d
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true' 
          AND block_timestamp::date = CURRENT_DATE - 8
    ),
    tab4 AS (
        SELECT COUNT(DISTINCT tx_from) AS User30d
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true' 
          AND block_timestamp::date = CURRENT_DATE - 31
    ),
    tab5 AS (
        SELECT COUNT(DISTINCT tx_from) AS User365d
        FROM axelar.core.fact_transactions
        WHERE tx_succeeded='true' 
          AND block_timestamp::date = CURRENT_DATE - 366
    )
    SELECT  
        ROUND((((User1d - User2d) / NULLIFZERO(User2d)) * 100), 2) AS "User Change (1D)",
        ROUND((((User1d - User7d) / NULLIFZERO(User7d)) * 100), 2) AS "User Change (7D)",
        ROUND((((User1d - User30d) / NULLIFZERO(User30d)) * 100), 2) AS "User Change (30D)",
        ROUND((((User1d - User365d) / NULLIFZERO(User365d)) * 100), 2) AS "User Change (1Y)"
    FROM tab1, tab2, tab3, tab4, tab5
    """
    return pd.read_sql(query, conn).iloc[0]

# Helper function to handle division by zero for Snowflake:
# NULLIFZERO returns NULL if the argument is zero, preventing division by zero error.

# --- Load Data ---
total_users = load_total_users(start_date, end_date)
median_user_tx = load_median_user_tx(start_date, end_date)
user_growth = load_user_growth()

# --- Row 1: Metrics ---
col1, col2 = st.columns(2)
col1.metric("Total number of Axelar network users", f"{total_users:,}")
col2.metric("Median Number of User Transactions", f"{median_user_tx}")

# --- Row 2: User Growth 1D & 7D ---
col3, col4 = st.columns(2)

def colored_metric(label, value):
    if value > 0:
        delta_color = "normal"
        delta = f"▲ {value}%"
        delta_color = "green"
    elif value < 0:
        delta = f"▼ {abs(value)}%"
        delta_color = "red"
    else:
        delta = "0%"
        delta_color = "normal"
    col = st.columns(1)[0]
    # We can use st.metric with delta_color param available in latest Streamlit
    # but if not available, use simple metric with colored delta using markdown
    return col.metric(label, f"{value}%", delta=delta, delta_color=delta_color)

with col3:
    st.metric(
        label="User Growth Percentage: 1D",
        value=f"{user_growth['User Change (1D)']}%",
        delta=f"{user_growth['User Change (1D)']}%",
        delta_color="normal" if user_growth['User Change (1D)'] == 0 else ("inverse" if user_growth['User Change (1D)'] < 0 else "normal")
    )
    # Better color handling below:
    if user_growth["User Change (1D)"] > 0:
        st.metric("User Growth Percentage: 1D", f"{user_growth['User Change (1D)']}%", delta=f"▲ {user_growth['User Change (1D)']}%", delta_color="green")
    elif user_growth["User Change (1D)"] < 0:
        st.metric("User Growth Percentage: 1D", f"{user_growth['User Change (1D)']}%", delta=f"▼ {abs(user_growth['User Change (1D)'])}%", delta_color="red")
    else:
        st.metric("User Growth Percentage: 1D", f"{user_growth['User Change (1D)']}%", delta="0%")

with col4:
    if user_growth["User Change (7D)"] > 0:
        st.metric("User Growth Percentage: 7D", f"{user_growth['User Change (7D)']}%", delta=f"▲ {user_growth['User Change (7D)']}%", delta_color="green")
    elif user_growth["User Change (7D)"] < 0:
        st.metric("User Growth Percentage: 7D", f"{user_growth['User Change (7D)']}%", delta=f"▼ {abs(user_growth['User Change (7D)'])}%", delta_color="red")
    else:
        st.metric("User Growth Percentage: 7D", f"{user_growth['User Change (7D)']}%", delta="0%")

# --- Row 3: User Growth 30D & 1Y ---
col5, col6 = st.columns(2)

with col5:
    if user_growth["User Change (30D)"] > 0:
        st.metric("User Growth Percentage: 30D", f"{user_growth['User Change (30D)']}%", delta=f"▲ {user_growth['User Change (30D)']}%", delta_color="green")
    elif user_growth["User Change (30D)"] < 0:
        st.metric("User Growth Percentage: 30D", f"{user_growth['User Change (30D)']}%", delta=f"▼ {abs(user_growth['User Change (30D)'])}%", delta_color="red")
    else:
        st.metric("User Growth Percentage: 30D", f"{user_growth['User Change (30D)']}%", delta="0%")

with col6:
    if user_growth["User Change (1Y)"] > 0:
        st.metric("User Growth Percentage: 1Y", f"{user_growth['User Change (1Y)']}%", delta=f"▲ {user_growth['User Change (1Y)']}%", delta_color="green")
    elif user_growth["User Change (1Y)"] < 0:
        st.metric("User Growth Percentage: 1Y", f"{user_growth['User Change (1Y)']}%", delta=f"▼ {abs(user_growth['User Change (1Y)'])}%", delta_color="red")
    else:
        st.metric("User Growth Percentage: 1Y", f"{user_growth['User Change (1Y)']}%", delta="0%")
