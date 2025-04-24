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

# 使用者設定介面
with st.sidebar:
    username = st.text_input("請輸入使用者名稱")
    selected_chapters = st.multiselect("選擇章節", list(chapter_mapping.keys()), default=["CH1"])
    question_count = st.number_input("出題數量", min_value=1, max_value=50, value=5)
    if st.button("開始出題"):
        valid_tags = [t for ch in selected_chapters for t in chapter_mapping[ch]]
        pool = df[df["章節"].astype(str).isin(valid_tags)].sample(n=min(question_count, len(df)))
        st.session_state.questions = pool.reset_index(drop=True)
        st.session_state.user_answers = []
        st.session_state.shuffled_options = {}
        st.session_state.show_result = False
        st.session_state.quiz_started = True

if st.session_state.quiz_started and st.session_state.questions is not None:
    for i, row in st.session_state.questions.iterrows():
        with st.expander(f"Q{i+1}. {row['題目']}", expanded=True):
            options = [row["A"], row["B"], row["C"], row["D"]]
            labels = ['A', 'B', 'C', 'D']
            zipped = list(zip(labels, options))

            if f"q{i}_options" not in st.session_state.shuffled_options:
                random.shuffle(zipped)
                st.session_state.shuffled_options[f"q{i}_options"] = zipped
            else:
                zipped = st.session_state.shuffled_options[f"q{i}_options"]

            label_to_option = {label: opt for label, opt in zipped}
            option_to_label = {opt: label for label, opt in zipped}
            correct_label = row["解答"]
            correct_text = row[correct_label]

            if not st.session_state.show_result:
                selected = st.radio("選項：", options=[opt for _, opt in zipped], key=f"q{i}")
                user_ans_label = option_to_label[selected]
            else:
                selected = st.session_state.user_answers[i]["使用者內容"]
                user_ans_label = st.session_state.user_answers[i]["使用者答案"]

            if len(st.session_state.user_answers) <= i:
                st.session_state.user_answers.append({
                    "使用者": username,
                    "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "章節": row["章節"],
                    "題號": row["題號"],
                    "正確答案": correct_label,
                    "正確內容": correct_text,
                    "使用者答案": user_ans_label,
                    "使用者內容": selected,
                    "解析": row["解析"],
                    "選項配對": zipped
                })

            if st.session_state.show_result:
                ans = st.session_state.user_answers[i]
                for label, opt in ans["選項配對"]:
                    if ans["使用者答案"] == ans["正確答案"] and label == ans["正確答案"]:
                        style = "color:green;font-weight:bold;"
                    elif ans["使用者答案"] != ans["正確答案"]:
                        if label == ans["正確答案"]:
                            style = "color:green;font-weight:bold;"
                        elif label == ans["使用者答案"]:
                            style = "color:red;text-decoration:line-through;"
                        else:
                            style = ""
                    else:
                        style = ""
                    st.markdown(f"<div style='{style}'>{label}. {opt}</div>", unsafe_allow_html=True)

                if ans["使用者答案"] != ans["正確答案"]:
                    st.markdown(f"<div style='margin-top:10px;'>解析：第{ans['章節']}章題號{ans['題號']}：{ans['解析']}</div>", unsafe_allow_html=True)

    if not st.session_state.show_result:
        if st.button("✅ 送出並評分"):
            st.session_state.show_result = True
    else:
        correct = sum(1 for ans in st.session_state.user_answers if ans["使用者答案"] == ans["正確答案"])
        total = len(st.session_state.questions)
        st.markdown(f"### 🎯 共 {total} 題，答對 {correct} 題")
        if st.button("🔁 重新出題"):
            st.session_state.quiz_started = False
            st.session_state.questions = None
            st.session_state.user_answers = []
            st.session_state.shuffled_options = {}
            st.session_state.show_result = False