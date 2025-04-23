...

# 每題答題次數統計顯示（根據 STATS_LOG）
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

...