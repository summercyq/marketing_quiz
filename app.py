
import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
from openpyxl import load_workbook

st.set_page_config(page_title="TIMS行銷專業能力認證 2025(初級)題庫", layout="wide")
st.title("TIMS行銷專業能力認證 2025(初級)題庫")

EXCEL_PATH = "行銷題庫總表.xlsx"
SHEET_NAME = "題庫總表"
WRONG_LOG = "錯題紀錄.csv"
STATS_LOG = "答題統計.csv"
EDIT_PASSWORD = "quiz2024"

@st.cache_data
def load_data():
    return pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

df = load_data()
chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}

# 初始化狀態
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "questions" not in st.session_state:
    st.session_state.questions = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = []
if "shuffled_options" not in st.session_state:
    st.session_state.shuffled_options = {}
if "show_result" not in st.session_state:
    st.session_state.show_result = False

def update_stats(user, chapter, qid):
    if os.path.exists(STATS_LOG):
        stats_df = pd.read_csv(STATS_LOG)
    else:
        stats_df = pd.DataFrame(columns=["使用者", "章節", "題號", "次數"])
    match = (stats_df["使用者"] == user) & (stats_df["章節"] == chapter) & (stats_df["題號"] == qid)
    if match.any():
        stats_df.loc[match, "次數"] += 1
    else:
        stats_df = pd.concat([stats_df, pd.DataFrame([{"使用者": user, "章節": chapter, "題號": qid, "次數": 1}])], ignore_index=True)
    stats_df.to_csv(STATS_LOG, index=False)

def log_wrong(user, chapter, qid, question):
    if os.path.exists(WRONG_LOG):
        log_df = pd.read_csv(WRONG_LOG)
    else:
        log_df = pd.DataFrame(columns=["使用者", "章節", "題號", "題目"])
    new_row = pd.DataFrame([{"使用者": user, "章節": chapter, "題號": qid, "題目": question}])
    log_df = pd.concat([log_df, new_row], ignore_index=True)
    log_df.to_csv(WRONG_LOG, index=False)
