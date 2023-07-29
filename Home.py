import datetime as dt
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil import tz
from PIL import Image

from src.frontend import (
    calc_win_percentage,
    create_gsheets_database_connection,
    run_query,
)

st.set_page_config(page_title="Home")
conn = create_gsheets_database_connection()

image = Image.open(st.secrets["LOGO_FILE"])

col1, col2, col3 = st.columns([6, 6, 4])
with col1:
    st.write("")
with col2:
    st.image(image, width=120)
with col3:
    st.write("")

# Retrieve Data
sheet_url = st.secrets["private_gsheets_url_match"]
sheet_url_legacy = st.secrets["private_gsheets_url_match_legacy"]

rows = run_query(f'SELECT * FROM "{sheet_url}"', conn)
df_team_api = pd.DataFrame(rows)
df_team_api["date_compare"] = pd.to_datetime(df_team_api["date"]).dt.date

if sheet_url_legacy != "":
    rows_legacy = run_query(f'SELECT * FROM "{sheet_url_legacy}"', conn)
    df_team_legacy = pd.DataFrame(rows_legacy)
    df_team_legacy["date_compare"] = pd.to_datetime(df_team_legacy["date"]).dt.date
    df_team_all = pd.concat([df_team_api, df_team_legacy], axis=0)
else:
    df_team_all = df_team_api.copy()

df_team_all.date = pd.to_datetime(df_team_all.date)
sorted_df = df_team_all.sort_values(by="date")
min_date = sorted_df.date.iloc[0]
max_date = sorted_df.date.iloc[-1] + timedelta(days=1)

st.title(st.secrets["APP_TITLE"])
# st.slider('Select Date Range', min_value=min_date, max_value=max_date, )
date_col1, date_col2 = st.columns(2)
with date_col1:
    start_date = st.date_input("Start Date", max_date - timedelta(days=90))
with date_col2:
    end_date = st.date_input("End Date", max_date)
# convert to datetimes for comparison
start_date = datetime(start_date.year, start_date.month, start_date.day)
end_date = datetime(end_date.year, end_date.month, end_date.day)
