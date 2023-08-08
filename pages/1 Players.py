import os
from datetime import datetime, timedelta

import numpy as np
import pdb
import pandas as pd
import plotly.express as px
import streamlit as st

from src.frontend import get_config, get_kds
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
    on=['Riot_IDs', 'name', 'tag'],
    how='left'
)

df_player = df_player[~df_player['Riot_IDs'].isin(cfg["retired_players"])]

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

df_player.loc[:, cfg["integer_columns"]] = df_player.loc[
    :, cfg["integer_columns"]
].fillna(0)
df_player.loc[:, cfg["float_columns"]] = df_player.loc[:, cfg["float_columns"]].fillna(
    0
)
df_player = df_player.astype(int_cols)
df_player = df_player.astype(float_cols)

# Calculate z-scores
df_player['KDA'] = (df_player['kills'] + df_player['assists']) / df_player['deaths']

st.header("General Player Statistics")

df_c = (
    df_player.loc[:, ["Riot_IDs", "clutch_wins", "clutch_counts"]]
    .fillna(0)
    .groupby("Riot_IDs")
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
        ["Riot_IDs"] + general_cols,
    ]
    .groupby("Riot_IDs")
    .sum()
    .rename(columns={"first_bloods": "first bloods"})
)
pivot_acs = (
    df_player.loc[:, ["Riot_IDs", "acs"]]
    .groupby("Riot_IDs")
    .mean()
    .rename(columns={"acs": "avg. acs"})
)
pivot_general = pd.merge(pivot_general, pivot_acs, left_index=True, right_index=True)
pivot_general = pd.merge(
    pivot_general,
    df_c.set_index("Riot_IDs").loc[:, "clutch_percent"],
    left_index=True,
    right_index=True,
)
match_counts = (
    df_player.groupby(["Riot_IDs"])
    .count()
    .agent.reset_index()
    .rename(columns={"agent": "match counts"})
    .set_index("Riot_IDs")
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
]
# pivot_general.columns=['kills', 'deaths', 'assists', 'first_bloods', 'eco_score', 'acs']

kill_pivot_agent = (
    df_player.pivot_table(values="kills", columns="agent", index="Riot_IDs", aggfunc="sum")
    .fillna(0)
    .astype("int64")
)
kill_pivot_agent["Total"] = kill_pivot_agent.apply(lambda row: sum(row), axis=1)

st.header("Average K/D by Agent")

wavg_col = "Weight. Avg. K/D"
df_player_kd, kd_pivot = get_kds(df_player, wavg_col)
# Change order of columns
new_cols = list(kd_pivot.columns)
new_cols.reverse()
kd_pivot = kd_pivot.loc[:, new_cols]
st.write(kd_pivot.sort_values(by=wavg_col, ascending=False).round(4))
st.write(
    "Note: Weighted Average K/D controls for the amount of times a player plays as a certain agent"
)

# Calculate Ranks
teams = df_player_kd.team.unique()
team_rank_list = []
for team in teams:
    df_filter = df_player_kd[df_player_kd.team == team]
    team_perc_ranks = df_filter.groupby('Riot_IDs').mean(numeric_only=True)['K/D'].rank(pct=True).round(2).reset_index().rename(columns={'K/D':'Team Rank'})
    team_rank_list.append(team_perc_ranks)
df_player_team_perc = pd.concat(team_rank_list)
# Calculate percentile scores for each player across the entire dataset
df_player_global_perc = df_player_kd.groupby('Riot_IDs').mean(numeric_only=True)['K/D'].rank(pct=True).round(2).reset_index().rename(columns={'K/D':'Global Rank'})
df_ranks = df_player_team_perc.merge(df_player_global_perc, on=['Riot_IDs'])
st.header("Average K/D by Map")
kd_pivot_map = df_player_kd.pivot_table(
    values="K/D", columns="map", index="Riot_IDs"
).fillna(0)
st.write(kd_pivot_map.round(4))
# st.plotly_chart(px.imshow(kd_pivot_map.round(4), title="Average K/D by Map Viz"))

st.header('Individual Statistics')
player_list = list(df_player['Riot_IDs'].unique())
player_list.extend(['All'])
player_select = st.selectbox(label='Select Player', options=player_list)

if player_select == 'All':
    st.write(pivot_general.loc[:, display_cols].sort_values(by="kills", ascending=False))
else:
    disp_pivot = pivot_general.loc[pivot_general.index==player_select, display_cols].\
        sort_values(by="kills", ascending=False).merge(df_ranks.loc[:, ['Riot_IDs', 'Global Rank', 'Team Rank']], on='Riot_IDs', how='left')
    st.write(disp_pivot)
st.header("Shooting Breakdown")
df_headshot_ts = df_player.loc[
    df_player['Riot_IDs'] == player_select, ["Riot_IDs", "date", "bodyshots", "legshots", "headshots"]
].dropna()
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
    x="Riot_IDs",
    y=["legshots", "bodyshots", "headshots"],
    barmode="stack",
    barnorm="percent",
).update_xaxes(categoryorder="total descending")
st.plotly_chart(fig)
# fig_shots = px.line(df_headshot_ts, x="date", y="count", color='Riot_IDs', line_shape="linear")
# st.plotly_chart(fig_shots)
