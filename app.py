import streamlit as st
import pandas as pd
import requests
import zipfile
from io import BytesIO
from datetime import datetime
import os
import yfinance as yf
from datetime import date

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="Silver Retail Sentiment",
    layout="wide"
)

st.title("🪙 Silver Retail Sentiment Dashboard")

# ---------------- COT DATA ----------------
@st.cache_data(ttl=86400, show_spinner=False)
def load_cot_data():

    url = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip"
    r = requests.get(url)

    z = zipfile.ZipFile(BytesIO(r.content))
    file_name = z.namelist()[0]

    df = pd.read_csv(z.open(file_name), low_memory=False)

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
# ---------------- PSLV DATA ----------------
@st.cache_data(ttl=3600)
def load_pslv():
    df = pd.read_csv("pslv_data.csv", parse_dates=["date"])
    return df

pslv = load_pslv()
# ---------------- PSLV AUTO UPDATE ----------------

if st.button("🔄 Update PSLV now"):
    ticker = yf.Ticker("PSLV")
    info = ticker.fast_info

    new_row = {
        "date": pd.to_datetime(date.today()),
        "shares_outstanding": info.get("sharesOutstanding", None),
        "silver_oz": info.get("sharesOutstanding", 0)  # proxy
    }

    pslv = pd.concat([pslv, pd.DataFrame([new_row])])
    pslv.to_csv("pslv_data.csv", index=False)

    st.success("PSLV updated!")

latest_pslv = pslv.iloc[-1]

# find last row with different ounces
prev_rows = pslv[pslv["silver_oz"] != latest_pslv["silver_oz"]]

if len(prev_rows) > 0:
    prev_pslv = prev_rows.iloc[-1]
    oz_change = latest_pslv["silver_oz"] - prev_pslv["silver_oz"]
else:
    oz_change = 0

def pslv_score_from_flow(oz):
    if oz < 0:
        return 5
    elif oz < 500_000:
        return 10
    elif oz < 2_000_000:
        return 15
    elif oz < 5_000_000:
        return 20
    else:
        return 25

pslv_score_live = pslv_score_from_flow(oz_change)
# ---------------- PHYSICAL DATA ----------------

@st.cache_data(ttl=3600)
def load_physical():
    df = pd.read_csv("physical_data.csv", parse_dates=["date"])
    return df

physical = load_physical()
latest_physical = physical.iloc[-1]

premium = latest_physical["premium_pct"]

def physical_score_from_premium(p):
    if p < 5:
        return 5
    elif p < 10:
        return 10
    elif p < 20:
        return 15
    elif p < 35:
        return 20
    else:
        return 25

physical_score_live = physical_score_from_premium(premium)
# tempo vs historikk
physical = physical.copy()
physical["mean"] = physical["premium_pct"].rolling(30).mean()
physical["std"] = physical["premium_pct"].rolling(30).std()

physical["z"] = (
    (physical["premium_pct"] - physical["mean"]) /
    physical["std"]
)

latest_physical_z = physical.iloc[-1]["z"]

# ---------------- PSLV FLOW NORMALIZATION ----------------

pslv = pslv.copy()
pslv["flow"] = pslv["silver_oz"].diff()

window = 30  # dager, juster senere
pslv["mean"] = pslv["flow"].rolling(window).mean()
pslv["std"] = pslv["flow"].rolling(window).std()

pslv["z"] = (pslv["flow"] - pslv["mean"]) / pslv["std"]

latest_pslv_z = pslv.iloc[-1]["z"]

# ---------------- HEADER ----------------
c1, c2, c3 = st.columns([2, 1, 1])

total_heat = int(
    0.5 * cot_score_live +
    0.3 * pslv_score_live +
    0.2 * physical_score_live
)

# ---------------- INTERPRETATION ENGINE ----------------

def interpret_market(cot_score, pslv_score, heat):

    if heat < 8:
        phase = "early participation"
    elif heat < 15:
        phase = "normal involvement"
    elif heat < 22:
        phase = "crowding building"
    else:
        phase = "possible late-stage enthusiasm"

    if pslv_score > cot_score:
        driver = "ETF flows dominate futures positioning"
    elif cot_score > pslv_score:
        driver = "futures positioning leads ETF demand"
    else:
        driver = "futures and ETF activity are aligned"

    return f"""
Retail activity suggests **{phase}**.

Main driver: **{driver}**.

This environment typically reflects expanding interest, 
but not necessarily a terminal blow-off.
"""

interpretation_text = interpret_market(
    cot_score_live,
    pslv_score_live,
    total_heat
)

st.metric(
    "🔥 Retail Heat Index",
    total_heat,
    delta="COT + PSLV"
)

st.markdown("---")
st.subheader("🧠 Market interpretation")
st.markdown(interpretation_text)

with c2:
    st.metric(
        "COT score (live)",
        cot_score_live
    )
    st.caption(f"Z-score (52w): {latest_z:.2f}")

with c3:
    st.metric("PSLV score", "—")
    st.caption("Coming next")

st.caption(f"Last updated (COT): {latest_cot['date']}")

st.markdown("---")

# ---------------- MODULES ----------------
# ---------------- MODULES ----------------
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.subheader("📊 COT")
    st.caption("Live")
    st.metric("Retail Z-score", f"{latest_z:.2f}")

with m2:
    st.subheader("🪙 PSLV")
    st.metric(
        "Flow score",
        pslv_score_live,
        delta=f"{oz_change:,.0f} oz"
    )
    st.caption(f"Flow Z-score: {latest_pslv_z:.2f}")

with m3:
    st.subheader("🧱 Physical")
    st.metric(
        "Premium",
        f"{premium:.1f}%"
    )
    st.caption(f"Z-score: {latest_physical_z:.2f}")

with m4:
    st.subheader("📈 Options")
    st.caption("Module coming later")

st.markdown("---")

# ---------------- HISTORY ----------------
