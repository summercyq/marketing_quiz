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

# 初始化 session state
for key in ["quiz_started", "questions", "user_answers", "shuffled_options", "show_result"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "quiz_started" else [] if key.endswith("s") else None

# Sidebar 使用者與出題模式設定
st.sidebar.header("使用者與模式設定")
st.session_state.username = st.sidebar.text_input("請輸入使用者名稱", value=st.session_state.get("username", ""))
mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式"])
selected_chapters = st.sidebar.multiselect("選擇章節：", list(chapter_mapping.keys()), default=["CH1"])
num_questions = st.sidebar.number_input("出題數量", min_value=1, max_value=50, value=5)

if st.sidebar.button("🚀 開始出題") and st.session_state.username.strip():
    st.session_state.quiz_started = True
    st.session_state.user_answers = []
    st.session_state.shuffled_options = {}
    st.session_state.show_result = False

    if mode == "一般出題模式":
        sections = [s for ch in selected_chapters for s in chapter_mapping[ch]]
        filtered = df[df["章節"].astype(str).isin(sections)]
    else:
        if os.path.exists(WRONG_LOG):
            log = pd.read_csv(WRONG_LOG)
            filtered = df.merge(log[log["使用者"].str.lower() == st.session_state.username.lower()][["章節", "題號"]], on=["章節", "題號"])
        else:
            filtered = pd.DataFrame()

    if not filtered.empty:
        st.session_state.questions = filtered.sample(n=min(num_questions, len(filtered))).reset_index(drop=True)
    else:
        st.session_state.quiz_started = False
        st.error("找不到符合條件的題目")

# 出題與作答畫面
if st.session_state.quiz_started and st.session_state.questions is not None:
    st.markdown("---")
    for i, row in st.session_state.questions.iterrows():
        with st.expander(f"Q{i+1}. {row['題目']}", expanded=True):
            options = [row['A'], row['B'], row['C'], row['D']]
            labels = ['A', 'B', 'C', 'D']
            zipped = list(zip(labels, options))
            if f"q{i}_options" not in st.session_state.shuffled_options:
                random.shuffle(zipped)
                st.session_state.shuffled_options[f"q{i}_options"] = zipped
            else:
                zipped = st.session_state.shuffled_options[f"q{i}_options"]

            label_to_opt = {label: opt for label, opt in zipped}
            opt_to_label = {opt: label for label, opt in zipped}
            correct_label = row["解答"]
            correct_text = row[correct_label]

            if not st.session_state.show_result:
                selected = st.radio("選項：", [opt for _, opt in zipped], key=f"q{i}", index=None)
                if selected is not None:
                    user_ans_label = opt_to_label.get(selected, "")
                else:
                    user_ans_label = ""
            else:
                ans = st.session_state.user_answers[i]
                user_ans_label = ans["使用者答案"]
                selected = ans["使用者內容"]

            if len(st.session_state.user_answers) <= i:
                st.session_state.user_answers.append({
                    "使用者": st.session_state.username,
                    "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "正確答案": correct_label,
                    "正確內容": correct_text,
                    "使用者答案": user_ans_label,
                    "使用者內容": selected,
                    "章節": row["章節"],
                    "題號": row["題號"],
                    "解析": row["解析"],
                    "選項配對": zipped
                })
            else:
                st.session_state.user_answers[i]["使用者答案"] = user_ans_label
                st.session_state.user_answers[i]["使用者內容"] = selected

    if not st.session_state.show_result:
        if st.button("✅ 送出並評分"):
            st.session_state.show_result = True

            # 寫入錯題與答題統計紀錄
            wrong_records = []
            stat_records = []
            for ans in st.session_state.user_answers:
                stat_records.append({
                    "使用者": ans["使用者"],
                    "章節": ans["章節"],
                    "題號": ans["題號"],
                    "時間": ans["時間"]
                })
                if ans["使用者內容"] != ans["正確內容"]:
                    wrong_records.append({
                        "使用者": ans["使用者"],
                        "章節": ans["章節"],
                        "題號": ans["題號"],
                        "題目": ans["使用者內容"]
                    })

            if wrong_records:
                df_wrong = pd.DataFrame(wrong_records)
                if os.path.exists(WRONG_LOG):
                    old_wrong = pd.read_csv(WRONG_LOG)
                    df_wrong = pd.concat([old_wrong, df_wrong], ignore_index=True)
                    df_wrong.drop_duplicates(subset=["使用者", "章節", "題號"], inplace=True)
                df_wrong.to_csv(WRONG_LOG, index=False)

            df_stat = pd.DataFrame(stat_records)
            if os.path.exists(STATS_LOG):
                old_stat = pd.read_csv(STATS_LOG)
                df_stat = pd.concat([old_stat, df_stat], ignore_index=True)
            df_stat.to_csv(STATS_LOG, index=False)

    if st.session_state.show_result:
        total = len(st.session_state.questions)
        correct = 0

        for i, ans in enumerate(st.session_state.user_answers):
            q = st.session_state.questions.iloc[i]
            st.markdown(f"**Q{i+1}. {q['題目']}**")

            for label, opt in ans["選項配對"]:
                is_user_selected = opt == ans["使用者內容"]
                is_correct = opt == ans["正確內容"]

                style = ""
                if is_user_selected and is_correct:
                    style = "color:green;font-weight:bold;"
                elif is_user_selected and not is_correct:
                    style = "color:red;font-weight:bold;text-decoration:line-through;"
                elif not is_user_selected and is_correct:
                    style = "color:green;font-weight:bold;"

                st.markdown(f"<div style='{style}'>{label}. {opt}</div>", unsafe_allow_html=True)

            if ans["使用者內容"] == ans["正確內容"]:
                correct += 1
            else:
                st.markdown(f"解析：第{ans['章節']}章題號{ans['題號']}：{ans['解析']}")

        st.markdown(f"### 🎯 共 {total} 題，答對 {correct} 題")
        if st.button("🔄 重新出題"):
            st.session_state.quiz_started = False
            st.session_state.questions = None
            st.session_state.user_answers = []
            st.session_state.shuffled_options = {}
            st.session_state.show_result = False
