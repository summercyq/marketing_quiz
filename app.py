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
# CH1 到 CH9
chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}
# 原有的 CH10 處理已被刪除

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
                        # Invalidate cache so next load_data gets the updated data
                        st.cache_data.clear()
                        # Reload data to refresh the view if needed (optional, depends on desired behavior)
                        # df = load_data() # This might cause issues if called within the admin section logic flow
                    except FileNotFoundError:
                         st.error(f"錯誤：找不到題庫檔案 `{EXCEL_PATH}` 無法儲存。")
                    except Exception as e:
                         st.error(f"更新題目時發生錯誤：{e}")

            else:
                st.info("找不到符合搜尋條件的題目。")

        elif tool == "錯題紀錄管理":
            st.subheader("🧹 管理錯題紀錄")
            submode = st.radio("選擇清除方式", ["單一使用者", "全部使用者"], key="clear_wrong_radio") # Added key
            if os.path.exists(WRONG_LOG):
                try:
                    df_wrong = pd.read_csv(WRONG_LOG)
                    unique_users = df_wrong["使用者"].unique().tolist()
                    if not unique_users:
                         st.info("錯題紀錄中沒有使用者紀錄。")
                    else:
                        if submode == "單一使用者":
                            # Use selectbox to choose user if users exist
                            target_user = st.selectbox("選擇要清除錯題的使用者", unique_users, key="select_user_clear") # Added key
                            if st.button(f"🧹 清除使用者 `{target_user}` 的錯題", key="clear_single_wrong_button"): # Added key
                                df_wrong = df_wrong[df_wrong["使用者"].str.lower() != target_user.lower()]
                                df_wrong.to_csv(WRONG_LOG, index=False)
                                st.success(f"已清除使用者 `{target_user}` 的錯題紀錄")
                                st.rerun() # Rerun to update the user list

                        elif submode == "全部使用者":
                            # Add a confirmation step for clearing all
                            st.warning("此操作將清除所有使用者的錯題紀錄，無法復原！")
                            if st.button("🧨 確認清除全部錯題", key="clear_all_wrong_button"): # Added key
                                os.remove(WRONG_LOG)
                                st.success("已清除所有錯題紀錄檔案")
                                st.rerun() # Rerun to update the view
                except pd.errors.EmptyDataError:
                    st.info("錯題紀錄檔案為空。")
                except FileNotFoundError:
                     st.info("錯題紀錄檔案不存在。") # Should be caught by os.path.exists, but good practice
                except Exception as e:
                    st.error(f"讀取或處理錯題紀錄時發生錯誤：{e}")
            else:
                st.info("錯題紀錄檔案不存在。")


        elif tool == "下載統計":
            st.subheader("📊 下載統計資料")
            if os.path.exists(STATS_LOG):
                try:
                    with open(STATS_LOG, "rb") as f:
                        st.download_button(
                            label="📥 下載答題統計 (CSV)",
                            data=f,
                            file_name="答題統計.csv",
                            mime="text/csv",
                            key="download_stats_button" # Added key
                        )
                except Exception as e:
                    st.error(f"讀取答題統計檔案時發生錯誤：{e}")
            else:
                st.info("答題統計檔案不存在。")

    elif admin_pwd != "": # Show message if password is wrong but not empty
         st.sidebar.error("密碼錯誤")


