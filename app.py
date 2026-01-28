import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Silver Retail Sentiment",
    layout="wide"
)

st.title("🪙 Silver Retail Sentiment Dashboard")

# Load data
scores = pd.read_csv("scores.csv")
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
