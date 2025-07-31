import streamlit as st

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Network Performance Analysis",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Title with Logo ---
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar" style="width:60px; height:60px;">
        <h1 style="margin: 0;">Axelar Network Performance Analysis</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Reference and Rebuild Info ---
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" alt="Eman Raz" style="width:25px; height:25px; border-radius: 50%;">
            <span>Rebuilt by: <a href="https://x.com/0xeman_raz" target="_blank">Eman Raz</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Info Box ---
st.markdown(
    """
    <div style="background-color: #c3c3c3; padding: 15px; border-radius: 10px; border: 1px solid #c3c3c3;">
        Axelar Network is a decentralized blockchain platform designed to enable seamless interoperability between disparate blockchain ecosystems. 
        Launched to address the fragmentation in the blockchain space, Axelar provides a robust infrastructure for cross-chain communication, 
        allowing different blockchains to securely share data and transfer assets. By leveraging a decentralized network of validators and 
        a universal protocol, Axelar facilitates scalable, secure, and efficient interactions across blockchains, empowering developers to 
        build applications that operate across multiple chains without complex integrations. With its focus on simplifying cross-chain 
        connectivity, Axelar aims to drive the adoption of Web3 by creating a unified, interoperable blockchain environment.
    </div>
    """,
    unsafe_allow_html=True
)


# --- Links with Logos ---
st.markdown(
    """
    <div style="font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://www.axelar.network/" target="_blank">Axelar Website</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="X" style="width:20px; height:20px;">
            <a href="https://x.com/axelar" target="_blank">Axelar X Account</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


