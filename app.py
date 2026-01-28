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
def load_cot_data():
    if os.path.exists("cot_data.csv"):
        return pd.read_csv("cot_data.csv")

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
        raise ValueError(
            f"Could not find non-reportable columns. "
            f"Available columns: {list(silver.columns)}"
        )

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

    out.to_csv("cot_data.csv", index=False)
    return out

cot = load_cot_data()
latest_cot = cot.iloc[-1]

# ---------------- SCORES (TEMP) ----------------
scores = pd.read_csv("scores.csv")
latest = scores.iloc[-1]

# ---------------- HEADER ----------------
c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    st.metric(
        "🔥 Retail Heat Index",
        int(latest["total"]),
        delta=int(latest["change"])
    )

with c2:
    st.metric("COT score", latest["cot_score"])

with c3:
    st.metric("PSLV score", latest["pslv_score"])

st.caption(f"Last updated: {latest['date']}")

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
st.subheader("📉 Retail Heat Index – History")
st.line_chart(scores.set_index("date")[["total"]])
