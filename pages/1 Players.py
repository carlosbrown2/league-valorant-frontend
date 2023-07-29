import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.frontend import get_config
from src.frontend import create_gsheets_database_connection, run_query

conn = create_gsheets_database_connection()

dirname = os.path.dirname(__file__)
cfg = get_config(os.path.join("src", "config.yml"))

st.markdown("# Player Stats")

# Retrieve Data
sheet_url_match = st.secrets["private_gsheets_url_match"]
sheet_url_match_legacy = st.secrets["private_gsheets_url_match_legacy"]
sheet_url_player = st.secrets["private_gsheets_url_player"]
sheet_url_player_legacy = st.secrets["private_gsheets_url_player_legacy"]
sheet_url_roster = st.secrets["private_gsheets_url_roster"]

with st.spinner("Retrieving Player and Match Data..."):
    team_rows = run_query(f'SELECT * FROM "{sheet_url_match}"', conn)
    # team_rows_legacy = run_query(f'SELECT * FROM "{sheet_url_match_legacy}"', conn)
    player_rows = run_query(f'SELECT * FROM "{sheet_url_player}"', conn)
    # player_rows_legacy = run_query(f'SELECT * FROM "{sheet_url_player_legacy}"', conn)
    roster = run_query(f'SELECT * FROM "{sheet_url_roster}"', conn)

df_team = pd.DataFrame(team_rows)
df_player = pd.DataFrame(player_rows)
df_roster = pd.DataFrame(roster)

df_player = df_player.merge(
    df_team.loc[:, ["match_id", "date", "map"]],
    on="match_id",
    how="left",
)
df_player = df_player.merge(
    df_roster,
    on=['name', 'tag'],
    how='left'
)

# df_player.outcome = df_player.outcome.fillna("B")
df_player = df_player[~df_player.name.isin(cfg["retired_players"])]
# st.write(df_player.kills.groupby("name").sum())

df_team["date"] = pd.to_datetime(df_team["date"], utc=True)
min_date = df_team.date.min()
max_date = df_team.date.max() + timedelta(days=1)

select_col1, select_col2, select_col3 = st.columns(3)
with select_col1:
    start_date = st.date_input("Start Date", min_date)
with select_col2:
    end_date = st.date_input("End Date", max_date)

# convert to datetimes for comparison
start_date = datetime(start_date.year, start_date.month, start_date.day)
end_date = datetime(end_date.year, end_date.month, end_date.day)

df_player["date"] = pd.to_datetime(df_player["date"])
df_player = df_player.loc[
    (df_player.date >= start_date) & (df_player.date <= end_date), :
]

int_cols = {col: "int64" for col in cfg["integer_columns"]}
float_cols = {col: "float" for col in cfg["float_columns"]}
df_headshot_ts = df_player.loc[
    :, ["name", "date", "bodyshots", "legshots", "headshots"]
].dropna()
df_player.loc[:, cfg["integer_columns"]] = df_player.loc[
    :, cfg["integer_columns"]
].fillna(0)
df_player.loc[:, cfg["float_columns"]] = df_player.loc[:, cfg["float_columns"]].fillna(
    0
)
df_player = df_player.astype(int_cols)
df_player = df_player.astype(float_cols)

# Calculate z-scores


