import streamlit as st
import pandas as pd
import random

@st.cache_data
def load_data():
    df = pd.read_excel("行銷題庫總表.xlsx", sheet_name="題庫總表")
    return df

chapter_mapping = {
    f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)
}

df = load_data()

st.title("📚 行銷隨機測驗系統")
st.markdown("請選擇章節與題目數量，系統將自動亂數出題並評分。")

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
    selected_chapters = st.multiselect("選擇章節：", list(chapter_mapping.keys()), default=["CH1"])
    num_questions = st.number_input("出題數量：", min_value=1, max_value=50, value=5)
    start_quiz = st.button("🚀 開始出題")

if start_quiz:
    st.session_state.quiz_started = True
    st.session_state.user_answers = []
    st.session_state.shuffled_options = {}
    st.session_state.show_result = False

    valid_sections = []
    for ch in selected_chapters:
        valid_sections.extend(chapter_mapping.get(ch, []))

    filtered_df = df[df['章節'].astype(str).isin(valid_sections)]

    if filtered_df.empty:
        st.error("找不到符合條件的題目，請重新選擇章節。")
        st.session_state.quiz_started = False
    else:
        st.session_state.questions = filtered_df.sample(
            n=min(num_questions, len(filtered_df))
        ).reset_index(drop=True)

if st.session_state.quiz_started and st.session_state.questions is not None:
    st.subheader("📝 開始作答：")
    for i, row in st.session_state.questions.iterrows():
        st.markdown(f"**Q{i+1}. {row['題目']}**")

        options = [row['A'], row['B'], row['C'], row['D']]
        labels = ['A', 'B', 'C', 'D']

        if f"q{i}_options" not in st.session_state.shuffled_options:
            shuffled = list(zip(labels, options))
            random.shuffle(shuffled)
            st.session_state.shuffled_options[f"q{i}_options"] = shuffled
        else:
            shuffled = st.session_state.shuffled_options[f"q{i}_options"]

        option_dict = {opt: label for label, opt in shuffled}

        selected = st.radio(
            label="選項：",
            options=[opt for _, opt in shuffled],
            key=f"q{i}"
        )

        if len(st.session_state.user_answers) <= i:
            st.session_state.user_answers.append({
                "正確答案": row['解答'],
                "解析": row['解析'],
                "使用者答案": option_dict.get(selected),
                "章節": row['章節'],
                "題號": row['題號']
            })
        else:
            st.session_state.user_answers[i]["使用者答案"] = option_dict.get(selected)

        if st.session_state.show_result:
            ans = st.session_state.user_answers[i]
            is_correct = ans['使用者答案'] == ans['正確答案']
            result_msg = "✅" if is_correct else f"❌ 正解為 `{ans['正確答案']}`"

            st.markdown(f"- 你的答案：`{ans['使用者答案']}`  {result_msg}")
            st.markdown(f"- 📘 **解析（{ans['章節']} / 題號 {ans['題號']}）**：{ans['解析']}")
        st.markdown("---")

    if st.button("✅ 送出並評分"):
        st.session_state.show_result = True
