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
STATS_LOG = "答題統計.csv"
EDIT_PASSWORD = "quiz2024"

@st.cache_data
def load_data():
    """Loads the question data from the Excel file."""
    try:
        return pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    except FileNotFoundError:
        st.error(f"錯誤：找不到題庫檔案 `{EXCEL_PATH}`。請確認檔案是否存在。")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"載入題庫時發生錯誤：{e}")
        return pd.DataFrame()

df = load_data()

chapter_mapping = {f"CH{i}": [f"{i}-1", f"{i}-2"] for i in range(1, 10)}

for key in ["quiz_started", "questions", "user_answers", "shuffled_options", "last_settings", "is_admin_mode"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "is_admin_mode" or key == "quiz_started" else [] if key.endswith("s") else None

def generate_quiz_questions(username, mode, selected_chapters, num_questions, dataframe, chapter_map, wrong_log_path):
    """Generates a list of questions based on the selected mode and settings."""
    if dataframe.empty:
         st.warning("題庫資料為空，無法產生題目。")
         return pd.DataFrame()

    if mode == "一般出題模式":
        sections = [s for ch in selected_chapters for s in chapter_map.get(ch, [])]
        filtered = dataframe[dataframe["章節"].astype(str).isin(sections)]
        if filtered.empty:
             st.warning(f"找不到符合所選章節 ({', '.join(selected_chapters)}) 的題目。")
             return pd.DataFrame()

    elif mode == "錯題再練模式":
        if os.path.exists(wrong_log_path):
            try:
                log = pd.read_csv(wrong_log_path)
                user_wrong_log = log[log["使用者"].str.lower() == username.lower()]

                if selected_chapters:
                    sections = [s for ch in selected_chapters for s in chapter_map.get(ch, [])]
                    user_wrong_log = user_wrong_log[user_wrong_log["章節"].astype(str).isin(sections)]

                if user_wrong_log.empty:
                     st.info(f"使用者 `{username}` 沒有錯題紀錄，或所選章節 ({', '.join(selected_chapters)}) 中沒有錯題。")
                     return pd.DataFrame()

                filtered = dataframe.merge(
                    user_wrong_log[["章節", "題號"]].drop_duplicates(),
                    on=["章節", "題號"]
                )
                if filtered.empty:
                     st.warning(f"根據錯題紀錄，找不到對應的題目。")
                     return pd.DataFrame()

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

    else:
        st.error("內部錯誤：無效的測驗模式選擇。")
        return pd.DataFrame()

    if not filtered.empty:
        return filtered.sample(n=min(num_questions, len(filtered))).reset_index(drop=True)
    else:
        return pd.DataFrame()


# --- Sidebar ---
st.sidebar.header("使用者與模式設定")
st.session_state.username = st.sidebar.text_input("請輸入使用者名稱", value=st.session_state.get("username", ""), key="username_input")

if not st.session_state.is_admin_mode:
    quiz_mode = st.sidebar.radio("選擇模式：", ["一般出題模式", "錯題再練模式"], key="quiz_mode_radio")
    selected_chapters = st.sidebar.multiselect("選擇章節：", list(chapter_mapping.keys()), default=["CH1"], key="chapters_select")
    num_questions = st.sidebar.number_input("出題數量", min_value=1, max_value=50, value=5, key="num_questions_input")

    if st.sidebar.button("🚀 開始出題", key="start_quiz_button"):
        if not st.session_state.username.strip():
            st.sidebar.warning("請先輸入使用者名稱！")
        elif df.empty:
             st.sidebar.warning("題庫資料為空，無法開始測驗。")
        else:
            st.session_state.quiz_started = True
            st.session_state.user_answers = []
            st.session_state.shuffled_options = {}
            st.session_state.last_settings = {
                "username": st.session_state.username,
                "mode": quiz_mode,
                "selected_chapters": selected_chapters,
                "num_questions": num_questions
            }
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

st.sidebar.markdown("---")
st.session_state.is_admin_mode = st.sidebar.checkbox("🛠️ 啟用管理者模式", key="admin_mode_checkbox")

# --- Main Content Area ---
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
                    options_list = result.apply(lambda x: f"{x['章節']}-{x['題號']} {x['題目']}", axis=1).tolist()
                    selected_label = st.selectbox("選擇題目", options_list, key="select_question_edit")
                    selected_row_data = result[result.apply(lambda x: f"{x['章節']}-{x['題號']} {x['題目']}", axis=1) == selected_label].iloc[0]

                    st.write(f"目前章節-題號: {selected_row_data.get('章節', 'N/A')}-{selected_row_data.get('題號', 'N/A')}")
                    st.write(f"題目內文: {selected_row_data.get('題目', 'N/A')}")

                    new_A = st.text_input("選項 A", selected_row_data.get("A", ""), key="edit_A")
                    new_B = st.text_input("選項 B", selected_row_data.get("B", ""), key="edit_B")
                    new_C = st.text_input("選項 C", selected_row_data.get("C", ""), key="edit_C")
                    new_D = st.text_input("選項 D", selected_row_data.get("D", ""), key="edit_D")
                    new_expl = st.text_area("解析", selected_row_data.get("解析", ""), key="edit_expl")

                    if st.button("✅ 更新題目", key="update_question_button"):
                        try:
                            wb = load_workbook(EXCEL_PATH)
                            ws = wb[SHEET_NAME]
                            for row in ws.iter_rows(min_row=2):
                                if str(row[0].value) == str(selected_row_data.get("章節", None)) and str(row[1].value) == str(selected_row_data.get("題號", None)):
                                    row[2].value = new_A
                                    row[3].value = new_B
                                    row[4].value = new_C
                                    row[5].value = new_D
                                    row[9].value = new_expl
                                    break
                            wb.save(EXCEL_PATH)
                            st.success("✅ 題目已更新成功")
                            st.cache_data.clear()
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
                                st.rerun()
                        elif submode == "全部使用者":
                            st.warning("此操作將清除所有使用者的錯題紀錄，無法復原！")
                            if st.button("🧨 確認清除全部錯題", key="clear_all_wrong_button"):
                                os.remove(WRONG_LOG)
                                st.success("已清除所有錯題紀錄檔案")
                                st.rerun()
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

    elif admin_pwd != "":
         st.error("密碼錯誤")

# Display Quiz Interface if not in Admin Mode and quiz is started
else: # st.session_state.is_admin_mode is False
    # In quiz mode, define the valid answer labels
    VALID_ANSWER_LABELS = ['A', 'B', 'C', 'D']

    if st.session_state.quiz_started and st.session_state.questions is not None and not st.session_state.questions.empty:
        total_questions_in_quiz = len(st.session_state.questions)
        # all_answered flag will be determined after the loop finishes

        for i, row in st.session_state.questions.iterrows():
            question_key = f"q{i}_quiz" # Unique key for the radio button

            # Find if this question has a recorded answer in session state *at the start of this rerun's loop iteration*
            answered_item_at_start_of_rerun = next((item for item in st.session_state.user_answers if item.get("章節") == row.get("章節") and item.get("題號") == row.get("題號")), None)

            # Prepare options list for display
            display_options = []
            labels = ['A', 'B', 'C', 'D'] # Define labels here for zipped

            # Get shuffled options (from session state) and map to original labels
            shuffled_key = f"q{i}_options_quiz"
            if shuffled_key not in st.session_state.shuffled_options:
                options = [row.get('A', ''), row.get('B', ''), row.get('C', ''), row.get('D', '')]
                options = [str(opt) if opt is not None else "N/A" for opt in options]
                zipped = list(zip(labels, options))
                random.shuffle(zipped)
                st.session_state.shuffled_options[shuffled_key] = zipped
            else:
                zipped = st.session_state.shuffled_options[shuffled_key]

            # Show A.B.C.D labels if the question was answered *before this loop iteration started*
            if answered_item_at_start_of_rerun is not None:
                display_options = [f"{label}. {opt_text}" for label, opt_text in zipped]
            else:
                display_options = [opt_text for label, opt_text in zipped]

            # --- Determine the index of the option that should be initially selected ---
            initial_selection_index = None
            current_radio_state_value = st.session_state.get(question_key)

            if current_radio_state_value is not None:
                try:
                     initial_selection_index = display_options.index(current_radio_state_value)
                except ValueError:
                     original_text_from_state = None
                     for label, opt_text in zipped:
                          if current_radio_state_value == opt_text or (isinstance(current_radio_state_value, str) and current_radio_state_value == f"{label}. {opt_text}"):
                              original_text_from_state = opt_text
                              break

                     if original_text_from_state is not None:
                         for j, display_str in enumerate(display_options):
                              if isinstance(display_str, str) and original_text_from_state in display_str:
                                   initial_selection_index = j
                                   break

            with st.container():
                st.markdown(f"**Q{i + 1}. {row.get('題目', 'N/A')}**")

                # Display radio buttons
                disabled_status = answered_item_at_start_of_rerun is not None
                selected = st.radio("選項：", display_options,
                                    key=question_key,
                                    index=initial_selection_index,
                                    disabled=disabled_status)


                # --- Handle Feedback, Explanation, and Recording if Selected ---
                if selected is not None:
                    answered_item_before_recording = next((item for item in st.session_state.user_answers if item.get("章節") == row.get("章節") and item.get("題號") == row.get("題號")), None)

                    if answered_item_before_recording is None:
                         # --- Record the New Answer ---
                         original_selected_text = selected
                         user_ans_label = next((label for label, opt_text in zipped if opt_text == original_selected_text), None)

                         if original_selected_text is not None and user_ans_label is not None:
                            correct_label_actual = str(row.get("解答", "")).strip().upper()
                            if correct_label_actual not in VALID_ANSWER_LABELS or not correct_label_actual:
                                st.error(f"題目 {row.get('章節', 'N/A')}-{row.get('題號', 'N/A')} 的解答格式錯誤：'{row.get('解答', 'None')}'。此題無法記錄作答結果。")
                            else:
                                is_correct = (user_ans_label == correct_label_actual)

                                newly_answered_item = {
                                     "使用者": st.session_state.username,
                                     "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                     "正確答案": correct_label_actual,
                                     "正確內容": row.get(correct_label_actual, "N/A"),
                                     "使用者答案": user_ans_label,
                                     "使用者內容": original_selected_text,
                                     "章節": row.get("章節", "N/A"),
                                     "題號": row.get("題號", "N/A"),
                                     "題目": row.get("題目", "N/A"),
                                     "解析": row.get("解析", "無解析"),
                                     "是否正確": is_correct
                                }
                                st.session_state.user_answers.append(newly_answered_item)

                                # --- Display Feedback and Explanation for the NEW answer ---
                                if newly_answered_item.get("是否正確") is True:
                                    st.success(f"✅ 答對了！")
                                else:
                                    st.error(f"❌ 答錯了。正確答案是：{newly_answered_item.get('正確答案', 'N/A')}. {newly_answered_item.get('正確內容', 'N/A')}")
                                st.markdown(f"※{newly_answered_item.get('章節', 'N/A')}第{newly_answered_item.get('題號', 'N/A')}題解析：{newly_answered_item.get('解析', '無解析')}")

                    else:
                      # --- Display Feedback and Explanation for the PREVIOUS answer ---
                      if answered_item_before_recording.get("是否正確") is True:
                          st.success(f"✅ 答對了！")
                      else:
                          st.error(f"❌ 答錯了。正確答案是：{answered_item_before_recording.get('正確答案', 'N/A')}. {answered_item_before_recording.get('正確內容', 'N/A')}")
                      st.markdown(f"※{answered_item_before_recording.get('章節', 'N/A')}第{answered_item_before_recording.get('題號', 'N/A')}題解析：{answered_item_before_recording.get('解析', '無解析')}")


        # --- Evaluate Quiz Completion and Display Results After the Loop ---
        # Calculate total valid questions ONCE after the loop
        final_total_valid_questions = len([
             1 for _, row in st.session_state.questions.iterrows()
             if str(row.get("解答", "")).strip().upper() in VALID_ANSWER_LABELS
        ])

        # Calculate answered count (unique) ONCE after the loop
        # This counts unique questions from user_answers that are in the current quiz set
        answered_questions_in_quiz = {(item.get("章節"), item.get("題號")) for item in st.session_state.user_answers if (item.get("章節"), item.get("題號")) in [(str(q.get("章節", "")), str(q.get("題號", ""))) for _, q in st.session_state.questions.iterrows()]}
        final_answered_count = len(answered_questions_in_quiz)


        # Determine if all answered using these final counts
        # This condition controls whether the final results block is shown
        all_answered = final_total_valid_questions > 0 and final_answered_count >= final_total_valid_questions


        # --- Display Results and Restart Button ---
        if all_answered:
            st.markdown("---")
            # Calculate correct count based on all correct answers within the current quiz set
            final_correct_count = sum(1 for item in st.session_state.user_answers if (item.get('章節'), item.get('題號')) in [(str(q.get('章節', '')), str(q.get('題號', ''))) for _, q in st.session_state.questions.iterrows()] and item.get('是否正確') is True)
            st.markdown(f"### 🎯 本次測驗結果：總計 {final_total_valid_questions} 題，答對 {final_correct_count} 題")

            # --- Logging Wrong Answers (after quiz completion) ---
            wrong_answers_this_quiz_set = [
                item for item in st.session_state.user_answers
                if (item.get("章節"), item.get("題號")) in [(str(q.get("章節", "")), str(q.get("題號", ""))) for _, q in st.session_state.questions.iterrows()]
                and item.get("是否正確") is False
            ]

            if wrong_answers_this_quiz_set:
                try:
                    if os.path.exists(WRONG_LOG):
                        df_wrong_log = pd.read_csv(WRONG_LOG)
                    else:
                        df_wrong_log = pd.DataFrame(columns=["使用者", "時間", "章節", "題號", "題目", "使用者答案", "使用者內容", "正確答案", "正確內容", "解析"])

                    new_wrong_entries = []
                    existing_wrong_keys = set(tuple(map(str, row[["使用者", "章節", "題號"]].tolist())) for _, row in df_wrong_log.iterrows())

                    for entry in wrong_answers_this_quiz_set:
                        entry_key = (str(entry.get("使用者", "")), str(entry.get("章節", "")), str(entry.get("題號", "")))
                        if entry_key not in existing_wrong_keys:
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
                except Exception as e:
                    st.error(f"記錄錯題時發生錯誤：{e}")

            # --- Restart Button ---
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
                        st.warning("找不到符合條件的題目，無法重新出題。請檢查設定或錯題紀錄。")
                 else:
                    st.error("無法找到上一次的測驗設定。請使用側邊欄重新開始。")
        else:
             st.markdown("---")
             # Use VALID_ANSWER_LABELS for calculating valid questions for progress display (should be the same as final_total_valid_questions)
             progress_total_valid = len([
                  1 for _, row in st.session_state.questions.iterrows()
                  if str(row.get("解答", "")).strip().upper() in VALID_ANSWER_LABELS
             ])
             # Count UNIQUE answered questions for progress display (should be the same as final_answered_count)
             answered_questions_in_quiz_progress = {(item.get("章節"), item.get("題號")) for item in st.session_state.user_answers if (item.get("章節"), item.get("題號")) in [(q.get("章節", ""), q.get("題號", "")) for _, q in st.session_state.questions.iterrows()]}
             progress_answered_count = len(answered_questions_in_quiz_progress)


             st.info(f"已回答 {progress_answered_count} / {progress_total_valid} 題。")
             if progress_total_valid > progress_answered_count:
                st.markdown("請繼續作答。")
