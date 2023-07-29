import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil import tz
from datetime import datetime, timedelta

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
# sheet_url_legacy = st.secrets["private_gsheets_url_match_legacy"]

team_rows = run_query(f'SELECT * FROM "{sheet_url_match}"', conn)
# team_rows_legacy = run_query(f'SELECT * FROM "{sheet_url_legacy}"', conn)

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
st.write(f'Total Number of Games : {df_team.shape[0]}')

df_team["game_length"] = df_team["game_length"].astype("float")
df_team["rounds"] = df_team["rounds"].astype("int64")
df_team["source"] = "API"

# df_team["team_score"] = df_team.apply(
#     lambda row: row["red_score"] if row["home_team"] == "Red" else row["blue_score"],
#     axis=1,
# )
# df_team["opponent_score"] = df_team.apply(
#     lambda row: row["red_score"] if row["home_team"] == "Blue" else row["blue_score"],
#     axis=1,
# )
# fig_op = px.scatter(win_loss, x='Win', y='Loss', color='opponent', title='W/L Breakdown by Opponent')
# st.plotly_chart(fig_op)
# df_team["team_score"] = df_team["team_score"].astype("int64")
# df_team["opponent_score"] = df_team["opponent_score"].astype("int64")

# df_team = pd.concat([df_team_legacy, df_team], axis=0)

avg_game_length = df_team.game_length.mean()
avg_rounds = df_team.rounds.mean()

team_set = set(df_team.red_team.sort_values().unique()).union(set(df_team.blue_team.sort_values().unique()))
team = st.selectbox("Select Team", team_set)
team_select = df_team[(df_team.red_team == team) | (df_team.blue_team == team)]
st.write(team_select.loc[:, ['date', 'day_of_week', 'game_length', 'rounds', 'map', 'red_score', 'blue_score', 'red_team', 'blue_team', 'winner']])

metric_col1, metric_col2 = st.columns(2)
with metric_col1:
    st.metric('Average play time:', value=round(team_select.game_length.mean(), 2))

with metric_col2:
    st.metric('Wins %: ', value=round(team_select[team_select.winner == team].shape[0] / team_select.shape[0], 2))
