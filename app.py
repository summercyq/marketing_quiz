
import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
from openpyxl import load_workbook

EXCEL_PATH = "行銷題庫總表.xlsx"
SHEET_NAME = "題庫總表"
WRONG_LOG = "錯題紀錄.csv"

@st.cache_data
def load_data():
    return pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

def write_wrong_log(record):
    new_row = pd.DataFrame([record])
    if os.path.exists(WRONG_LOG):
        df_old = pd.read_csv(WRONG_LOG)
        df_all = pd.concat([df_old, new_row], ignore_index=True)
    else:
        df_all = new_row
    df_all.to_csv(WRONG_LOG, index=False)

df = load_data()
chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}

st.title("📚 行銷測驗系統")

mode = st.sidebar.radio("選擇模式", ["一般出題模式", "錯題再練模式"])

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

with st.sidebar:
    username = st.text_input("請輸入你的姓名（作為錯題紀錄）", key="username")
    num_questions = st.number_input("出題數量：", min_value=1, max_value=50, value=5)
    start_quiz = st.button("🚀 開始出題")

if start_quiz and username.strip():
    st.session_state.quiz_started = True
    st.session_state.user_answers = []
    st.session_state.shuffled_options = {}
    st.session_state.show_result = False

    if mode == "一般出題模式":
        selected_chapters = st.multiselect("選擇章節：", list(chapter_mapping.keys()), default=["CH1"])
        valid_sections = []
        for ch in selected_chapters:
            valid_sections.extend(chapter_mapping.get(ch, []))
        filtered_df = df[df["章節"].astype(str).isin(valid_sections)]
    else:
        if not os.path.exists(WRONG_LOG):
            st.error("❌ 尚未有錯題紀錄，請先使用一般模式作答")
            filtered_df = pd.DataFrame()
        else:
            wrong_df = pd.read_csv(WRONG_LOG)
            filtered_df = df.merge(wrong_df[["章節", "題號"]].drop_duplicates(), on=["章節", "題號"])

    if filtered_df.empty:
        st.error("❌ 找不到符合條件的題目")
        st.session_state.quiz_started = False
    else:
        st.session_state.questions = filtered_df.sample(
            n=min(num_questions, len(filtered_df))
        ).reset_index(drop=True)
elif start_quiz and not username.strip():
    st.error("❗ 請輸入使用者名稱後再開始作答")

if st.session_state.quiz_started and st.session_state.questions is not None:
    st.subheader("📝 開始作答")
    for i, row in st.session_state.questions.iterrows():
        with st.expander(f"Q{i+1}. {row['題目']}", expanded=True):
            options = [row['A'], row['B'], row['C'], row['D']]
            labels = ['A', 'B', 'C', 'D']
            if f"q{i}_options" not in st.session_state.shuffled_options:
                shuffled = list(zip(labels, options))
                random.shuffle(shuffled)
                st.session_state.shuffled_options[f"q{i}_options"] = shuffled
            else:
                shuffled = st.session_state.shuffled_options[f"q{i}_options"]

            option_dict = {opt: label for label, opt in shuffled}
            selected = st.radio("選項：", options=[opt for _, opt in shuffled], key=f"q{i}")

            if len(st.session_state.user_answers) <= i:
                st.session_state.user_answers.append({
                    "使用者": username,
                    "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "正確答案": row['解答'],
                    "解析": row['解析'],
                    "使用者答案": option_dict.get(selected),
                    "章節": row['章節'],
                    "題號": row['題號'],
                    "題目": row['題目']
                })
            else:
                st.session_state.user_answers[i]["使用者答案"] = option_dict.get(selected)

            if st.session_state.show_result:
                ans = st.session_state.user_answers[i]
                is_correct = ans['使用者答案'] == ans['正確答案']
                if not is_correct:
                    write_wrong_log(ans)
                st.markdown(f"- 你的答案：`{ans['使用者答案']}`")
                if not is_correct:
                    st.markdown(f"- ❌ 正解為：`{ans['正確答案']}`")
                    st.markdown(f"- 📘 解析：{ans['解析']}")
                else:
                    st.markdown("✅ 答對！")

    if st.button("✅ 送出並評分"):
        st.session_state.show_result = True