st.header("General Player Statistics")
player_list = list(df_player['name'].unique())
player_list.extend(['All'])
player_select = st.selectbox(label='Select Player', options=player_list)
df_c = (
    df_player.loc[:, ["name", "clutch_wins", "clutch_counts"]]
    .fillna(0)
    .groupby("name")
    .sum()
    .reset_index()
)
df_c["clutch_percent"] = df_c["clutch_wins"] / df_c["clutch_counts"] * 100
df_c["clutch_percent"] = df_c["clutch_percent"].round(2)
general_cols = [
    "kills",
    "deaths",
    "assists",
    "first_bloods",
    "first_duels",
    "first_deaths",
    "bodyshots",
    "headshots",
    "legshots",
]
pivot_general = (
    df_player.loc[
        :,
        ["name"] + general_cols,
    ]
    .groupby("name")
    .sum()
    .rename(columns={"first_bloods": "first bloods"})
)
pivot_acs = (
    df_player.loc[:, ["name", "acs"]]
    .groupby("name")
    .mean()
    .rename(columns={"acs": "avg. acs"})
)
pivot_general = pd.merge(pivot_general, pivot_acs, left_index=True, right_index=True)
pivot_general = pd.merge(
    pivot_general,
    df_c.set_index("name").loc[:, "clutch_percent"],
    left_index=True,
    right_index=True,
)
match_counts = (
    df_player.groupby(["name"])
    .count()
    .agent.reset_index()
    .rename(columns={"agent": "match counts"})
    .set_index("name")
)
pivot_general = pd.merge(pivot_general, match_counts, left_index=True, right_index=True)
# Calculate per match stats
pivot_general["kills / match"] = pivot_general.kills / pivot_general["match counts"]
pivot_general["deaths / match"] = pivot_general.deaths / pivot_general["match counts"]
pivot_general["assists / match"] = pivot_general.assists / pivot_general["match counts"]
pivot_general["headshot %"] = (
    pivot_general["headshots"]
    / (
        pivot_general["headshots"]
        + pivot_general["bodyshots"]
        + pivot_general["legshots"]
    )
    * 100
)
pivot_general = pivot_general.rename(
    columns={"first_duels": "first duels", "first_deaths": "first deaths"}
)
display_cols = [
    "match counts",
    "kills",
    "kills / match",
    "deaths",
    "deaths / match",
    "assists",
    "assists / match",
    "headshot %",
    "first bloods",
    "first duels",
    "first deaths",
    "avg. acs",
    "clutch_percent",
]
# pivot_general.columns=['kills', 'deaths', 'assists', 'first_bloods', 'eco_score', 'acs']
if player_select == 'All':
    st.write(pivot_general.loc[:, display_cols].sort_values(by="kills", ascending=False))
else:
    st.write(pivot_general.loc[pivot_general.index==player_select, display_cols].sort_values(by="kills", ascending=False))
kill_pivot_agent = (
    df_player.pivot_table(values="kills", columns="agent", index="name", aggfunc="sum")
    .fillna(0)
    .astype("int64")
)
kill_pivot_agent["Total"] = kill_pivot_agent.apply(lambda row: sum(row), axis=1)

st.header("Average K/D by Agent")
df_player["K/D"] = df_player["kills"] / df_player["deaths"]
wavg_col = "Weight. Avg. K/D"
agent_counts = df_player.groupby(["name", "agent"]).count().map.reset_index()
agent_counts = agent_counts.rename(columns={"map": "weight"})
df_player_kd = df_player.merge(agent_counts, on=["name", "agent"])
kd_weightavg = df_player_kd.groupby("name").apply(
    lambda x: np.average(x["K/D"], weights=x["weight"])
)
kd_weightavg = kd_weightavg.reset_index().rename(columns={0: wavg_col})
kd_pivot = df_player_kd.pivot_table(values="K/D", columns="agent", index="name").fillna(
    0
)
kd_pivot = kd_pivot.merge(kd_weightavg, on=["name"], how="inner").set_index("name")
st.write(kd_pivot.sort_values(by=wavg_col, ascending=False).round(4))
st.write(
    "Note: Weighted Average K/D controls for the amount of times a player plays as a certain agent"
)

st.header("Average K/D by Map")
kd_pivot_map = df_player_kd.pivot_table(
    values="K/D", columns="map", index="name"
).fillna(0)
st.write(kd_pivot_map.round(4))
# st.plotly_chart(px.imshow(kd_pivot_map.round(4), title="Average K/D by Map Viz"))
st.header("Shooting Breakdown")
shot_types = {'headshots': int, 'bodyshots': int, 'legshots': int}
df_headshot_ts = df_headshot_ts.astype(shot_types)
df_headshot_ts["headshot %"] = (
    df_headshot_ts["headshots"]
    / (
        df_headshot_ts["headshots"]
        + df_headshot_ts["bodyshots"]
        + df_headshot_ts["legshots"]
    )
    * 100
)
fig = px.histogram(
    df_headshot_ts,
    x="name",
    y=["legshots", "bodyshots", "headshots"],
    barmode="stack",
    barnorm="percent",
).update_xaxes(categoryorder="total descending")
st.plotly_chart(fig)
# fig_shots = px.line(df_headshot_ts, x="date", y="count", color='name', line_shape="linear")
# st.plotly_chart(fig_shots)
