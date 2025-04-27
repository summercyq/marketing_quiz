import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
from openpyxl import load_workbook # 確保這個函式有被使用到，如果只用來讀取，pd.read_excel就夠了，但這裡用於寫入

st.set_page_config(page_title="TIMS行銷專業能力認證 2025(初級)題庫", layout="wide")
st.title("TIMS行銷專業專業能力認證 2025(初級)題庫")

# 檔案路徑設定
EXCEL_PATH = "行銷題庫總表.xlsx"
SHEET_NAME = "題庫總表"
WRONG_LOG = "錯題紀錄.csv"
STATS_LOG = "答題統計.csv" # 答題統計功能未在原碼中實現，但路徑已定義
EDIT_PASSWORD = "quiz2024"

# 使用st.cache_data載入資料，避免每次重跑都重新載入
@st.cache_data
def load_data():
    """Loads the question data from the Excel file."""
    try:
        return pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    except FileNotFoundError:
        st.error(f"錯誤：找不到題庫檔案 `{EXCEL_PATH}`。請確認檔案是否存在。")
        return pd.DataFrame() # Return empty dataframe on error
    except Exception as e:
        st.error(f"載入題庫時發生錯誤：{e}")
        return pd.DataFrame()

df = load_data()

# 如果載入失敗，中止執行後續依賴df的程式碼
if df.empty and not (mode == "管理者登入" and tool == "錯題紀錄管理" and os.path.exists(WRONG_LOG)):
     st.stop() # Stop execution if dataframe is empty and not in specific admin mode

# 章節對應關係
chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}
# 增加CH10的處理
chapter_mapping["CH10"] = ["10-1"] # Assuming CH10 only has 10-1

