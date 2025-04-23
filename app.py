
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

mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式", "編輯題庫"])

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

if mode == "編輯題庫":
    password = st.text_input("🔐 請輸入密碼以進入題庫編輯模式", type="password")
    if password == EDIT_PASSWORD:
        keyword = st.text_input("🔎 搜尋題目關鍵字")
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
                st.success("✅ 題庫已更新成功！" if success else "❌ 更新失敗，請確認題號存在。")

        if os.path.exists(EDIT_LOG):
            st.subheader("🕓 最近修改紀錄")
            log = pd.read_csv(EDIT_LOG)
            st.dataframe(log.tail(10), use_container_width=True)
    elif password:
        st.error("❌ 密碼錯誤")

else:
    with st.sidebar:
        username = st.text_input("🧑 請輸入你的姓名", key="username")
        selected_chapters = st.multiselect("選擇章節", list(chapter_mapping.keys()), default=["CH1"])
        num_questions = st.number_input("出題數量", min_value=1, max_value=50, value=5)
        start_quiz = st.button("🚀 開始出題")

    if start_quiz and username.strip():
        st.session_state.quiz_started = True
        st.session_state.user_answers = []
        st.session_state.shuffled_options = {}
        st.session_state.show_result = False

        if mode == "一般出題模式":
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
            st.session_state.questions = filtered_df.sample(n=min(num_questions, len(filtered_df))).reset_index(drop=True)
    elif start_quiz and not username.strip():
        st.error("❗ 請輸入使用者名稱後再開始作答")

    if st.session_state.quiz_started and st.session_state.questions is not None:
        st.subheader("📝 開始作答")
        if st.button("✅ 送出並評分"):
            st.session_state.show_result = True

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
                selected = st.radio("選項：", options=[opt for _, opt in shuffled], key=f"q{i}", disabled=st.session_state.show_result)

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
                    correct_label = ans['正確答案']
                    for label, opt in shuffled:
                        style = ""
                        if st.session_state.show_result:
                            if is_correct and label == correct_label:
                                style = "color:green;font-weight:bold;"
                            elif not is_correct:
                                if label == correct_label:
                                    style = "color:green;font-weight:bold;"
                                elif label == ans['使用者答案']:
                                    style = "color:red;font-weight:bold;"
                        st.markdown(f"<div style='{style}'>{label}. {opt}</div>", unsafe_allow_html=True)
                    if not is_correct:
                        write_wrong_log(ans)
                        st.markdown(f"<div style='margin-top:10px;'><strong>解析：</strong>第{ans['章節']}章題號{ans['題號']}：{ans['解析']}</div>", unsafe_allow_html=True)
