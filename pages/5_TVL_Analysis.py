import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go
import requests  # ← Added for D.API

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: TVL Analysis💸")

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

# --- getting D.API Data -------------------------
@st.cache_data
def load_dune_tvl():
    url = "https://api.dune.com/api/v1/query/5524904/results?api_key=kmCBMTxWKBxn6CVgCXhwDvcFL1fBp6rO"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        rows = data["result"]["rows"]  # گرفتن دیتا
        return pd.DataFrame(rows)
    else:
        st.error(f"Failed to fetch Dune data: {response.status_code}")
        return pd.DataFrame(columns=["Chain", "Token Symbol", "TVL"])

# --- Load Data ----------------------------------------------------------------------------------------
dune_tvl = load_dune_tvl()  # ← D.Data ---------------------------------

# --- Row Data ------------------------------------------------------------------------------------------

# --- Row 1: D.Table ----------------
st.markdown("<h4 style='font-size:18px;'>TVL of Different Chains</h4>", unsafe_allow_html=True)
st.dataframe(dune_tvl, use_container_width=True)
