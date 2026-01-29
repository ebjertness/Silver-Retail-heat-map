import streamlit as st
import pandas as pd
import requests
import zipfile
from io import BytesIO
from datetime import datetime
import os

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="Silver Retail Sentiment",
    layout="wide"
)

st.title("🪙 Silver Retail Sentiment Dashboard")

# ---------------- COT DATA ----------------
@st.cache_data(ttl=43200)
def load_cot_data():

    url = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip"
    r = requests.get(url)

    z = zipfile.ZipFile(BytesIO(r.content))
    file_name = z.namelist()[0]

    df = pd.read_csv(z.open(file_name))

    silver = df[
        df["Market_and_Exchange_Names"].str.contains(
            "SILVER - COMMODITY EXCHANGE INC", na=False
        )
    ]

    possible_pairs = [
        ("NonRept_Long_All", "NonRept_Short_All"),
        ("NonRept_Long", "NonRept_Short"),
        ("Non_Reportable_Long_All", "Non_Reportable_Short_All"),
        ("Non_Reportable_Long", "Non_Reportable_Short"),
    ]

    long_col = None
    short_col = None

    for lc, sc in possible_pairs:
        if lc in silver.columns and sc in silver.columns:
            long_col = lc
            short_col = sc
            break

    if long_col is None:
     st.warning(
        "Could not auto-detect non-reportable columns in COT data. "
        "Using fallback based on column name search."
    )

    # Fallback: try any column containing 'Non' and 'Long/Short'
    long_candidates = [c for c in silver.columns if "Long" in c and "Non" in c]
    short_candidates = [c for c in silver.columns if "Short" in c and "Non" in c]

    if long_candidates and short_candidates:
        long_col = long_candidates[0]
        short_col = short_candidates[0]
    else:
        st.error("COT column detection failed. Check CFTC format.")
        return pd.DataFrame(columns=["date", "retail_net", "open_interest"])

    silver["retail_net"] = silver[long_col] - silver[short_col]

    out = silver[
        [
            "Report_Date_as_YYYY-MM-DD",
            "retail_net",
            "Open_Interest_All"
        ]
    ]

    out.columns = ["date", "retail_net", "open_interest"]
    out["date"] = pd.to_datetime(out["date"])

    # out.to_csv("cot_data.csv", index=False)
    return out

cot = load_cot_data()
latest_cot = cot.iloc[-1]

# ---------------- COT SCORING ----------------
cot = cot.copy()
cot["retail_pct_oi"] = cot["retail_net"] / cot["open_interest"]

window = 52  # weeks
cot["mean"] = cot["retail_pct_oi"].rolling(window).mean()
cot["std"] = cot["retail_pct_oi"].rolling(window).std()

cot["z_score"] = (cot["retail_pct_oi"] - cot["mean"]) / cot["std"]

latest_z = cot.iloc[-1]["z_score"]

def cot_score_from_z(z):
    if z < -1:
        return 5
    elif z < 0.5:
        return 10
    elif z < 1.0:
        return 15
    elif z < 1.5:
        return 20
    else:
        return 25

cot_score_live = cot_score_from_z(latest_z)

# ---------------- HEADER ----------------
c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    st.metric(
    "🔥 Retail Heat Index",
    cot_score_live,
    delta="Driven by COT (live)"
)

with c2:
    st.metric(
        "COT score (live)",
        cot_score_live
    )
    st.caption(f"Z-score (52w): {latest_z:.2f}")

with c3:
    st.metric("PSLV score", "—")
    st.caption("Coming next")

st.caption(f"Last updated (COT): {latest_cot['date'].date()}")

st.divider()

# ---------------- MODULES ----------------
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.subheader("📊 COT (Live)")
    st.write(f"Retail net: {int(latest_cot['retail_net'])}")
    st.write(f"Open interest: {int(latest_cot['open_interest'])}")

with m2:
    st.subheader("🪙 PSLV")
    st.progress(latest["pslv_score"] / 25)

with m3:
    st.subheader("🧱 Physical")
    st.progress(latest["physical_score"] / 25)

with m4:
    st.subheader("📈 Options")
    st.progress(latest["options_score"] / 25)

st.divider()

# ---------------- HISTORY ----------------
