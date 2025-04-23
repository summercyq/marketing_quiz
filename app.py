
import streamlit as st
import pandas as pd
import os
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

mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式"])
username = st.sidebar.text_input("請輸入使用者名稱")
selected_chapters = st.sidebar.multiselect("選擇章節", list(chapter_mapping.keys()), default=["CH1"])
num_questions = st.sidebar.number_input("出題數量", min_value=1, max_value=50, value=5)
start_quiz = st.sidebar.button("🚀 開始出題")

st.markdown("---")
with st.expander("🛠️ 管理者登入"):
    admin_pwd = st.text_input("🔐 請輸入管理密碼", type="password")
    if admin_pwd == EDIT_PASSWORD:
        admin_action = st.radio("選擇管理功能", ["題庫編輯", "錯題紀錄管理", "下載紀錄"])

        if admin_action == "題庫編輯":
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
                    wb = load_workbook(EXCEL_PATH)
                    ws = wb[SHEET_NAME]
                    for row in ws.iter_rows(min_row=2):
                        if str(row[0].value) == str(row_data["章節"]) and str(row[1].value) == str(row_data["題號"]):
                            row[3].value, row[4].value = optA, optB
                            row[5].value, row[6].value = optC, optD
                            row[9].value = expl
                            break
                    wb.save(EXCEL_PATH)
                    st.success("✅ 題庫已更新")

        elif admin_action == "錯題紀錄管理":
            clear_mode = st.radio("清除模式", ["單一使用者", "全部使用者"])
            if clear_mode == "單一使用者":
                user_to_clear = st.text_input("🔍 請輸入使用者名稱")
                if st.button("🗑️ 清除該使用者錯題紀錄"):
                    if os.path.exists(WRONG_LOG):
                        wrong_df = pd.read_csv(WRONG_LOG)
                        new_df = wrong_df[wrong_df["使用者"].str.lower() != user_to_clear.strip().lower()]
                        new_df.to_csv(WRONG_LOG, index=False)
                        st.success(f"✅ 已清除 {user_to_clear} 的錯題紀錄")
                    else:
                        st.info("ℹ️ 尚未有錯題紀錄")
            else:
                if st.button("🧨 清除所有錯題紀錄"):
                    if os.path.exists(WRONG_LOG):
                        os.remove(WRONG_LOG)
                        st.success("✅ 已刪除所有錯題紀錄")
                    else:
                        st.info("ℹ️ 錯題紀錄檔案不存在")

        elif admin_action == "下載紀錄":
            target = st.radio("📥 選擇下載檔案", ["錯題紀錄", "答題統計"])
            if target == "錯題紀錄":
                if os.path.exists(WRONG_LOG):
                    with open(WRONG_LOG, "rb") as f:
                        st.download_button("📎 下載錯題紀錄.csv", data=f, file_name="錯題紀錄.csv")
                else:
                    st.warning("⚠️ 無錯題紀錄檔案")
            else:
                if os.path.exists(STATS_LOG):
                    with open(STATS_LOG, "rb") as f:
                        st.download_button("📎 下載答題統計.csv", data=f, file_name="答題統計.csv")
                else:
                    st.warning("⚠️ 無答題統計檔案")
    elif admin_pwd:
        st.error("❌ 密碼錯誤")
