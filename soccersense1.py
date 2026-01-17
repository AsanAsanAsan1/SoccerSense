import streamlit as st
import pandas as pd
from openai import OpenAI

# -----------------------------------------
# API KEY
# -----------------------------------------
client = OpenAI(api_key="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")

# -----------------------------------------
# DATA LOAD
# -----------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("Voetbaldata.xlsx", sheet_name=None)

    appearances = df["appearances"]
    leagues = df["leagues"]
    players = df["players"]
    shots = df["shots"]
    teams = df["teams"]
    teamstats = df["teamstats"]

    # Clean column whitespace (just in case)
    for d in [appearances, leagues, players, shots, teams, teamstats]:
        d.columns = d.columns.str.strip()

    return appearances, leagues, players, shots, teams, teamstats


appearances, leagues, players, shots, teams, teamstats = load_data()

st.set_page_config(page_title="Football Dashboard", layout="wide")
st.title("⚽ Football Analytics Dashboard")


# ==============================================================
# SIDEBAR – TEAM SELECTOR
# ==============================================================
st.sidebar.header("Team Dashboard")

team_lookup = dict(zip(teams["name"], teams["teamID"]))
selected_team_name = st.sidebar.selectbox("Select Team", list(team_lookup.keys()))
selected_team_id = team_lookup[selected_team_name]

team_data = teamstats[teamstats["teamID"] == selected_team_id]


# ==============================================================
# TEAM STATISTICS
# ==============================================================
st.header(f"📊 Team Overview: {selected_team_name}")

col1, col2, col3 = st.columns(3)

col1.metric("Goals per match", round(team_data["goals"].mean(), 2))
col2.metric("xG per match", round(team_data["xGoals"].mean(), 2))
col3.metric("PPDA per match", round(team_data["ppda"].mean(), 2))


# ==============================================================
# CLEAN NEW TEAM GRAPHS
# ==============================================================
# --- GRAPH 1: Shots & Shots on Target ---
st.subheader("🎯 Shot Quality Over Time")

chart_shots = team_data[["date", "shots", "shotsOnTarget"]].copy()
chart_shots = chart_shots.set_index("date")
st.line_chart(chart_shots)


# --- GRAPH 2: Defensive Discipline ---
st.subheader("🛑 Defensive Discipline (Fouls & Cards)")

chart_def = team_data[["date", "fouls", "yellowCards", "redCards"]].copy()
chart_def = chart_def.set_index("date")
st.area_chart(chart_def)


# ==============================================================
# SIDEBAR – PLAYER SELECTOR
# ==============================================================
st.sidebar.header("Player Dashboard")

player_lookup = dict(zip(players["name"], players["playerID"]))
selected_player_name = st.sidebar.selectbox("Select Player", list(player_lookup.keys()))
selected_player_id = player_lookup[selected_player_name]

player_data = appearances[appearances["playerID"] == selected_player_id]


# ==============================================================
# PLAYER STATISTICS
# ==============================================================
st.header(f"👤 Player Overview: {selected_player_name}")

if len(player_data) == 0:
    st.info("No match data for this player.")
else:
    colA, colB, colC = st.columns(3)

    colA.metric("Goals", int(player_data["goals"].sum()))
    colB.metric("xG", round(player_data["xGoals"].sum(), 2))
    colC.metric("Shots", int(player_data["shots"].sum()))

    st.subheader("📈 Match Performance")

    chart_player = player_data[["date", "goals", "xGoals", "shots"]].copy()
    chart_player = chart_player.set_index("date")
    st.line_chart(chart_player)


# ==============================================================
# AI ADVICE
# ==============================================================
st.header("🧠 AI Tactical Advice")

prompt = st.text_area("Ask AI anything:")

if st.button("Generate AI Advice"):
    with st.spinner("Thinking..."):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a football strategy and performance analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            st.write(response.choices[0].message["content"])
        except Exception as e:
            st.error(f"Error: {e}")
