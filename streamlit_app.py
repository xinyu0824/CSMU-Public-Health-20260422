import streamlit as st
import pandas as pd
import random

# --- 1. 網頁畫面設定 (Muji 質感) ---
st.set_page_config(page_title="📸 拍拍挑戰", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .task-box { background-color: #FFFFFF; padding: 25px; border: 1px solid #E6E6E1; border-radius: 4px; margin: 15px 0; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 2px; width: 100%; }
    .stButton>button:hover { border: 1px solid #8C8C8C; background-color: #EBEBE6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始設定與資料讀取 ---
SHEET_ID = "1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA"
USER_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=users"
TASK_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=tasks"

# 解決 CSV_URL 未定義的問題：統一使用 USER_CSV
@st.cache_data(ttl=10)
def load_data(url):
    try:
        return pd.read_csv(url)
    except Exception as e:
        return None

df_users = load_data(USER_CSV)

# --- 3. 初始化 Session State (預防 AttributeError) ---
if 'login' not in st.session_state:
    st.session_state.login = False
    st.session_state.real_name = ""
    st.session_state.student_id = ""
    st.session_state.nickname = ""
    st.session_state.current_task = "尚未領取任務"

# --- 4. 登入邏輯判斷 ---
if df_users is not None:
    COL_NAME = "name(姓名)"
    COL_ID = "Student ID(預設密碼)"
    COL_NICK = "Nickname(變更暱稱)"

    # A. 尚未登入：顯示登入介面
    if not st.session_state.login:
        st.title("🍂 拍照觀察員：身分登入")
        
        name_list = df_users[COL_NAME].dropna().tolist()
        selected_name = st.selectbox("帳號（預設為姓名）", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼（預設為學號）", type="password")

        if st.button("確認進入"):
            user_info = df_users[df_users[COL_NAME] == selected_name].iloc[0]
            correct_id = str(user_info[COL_ID]).strip()
            
            if input_pwd.strip() == correct_id:
                st.session_state.login = True
                st.session_state.real_name = selected_name
                st.session_state.student_id = correct_id
                # 處理暱稱為空值的情況
                nick = user_info[COL_NICK]
                st.session_state.nickname = "" if pd.isna(nick) else str(nick)
                st.rerun()
            else:
                st.error("密碼錯誤，請重新確認。")

    # B. 已登入：顯示個人空間
    else:
        # 決定顯示名稱：暱稱優先，若無則顯示本名
        display_name = st.session_state.nickname if st.session_state.nickname.strip() != "" else st.session_state.real_name

        st.title(f"📝 {display_name} 今天拍了沒📸")
        
        # 隱私灰色提示
        st.markdown(f"""
            <p style='color: #8C8C8C; font-size: 0.8rem; margin-top: -15px;'>
            已認證觀察員：{st.session_state.real_name} (ID: {st.session_state.student_id})
            </p>
        """, unsafe_allow_html=True)
        
        # 任務顯示區 (不須點擊直接顯示)
        st.markdown(f"""
        <div class="task-box">
            <p style="font-size: 0.8rem; color: #8C8C8C; margin: 0;">當前觀察目標</p>
            <h2 style="margin: 10px 0;">{st.session_state.current_task}</h2>
        </div>
        """, unsafe_allow_html=True)

        # 功能分頁
        tab1, tab2, tab3 = st.tabs(["🎯 領取任務", "🎁 抽獎進度", "⚙️ 個人設定"])

        with tab1:
            st.subheader("隨機抽取今日任務")
            difficulty = st.radio("選擇觀察難度", ["初級 (抽5張)", "中級 (抽3張)", "挑戰 (抽1張)"], horizontal=True)
            
            if st.button("🎲 隨機變更任務內容"):
                try:
                    df_tasks = pd.read_csv(TASK_CSV)
                    # 篩選難度（取標籤前兩個字，如「初級」）
                    target_diff = difficulty[:2]
                    filtered_tasks = df_tasks[df_tasks['difficulty'] == target_diff]
                    
                    if not filtered_tasks.empty:
                        new_task = random.choice(filtered_tasks['content'].tolist())
                        st.session_state.current_task = new_task
                        st.success("任務更新成功！")
                        st.rerun()
                    else:
                        st.warning(f"目前任務池中沒有「{target_diff}」等級的內容。")
                except:
                    st.error("讀取任務表失敗，請確認 Google Sheet 中有名為 'tasks' 的分頁。")

        with tab2:
            st.subheader("抽獎券累積進度")
            tickets = 1 # 這裡之後可以串接資料庫統計
            st.write(f"目前已獲得： **{tickets}** 張現場抽獎券")
            st.progress(tickets/10, text=f"累積進度：{tickets}/10")
            st.image("https://img.icons8.com/color/96/ticket.png")

        with tab3:
            st.subheader("帳號設定")
            st.write(f"真實姓名：{st.session_state.real_name}")
            new_nick = st.text_input("更換暱稱（暫時性）", value=st.session_state.nickname)
            if st.button("確認修改"):
                st.session_state.nickname = new_nick
                st.success("暱稱已修改！")
                st.rerun()
            st.info("💡 提醒：目前更換僅限本次登入，若需永久儲存請告知班代。")

else:
    st.error("❌ 無法連線至資料庫，請檢查 Google Sheets 連結與權限。")
