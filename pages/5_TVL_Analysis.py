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

if not dune_tvl.empty:
    # --- فیلتر جستجوی زنجیره ---
    chain_list = dune_tvl["Chain"].dropna().unique().tolist()
    default_index = chain_list.index("Axelar") if "Axelar" in chain_list else 0
    selected_chain = st.selectbox("🔎 جستجوی زنجیره", chain_list, index=default_index)

    # --- TVL زنجیره انتخابی ---
    selected_tvl = dune_tvl.loc[dune_tvl["Chain"] == selected_chain, "TVL"].sum()
    st.metric(label=f"TVL of {selected_chain}", value=f"${selected_tvl:,.0f}")

    # --- جدول ---
    st.markdown("<h4 style='font-size:18px;'>TVL of Different Chains</h4>", unsafe_allow_html=True)
    st.dataframe(dune_tvl.style.format({"TVL": "{:,.0f}"}), use_container
