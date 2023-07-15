import streamlit as st
from google.oauth2 import service_account
from gsheetsdb import connect
from langchain import ConversationChain, OpenAI
import yaml
import json


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
