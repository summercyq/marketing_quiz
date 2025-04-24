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
                selected = st.radio("選項：", [opt for _, opt in zipped], key=f"q{i}")
                user_ans_label = opt_to_label[selected]
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

            if st.session_state.show_result:
                for label, opt in st.session_state.user_answers[i]["選項配對"]:
                    if user_ans_label == correct_label and label == correct_label:
                        style = "color:green;font-weight:bold;"
                    elif user_ans_label != correct_label:
                        if label == correct_label:
                            style = "color:green;font-weight:bold;"
                        elif label == user_ans_label:
                            style = "color:red;font-weight:bold;text-decoration:line-through;"
                        else:
                            style = ""
                    else:
                        style = ""
                    st.markdown(f"<div style='{style}'>{label}. {opt}</div>", unsafe_allow_html=True)
                if user_ans_label != correct_label:
                    st.markdown(f"解析：第{row['章節']}章題號{row['題號']}：{row['解析']}")

    if not st.session_state.show_result:
        if st.button("✅ 送出並評分"):
            st.session_state.show_result = True
    else:
        total = len(st.session_state.questions)
        correct = sum(1 for ans in st.session_state.user_answers if ans["使用者答案"] == ans["正確答案"])
        st.markdown(f"### 🎯 共 {total} 題，答對 {correct} 題")
        if st.button("🔄 重新出題"):
            st.session_state.quiz_started = False
            st.session_state.questions = None
            st.session_state.user_answers = []
            st.session_state.shuffled_options = {}
            st.session_state.show_result = False

# 管理者登入功能
with st.sidebar.expander("🔐 管理者登入"):
    pwd = st.text_input("輸入密碼：", type="password")
    if pwd == EDIT_PASSWORD:
        tool = st.radio("管理功能", ["編輯題庫", "清除錯題紀錄", "下載紀錄"])
        if tool == "清除錯題紀錄":
            mode = st.radio("選擇清除方式：", ["全部使用者", "指定使用者"])
            if mode == "全部使用者" and st.button("🧨 清除全部"):
                if os.path.exists(WRONG_LOG): os.remove(WRONG_LOG)
                st.success("✅ 錯題紀錄已全部清除")
            elif mode == "指定使用者":
                target = st.text_input("輸入使用者名稱")
                if st.button("清除該使用者"):
                    if os.path.exists(WRONG_LOG):
                        log = pd.read_csv(WRONG_LOG)
                        log = log[log["使用者"].str.lower() != target.lower()]
                        log.to_csv(WRONG_LOG, index=False)
                        st.success("✅ 已清除")

        elif tool == "下載紀錄":
            if os.path.exists(WRONG_LOG):
                with open(WRONG_LOG, "rb") as f:
                    st.download_button("下載錯題紀錄", f, file_name="錯題紀錄.csv")
            if os.path.exists(STATS_LOG):
                with open(STATS_LOG, "rb") as f:
                    st.download_button("下載答題統計", f, file_name="答題統計.csv")

        elif tool == "編輯題庫":
            keyword = st.text_input("輸入題目關鍵字搜尋")
            df_edit = df[df["題目"].str.contains(keyword, na=False)] if keyword else df
            if not df_edit.empty:
                selected = st.selectbox("選擇題目：", df_edit["題目"])
                row = df_edit[df_edit["題目"] == selected].iloc[0]
                a = st.text_input("選項 A", row["A"])
                b = st.text_input("選項 B", row["B"])
                c = st.text_input("選項 C", row["C"])
                d = st.text_input("選項 D", row["D"])
                expl = st.text_area("解析", row["解析"])
                if st.button("✅ 更新題庫"):
                    wb = load_workbook(EXCEL_PATH)
                    ws = wb[SHEET_NAME]
                    for r in ws.iter_rows(min_row=2):
                        if str(r[0].value) == str(row["章節"]) and str(r[1].value) == str(row["題號"]):
                            r[3].value, r[4].value, r[5].value, r[6].value = a, b, c, d
                            r[9].value = expl
                            break
                    wb.save(EXCEL_PATH)
                    st.success("題目已更新成功")
    elif pwd:
        st.error("❌ 密碼錯誤")
