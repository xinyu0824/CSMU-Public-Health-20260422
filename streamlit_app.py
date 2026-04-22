import streamlit as st
import pandas as pd
import random

# --- 1. 無印風美學設定 ---
st.set_page_config(page_title=" 📸拍拍挑戰", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .task-box { background-color: #FFFFFF; padding: 20px; border: 1px solid #E6E6E1; border-radius: 4px; margin: 10px 0; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 資料讀取_任務 ---
SHEET_ID = "1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA"
# 讀取用戶資料
USER_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=users"
# 讀取任務清單 (請確保妳有建立一個 tasks 分頁)
TASK_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=tasks"

@st.cache_data(ttl=10)
def get_data(url):
    return pd.read_csv(url)

df_users = get_data(USER_CSV)

# --- 3. 讀取資料_帳號密碼 ---
@st.cache_data(ttl=10)
def get_data():
    try:
        # 直接用 pandas 讀取，這不經過 Secrets，最直覺
        return pd.read_csv(CSV_URL)
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return None

df = get_data()

# --- 4. 登入邏輯 ---
if 'login' not in st.session_state:
    st.session_state.login = False

if df is not None:
    # 定義妳的欄位名稱 (請確保 Google Sheet 第一列完全符合)
    COL_NAME = "name(姓名)"
    COL_ID = "Student ID(預設密碼)"
    COL_NICK = "Nickname(變更暱稱)"

    if not st.session_state.login:
        st.title("🍂拍照觀察員：身分登入")
        
        # 檢查欄位是否存在
        if COL_NAME not in df.columns:
            st.error(f"找不到欄位 '{COL_NAME}'，請檢查 Excel 第一列。")
            st.write("目前的欄位有：", list(df.columns))
            st.stop()

        name_list = df[COL_NAME].dropna().tolist()
        selected_name = st.selectbox("帳號（預設為姓名）", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼（預設為學號）", type="password")

        if st.button("確認進入"):
            user_info = df[df[COL_NAME] == selected_name].iloc[0]
            correct_id = str(user_info[COL_ID]).strip()
            
            if input_pwd.strip() == correct_id:
                # 這裡最關鍵：登入成功後要記得這三項資訊
                st.session_state.login = True
                st.session_state.real_name = selected_name # 存下本名
                st.session_state.student_id = correct_id  # 存下學號
                st.session_state.nickname = user_info[COL_NICK] # 存下暱稱
                st.rerun()
            else:
                st.error("密碼錯誤")

else:
            display_name = st.session_state.nickname

        # 大標題：質感顯示
        st.title(f"📝 {display_name} 今天拍了沒📸")
        
        # 小小的灰色提示：增加安全感與儀式感
        st.markdown(f"""
            <p style='color: #8C8C8C; font-size: 0.8rem; margin-top: -15px;'>
            已認證觀察員：{st.session_state.real_name} (ID: {st.session_state.student_id})
            </p>
        """, unsafe_allow_html=True)
        
        st.write("---") # 分隔線
        st.write("歡迎回來！現在就來看看今日的觀察任務吧。")
        
        # 之後這裡就可以接著放妳的「任務卡片」跟「上傳按鈕」
        
# --- 5. 登入後介面 ---
else:
    st.title(f"📝 {st.session_state.nickname} 的觀察空間")
    
    # 【核心功能 A：我的任務顯示區】(不須點擊就能看到)
    st.markdown(f"""
    <div class="task-box">
        <p style="font-size: 0.8rem; color: #8C8C8C; margin: 0;">當前觀察目標</p>
        <h2 style="margin: 10px 0;">{st.session_state.current_task}</h2>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🎯 領取任務", "🎁 抽獎進度", "⚙️ 個人設定"])

    with tab1:
        st.subheader("隨機抽取今日任務")
        difficulty = st.radio("選擇觀察難度", ["初級 (抽5張)", "中級 (抽3張)", "挑戰 (抽1張)"], horizontal=True)
        
        if st.button("🎲 隨機變更任務內容"):
            try:
                df_tasks = pd.read_csv(TASK_CSV)
                # 篩選難度並隨機抽一個
                filtered_tasks = df_tasks[df_tasks['difficulty'] == difficulty.split(" ")[0]]
                if not filtered_tasks.empty:
                    new_task = random.choice(filtered_tasks['content'].tolist())
                    st.session_state.current_task = new_task
                    st.success("任務已更新！")
                    st.rerun()
                else:
                    st.warning("Google Sheet 的 tasks 分頁中找不到對應難度的任務。")
            except:
                st.error("請確認妳的 Google Sheet 有一個名為 'tasks' 的分頁，且欄位有 'difficulty' 和 'content'。")

    with tab2:
        st.subheader("抽獎券累積")
        # 這裡未來可以對接妳 Google Sheets 紀錄的已完成張數
        tickets = 2 # 假設值
        st.write(f"目前已獲得： **{tickets}** 張現場抽獎券")
        st.progress(tickets/10, text=f"累積進度：{tickets}/10")
        st.image("https://img.icons8.com/color/96/ticket.png") # 簡單的視覺圖標

    with tab3:
        st.subheader("設定")
        st.write(f"真實姓名：{st.session_state.real_name}")
        new_nick = st.text_input("更換暱稱", value=st.session_state.nickname)
        st.info("💡 提醒：目前效率模式下，暱稱更換僅限本次登入有效。若需永久儲存，請聯繫班代登記。")
