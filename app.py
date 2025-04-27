import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
from openpyxl import load_workbook

st.set_page_config(page_title="TIMS行銷專業能力認證 2025(初級)題庫", layout="wide")
st.title("TIMS行銷專業能力認證 2025(初級)題庫")

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


# 章節對應關係 (CH10 已移除)
chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}


# 初始化 Session State
for key in ["quiz_started", "questions", "user_answers", "shuffled_options", "last_settings", "is_admin_mode"]:
    if key not in st.session_state:
        # Default is not in admin mode
        st.session_state[key] = False if key == "is_admin_mode" or key == "quiz_started" else [] if key.endswith("s") else None


# --- Helper function to generate quiz questions ---
def generate_quiz_questions(username, mode, selected_chapters, num_questions, dataframe, chapter_map, wrong_log_path):
    """Generates a list of questions based on the selected mode and settings."""
    if dataframe.empty:
         st.warning("題庫資料為空，無法產生題目。")
         return pd.DataFrame()

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
            except FileNotFoundError:
                 st.info("找不到錯題紀錄檔案。請先進行作答以產生紀錄。")
                 return pd.DataFrame()
            except Exception as e:
                 st.error(f"讀取錯題紀錄時發生錯誤：{e}")
                 return pd.DataFrame()

        else:
            st.info("找不到錯題紀錄檔案。請先進行作答以產生紀錄。")
            return pd.DataFrame()

    else: # Should not happen with the new structure
        st.error("內部錯誤：無效的測驗模式選擇。")
        return pd.DataFrame()

    # Sample questions
    if not filtered.empty:
        return filtered.sample(n=min(num_questions, len(filtered))).reset_index(drop=True)
    else:
        return pd.DataFrame()


# --- Sidebar ---
st.sidebar.header("使用者與模式設定")
st.session_state.username = st.sidebar.text_input("請輸入使用者名稱", value=st.session_state.get("username", ""), key="username_input")


