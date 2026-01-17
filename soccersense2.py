import streamlit as st
import pandas as pd
import plotly.express as px
from plotly import graph_objects as go
from openai import OpenAI

# ======================================
# BASIC CONFIG
# ======================================
st.set_page_config(page_title="SoccerSense", layout="wide")
st.title("⚽ SoccerSense – Coach & Player Intelligence")

client = OpenAI(api_key="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")

# ======================================
# LOAD DATA
# ======================================
@st.cache_data
def load_sheets(path="Voetbaldata.xlsx"):
    return pd.read_excel(path, sheet_name=None)

sheets = load_sheets()
appearances = sheets["appearances"]
players = sheets["players"]
teams = sheets["teams"]
shots = sheets["shots"]
teamstats = sheets["teamstats"]

# ======================================
# FIX DATATYPES
# ======================================
teams["teamID"] = teams["teamID"].astype(str)
teamstats["teamID"] = teamstats["teamID"].astype(str)
players["playerID"] = players["playerID"].astype(str)
shots["shooterID"] = shots["shooterID"].astype(str)

# ======================================
# NUMERIC CONVERSION
# ======================================
numeric_cols = [
    "goals", "xGoals", "shots", "shotsOnTarget",
    "deep", "ppda", "fouls", "corners",
    "yellowCards", "redCards"
]

for df in [teamstats, appearances]:
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ======================================
# NORMALIZATION
# ======================================
def fix_xg(x):
    if x == 0: return 0
    if x < 10: return x
    if x > 1000: return x / 10000
    if x > 100: return x / 100
    if x > 10: return x / 10
    return x

def fix_ppda(x):
    if x == 0: return 0
    if x < 40: return x
    if x > 10000: return x / 10000
    if x > 1000: return x / 1000
    if x > 100: return x / 100
    if x > 50: return x / 10
    return x

teamstats["xGoals"] = teamstats["xGoals"].apply(fix_xg)
teamstats["ppda"] = teamstats["ppda"].apply(fix_ppda)

# ======================================
# LOOKUPS
# ======================================
teams_lookup = dict(zip(teams["name"], teams["teamID"]))
players_lookup = dict(zip(players["name"], players["playerID"]))

# ======================================
# MODE SELECTOR
# ======================================
mode = st.radio("Selecteer modus", ["Coach Mode", "Player Mode"])

# ======================================
# COACH MODE
# ======================================
if mode == "Coach Mode":

    st.header("Coach Mode – Team Inzichten")

    team_name = st.selectbox("Kies team", list(teams_lookup.keys()))
    tid = teams_lookup[team_name]
    df_team = teamstats[teamstats["teamID"] == tid].sort_values("date")

    st.subheader("Teamstatistieken (Gemiddelden)")

    avg_goals = df_team["goals"].mean()
    avg_xg = df_team["xGoals"].mean()
    avg_ppda = df_team["ppda"].mean()
    avg_sot = df_team["shotsOnTarget"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Goals", f"{avg_goals:.2f}")
    c2.metric("xG", f"{avg_xg:.2f}")
    c3.metric("PPDA", f"{avg_ppda:.2f}")
    c4.metric("Shots OT", f"{avg_sot:.2f}")

    # ======================================
    # AI FEEDBACK PER STATISTIEK
    # ======================================
    st.subheader("AI Feedback per Statistiek")

    def ai_feedback(stat, value):
        prompt = f"""
Je bent een ervaren voetbalcoach en data-analist.
Geef maximaal 3 korte, concrete verbeterpunten.

Statistiek: {stat}
Waarde: {value:.2f}
"""
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return r.choices[0].message.content

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(ai_feedback("Goals", avg_goals))
    with col2:
        st.info(ai_feedback("Expected Goals (xG)", avg_xg))
    with col3:
        st.info(ai_feedback("PPDA", avg_ppda))
    with col4:
        st.info(ai_feedback("Shots on Target", avg_sot))

    # ======================================
    # GOALS VS XG
    # ======================================
    st.subheader("⚠️ Afwerking: Goals vs Verwachte Goals (xG)")

    df_last = df_team.tail(10).copy()
    fig = go.Figure()
    fig.add_bar(x=df_last["date"], y=df_last["xGoals"], name="xG", marker_color="lightgrey")
    fig.add_bar(x=df_last["date"], y=df_last["goals"], name="Goals", marker_color="green")
    fig.update_layout(barmode="group", height=450)
    st.plotly_chart(fig, use_container_width=True)

    # ======================================
    # TEAM TRAININGSADVIES
    # ======================================
    st.subheader("AI Trainingsadvies (Team)")

    if st.button("Genereer Teamtraining Advies"):
        prompt = f"""
Je bent een topcoach.
Genereer 4 concrete trainingen op basis van:

Goals: {avg_goals:.2f}
xG: {avg_xg:.2f}
PPDA: {avg_ppda:.2f}
"""
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        st.success(r.choices[0].message.content)

    # ======================================
    # AI COACH CHATBOT (FIXED)
    # ======================================
    st.subheader("🤖 AI Coach Assistant")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    coach_question = st.text_input(
        "Stel een vraag aan de AI-coach",
        placeholder="Bijv. Waarom scoren we minder dan onze xG?"
    )

    if st.button("Vraag AI Coach"):
        if coach_question.strip():
            context = f"""
Team: {team_name}
Goals: {avg_goals:.2f}
xG: {avg_xg:.2f}
PPDA: {avg_ppda:.2f}
Shots OT: {avg_sot:.2f}
"""
            prompt = f"""
Je bent een professionele voetbalcoach.
Beantwoord de vraag op basis van de data.

{context}

Vraag:
{coach_question}
"""
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            st.session_state.chat_history.append(("Coach", coach_question))
            st.session_state.chat_history.append(("AI", r.choices[0].message.content))

    for role, msg in st.session_state.chat_history:
        st.markdown(f"**{role}:** {msg}")

# ======================================
# PLAYER MODE
# ======================================
else:

    st.header("Player Mode – Persoonlijk Overzicht")

    player_name = st.selectbox("Kies speler", list(players_lookup.keys()))
    pid = players_lookup[player_name]

    df_shots = shots[shots["shooterID"] == pid].copy()
    df_shots["xGoal"] = pd.to_numeric(df_shots["xGoal"], errors="coerce").fillna(0)
    df_shots["xGoal"] = df_shots["xGoal"].apply(fix_xg)

    total_xg = df_shots["xGoal"].sum()
    total_shots = len(df_shots)

    c1, c2 = st.columns(2)
    c1.metric("Totaal xG", f"{total_xg:.2f}")
    c2.metric("Schoten", total_shots)

    st.subheader("Shotmap")

    if not df_shots.empty:
        fig = px.scatter(
            df_shots,
            x="positionX",
            y="positionY",
            color="xGoal",
            hover_data=["minute", "shotType", "shotResult"],
            title=f"Shotmap — {player_name}"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

    # ======================================
    # PLAYER AI ADVIES (TERUG!)
    # ======================================
    st.subheader("🤖 Persoonlijk AI-Advies")

    if st.button("Genereer Speleradvies"):
        prompt = f"""
Je bent een professionele voetbalcoach.

Speler: {player_name}
Totaal xG: {total_xg:.2f}
Aantal schoten: {total_shots}

Geef:
1. Wat deze speler goed doet
2. Wat verbeterd kan worden
3. 3 concrete trainingsvormen
"""

        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            st.success(r.choices[0].message.content)

        except:
            st.error("AI speleradvies is tijdelijk niet beschikbaar.")

