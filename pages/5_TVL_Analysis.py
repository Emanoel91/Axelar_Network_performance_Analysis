import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Network Performance Analysis",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Wide Layout ---
st.set_page_config(layout="wide")

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

st.title("Axelar Network: TVL Analysis💸")

# --- Getting D.API ---
@st.cache_data(ttl=3600)  # --- cache for 1 hour
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
    # --- chain search filter ---
    chain_list = dune_tvl["Chain"].unique().tolist()
    selected_chain = st.selectbox("🔎 Choose your desired chain", chain_list, index=chain_list.index("Axelar") if "Axelar" in chain_list else 0)

    # --- TVL for selected chain ---
    selected_tvl = dune_tvl.loc[dune_tvl["Chain"] == selected_chain, "TVL"].sum()
    st.metric(label=f"TVL of {selected_chain}", value=f"${selected_tvl:,.0f}")

    # --- table ---
    st.markdown("<h4 style='font-size:18px;'>TVL of Different Chains</h4>", unsafe_allow_html=True)
    st.dataframe(dune_tvl.style.format({"TVL": "{:,.0f}"}), use_container_width=True)

    # --- chart ---
    def human_format(num):
        if num >= 1e9:
            return f"{num/1e9:.1f}B"
        elif num >= 1e6:
            return f"{num/1e6:.1f}M"
        elif num >= 1e3:
            return f"{num/1e3:.1f}K"
        else:
            return str(int(num))

    fig = px.bar(
        dune_tvl.head(15),
        x="Chain",
        y="TVL",
        color="Chain",
        title="Top Chains by TVL ($USD)",
        text=dune_tvl.head(15)["TVL"].apply(human_format)
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Chain", yaxis_title="TVL", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data available.")

# --------------------------------------------------------------------------------------------------------------------------------------------------
st.title("📊 Axelar Token Data (from API)")

# --- Load API Data ---
@st.cache_data(ttl=3600)
def load_axelar_api():
    url = "https://api.axelarscan.io/api/getTVL"  # آدرس واقعی API که اول فرستادی
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch API data: {response.status_code}")
        return None

data = load_axelar_api()

# --- Parse Data ---
if data and "data" in data:
    rows = []
    for asset in data["data"]:
        asset_id = asset.get("asset", "")
        price = asset.get("price", None)
        total = asset.get("total", None)
        value = asset.get("value", None)
        asset_type = asset.get("assetType", "")
        abnormal = asset.get("is_abnormal_supply", False)

        tvl_data = asset.get("tvl", {})
        for chain, details in tvl_data.items():
            rows.append({
                "Asset ID": asset_id,
                "Asset Type": asset_type,
                "Chain": chain,
                "Token Symbol": details.get("contract_data", {}).get("symbol") if "contract_data" in details else None,
                "Token Name": details.get("contract_data", {}).get("name") if "contract_data" in details else None,
                "Contract Address": details.get("contract_data", {}).get("contract_address") if "contract_data" in details else None,
                "Gateway Address": details.get("gateway_address", None),
                "Supply": details.get("supply", None),
                "Total TVL": details.get("total", None),
                "Price (USD)": price,
                "Total Asset Value (USD)": value,
                "Is Abnormal?": abnormal
            })

    df = pd.DataFrame(rows)

    # --- Format Numbers ---
    numeric_cols = ["Supply", "Total TVL", "Price (USD)", "Total Asset Value (USD)"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Display Table ---
    st.dataframe(df.style.format({
        "Supply": "{:,.2f}",
        "Total TVL": "{:,.2f}",
        "Price (USD)": "{:,.4f}",
        "Total Asset Value (USD)": "{:,.2f}"
    }), use_container_width=True)

else:
    st.warning("No data available from API.")
# ----------------------------------------------------------------------------------------------------------------------------------------------
# --- محاسبه TVL کل با حذف Asset ID های تکراری ---
unique_assets = df.drop_duplicates(subset=["Asset ID"])
total_axelar_tvl = unique_assets["Total Asset Value (USD)"].sum()

# --- KPI ---
st.markdown(
    f"""
    <div style="background-color:#1E1E1E; padding:20px; border-radius:15px; text-align:center;">
        <h2 style="color:#00FFAA; font-size:22px; margin-bottom:5px;">Total Axelar TVL</h2>
        <h1 style="color:white; font-size:48px; font-weight:bold;">${total_axelar_tvl:,.0f}</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- آماده‌سازی داده برای Donut اول (Asset Type) ---
asset_type_df = unique_assets.copy()
asset_type_df["Asset Type Label"] = asset_type_df["Asset Type"].apply(
    lambda x: "ITS" if str(x).lower() == "its" else "non-ITS"
)
asset_type_summary = asset_type_df.groupby("Asset Type Label", as_index=False)["Total Asset Value (USD)"].sum()

fig_asset_type = px.pie(
    asset_type_summary,
    values="Total Asset Value (USD)",
    names="Asset Type Label",
    hole=0.5,
    color="Asset Type Label",
    color_discrete_map={"ITS": "#00FFAA", "non-ITS": "#FF4B4B"},
    title="Share of TVL by Asset Type"
)
fig_asset_type.update_traces(textposition="inside", textinfo="percent+label")
fig_asset_type.update_layout(showlegend=True)

# --- آماده‌سازی داده برای Donut دوم (Chain) ---
chain_summary = df.groupby("Chain", as_index=False)["Total Asset Value (USD)"].sum()

fig_chain = px.pie(
    chain_summary,
    values="Total Asset Value (USD)",
    names="Chain",
    hole=0.5,
    title="Share of TVL by Chain"
)
fig_chain.update_traces(textposition="inside", textinfo="percent+label")
fig_chain.update_layout(showlegend=True)

# --- نمایش دو نمودار در یک ردیف ---
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_asset_type, use_container_width=True)
with col2:
    st.plotly_chart(fig_chain, use_container_width=True)
