import os

import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta

from src.frontend import get_config
from src.frontend import (
    create_gsheets_database_connection,
    run_query,
    get_kds
)

conn = create_gsheets_database_connection()

st.title("Team Stats")

# Retrieve Data
dirname = os.path.dirname(__file__)
cfg = get_config(os.path.join("src", "config.yml"))
sheet_url_match = st.secrets["private_gsheets_url_match"]
sheet_url_player = st.secrets["private_gsheets_url_player"]
sheet_url_roster = st.secrets["private_gsheets_url_roster"]

with st.spinner('Retrieving Player and Match data...'):
    team_rows = run_query(f'SELECT * FROM "{sheet_url_match}"', conn)
    player_rows = run_query(f'SELECT * FROM "{sheet_url_player}"', conn)
    roster = run_query(f'SELECT * FROM "{sheet_url_roster}"', conn)

df_team = pd.DataFrame(team_rows)
df_player = pd.DataFrame(player_rows)
df_roster = pd.DataFrame(roster)

# Join players with roster and match data
df_player = df_player.merge(
    df_team.loc[:, ["match_id", "date", "map"]],
    on="match_id",
    how="left",
)

df_player = df_player.merge(
    df_roster,
    on=['name', 'tag', 'Riot_IDs'],
    how='left'
)

df_team_all = pd.DataFrame(team_rows)
df_team_all.date = pd.to_datetime(df_team_all.date)
sorted_df = df_team_all.sort_values(by="date")

min_date = sorted_df.date.iloc[0]
max_date = sorted_df.date.iloc[-1] + timedelta(days=1)

date_col1, date_col2 = st.columns(2)
with date_col1:
    start_date = st.date_input("Start Date", max_date - timedelta(days=90))
with date_col2:
    end_date = st.date_input("End Date", max_date)
# convert to datetimes for comparison
start_date = datetime(start_date.year, start_date.month, start_date.day)
end_date = datetime(end_date.year, end_date.month, end_date.day)

df_team = df_team_all.loc[
    (df_team_all.date >= start_date) & (df_team_all.date <= end_date), :
]

df_team = df_team.rename(columns={'team1': 'red_team', 'team2': 'blue_team'})
# st.write(f'Total Number of Games : {df_team.shape[0]}')

df_team["game_length"] = df_team["game_length"].astype("float")
df_team["rounds"] = df_team["rounds"].astype("int64")
df_team["source"] = "API"

avg_game_length = df_team.game_length.mean()
avg_rounds = df_team.rounds.mean()

def get_first_day_of_week(date):
    # Get the day of the week for the given date (Monday is 0, Sunday is 6)
    day_of_week = date.weekday()
    # Calculate the number of days to subtract to get the first day of the week (Monday)
    days_to_subtract = day_of_week
    first_day_of_week = date - timedelta(days=days_to_subtract)
    return first_day_of_week.date()


team_set = set(df_team.red_team.sort_values().unique()).union(set(df_team.blue_team.sort_values().unique()))
team = st.selectbox("Select Team", team_set)
team_select = df_team[(df_team.red_team == team) | (df_team.blue_team == team)]
team_select['week'] = team_select['date'].apply(get_first_day_of_week)
team_select['wins'] = team_select['winner'].apply(lambda t: 1 if t==team else 0)

st.header('Overall Summary')
metric_col1, metric_col2 = st.columns(2)
with metric_col1:
    st.metric('Average play time:', value=round(team_select.game_length.mean(), 2))

with metric_col2:
    st.metric('Wins %: ', value=round(team_select[team_select.winner == team].shape[0] / team_select.shape[0], 2))

st.header('Weekly Breakdown')
st.write(team_select.pivot_table(index='week', values=['game_length', 'rounds', 'wins'], aggfunc={'game_length':'mean', 'rounds':'mean', 'wins':'sum'}))

st.header("Average K/D by Map")
wavg_col = "Weight. Avg. K/D"
df_player_kd, kd_pivot = get_kds(df_player[df_player.team == team], wavg_col)
kd_pivot_map = df_player_kd.pivot_table(
    values="K/D", columns="map", index="name"
).fillna(0)
st.plotly_chart(px.imshow(kd_pivot_map.round(4), title="Average K/D by Map Viz", labels=dict(x="Map", y="Player", color="K/D"),))

# ['date', 'day_of_week', 'week', 'game_length', 'rounds', 'map', 'red_score', 'blue_score', 'red_team', 'blue_team', 'winner']

