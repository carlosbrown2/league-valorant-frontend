import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil import tz

from src.frontend import get_config
from src.frontend import (
    calc_win_percentage,
    create_gsheets_database_connection,
    run_query,
)

conn = create_gsheets_database_connection()


st.title("Team Stats")

# Retrieve Data
dirname = os.path.dirname(__file__)
cfg = get_config(os.path.join("src", "config.yml"))

sheet_url_match = st.secrets["private_gsheets_url_match"]
sheet_url_legacy = st.secrets["private_gsheets_url_match_legacy"]

team_rows = run_query(f'SELECT * FROM "{sheet_url_match}"', conn)
team_rows_legacy = run_query(f'SELECT * FROM "{sheet_url_legacy}"', conn)
df_team_api = pd.DataFrame(team_rows)
df_team_legacy = pd.DataFrame(team_rows_legacy)

df_team_api["game_length"] = df_team_api["game_length"].astype("float")
df_team_api["rounds"] = df_team_api["rounds"].astype("int64")
df_team_api["source"] = "API"
df_team_legacy["source"] = "Manual"

df_team_api["team_score"] = df_team_api.apply(
    lambda row: row["red_score"] if row["home_team"] == "Red" else row["blue_score"],
    axis=1,
)
df_team_api["opponent_score"] = df_team_api.apply(
    lambda row: row["red_score"] if row["home_team"] == "Blue" else row["blue_score"],
    axis=1,
)
# fig_op = px.scatter(win_loss, x='Win', y='Loss', color='opponent', title='W/L Breakdown by Opponent')
# st.plotly_chart(fig_op)
df_team_api["team_score"] = df_team_api["team_score"].astype("int64")
df_team_api["opponent_score"] = df_team_api["opponent_score"].astype("int64")

df_team = pd.concat([df_team_legacy, df_team_api], axis=0)

avg_game_length = df_team.game_length.mean()
avg_rounds = df_team.rounds.mean()


col1, col2 = st.columns(2)
with col1:
    st.metric("Average Game Length (m)", round(avg_game_length, 2))

with col2:
    st.metric("Average # Rounds", int(avg_rounds))

win_loss = df_team.pivot_table(
    values="map", index="red_roster", columns="outcome", aggfunc="count"
)
win_loss = win_loss.fillna(0).reset_index(drop=False)
df_team["date"] = pd.to_datetime(df_team["date"], utc=True)
win_perc = calc_win_percentage(df_team, outcome_col="outcome")
df_team = df_team.sort_values(by="date")
df_team["win_%"] = win_perc

fig_map = px.scatter(
    df_team, x="team_score", y="opponent_score", facet_col="map", title="Scores by Map"
)
# Update X Axis labels for readability
fig_map.for_each_xaxis(lambda x: x.update(title=""))
fig_map.for_each_yaxis(lambda y: y.update(title=""))
fig_map.add_annotation(
    x=0.5, y=-0.15, text="Team Score", xref="paper", yref="paper", showarrow=False
)
fig_map.add_annotation(
    x=-0.1,
    y=0.5,
    text="Opponent Score",
    textangle=-90,
    showarrow=False,
    xref="paper",
    yref="paper",
)
fig_map.for_each_annotation(lambda a: a.update(text=a.text.replace("map=", "")))

st.plotly_chart(fig_map)

## Map Breakdown
df_map = pd.pivot_table(
    df_team, index="map", columns="outcome", aggfunc="count"
).date.fillna(0)
df_map = df_map.astype("int64")
df_map["Win %"] = df_map["W"] / (df_map["W"] + df_map["L"])
df_map["Loss %"] = df_map["L"] / (df_map["W"] + df_map["L"])

df_map["Win %"] = df_map["Win %"] * 100
df_map["Win %"] = df_map["Win %"].round(3)
df_map["Loss %"] = df_map["Loss %"] * 100
df_map["Loss %"] = df_map["Loss %"].round(3)

## Pistol Rounds
pistols = df_team.pistol_rounds.value_counts(normalize=True) * 100
pistols.round(2).sort_index(ascending=False)
winloss = pd.pivot_table(
    data=df_team, index="pistol_rounds", columns="outcome", aggfunc="count"
).reset_index()["match_id"]
winloss["P_win_match"] = winloss["W"] / (winloss["L"] + winloss["W"]) * 100
pistols = pistols.reset_index().merge(
    winloss.round(2), left_on="index", right_index=True
)
pistols = pistols.rename(columns={"pistol_rounds": "Win Rate"}).set_index("index")

col3, col4 = st.columns(2)
with col3:
    st.header("Map Breakdown")
    st.write(
        df_map.loc[:, ["W", "L", "Win %", "Loss %"]].sort_values(
            by="W", ascending=False
        )
    )
    st.markdown("**Win Rate** = How often you win this many pistol rounds")
    st.markdown(
        "**P_win_match** = The probability you win the match given you win this many pistol rounds"
    )

with col4:
    st.header("Pistol Round Stats")
    st.write(
        pistols.loc[:, ["Win Rate", "P_win_match"]].sort_index(axis=0, ascending=False)
    )
    st.header("Avg. Score (given Loss), by Map")
    df_loss = df_team[df_team.outcome == "L"]
    df_loss["calc_home_score"] = df_loss.apply(
        lambda row: row["blue_score"]
        if row["home_team"] == "Blue"
        else row["red_score"],
        axis=1,
    )
    df_loss["loss_score"] = df_loss.calc_home_score.combine_first(df_loss.team_score)
    st.write(
        df_loss.groupby("map")
        .loss_score.mean()
        .reset_index()
        .rename(columns={"loss_score": "score"})
        .sort_values(by="score", ascending=False)
        .set_index("map")
        .T
    )

# # Opponent Breakdown
st.header("Opponent Breakdown")
opponent = st.selectbox("Select Opponent", df_team.opponent.sort_values().unique())
df_opponent = df_team[df_team["opponent"] == opponent]
df_opponent.date = df_opponent.date.apply(lambda x: x.date())
st.write(
    df_opponent.loc[
        :,
        [
            "date",
            "opponent",
            "map",
            "team_score",
            "opponent_score",
            "pistol_rounds",
            "outcome",
        ],
    ].reset_index(drop=True)
)
col5, col6 = st.columns(2)
with col5:
    st.write(df_opponent.outcome.value_counts().rename("Sum"))
with col6:
    st.write(
        df_opponent.pivot_table(
            index="map", columns="outcome", values="date", aggfunc="count"
        )
        .fillna(0)
        .astype("int64")
    )
