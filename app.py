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

# 初始化 session_state
for key in ["quiz_started", "questions", "user_answers", "shuffled_options", "show_result"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "quiz_started" else [] if key.endswith("s") else None
# Sidebar - 使用者與出題設定
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
            filtered = df.merge(
                log[log["使用者"].str.lower() == st.session_state.username.lower()][["章節", "題號"]],
                on=["章節", "題號"]
            )
        else:
            filtered = pd.DataFrame()

    if not filtered.empty:
        st.session_state.questions = filtered.sample(n=min(num_questions, len(filtered))).reset_index(drop=True)
    else:
        st.session_state.quiz_started = False
        st.error("找不到符合條件的題目")
if st.session_state.quiz_started and st.session_state.questions is not None:
    st.markdown("---")
    total = len(st.session_state.questions)
    correct = 0

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
            else:
                ans = st.session_state.user_answers[i]
                is_correct = ans["使用者內容"] == ans["正確內容"]
                if is_correct:
                    correct += 1
                for label, opt in ans["選項配對"]:
                    style = ""
                    if opt == ans["正確內容"]:
                        style = "color:green;font-weight:bold;"
                    elif opt == ans["使用者內容"] and not is_correct:
                        style = "color:red;font-weight:bold;text-decoration:line-through;"
                    st.markdown(f"<div style='{style}'>{label}. {opt}</div>", unsafe_allow_html=True)

                if not is_correct:
                    st.markdown(f"解析：第{ans['章節']}章題號{ans['題號']}：{ans['解析']}")

                # 錯題紀錄
                if not is_correct:
                    if os.path.exists(WRONG_LOG):
                        log_df = pd.read_csv(WRONG_LOG)
                        new_entry = {"使用者": ans["使用者"], "章節": ans["章節"], "題號": ans["題號"], "題目": row["題目"]}
                        log_df = pd.concat([log_df, pd.DataFrame([new_entry])], ignore_index=True)
                        log_df.drop_duplicates(inplace=True)
                    else:
                        log_df = pd.DataFrame([{
                            "使用者": ans["使用者"], "章節": ans["章節"], "題號": ans["題號"], "題目": row["題目"]
                        }])
                    log_df.to_csv(WRONG_LOG, index=False)

                # 答題統計
                if os.path.exists(STATS_LOG):
                    stats_df = pd.read_csv(STATS_LOG)
                else:
                    stats_df = pd.DataFrame(columns=["使用者", "章節", "題號", "次數"])
                match = (stats_df["使用者"] == ans["使用者"]) & \
                        (stats_df["章節"] == ans["章節"]) & \
                        (stats_df["題號"] == ans["題號"])
                if match.any():
                    stats_df.loc[match, "次數"] += 1
                else:
                    stats_df = pd.concat([
                        stats_df,
                        pd.DataFrame([{"使用者": ans["使用者"], "章節": ans["章節"], "題號": ans["題號"], "次數": 1}])
                    ], ignore_index=True)
                stats_df.to_csv(STATS_LOG, index=False)
    if not st.session_state.show_result:
        if st.button("✅ 送出並評分"):
            st.session_state.show_result = True
    else:
        st.markdown(f"### 🎯 共 {total} 題，答對 {correct} 題")
        if st.button("🔄 重新出題"):
            st.session_state.quiz_started = False
            st.session_state.questions = None
            st.session_state.user_answers = []
            st.session_state.shuffled_options = {}
            st.session_state.show_result = False
# 管理者登入與功能選單
with st.sidebar.expander("🛠️ 管理者登入"):
    admin_password = st.text_input("輸入管理密碼：", type="password")
    if admin_password == EDIT_PASSWORD:
        st.success("登入成功，請選擇功能")

        tab = st.radio("管理功能選單", ["編輯題庫", "錯題紀錄管理", "答題統計查詢"])

        if tab == "編輯題庫":
            keyword = st.text_input("🔍 搜尋題目關鍵字")
            result = df[df["題目"].str.contains(keyword, na=False)] if keyword else df
            if not result.empty:
                selected_row = st.selectbox(
                    "選擇要編輯的題目",
                    result.apply(lambda x: f"{x['章節']} - {x['題號']}：{x['題目']}", axis=1)
                )
                if selected_row:
                    row_data = result[result.apply(
                        lambda x: f"{x['章節']} - {x['題號']}：{x['題目']}", axis=1
                    ) == selected_row].iloc[0]
                    st.markdown(f"### 題目：{row_data['題目']}")
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
                                row[3].value = optA
                                row[4].value = optB
                                row[5].value = optC
                                row[6].value = optD
                                row[9].value = expl
                                break
                        wb.save(EXCEL_PATH)
                        st.success("題目已更新成功")

        elif tab == "錯題紀錄管理":
            clear_mode = st.radio("選擇清除模式", ["單一使用者", "全部使用者"])
            if clear_mode == "單一使用者":
                user_to_clear = st.text_input("輸入使用者名稱")
                if st.button("🗑️ 清除該使用者錯題"):
                    if os.path.exists(WRONG_LOG):
                        wrong_df = pd.read_csv(WRONG_LOG)
                        new_df = wrong_df[wrong_df["使用者"].str.lower() != user_to_clear.strip().lower()]
                        new_df.to_csv(WRONG_LOG, index=False)
                        st.success(f"✅ 已清除 {user_to_clear} 的錯題紀錄")
                    else:
                        st.info("尚無錯題紀錄")
            else:
                if st.button("🧨 清除所有錯題紀錄"):
                    if os.path.exists(WRONG_LOG):
                        os.remove(WRONG_LOG)
                        st.success("✅ 所有錯題紀錄已刪除")
                    else:
                        st.info("錯題紀錄檔案不存在")

        elif tab == "答題統計查詢":
            if os.path.exists(STATS_LOG):
                df_stat = pd.read_csv(STATS_LOG)
                stat_counts = df_stat.groupby(['章節', '題號']).size().reset_index(name='答題次數')
                stat_display = df.merge(stat_counts, on=['章節', '題號'], how='left')
                stat_display = stat_display[['章節', '題號', '題目', '答題次數']].fillna(0)
                stat_display['答題次數'] = stat_display['答題次數'].astype(int)
                st.dataframe(stat_display.sort_values(by='答題次數', ascending=False), use_container_width=True)
            else:
                st.info("目前尚無答題統計資料")
    elif admin_password:
        st.error("❌ 密碼錯誤")