# --- Sidebar - Quiz Settings (Only display if not in admin mode) ---
if not st.session_state.is_admin_mode:
    quiz_mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式"], key="quiz_mode_radio") # Removed "管理者登入"
    selected_chapters = st.sidebar.multiselect("選擇章節：", list(chapter_mapping.keys()), default=["CH1"], key="chapters_select")
    num_questions = st.sidebar.number_input("出題數量", min_value=1, max_value=50, value=5, key="num_questions_input")

    # Start Quiz Button
    if st.sidebar.button("🚀 開始出題", key="start_quiz_button"):
        if not st.session_state.username.strip():
            st.sidebar.warning("請先輸入使用者名稱！")
        elif df.empty:
             st.sidebar.warning("題庫資料為空，無法開始測驗。")
        else:
            st.session_state.quiz_started = True
            st.session_state.user_answers = [] # Reset answers for new quiz
            st.session_state.shuffled_options = {} # Reset shuffled options

            # Store current settings in session state for restarting
            st.session_state.last_settings = {
                "username": st.session_state.username,
                "mode": quiz_mode, # Use quiz_mode selected in sidebar
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
                 # Warning is already shown inside generate_quiz_questions

# --- Sidebar - Admin Mode Switch (Placed below the quiz settings/start button in sidebar) ---
st.sidebar.markdown("---") # Separator
st.session_state.is_admin_mode = st.sidebar.checkbox("🛠️ 啟用管理者模式", key="admin_mode_checkbox")


# --- Main Content Area ---

# Display Admin Interface if in Admin Mode
if st.session_state.is_admin_mode:
    st.header("🔒 管理者登入")
    admin_pwd = st.text_input("請輸入管理者密碼", type="password", key="admin_pwd_input")

    if admin_pwd == EDIT_PASSWORD:
        st.header("📋 管理功能")
        tool = st.radio("請選擇功能", ["題庫編輯", "錯題紀錄管理", "下載統計"], key="admin_tool_radio")

        if tool == "題庫編輯":
            st.subheader("✏️ 編輯題目")
            if df.empty:
                 st.warning("題庫資料為空，無法編輯題目。")
            else:
                keyword = st.text_input("搜尋關鍵字", key="edit_keyword")
                result = df[df["題目"].str.contains(keyword, na=False)] if keyword else df

                if not result.empty:
                    # Create a unique identifier for the selectbox
                    options_list = result.apply(lambda x: f"{x['章節']}-{x['題號']} {x['題目']}", axis=1).tolist()
                    selected_label = st.selectbox("選擇題目", options_list, key="select_question_edit")

                    # Find the row based on the selected label
                    selected_row_data = result[result.apply(lambda x: f"{x['章節']}-{x['題號']} {x['題目']}", axis=1) == selected_label].iloc[0]

                    # Display and allow editing fields
                    st.write(f"目前章節-題號: {selected_row_data.get('章節', 'N/A')}-{selected_row_data.get('題號', 'N/A')}")
                    # Display current question text, not editable here as per original code
                    st.write(f"題目內文: {selected_row_data.get('題目', 'N/A')}")

                    # Use .get with default values for robustness
                    new_A = st.text_input("選項 A", selected_row_data.get("A", ""), key="edit_A")
                    new_B = st.text_input("選項 B", selected_row_data.get("B", ""), key="edit_B")
                    new_C = st.text_input("選項 C", selected_row_data.get("C", ""), key="edit_C")
                    new_D = st.text_input("選項 D", selected_row_data.get("D", ""), key="edit_D")
                    new_expl = st.text_area("解析", selected_row_data.get("解析", ""), key="edit_expl")

                    if st.button("✅ 更新題目", key="update_question_button"):
                        try:
                            wb = load_workbook(EXCEL_PATH)
                            ws = wb[SHEET_NAME]
                            # Find the row by 章節 and 題號 to update
                            for row in ws.iter_rows(min_row=2): # Assuming header is row 1
                                # Convert to string for comparison to handle potential mixed types
                                if str(row[0].value) == str(selected_row_data.get("章節", None)) and str(row[1].value) == str(selected_row_data.get("題號", None)):
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
                            # No need to rerun here unless you want the selectbox options to update immediately, which might be jarring.
                            # A full rerun happens implicitly on button click anyway.

                        except FileNotFoundError:
                             st.error(f"錯誤：找不到題庫檔案 `{EXCEL_PATH}` 無法儲存。")
                        except Exception as e:
                             st.error(f"更新題目時發生錯誤：{e}")

                else:
                    st.info("找不到符合搜尋條件的題目。")

        elif tool == "錯題紀錄管理":
            st.subheader("🧹 管理錯題紀錄")
            submode = st.radio("選擇清除方式", ["單一使用者", "全部使用者"], key="clear_wrong_radio")
            if os.path.exists(WRONG_LOG):
                try:
                    df_wrong = pd.read_csv(WRONG_LOG)
                    unique_users = df_wrong["使用者"].unique().tolist()
                    if not unique_users:
                         st.info("錯題紀錄中沒有使用者紀錄。")
                    else:
                        if submode == "單一使用者":
                            target_user = st.selectbox("選擇要清除錯題的使用者", unique_users, key="select_user_clear")
                            if st.button(f"🧹 清除使用者 `{target_user}` 的錯題", key="clear_single_wrong_button"):
                                df_wrong = df_wrong[df_wrong["使用者"].str.lower() != target_user.lower()]
                                df_wrong.to_csv(WRONG_LOG, index=False)
                                st.success(f"已清除使用者 `{target_user}` 的錯題紀錄")
                                st.rerun() # Use st.rerun()

                        elif submode == "全部使用者":
                            st.warning("此操作將清除所有使用者的錯題紀錄，無法復原！")
                            if st.button("🧨 確認清除全部錯題", key="clear_all_wrong_button"):
                                os.remove(WRONG_LOG)
                                st.success("已清除所有錯題紀錄檔案")
                                st.rerun() # Use st.rerun()
                except pd.errors.EmptyDataError:
                    st.info("錯題紀錄檔案為空。")
                except FileNotFoundError:
                     st.info("錯題紀錄檔案不存在。")
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
                            key="download_stats_button"
                        )
                except Exception as e:
                    st.error(f"讀取答題統計檔案時發生錯誤：{e}")
            else:
                st.info("答題統計檔案不存在。")

    elif admin_pwd != "": # Show message if password is wrong but not empty
         st.error("密碼錯誤")


# Display Quiz Interface if not in Admin Mode and quiz is started
# ... (前面的程式碼都保留) ...

# Display Quiz Interface if not in Admin Mode and quiz is started
# ... (code before the else: # st.session_state.is_admin_mode is False block) ...

