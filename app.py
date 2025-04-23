
import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
from openpyxl import load_workbook

EXCEL_PATH = "行銷題庫總表.xlsx"
SHEET_NAME = "題庫總表"
WRONG_LOG = "錯題紀錄.csv"
EDIT_LOG = "修改紀錄.csv"
EDIT_PASSWORD = "quiz2024"

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

def log_edit(章節, 題號, 欄位, 原值, 新值):
    row = {
        "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "章節": 章節,
        "題號": 題號,
        "欄位": 欄位,
        "原值": 原值,
        "新值": 新值
    }
    new_row = pd.DataFrame([row])
    if os.path.exists(EDIT_LOG):
        df_old = pd.read_csv(EDIT_LOG)
        df_all = pd.concat([df_old, new_row], ignore_index=True)
    else:
        df_all = new_row
    df_all.to_csv(EDIT_LOG, index=False)

def update_excel(章節, 題號, updates):
    wb = load_workbook(EXCEL_PATH)
    ws = wb[SHEET_NAME]
    for row in ws.iter_rows(min_row=2):
        if str(row[0].value) == str(章節) and str(row[1].value) == str(題號):
            for col, key in zip([3,4,5,6,9], ["A","B","C","D","解析"]):
                old = str(row[col].value)
                new = updates[key]
                if old != new:
                    row[col].value = new
                    log_edit(章節, 題號, key, old, new)
            wb.save(EXCEL_PATH)
            return True
    return False

df = load_data()
chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}

st.title("📚 行銷測驗系統")
mode = st.sidebar.radio("選擇模式：", ["出題與作答", "編輯題庫"])

if mode == "編輯題庫":
    st.header("🔐 編輯題庫（需密碼）")
    password = st.text_input("請輸入密碼", type="password")
    if password == EDIT_PASSWORD:
        keyword = st.text_input("🔍 搜尋題目關鍵字")
        result = df[df["題目"].str.contains(keyword, na=False)] if keyword else df

        selected_row = st.selectbox("選擇要編輯的題目", result.apply(lambda x: f"{x['章節']} - {x['題號']}：{x['題目']}", axis=1))

        if selected_row:
            row_data = result[result.apply(lambda x: f"{x['章節']} - {x['題號']}：{x['題目']}", axis=1) == selected_row].iloc[0]
            st.markdown(f"### 題目：{row_data['題目']}")
            optA = st.text_input("選項 A", row_data["A"])
            optB = st.text_input("選項 B", row_data["B"])
            optC = st.text_input("選項 C", row_data["C"])
            optD = st.text_input("選項 D", row_data["D"])
            expl = st.text_area("解析", row_data["解析"])

            if st.button("✅ 更新題庫"):
                success = update_excel(row_data["章節"], row_data["題號"], {
                    "A": optA, "B": optB, "C": optC, "D": optD, "解析": expl
                })
                if success:
                    st.success("✅ 題庫已更新成功！")
                else:
                    st.error("❌ 更新失敗，請確認題號存在。")

        if os.path.exists(EDIT_LOG):
            st.subheader("🕓 最近修改紀錄")
            log = pd.read_csv(EDIT_LOG)
            st.dataframe(log.tail(5), use_container_width=True)

    elif password:
        st.error("❌ 密碼錯誤")

else:
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

    selected_chapters = st.sidebar.multiselect("選擇章節：", list(chapter_mapping.keys()), default=["CH1"])
    num_questions = st.sidebar.number_input("出題數量：", min_value=1, max_value=30, value=5)
    start_quiz = st.sidebar.button("🚀 開始出題")

    if start_quiz:
        st.session_state.quiz_started = True
        st.session_state.user_answers = []
        st.session_state.shuffled_options = {}
        st.session_state.show_result = False

        valid_sections = []
        for ch in selected_chapters:
            valid_sections.extend(chapter_mapping.get(ch, []))
        filtered_df = df[df["章節"].astype(str).isin(valid_sections)]

        if filtered_df.empty:
            st.error("❌ 找不到符合條件的題目")
            st.session_state.quiz_started = False
        else:
            st.session_state.questions = filtered_df.sample(
                n=min(num_questions, len(filtered_df))
            ).reset_index(drop=True)

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
