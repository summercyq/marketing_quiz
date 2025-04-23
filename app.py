import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
from openpyxl import load_workbook

st.set_page_config(page_title="TIMS行銷專業能力認證 2025(初級)題庫", layout="wide")
st.title("TIMS行銷專業能力認證 2025(初級)題庫")

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

# 顯示題目的選項處理邏輯（紅字＋刪除線與綠色加粗）
# 請將這段整合至你的選項呈現邏輯中
# for idx, (label, opt) in enumerate(zipped):
#     option_style = ""
#     if show_result and selected:
#         if selected == correct_answer:
#             option_style = 'color: green; font-weight: bold'
#         else:
#             if label == selected:
#                 option_style = 'color: red; text-decoration: line-through;'
#             elif label == correct_answer:
#                 option_style = 'color: green; font-weight: bold'
#     st.markdown(f"<div style='{option_style}'>{label}. {opt}</div>", unsafe_allow_html=True)

# 評分完成後需鎖定答案不可再修改邏輯示意：
# if show_result:
#     st.selectbox("作答已完成", [user_answer], disabled=True)

# 管理者登入整合區塊
with st.expander("🛠️ 管理者登入"):
    admin_pwd = st.text_input("請輸入管理者密碼：", type="password")
    if admin_pwd == EDIT_PASSWORD:
        action = st.radio("請選擇管理功能：", ["題庫編輯", "錯題紀錄管理", "下載紀錄"])

        if action == "題庫編輯":
            st.subheader("✏️ 題庫編輯功能")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 儲存修改"):
                try:
                    edited_df.to_excel(EXCEL_PATH, index=False)
                    st.success("題庫已成功儲存！")
                except Exception as e:
                    st.error(f"儲存失敗：{e}")

        elif action == "錯題紀錄管理":
            st.subheader("🧹 錯題紀錄清除功能")
            clear_option = st.radio("選擇清除範圍：", ["全部使用者", "指定使用者"])
            if clear_option == "全部使用者":
                if st.button("⚠️ 清除所有使用者的錯題紀錄"):
                    if os.path.exists(WRONG_LOG):
                        os.remove(WRONG_LOG)
                        st.success("所有錯題紀錄已刪除！")
                    else:
                        st.info("尚無錯題紀錄檔案")
            else:
                username = st.text_input("請輸入使用者名稱")
                if st.button("🧼 清除該使用者的錯題紀錄"):
                    if os.path.exists(WRONG_LOG):
                        df_wrong = pd.read_csv(WRONG_LOG)
                        df_wrong = df_wrong[df_wrong["使用者"] != username]
                        df_wrong.to_csv(WRONG_LOG, index=False)
                        st.success(f"使用者 {username} 的錯題紀錄已清除！")
                    else:
                        st.info("尚無錯題紀錄檔案")

        elif action == "下載紀錄":
            st.subheader("📥 紀錄下載")
            option = st.selectbox("選擇要下載的檔案：", ["錯題紀錄", "答題統計"])
            if option == "錯題紀錄" and os.path.exists(WRONG_LOG):
                with open(WRONG_LOG, "rb") as f:
                    st.download_button("📄 下載錯題紀錄", data=f, file_name="錯題紀錄.csv")
            elif option == "答題統計" and os.path.exists(STATS_LOG):
                with open(STATS_LOG, "rb") as f:
                    st.download_button("📊 下載答題統計", data=f, file_name="答題統計.csv")
            else:
                st.info("找不到對應的紀錄檔案。")

    elif admin_pwd:
        st.warning("密碼錯誤，請再試一次。")
