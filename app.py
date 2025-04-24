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

# Sidebar - 使用者資訊與模式
st.sidebar.header("使用者與出題設定")
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

# 出題畫面
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
                user_ans_label = opt_to_label[selected] if selected else ""
            else:
                ans = st.session_state.user_answers[i]
                selected = ans["使用者內容"]
                user_ans_label = ans["使用者答案"]

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

    if not st.session_state.show_result:
        if st.button("✅ 送出並評分"):
            st.session_state.show_result = True

            wrong_records, stat_records = [], []
            for ans in st.session_state.user_answers:
                stat_records.append({"使用者": ans["使用者"], "章節": ans["章節"], "題號": ans["題號"], "時間": ans["時間"]})
                if ans["使用者內容"] != ans["正確內容"]:
                    wrong_records.append({"使用者": ans["使用者"], "章節": ans["章節"], "題號": ans["題號"], "題目": ans["使用者內容"]})

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
        correct = sum(1 for ans in st.session_state.user_answers if ans["使用者內容"] == ans["正確內容"])
        st.markdown(f"### 🎯 共 {total} 題，答對 {correct} 題")

        for i, ans in enumerate(st.session_state.user_answers):
            st.markdown(f"**Q{i+1}. {ans['正確內容']}**")
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

            if ans["使用者內容"] != ans["正確內容"]:
                st.markdown(f"解析：第{ans['章節']}章題號{ans['題號']}：{ans['解析']}")

        if st.button("🔄 重新出題"):
            st.session_state.quiz_started = False
            st.session_state.questions = None
            st.session_state.user_answers = []
            st.session_state.shuffled_options = {}
            st.session_state.show_result = False

# 管理功能
with st.sidebar.expander("🛠️ 管理者登入"):
    password = st.text_input("請輸入管理密碼", type="password")
    if password == EDIT_PASSWORD:
        admin_tab = st.radio("選擇管理功能：", ["題庫編輯", "錯題紀錄管理", "下載紀錄"])

        if admin_tab == "題庫編輯":
            keyword = st.text_input("🔍 輸入關鍵字搜尋題目")
            results = df[df["題目"].str.contains(keyword, na=False)] if keyword else df
            selected = st.selectbox("選擇題目：", results.apply(lambda x: f"{x['章節']} - {x['題號']}：{x['題目']}", axis=1))
            if selected:
                row_data = results[results.apply(lambda x: f"{x['章節']} - {x['題號']}：{x['題目']}", axis=1) == selected].iloc[0]
                optA = st.text_input("選項 A", row_data["A"])
                optB = st.text_input("選項 B", row_data["B"])
                optC = st.text_input("選項 C", row_data["C"])
                optD = st.text_input("選項 D", row_data["D"])
                expl = st.text_area("解析", row_data["解析"])
                if st.button("✅ 更新題庫"):
                    wb = load_workbook(EXCEL_PATH)
                    ws = wb[SHEET_NAME]
                    for row in ws.iter_rows(min_row=2):
                        if str(row[0].value) == str(row_data["章節"]) and str(row[1].value) == str(row_data["題號"]):
                            row[3].value, row[4].value = optA, optB
                            row[5].value, row[6].value = optC, optD
                            row[9].value = expl
                            break
                    wb.save(EXCEL_PATH)
                    st.success("✅ 題目已更新成功")

        elif admin_tab == "錯題紀錄管理":
            clear_mode = st.radio("清除模式", ["單一使用者", "所有使用者"])
            if clear_mode == "單一使用者":
                user = st.text_input("使用者名稱")
                if st.button("🧹 清除該使用者錯題"):
                    if os.path.exists(WRONG_LOG):
                        dfw = pd.read_csv(WRONG_LOG)
                        dfw = dfw[dfw["使用者"].str.lower() != user.lower()]
                        dfw.to_csv(WRONG_LOG, index=False)
                        st.success(f"✅ 已清除 {user} 的錯題紀錄")
            else:
                if st.button("🧨 清除所有錯題紀錄"):
                    if os.path.exists(WRONG_LOG):
                        os.remove(WRONG_LOG)
                        st.success("✅ 所有錯題紀錄已刪除")

        elif admin_tab == "下載紀錄":
            file_option = st.radio("選擇檔案：", ["錯題紀錄", "答題統計"])
            filepath = WRONG_LOG if file_option == "錯題紀錄" else STATS_LOG
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    st.download_button("📥 下載檔案", f, file_name=filepath, mime="text/csv")
            else:
                st.info("檔案不存在")
