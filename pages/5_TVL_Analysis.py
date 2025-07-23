import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- Wide Layout ---
st.set_page_config(layout="wide")

st.title("Axelar Network: TVL Analysis💸")

# --- گرفتن داده‌ها از Dune API ---
@st.cache_data(ttl=3600)  # کش به مدت ۱ ساعت
def load_dune_tvl():
    url = "https://api.dune.com/api/v1/query/5524904/results?api_key=kmCBMTxWKBxn6CVgCXhwDvcFL1fBp6rO"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data["result"]["rows"])
        if "TVL" in df.columns:
            df["TVL"] = pd.to_numeric(df["TVL"], errors="coerce")
            df = df.sort_values("TVL", ascending=False)
        return df
    else:
        st.error(f"Failed to fetch Dune data: {response.status_code}")
        return pd.DataFrame(columns=["Chain", "Token Symbol", "TVL"])

# --- Load Data ---
dune_tvl = load_dune_tvl()

# --- نمایش جدول ---
st.markdown("<h4 style='font-size:18px;'>TVL of Different Chains</h4>", unsafe_allow_html=True)
st.dataframe(dune_tvl.style.format({"TVL": "{:,.0f}"}), use_container_width=True)

# --- نمودار میله‌ای TVL ---
if not dune_tvl.empty:
    fig = px.bar(
        dune_tvl.head(15),  # ۱۵ زنجیره برتر
        x="Chain",
        y="TVL",
        color="Chain",
        title="Top Chains by TVL",
        text_auto=".2s"
    )
    fig.update_layout(xaxis_title="Chain", yaxis_title="TVL", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
