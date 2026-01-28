import streamlit as st
import pandas as pd
import requests
import zipfile
from io import BytesIO
from datetime import datetime
import os

st.set_page_config(
    page_title="Silver Retail Sentiment",
    layout="wide"
)

st.title("🪙 Silver Retail Sentiment Dashboard")

# ---------- COT FETCH ----------
def load_cot_data():
    if os.path.exists("cot_data.csv"):
        return pd.read_csv("cot_data.csv")

    url = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip"
    r = requests.get(url)

    z = zipfile.ZipFile(BytesIO(r.content))
    file_name = z.namelist()[0]

    df = pd.read_csv(z.open(file_name))
    silver = df[df["Market_and_Exchange_Names"].str.contains(
        "SILVER - COMMODITY EXCHANGE INC", na=False
    )]

    # Handle different COT column naming conventions
if "NonRept_Long_All" in silver.columns:
    long_col = "NonRept_Long_All"
    short_col = "NonRept_Short_All"
else:
    long_col = "NonRept_Long"
    short_col = "NonRept_Short"

silver["retail_net"] = silver[long_col] - silver[short_col]
    )

    out = silver[[
        "Report_Date_as_YYYY-MM-DD",
        "retail_net",
        "Open_Interest_All"
    ]]

    out.columns = ["date", "retail_net", "open_interest"]
    out["date"] = pd.to_datetime(out["date"])

    out.to_csv("cot_data.csv", index=False)
    return out

cot = load_cot_data()
latest_cot = cot.iloc[-1]

# ---------- DEMO SCORES ----------
scores = pd.read_csv("scores.csv")
latest = scores.iloc[-1]
import pandas as pd

st.set_page_config(
    page_title="Silver Retail Sentiment",
    layout="wide"
)

st.title("🪙 Silver Retail Sentiment Dashboard")

# Load data
scores = pd.read_csv("scores.csv")

cot = pd.read_csv("cot_data.csv")
latest_cot = cot.iloc[-1]

st.sidebar.subheader("📊 COT – Live data")
st.sidebar.write(f"Retail net: {int(latest_cot['retail_net'])}")
st.sidebar.write(f"Open interest: {int(latest_cot['open_interest'])}")
latest = scores.iloc[-1]

# Header
c1, c2, c3 = st.columns([2,1,1])

with c1:
    st.metric(
        "🔥 Retail Heat Index",
        int(latest["total"]),
        delta=int(latest["change"])
    )

with c2:
    st.metric("COT", latest["cot_score"])

with c3:
    st.metric("PSLV", latest["pslv_score"])

st.caption(f"Last updated: {latest['date']}")

st.divider()

# Modules
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.subheader("📊 COT")
    st.progress(latest["cot_score"] / 25)

with c2:
    st.subheader("🪙 PSLV")
    st.progress(latest["pslv_score"] / 25)

with c3:
    st.subheader("🧱 Physical")
    st.progress(latest["physical_score"] / 25)

with c4:
    st.subheader("📈 Options")
    st.progress(latest["options_score"] / 25)

st.divider()
st.subheader("📉 Retail Heat – History")
st.line_chart(scores.set_index("date")[["total"]])
