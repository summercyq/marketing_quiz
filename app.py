import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime

st.set_page_config(page_title="TIMS行銷專業能力認證 2025(初級)題庫", layout="wide")
st.title("TIMS行銷專業能力認證 2025(初級)題庫")

# 頁面狀態儲存
if "last_chapters" not in st.session_state:
    st.session_state.last_chapters = []
if "last_question_count" not in st.session_state:
    st.session_state.last_question_count = 10
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "username" not in st.session_state:
    st.session_state.username = "guest"

# 首頁介紹
st.markdown("### 製作者：Summer CYQ")
st.markdown("#### 這是一套支援出題、作答、評分、錯題追蹤與管理的互動題庫系統")
st.markdown("#### 使用方式：")
st.markdown("1. 可多選章節")
st.markdown("2. 可自訂題數（最多 50 題）")
st.markdown("3. 綠字為正確答案，紅字＋刪除線為錯誤答案")

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

st.sidebar.text_input("請輸入使用者名稱", key="username")

# 出題區域
with st.expander("🎯 題目設定與出題"):
    selected_chapters = st.multiselect("請選擇章節：", list(chapter_mapping.keys()), default=st.session_state.last_chapters)
    question_count = st.number_input("請輸入題數（最多 50 題）", min_value=1, max_value=50, value=st.session_state.last_question_count)

    def generate_questions(chapters, count):
        selected_tags = [t for ch in chapters for t in chapter_mapping[ch]]
        pool = df[df['章節'].isin(selected_tags)]
        questions = pool.sample(min(count, len(pool))).to_dict(orient='records')
        for q in questions:
            options = [q['選項A'], q['選項B'], q['選項C'], q['選項D']]
            random.shuffle(options)
            q['選項'] = options
        return questions

    if st.button("🚀 出題"):
        st.session_state.last_chapters = selected_chapters
        st.session_state.last_question_count = question_count
        st.session_state.questions = generate_questions(selected_chapters, question_count)
        st.session_state.answers = {}
        st.session_state.submitted = False

    if st.button("🔁 重新出題（使用上一組設定）"):
        st.session_state.questions = generate_questions(st.session_state.last_chapters, st.session_state.last_question_count)
        st.session_state.answers = {}
        st.session_state.submitted = False

# 題目作答區域
if st.session_state.questions:
    st.markdown("---")
    st.subheader("📋 題目區")
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}. {q['題目']}**")
        correct_option = q[f"選項{q['解答']}"]
        selected = st.selectbox("選擇作答：", q['選項'], key=f"q_{i}", disabled=st.session_state.submitted)
        st.session_state.answers[i] = selected
        if st.session_state.submitted:
            for opt in q['選項']:
                if selected == correct_option and opt == selected:
                    st.markdown(f"<div style='color: green; font-weight: bold'>{opt}</div>", unsafe_allow_html=True)
                elif selected != correct_option:
                    if opt == selected:
                        st.markdown(f"<div style='color: red; text-decoration: line-through'>{opt}</div>", unsafe_allow_html=True)
                    elif opt == correct_option:
                        st.markdown(f"<div style='color: green; font-weight: bold'>{opt}</div>", unsafe_allow_html=True)
            st.markdown(f"📝 解析：第{str(q['章節']).split('-')[0]}章題號{q['題號']}：{q['解析']}")

    if not st.session_state.submitted:
        if st.button("📊 送出評分"):
            st.session_state.submitted = True
            correct = 0
            stats = []
            wrongs = []
            for i, q in enumerate(st.session_state.questions):
                correct_opt = q[f"選項{q['解答']}"]
                user_answer = st.session_state.answers[i]
                is_correct = (user_answer == correct_opt)
                stats.append({"使用者": st.session_state.username, "章節": q['章節'], "題號": q['題號'], "題目": q['題目'], "結果": "✔" if is_correct else "✘"})
                if not is_correct:
                    wrongs.append({"使用者": st.session_state.username, "章節": q['章節'], "題號": q['題號'], "題目": q['題目']})
                if is_correct:
                    correct += 1

            st.success(f"✅ 總共 {len(st.session_state.questions)} 題，答對 {correct} 題")

            stat_df = pd.DataFrame(stats)
            wrong_df = pd.DataFrame(wrongs)

            if os.path.exists(STATS_LOG):
                stat_df.to_csv(STATS_LOG, mode='a', index=False, header=False)
            else:
                stat_df.to_csv(STATS_LOG, index=False)

            if not wrong_df.empty:
                if os.path.exists(WRONG_LOG):
                    wrong_df.to_csv(WRONG_LOG, mode='a', index=False, header=False)
                else:
                    wrong_df.to_csv(WRONG_LOG, index=False)

# 每題答題次數統計顯示
with st.expander("📈 題目答題次數統計"):
    if os.path.exists(STATS_LOG):
        df_stat = pd.read_csv(STATS_LOG)
        stat_counts = df_stat.groupby(['章節', '題號']).size().reset_index(name='答題次數')
        stat_display = df.merge(stat_counts, on=['章節', '題號'], how='left')
        stat_display = stat_display[['章節', '題號', '題目', '答題次數']].fillna(0)
        stat_display['答題次數'] = stat_display['答題次數'].astype(int)
        st.dataframe(stat_display.sort_values(by='答題次數', ascending=False), use_container_width=True)
    else:
        st.info("目前尚無答題統計資料，請先完成一次評分。")

# 錯題再練模式
with st.expander("🔁 錯題再練模式"):
    if os.path.exists(WRONG_LOG):
        df_wrong = pd.read_csv(WRONG_LOG)
        df_user_wrong = df_wrong[df_wrong["使用者"] == st.session_state.username]
        if df_user_wrong.empty:
            st.info("目前沒有錯題紀錄，請先完成一次評分。")
        else:
            retry_questions = df.merge(df_user_wrong[["章節", "題號"]], on=["章節", "題號"], how="inner")
            retry_questions = retry_questions.to_dict(orient='records')
            for q in retry_questions:
                options = [q['選項A'], q['選項B'], q['選項C'], q['選項D']]
                random.shuffle(options)
                q['選項'] = options
            st.session_state.questions = retry_questions
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.success(f"共載入 {len(retry_questions)} 題錯題，請開始作答！")
    else:
        st.warning("尚無錯題紀錄檔案。")