# 初始化 Session State
for key in ["quiz_started", "questions", "user_answers", "shuffled_options", "last_settings"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "quiz_started" else [] if key.endswith("s") else None

# --- Helper function to generate quiz questions ---
def generate_quiz_questions(username, mode, selected_chapters, num_questions, dataframe, chapter_map, wrong_log_path):
    """Generates a list of questions based on the selected mode and settings."""
    if mode == "一般出題模式":
        sections = [s for ch in selected_chapters for s in chapter_map.get(ch, [])] # Use .get to handle potential missing keys
        filtered = dataframe[dataframe["章節"].astype(str).isin(sections)]
        if filtered.empty:
             st.warning(f"找不到符合所選章節 ({', '.join(selected_chapters)}) 的題目。")
             return pd.DataFrame()

    elif mode == "錯題再練模式":
        if os.path.exists(wrong_log_path):
            try:
                log = pd.read_csv(wrong_log_path)
                # Filter log for the current user and chapters (if chapters selected)
                user_wrong_log = log[log["使用者"].str.lower() == username.lower()]

                # Apply chapter filter if selected_chapters is not empty
                if selected_chapters:
                    sections = [s for ch in selected_chapters for s in chapter_map.get(ch, [])]
                    user_wrong_log = user_wrong_log[user_wrong_log["章節"].astype(str).isin(sections)]

                if user_wrong_log.empty:
                     st.info(f"使用者 `{username}` 沒有錯題紀錄，或所選章節 ({', '.join(selected_chapters)}) 中沒有錯題。")
                     return pd.DataFrame()

                # Merge with the main dataframe to get full question details
                filtered = dataframe.merge(
                    user_wrong_log[["章節", "題號"]].drop_duplicates(), # Use drop_duplicates in case a question is in the log multiple times
                    on=["章節", "題號"]
                )
                if filtered.empty:
                     st.warning(f"根據錯題紀錄，找不到對應的題目。")
                     return pd.DataFrame() # Should not happen if user_wrong_log is not empty and merge keys are correct

            except pd.errors.EmptyDataError:
                 st.info("錯題紀錄檔案為空。")
                 return pd.DataFrame()
            except Exception as e:
                 st.error(f"讀取錯題紀錄時發生錯誤：{e}")
                 return pd.DataFrame()

        else:
            st.info("找不到錯題紀錄檔案。請先進行作答以產生紀錄。")
            return pd.DataFrame()

    else: # Should not happen with current mode radio, but good practice
        st.error("無效的模式選擇。")
        return pd.DataFrame()

    # Sample questions
    if not filtered.empty:
        return filtered.sample(n=min(num_questions, len(filtered))).reset_index(drop=True)
    else:
        return pd.DataFrame()


# --- Sidebar ---
st.sidebar.header("使用者與模式設定")
st.session_state.username = st.sidebar.text_input("請輸入使用者名稱", value=st.session_state.get("username", ""), key="username_input") # Added key
mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式", "管理者登入"], key="mode_radio") # Added key
selected_chapters = st.sidebar.multiselect("選擇章節：", list(chapter_mapping.keys()), default=["CH1"], key="chapters_select") # Added key
num_questions = st.sidebar.number_input("出題數量", min_value=1, max_value=50, value=5, key="num_questions_input") # Added key

# --- Admin Login ---
if mode == "管理者登入":
    admin_pwd = st.sidebar.text_input("請輸入管理者密碼", type="password")
    if admin_pwd == EDIT_PASSWORD:
        st.header("📋 管理功能")
        tool = st.radio("請選擇功能", ["題庫編輯", "錯題紀錄管理", "下載統計"], key="admin_tool_radio") # Added key
        if tool == "題庫編輯":
            st.subheader("✏️ 編輯題目")
            keyword = st.text_input("搜尋關鍵字", key="edit_keyword") # Added key
            result = df[df["題目"].str.contains(keyword, na=False)] if keyword else df

            if not result.empty:
                # Create a unique identifier for the selectbox
                options_list = result.apply(lambda x: f"{x['章節']}-{x['題號']} {x['題目']}", axis=1).tolist()
                selected_label = st.selectbox("選擇題目", options_list, key="select_question_edit") # Added key

                # Find the row based on the selected label
                selected_row_data = result[result.apply(lambda x: f"{x['章節']}-{x['題號']} {x['題目']}", axis=1) == selected_label].iloc[0]

                # Display and allow editing fields
                st.write(f"目前章節-題號: {selected_row_data['章節']}-{selected_row_data['題號']}")
                # Display current question text, not editable here as per original code
                st.write(f"題目內文: {selected_row_data['題目']}")

                new_A = st.text_input("選項 A", selected_row_data["A"], key="edit_A") # Added key
                new_B = st.text_input("選項 B", selected_row_data["B"], key="edit_B") # Added key
                new_C = st.text_input("選項 C", selected_row_data["C"], key="edit_C") # Added key
                new_D = st.text_input("選項 D", selected_row_data["D"], key="edit_D") # Added key
                # Assuming "解答" column exists and needs to be handled carefully - original code didn't edit this, only options and parsing.
                # We will not add editing for "解答" to match original intent.
                new_expl = st.text_area("解析", selected_row_data["解析"], key="edit_expl") # Added key

                if st.button("✅ 更新題目", key="update_question_button"): # Added key
                    try:
                        wb = load_workbook(EXCEL_PATH)
                        ws = wb[SHEET_NAME]
                        # Find the row by 章節 and 題號 to update
                        for row in ws.iter_rows(min_row=2): # Assuming header is row 1
                            # Convert to string for comparison to handle potential mixed types
                            if str(row[0].value) == str(selected_row_data["章節"]) and str(row[1].value) == str(selected_row_data["題號"]):
                                # Update option cells (assuming columns C, D, E, F are A, B, C, D - index 2, 3, 4, 5)
                                row[2].value = new_A # Column C for Option A
                                row[3].value = new_B # Column D for Option B
                                row[4].value = new_C # Column E for Option C
                                row[5].value = new_D # Column F for Option D
                                # Update explanation cell (assuming column J is 解析 - index 9)
                                row[9].value = new_expl
                                break # Found and updated the row
                        wb.save(EXCEL_PATH)
                        st.success("✅ 題目已更新成功")
                        # Invalidate cache
