
import streamlit as st
import pandas as pd
import random
import os

st.set_page_config(page_title="TIMS行銷專業能力認證 2025(初級)題庫", layout="wide")
st.title("TIMS行銷專業能力認證 2025(初級)題庫")

EXCEL_PATH = "行銷題庫總表.xlsx"
SHEET_NAME = "題庫總表"
WRONG_LOG = "錯題紀錄.csv"

@st.cache_data
def load_data():
    return pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

df = load_data()
chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}

mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式"])
username = st.sidebar.text_input("請輸入使用者名稱")
num_questions = st.sidebar.number_input("出題數量", min_value=1, max_value=50, value=5)
start_quiz = st.sidebar.button("🚀 開始出題")

if start_quiz and username.strip():
    username = username.strip()
    if mode == "錯題再練模式":
        if os.path.exists(WRONG_LOG):
            wrong_df = pd.read_csv(WRONG_LOG)
            wrong_df["使用者"] = wrong_df["使用者"].astype(str).str.strip().str.lower()
            username_lower = username.lower()

            matched = wrong_df[wrong_df["使用者"] == username_lower]
            st.info(f"✅ 找到 {len(matched)} 筆與使用者 `{username}` 相關的錯題")

            if len(matched) == 0:
                st.warning("⚠️ 此使用者目前尚無錯題紀錄")
            else:
                matched["章節"] = matched["章節"].astype(str)
                matched["題號"] = matched["題號"].astype(str)
                df["章節"] = df["章節"].astype(str)
                df["題號"] = df["題號"].astype(str)
                merged = df.merge(matched[["章節", "題號"]].drop_duplicates(), on=["章節", "題號"])
                st.success(f"🎯 成功比對到 {len(merged)} 題可以再練")
                st.write(merged[["章節", "題號", "題目"]].head(num_questions))
        else:
            st.error("❌ 尚未有任何錯題紀錄")
    else:
        selected_chapters = st.sidebar.multiselect("選擇章節", list(chapter_mapping.keys()), default=["CH1"])
        valid_sections = []
        for ch in selected_chapters:
            valid_sections.extend(chapter_mapping.get(ch, []))
        filtered_df = df[df["章節"].astype(str).isin(valid_sections)]
        sample = filtered_df.sample(n=min(num_questions, len(filtered_df))).reset_index(drop=True)
        st.success(f"✅ 隨機抽取 {len(sample)} 題")
        st.write(sample[["章節", "題號", "題目"]])