# --- Quiz Logic (for non-admin modes) ---
else: # mode is "一般出題模式" or "錯題再練模式"

    # Button to start the quiz
    if st.sidebar.button("🚀 開始出題", key="start_quiz_button"): # Added key
        if not st.session_state.username.strip():
            st.sidebar.warning("請先輸入使用者名稱！")
        else:
            st.session_state.quiz_started = True
            st.session_state.user_answers = [] # Reset answers for new quiz
            st.session_state.shuffled_options = {} # Reset shuffled options

            # Store current settings in session state for restarting
            st.session_state.last_settings = {
                "username": st.session_state.username,
                "mode": mode,
                "selected_chapters": selected_chapters,
                "num_questions": num_questions
            }

            # Generate questions
            st.session_state.questions = generate_quiz_questions(
                st.session_state.last_settings["username"],
                st.session_state.last_settings["mode"],
                st.session_state.last_settings["selected_chapters"],
                st.session_state.last_settings["num_questions"],
                df,
                chapter_mapping,
                WRONG_LOG
            )

            # If no questions were generated, reset quiz_started
            if st.session_state.questions.empty:
                 st.session_state.quiz_started = False


    # Display Quiz Questions if started and questions exist
    if st.session_state.quiz_started and st.session_state.questions is not None and not st.session_state.questions.empty:
        st.markdown("---")
        total_questions = len(st.session_state.questions)
        # Initialize correct_count for display
        current_correct_count = 0
        # Use a flag to track if all questions have been answered
        all_answered = True

        # Collect answers in a temporary list before processing/logging
        temp_user_answers = []

        for i, row in st.session_state.questions.iterrows():
            question_key = f"q{i}" # Unique key for the radio button

            # Check if this question has been answered in the current session state
            # We need to check based on question identifier, not just list index
            # A robust way is to check if a user answer exists for this specific question (章節, 題號)
            answered_item = next((item for item in st.session_state.user_answers if item["章節"] == row["章節"] and item["題號"] == row["題號"]), None)


            with st.container(): # Use st.container()
                st.markdown(f"**Q{i + 1}. {row['題目']}**")
                options = [row['A'], row['B'], row['C'], row['D']]
                labels = ['A', 'B', 'C', 'D']
                # Shuffle options only once per question per session
                if f"q{i}_options" not in st.session_state.shuffled_options:
                    zipped = list(zip(labels, options))
                    random.shuffle(zipped)
                    st.session_state.shuffled_options[f"q{i}_options"] = zipped
                else:
                    zipped = st.session_state.shuffled_options[f"q{i}_options"]

                # Create mappings between labels (A,B,C,D) and their text content
                label_to_opt = {label: opt for label, opt in zipped}
                opt_to_label = {opt: label for label, opt in zipped}

                correct_label = str(row["解答"]).strip().upper() # Ensure correct format
                if correct_label not in labels:
                     st.error(f"題目 {row['章節']}-{row['題號']} 的解答格式錯誤：'{row['解答']}'。應為 A, B, C, 或 D。")
                     # Skip processing this question further if correct answer is invalid
                     all_answered = False # Consider it unanswered due to error
                     continue # Move to the next question

                # Find the text of the correct answer based on the label
                correct_text = row.get(correct_label, "無效的解答選項文字") # Use .get for safety

                # Display radio buttons
                # If already answered, display selected answer but disable the radio
                if answered_item:
                    selected = st.radio("選項：", [opt for _, opt in zipped],
                                        key=question_key,
                                        index=[opt for _, opt in zipped].index(answered_item["使用者內容"]) if answered_item["使用者內容"] in [opt for _, opt in zipped] else None,
                                        disabled=True)
                else:
                    selected = st.radio("選項：", [opt for _, opt in zipped],
                                        key=question_key,
                                        index=None,
                                        disabled=False)
                    if selected is None: # If no option is selected yet for this question
                         all_answered = False


                # Process answer if selected
                if selected is not None:
                    # Find the label corresponding to the selected text
                    user_ans_label = opt_to_label.get(selected) # Use .get for safety

                    # Determine if the answer is correct
                    # Compare the label the user chose with the correct label
                    is_correct = (user_ans_label == correct_label) # Compare labels directly

                    # Display feedback
                    if is_correct:
                        st.success(f"✅ 答對了！")
                        current_correct_count += 1
                    else:
                        st.error(f"❌ 答錯了。正確答案是：{correct_label}. {correct_text}")

                    # Display explanation
                    # Only show explanation after an answer is selected
                    st.markdown(f"解析：{row['解析']}") # Assuming '解析' column exists

                    # Record the answer if it's the first time this question is answered in this run
                    if not answered_item:
                         temp_user_answers.append({
                            "使用者": st.session_state.username,
                            "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "正確答案": correct_label,
                            "正確內容": correct_text,
                            "使用者答案": user_ans_label if user_ans_label is not None else "未選", # Log "未選" if somehow missing label
                            "使用者內容": selected,
                            "章節": row["章節"],
                            "題號": row["題號"],
                            "題目": row["題目"], # Added for better logging
                            "解析": row["解析"],
                            # "選項配對": zipped, # Optional: log shuffled order
                            "是否正確": is_correct
                        })

        # Append newly recorded answers to the session state list
        st.session_state.user_answers.extend(temp_user_answers)

        # Calculate total correct from all answered questions in this run
        # Filter out None answers if any were recorded before selection logic refined
        correct_count_so_far = sum(1 for item in st.session_state.user_answers if item.get("是否正確") is True)
        # Correct count should only count correctly answered *unique* questions in the current quiz set
        # Let's recalculate based on the current questions and recorded answers
        correct_count = 0
        for _, row in st.session_state.questions.iterrows():
            answered_item = next((item for item in st.session_state.user_answers if item["章節"] == row["章節"] and item["題號"] == row["題號"]), None)
            if answered_item and answered_item.get("是否正確") is True:
                correct_count += 1


        # --- Display Results and Restart Button ---
        # Only show total score and restart button if all questions are answered
        if all_answered:
            st.markdown("---")
            st.markdown(f"### 🎯 本次測驗結果：總計 {total_questions} 題，答對 {correct_count} 題")

            # --- Logging Wrong Answers (after quiz completion) ---
            wrong_answers_this_quiz = [
                item for item in st.session_state.user_answers
                if item.get("是否正確") is False
                and (item["章節"], item["題號"]) in [(q["章節"], q["題號"]) for _, q in st.session_state.questions.iterrows()] # Ensure it's from this quiz set
            ]

            if wrong_answers_this_quiz:
                try:
                    # Load existing log or create new
                    if os.path.exists(WRONG_LOG):
                        df_wrong_log = pd.read_csv(WRONG_LOG)
                    else:
                        df_wrong_log = pd.DataFrame(columns=["使用者", "時間", "章節", "題號", "題目", "使用者答案", "使用者內容", "正確答案", "正確內容", "解析"])

                    # Append new wrong answers, avoiding duplicates for the same user/question combination
                    new_wrong_entries = []
                    existing_wrong = set(tuple(row[["使用者", "章節", "題號"]].astype(str).tolist()) for _, row in df_wrong_log.iterrows())

                    for entry in wrong_answers_this_quiz:
                        entry_key = (entry["使用者"], entry["章節"], entry["題號"])
                        if entry_key not in existing_wrong:
                            new_wrong_entries.append(entry)
                            existing_wrong.add(entry_key) # Add to set to prevent adding duplicates within the current batch

                    if new_wrong_entries:
                        df_new_wrong = pd.DataFrame(new_wrong_entries)
                        # Ensure columns match before concatenating
                        df_new_wrong = df_new_wrong[["使用者", "時間", "章節", "題號", "題目", "使用者答案", "使用者內容", "正確答案", "正確內容", "解析"]]
                        df_wrong_log = pd.concat([df_wrong_log, df_new_wrong], ignore_index=True)
                        df_wrong_log.to_csv(WRONG_LOG, index=False)
                        # st.info(f"已記錄 {len(new_wrong_entries)} 筆錯題到錯題紀錄。") # Optional: show confirmation

                except Exception as e:
                    st.error(f"記錄錯題時發生錯誤：{e}")


           # --- Restart Button ---
            # This button will now use the last_settings
            if st.button("🔄 重新出題", key="restart_quiz_button_completed"): # Added key
                 if st.session_state.last_settings:
                    st.session_state.quiz_started = True # Indicate a new quiz should start
                    st.session_state.user_answers = [] # Reset answers for the new quiz
                    st.session_state.shuffled_options = {} # Reset shuffled options

                    # Regenerate questions using the saved settings
                    st.session_state.questions = generate_quiz_questions(
                        st.session_state.last_settings["username"],
                        st.session_state.last_settings["mode"],
                        st.session_state.last_settings["selected_chapters"],
                        st.session_state.last_settings["num_questions"],
                        df,
                        chapter_mapping,
                        WRONG_LOG
                    )

                    # If regeneration failed (e.g., no wrong questions left), stop the quiz
                    if st.session_state.questions.empty:
                        st.session_state.quiz_started = False
                        st.warning("找不到符合條件的題目，無法重新出題。請檢查設定或錯題紀錄。")
                    # else: # 移除這整個 else 區塊和裡面的 st.rerun()
                        # st.rerun() # Rerun to display the new set of questions


                 else:
                    # This case should theoretically not happen if the button is only shown after a quiz
                    st.error("無法找到上一次的測驗設定。請使用側邊欄重新開始。")

        else:
            # If not all answered, display progress or just the questions
             st.markdown("---")
             st.info(f"已回答 {len(st.session_state.user_answers)} / {total_questions} 題。")
             st.markdown("請繼續作答。")
