import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

st.set_page_config(page_title="Fraud/Ops Triage Dashboard", layout="wide")
st.title("Fraud/Ops Incident Triage Dashboard")


@st.cache_data(ttl=10)
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    df = pd.read_sql_query("SELECT * FROM triage_history ORDER BY id", conn)
    conn.close()
    if df.empty:
        return df
    df["ingested_at"] = pd.to_datetime(df["ingested_at"])
    df["triaged_at"] = pd.to_datetime(df["triaged_at"])
    df["time_to_triage_seconds"] = (df["triaged_at"] - df["ingested_at"]).dt.total_seconds()
    df["date"] = df["ingested_at"].dt.date
    return df


df = load_data()

if df.empty:
    st.info("No triage history yet. Run some tickets through the pipeline first.")
    st.stop()

total_tickets = len(df)
escalated_count = int(df["escalated"].sum())
escalation_rate = escalated_count / total_tickets * 100
avg_time_to_triage = df["time_to_triage_seconds"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total tickets triaged", total_tickets)
col2.metric("Escalation rate", f"{escalation_rate:.1f}%", help=f"{escalated_count}/{total_tickets} escalated to Slack")
col3.metric("Avg. time to first triage", f"{avg_time_to_triage:.1f}s")
col4.metric("Avg. confidence", f"{df['confidence'].mean():.0f}%")

st.subheader("Triage volume over time")
volume_by_date = df.groupby("date").size().rename("tickets")
st.bar_chart(volume_by_date)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Confidence distribution")
    bins = pd.cut(df["confidence"], bins=[0, 20, 40, 60, 65, 80, 100])
    hist = df.groupby(bins, observed=True).size().rename("count")
    hist.index = hist.index.astype(str)
    st.bar_chart(hist)

with col_right:
    st.subheader("Risk tier breakdown")
    risk_counts = df["risk_tier"].value_counts()
    st.bar_chart(risk_counts)

st.subheader("Escalation decisions")
decision_counts = df["decision"].value_counts()
st.bar_chart(decision_counts)

st.subheader("Full triage history")
display_cols = [
    "ticket_key", "date", "risk_tier", "confidence", "suggested_team",
    "escalated", "decision", "final_risk_tier", "final_team", "time_to_triage_seconds",
]
st.dataframe(df[display_cols], width="stretch")
