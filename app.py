import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime

st.set_page_config(page_title="TIMS行銷專業能力認證 2025(初級)題庫", layout="wide")
st.title("TIMS行銷專業能力認證 2025(初級)題庫")

# 狀態儲存
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

# Sidebar 使用者名稱與設定區域
with st.sidebar:
    st.header("使用者設定")
    st.text_input("請輸入使用者名稱", key="username")

    with st.expander("🎯 題目設定與出題"):
        selected_chapters = st.multiselect("請選擇章節：", list(chapter_mapping.keys()), default=st.session_state.last_chapters)
        question_count = st.number_input("請輸入題數（最多 50 題）", min_value=1, max_value=50, value=st.session_state.last_question_count)

        def generate_questions(chapters, count):
            selected_tags = [t for ch in chapters for t in chapter_mapping[ch]]
            pool = df[df['章節'].isin(selected_tags)]

            # 防呆：排除資料不完整的題目
            required_fields = ['A', 'B', 'C', 'D', '題目', '題號', '解答']
            pool = pool.dropna(subset=required_fields)

            if pool.empty:
                st.warning("選擇的章節中沒有足夠的題目或資料不完整，請檢查題庫。")
                return []

            questions = pool.sample(min(count, len(pool))).to_dict(orient='records')
            for q in questions:
                options = [q['A'], q['B'], q['C'], q['D']]
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
                    options = [q['A'], q['B'], q['C'], q['D']]
                    random.shuffle(options)
                    q['選項'] = options
                st.session_state.questions = retry_questions
                st.session_state.answers = {}
                st.session_state.submitted = False
                st.success(f"共載入 {len(retry_questions)} 題錯題，請開始作答！")
        else:
            st.warning("尚無錯題紀錄檔案。")

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