# Display Quiz Interface if not in Admin Mode and quiz is started
else: # st.session_state.is_admin_mode is False
    if st.session_state.quiz_started and st.session_state.questions is not None and not st.session_state.questions.empty:
        total_questions = len(st.session_state.questions)
        # all_answered = True # <-- Still removed

        # Collect answers in a temporary list for this render cycle
        temp_user_answers = []

        for i, row in st.session_state.questions.iterrows():
            question_key = f"q{i}_quiz" # Unique key for the radio button in quiz mode

            # Find if this question was answered in a previous rerun within this quiz session
            # Here, we need the potentially *previously* stored answer to set the initial state (index, disabled)
            # Ensure comparison keys are strings for robustness
            answered_item = next((item for item in st.session_state.user_answers
                                  if str(item.get("章節")) == str(row.get("章節")) and str(item.get("題號")) == str(row.get("題號"))), None)

            with st.container():
                st.markdown(f"**Q{i + 1}. {row.get('題目', 'N/A')}**") # Use .get for safety
                # Get original options text and labels
                options = [row.get('A', ''), row.get('B', ''), row.get('C', ''), row.get('D', '')]
                labels = ['A', 'B', 'C', 'D']

                # Handle potential None values in options gracefully
                options = [str(opt) if opt is not None else "" for opt in options] # Changed "N/A" to "" for cleaner display

                # Shuffle options only once per question per session
                shuffled_key = f"q{i}_options_quiz"
                if shuffled_key not in st.session_state.shuffled_options:
                    zipped = list(zip(labels, options))
                    random.shuffle(zipped)
                    st.session_state.shuffled_options[shuffled_key] = zipped
                else:
                    zipped = st.session_state.shuffled_options[shuffled_key]

                # Create mappings from the *shuffled* order
                shuffled_labels = [item[0] for item in zipped]
                shuffled_options_text = [item[1] for item in zipped]
                label_to_opt_shuffled = dict(zipped) # {'Shuffled_Label': 'Shuffled_Text'}
                opt_to_label_shuffled = {v: k for k, v in label_to_opt_shuffled.items()} # {'Shuffled_Text': 'Shuffled_Label'}

                # We still need the original mapping for correct_text lookup
                original_label_to_opt = {'A': row.get('A', ''), 'B': row.get('B', ''), 'C': row.get('C', ''), 'D': row.get('D', '')}


                correct_label = str(row.get("解答", "")).strip().upper()
                # Validate correct label - Keep this check for displaying errors
                if correct_label not in labels or not correct_label:
                    st.error(f"題目 {row.get('章節', 'N/A')}-{row.get('題號', 'N/A')} 的解答格式錯誤：'{row.get('解答', 'None')}'。應為 A, B, C, 或 D。此題無法作答。")
                    continue # Skip this question's radio button and processing

                # Get the correct answer text using the original mapping
                correct_text = original_label_to_opt.get(correct_label, "無效的解答選項文字")


                # --- START: Adjusted Section for conditional display and index ---

                display_options = [] # List to hold options shown in st.radio
                selected_index_for_radio = None # Index for st.radio pre-selection

                # Build the list of options to display and determine the pre-selected index if answered
                if answered_item is not None:
                    # If answered, format options with label (e.g., "A. Option Text")
                    # Use the labels and texts from the *shuffled* zipped list
                    answered_content_text = answered_item.get("使用者內容")
                    for idx, (label, opt_text) in enumerate(zipped):
                        formatted_option = f"{label}. {opt_text}"
                        display_options.append(formatted_option)
                        # Find the index if this option text matches the user's previous answer content
                        if opt_text == answered_content_text:
                             selected_index_for_radio = idx

                else:
                    # If not answered, display only the option text (e.g., "Option Text")
                    # Use the texts from the *shuffled* zipped list
                    for idx, (label, opt_text) in enumerate(zipped):
                        display_options.append(opt_text)
                    # selected_index_for_radio remains None initially for unanswered questions


                # --- END: Adjusted Section for conditional display and index ---


                # Display radio buttons using the conditionally built display_options list
                # If answered_item is not None, index will be set and disabled=True
                # If answered_item is None, index will be None and disabled=False
                selected = st.radio("選項：", display_options,
                                     key=question_key,
                                     index=selected_index_for_radio, # Use the determined index
                                     disabled=answered_item is not None) # Disable if already answered

                # --- START: Adjusted Section for processing selected answer and feedback ---
                # If the user selected an answer in this rerun AND it wasn't previously answered
                if selected is not None and answered_item is None:
                    # In this block (answered_item is None), 'selected' is the raw option text
                    user_selected_option_text = selected

                    # Find the original label (A, B, C, D) corresponding to this text
                    # Use the opt_to_label_shuffled mapping which correctly maps text to its shuffled label
                    user_ans_label = opt_to_label_shuffled.get(user_selected_option_text)

                    # Determine correctness based on the original correct_label and the user's chosen label
                    is_correct = (user_ans_label == correct_label)

                    # Add to temporary list for this render cycle's new answers
                    temp_user_answers.append({
                        "使用者": st.session_state.username,
                        "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "正確答案": correct_label, # Store the original correct label
                        "正確內容": correct_text, # Store the original correct text
                        "使用者答案": user_ans_label if user_ans_label is not None else "未選", # Store the user's chosen label (A, B, C, D based on shuffle)
                        "使用者內容": user_selected_option_text, # Store the original option text content user selected
                        "章節": row.get("章節", "N/A"),
                        "題號": row.get("題號", "N/A"),
                        "題目": row.get("題目", "N/A"),
                        "解析": row.get("解析", "無解析"),
                        "是否正確": is_correct
                    })

                    # Display feedback and explanation immediately after selection
                    if is_correct:
                        st.success(f"✅ 答對了！")
                    else:
                        # Find the correct option text using the correct_label
                        st.error(f"❌ 答錯了。正確答案是：{correct_label}. {correct_text}")

                    # Display explanation
                    st.markdown(f"※章節{row.get('章節', 'N/A')} 第{row.get('題號', 'N/A')}題解析：{row.get('解析', '無解析')}")

                # If the question was already answered (in a previous rerun)
                elif answered_item is not None:
                    # Display feedback and explanation based on stored data.
                    # The display_options contained formatted text ("A. Option Text") when this was rendered as answered.
                    # We need the data from the stored answered_item for feedback.
                    if answered_item.get("是否正確") is True:
                         st.success(f"✅ 答對了！")
                    else:
                         st.error(f"❌ 答錯了。正確答案是：{answered_item.get('正確答案', 'N/A')}. {answered_item.get('正確內容', 'N/A')}")
                    st.markdown(f"※{answered_item.get('章節', 'N/A')}第{answered_item.get('題號', 'N/A')}題解析：{answered_item.get('解析', '無解析')}")

                # --- END: Adjusted Section for processing selected answer and feedback ---


        # Append newly recorded answers (from this rerun) to the session state list
        st.session_state.user_answers.extend(temp_user_answers)

        # --- Recalculate all_answered and correct_count after the loop ---
        # Invalidate questions with invalid correct answers
        valid_questions_in_quiz_keys = [
            (str(q.get("章節", "")), str(q.get("題號", "")))
            for _, q in st.session_state.questions.iterrows()
            if str(q.get("解答", "")).strip().upper() in ['A', 'B', 'C', 'D']
        ]
        total_valid_questions = len(valid_questions_in_quiz_keys)

        # Count how many valid questions in the current quiz have an answer recorded in session_state.user_answers
        answered_valid_question_keys = set(
            (str(item.get("章節", "")), str(item.get("題號", "")))
            for item in st.session_state.user_answers
            if (str(item.get("章節", "")), str(item.get("題號", ""))) in valid_questions_in_quiz_keys
        )

        # all_answered is true if the count of answered valid questions matches the total count of valid questions
        all_answered = len(answered_valid_question_keys) == total_valid_questions and total_valid_questions > 0


        # Recalculate correct count by iterating through the *current quiz questions*
        correct_count = 0
        for _, q_row in st.session_state.questions.iterrows():
             q_key = (str(q_row.get("章節")), str(q_row.get("題號")))
             # Only count if the question is valid and an answer is recorded for it
             if q_key in valid_questions_in_quiz_keys:
                  answered_item = next((item for item in st.session_state.user_answers
                                        if (str(item.get("章節")), str(item.get("題號"))) == q_key), None)
                  # If an answer was found and it was correct
                  if answered_item is not None and answered_item.get("是否正確") is True:
                       correct_count += 1


        # --- Display Results and Restart Button ---
        if all_answered:
            st.markdown("---")
            st.markdown(f"### 🎯 本次測驗結果：總計 {total_valid_questions} 題，答對 {correct_count} 題")

            # --- Logging Wrong Answers (after quiz completion) ---
            # Only log wrong answers that were *newly recorded* in the temp_user_answers list during this completion render
            wrong_answers_this_quiz_run = [
                 item for item in temp_user_answers # Use temp_user_answers
                 if item.get("是否正確") is False
             ]

            if wrong_answers_this_quiz_run:
                 try:
                     # Load existing log or create new
                     if os.path.exists(WRONG_LOG):
                         df_wrong_log = pd.read_csv(WRONG_LOG)
                     else:
                         # Define columns explicitly for a new dataframe
                         df_wrong_log = pd.DataFrame(columns=["使用者", "時間", "章節", "題號", "題目", "使用者答案", "使用者內容", "正確答案", "正確內容", "解析"])

                     # Append new wrong answers, avoiding duplicates for the same user/question combination
                     new_wrong_entries = []
                     # Create a set of existing wrong answers by user, chapter, question number (as strings)
                     existing_wrong_keys = set(tuple(map(str, row[["使用者", "章節", "題號"]].tolist())) for _, row in df_wrong_log.iterrows())

                     for entry in wrong_answers_this_quiz_run:
                         entry_key = (str(entry.get("使用者", "")), str(entry.get("章節", "")), str(entry.get("題號", "")))
                         # Check if the question is valid AND the entry is not a duplicate in the log
                         if (str(entry.get("章節", "")), str(entry.get("題號", ""))) in valid_questions_in_quiz_keys and entry_key not in existing_wrong_keys:
                              entry_to_append = {
                                  "使用者": entry.get("使用者", ""),
                                  "時間": entry.get("時間", ""),
                                  "章節": entry.get("章節", ""),
                                  "題號": entry.get("題號", ""),
                                  "題目": entry.get("題目", ""),
                                  "使用者答案": entry.get("使用者答案", ""),
                                  "使用者內容": entry.get("使用者內容", ""),
                                  "正確答案": entry.get("正確答案", ""),
                                  "正確內容": entry.get("正確內容", ""),
                                  "解析": entry.get("解析", "")
                              }
                              new_wrong_entries.append(entry_to_append)
                              existing_wrong_keys.add(entry_key)

                     if new_wrong_entries:
                         df_new_wrong = pd.DataFrame(new_wrong_entries)
                         required_cols = ["使用者", "時間", "章節", "題號", "題目", "使用者答案", "使用者內容", "正確答案", "正確內容", "解析"]
                         df_new_wrong = df_new_wrong.reindex(columns=required_cols)
                         df_wrong_log = pd.concat([df_wrong_log, df_new_wrong], ignore_index=True)
                         df_wrong_log.to_csv(WRONG_LOG, index=False)
                         # st.info(f"已記錄 {len(new_wrong_entries)} 筆錯題到錯題紀錄。") # Optional: show confirmation

                 except Exception as e:
                     st.error(f"記錄錯題時發生錯誤：{e}")


            # --- Restart Button (in Main Area after results) ---
            if st.button("🔄 重新出題", key="restart_quiz_button_completed"):
                 if st.session_state.last_settings:
                     st.session_state.quiz_started = True
                     st.session_state.user_answers = []
                     st.session_state.shuffled_options = {}

                     st.session_state.questions = generate_quiz_questions(
                         st.session_state.last_settings["username"],
                         st.session_state.last_settings["mode"],
                         st.session_state.last_settings["selected_chapters"],
                         st.session_state.last_settings["num_questions"],
                         df,
                         chapter_mapping,
                         WRONG_LOG
                     )

                     if st.session_state.questions.empty:
                         st.session_state.quiz_started = False
                         # st.warning already inside generate_quiz_questions
                     st.rerun()

                 else:
                     st.error("無法找到上一次的測驗設定。請使用側邊欄重新開始。")

        else:
            # Display progress
            answered_count_for_current_quiz = len(answered_valid_question_keys)
            st.markdown("---")
            st.info(f"已回答 {answered_count_for_current_quiz} / {total_valid_questions} 題。")
            if total_valid_questions > 0:
                 st.markdown("請繼續作答。")
            elif total_questions > 0 and total_valid_questions == 0:
                 st.warning("本次測驗中的所有題目解答格式均無效，無法完成作答。請通知管理者修正題庫。")
            # else: total_questions == 0, handled by load_data or generate_quiz_questions

    # Implicit else: If quiz_started is False, nothing is displayed in the main area except the title.
