import streamlit as st
from google.oauth2 import service_account
from gsheetsdb import connect
from langchain import ConversationChain, OpenAI
import numpy as np
import yaml
import json
import pdb

# Perform SQL query on the Google Sheet.
# Uses st.cache to only rerun when the query changes or after 10 min.
@st.cache(ttl=600)
@st.experimental_singleton
def run_query(query, _conn):
    rows = _conn.execute(query, headers=1)
    rows = rows.fetchall()
    return rows

def get_config(cfg_path):
    with open(cfg_path, "r") as stream:
        try:
            cfg = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return cfg


@st.cache(allow_output_mutation=True)
@st.experimental_singleton
def cache_convo(temp):
    """Create chatbot conversation object

    Parameters
    ----------
    temp : float, [0,1]
        temperature for chatgpt

    Returns
    -------
    ConversationChain
        conversation singleton
    """
    llm = OpenAI(temperature=temp)
    return ConversationChain(llm=llm, verbose=False)


def create_gsheets_database_connection():
    # Generate credentials object
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
            ],
        )
    except:
        # Expects a mapping, so parse to dict with json package
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(st.secrets["gcp_service_account"]),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
            ],
        )
    # Create a connection object.
    conn = connect(credentials=credentials)
    return conn


@st.cache
def calc_win_percentage(df, outcome_col):
    df = df.sort_values(by="date")
    outcome_list = df[outcome_col].to_list()

    win_perc = [1 if outcome_list[0] == "W" else 1]
    win_counter = sum(win_perc)
    total = 1
    for ind, outcome in enumerate(outcome_list[1:]):
        total += 1
        if outcome == "W":
            win_counter += 1
            win_perc.append(win_counter / total)
        else:
            win_perc.append(win_counter / total)
    return win_perc


def get_kds(df_player, wavg_col):
    # K/D calculations and pivot tabless
    df_player["K/D"] = df_player["kills"].astype(float) / df_player["deaths"].astype(float)
    agent_counts = df_player.groupby(["Riot_IDs", "agent", 'name', 'tag']).count().map.reset_index()
    agent_counts = agent_counts.rename(columns={"map": "weight"})
    df_player_kd = df_player.merge(agent_counts, on=["Riot_IDs", "agent", 'name', 'tag'])
    kd_weightavg = df_player_kd.groupby("Riot_IDs").apply(lambda x: np.average(x["K/D"], weights=x["weight"]))
    kd_weightavg = kd_weightavg.reset_index().rename(columns={0: wavg_col})
    kd_pivot = df_player_kd.pivot_table(values="K/D", columns="agent", index="Riot_IDs").fillna(0).reset_index()
    kd_pivot = kd_pivot.merge(kd_weightavg, on=["Riot_IDs"], how="inner").set_index("Riot_IDs")
    return df_player_kd, kd_pivot