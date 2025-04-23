
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


mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式", "題庫編輯"])

if mode == "題庫編輯":
    password = st.text_input("🔐 請輸入密碼進入編輯模式", type="password")
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
                from openpyxl import load_workbook
                wb = load_workbook(EXCEL_PATH)
                ws = wb[SHEET_NAME]
                for row in ws.iter_rows(min_row=2):
                    if str(row[0].value) == str(row_data["章節"]) and str(row[1].value) == str(row_data["題號"]):
                        row[3].value, row[4].value = optA, optB
                        row[5].value, row[6].value = optC, optD
                        row[9].value = expl
                        break
                wb.save(EXCEL_PATH)
                st.success("題目已更新成功")
    elif password:
        st.error("❌ 密碼錯誤")

else:
    with st.sidebar:
        username = st.text_input("請輸入使用者名稱")
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

        elif mode == "錯題再練模式":
            if os.path.exists(WRONG_LOG):
                wrong_df = pd.read_csv(WRONG_LOG)
                wrong_df["使用者"] = wrong_df["使用者"].astype(str).str.strip().str.lower()
                username_lower = username.strip().lower()
                matched = wrong_df[wrong_df["使用者"] == username_lower]
                if len(matched) == 0:
                    st.warning("⚠️ 此使用者目前尚無錯題紀錄")
                    filtered_df = pd.DataFrame()
                else:
                    st.info(f"✅ 找到 {len(matched)} 筆與使用者 `{username}` 相關的錯題")
                    matched["章節"] = matched["章節"].astype(str)
                    matched["題號"] = matched["題號"].astype(str)
                    df["章節"] = df["章節"].astype(str)
                    df["題號"] = df["題號"].astype(str)
                    filtered_df = df.merge(matched[["章節", "題號"]].drop_duplicates(), on=["章節", "題號"])
                    st.success(f"🎯 成功比對到 {len(filtered_df)} 題可以再練")
            else:
                st.error("❌ 尚未有任何錯題紀錄")
                filtered_df = pd.DataFrame()

        if not filtered_df.empty:
            st.session_state.questions = filtered_df.sample(n=min(num_questions, len(filtered_df))).reset_index(drop=True)
        else:
            st.error("❌ 找不到符合條件的題目")
            st.session_state.quiz_started = False


    if st.session_state.quiz_started and st.session_state.questions is not None:
        if st.session_state.show_result:
            total = len(st.session_state.questions)
            correct = sum(1 for ans in st.session_state.user_answers if ans["使用者答案"] == ans["正確答案"])
            st.markdown(f"### 📊 總共 {total} 題，答對 {correct} 題")

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

                label_to_option = {label: opt for label, opt in zipped}
                option_to_label = {opt: label for label, opt in zipped}
                correct_label = row["解答"]
                correct_text = row[correct_label]

                if not st.session_state.show_result:
                    selected = st.radio("選項：", options=[opt for _, opt in zipped], key=f"q{i}")
                    user_ans_label = option_to_label.get(selected)
                else:
                    user_ans_label = st.session_state.user_answers[i]["使用者答案"]
                    selected = st.session_state.user_answers[i]["使用者內容"]

                if len(st.session_state.user_answers) <= i:
                    st.session_state.user_answers.append({
                        "使用者": username,
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
                    update_stats(username, row["章節"], row["題號"])
                else:
                    st.session_state.user_answers[i]["使用者答案"] = user_ans_label
                    st.session_state.user_answers[i]["使用者內容"] = selected

                if st.session_state.show_result:
                    ans = st.session_state.user_answers[i]
                    for label, opt in ans["選項配對"]:
                        if ans["使用者答案"] == ans["正確答案"] and label == ans["正確答案"]:
                            style = "color:green;font-weight:bold;"
                        elif ans["使用者答案"] != ans["正確答案"]:
                            if label == ans["正確答案"]:
                                style = "color:green;font-weight:bold;"
                            elif label == ans["使用者答案"]:
                                style = "color:red;font-weight:bold;"
                            else:
                                style = ""
                        else:
                            style = ""
                        st.markdown(f"<div style='{style}'>{label}. {opt}</div>", unsafe_allow_html=True)
                    if ans["使用者答案"] != ans["正確答案"]:
                        log_wrong(ans["使用者"], ans["章節"], ans["題號"], row["題目"])
                        st.markdown(f"<div style='margin-top:10px;'>解析：第{ans['章節']}章題號{ans['題號']}：{ans['解析']}</div>", unsafe_allow_html=True)

        if not st.session_state.show_result:
            if st.button("✅ 送出並評分", key="submit_final"):
                st.session_state.show_result = True
        else:
            if st.button("🔄 重新出題", key="restart"):
                st.session_state.quiz_started = False
                st.session_state.questions = None
                st.session_state.user_answers = []
                st.session_state.shuffled_options = {}
                st.session_state.show_result = False
