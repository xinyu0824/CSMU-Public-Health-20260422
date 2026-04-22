import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 基礎美學設定 (無印良品風) ---
st.set_page_config(page_title="甲班生活觀察計畫", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; } /* 暖米色背景 */
    h1, h2, p, label, .stMarkdown { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .stButton>button {
        background-color: #FFFFFF; color: #5F5F5F;
        border: 1px solid #D9D9D9; border-radius: 2px;
        transition: 0.3s;
    }
    .stButton>button:hover { border: 1px solid #8C8C8C; background-color: #EBEBE6; }
    /* 卡片裝飾 */
    .css-card {
        background-color: #FFFFFF; padding: 25px;
        border-radius: 4px; border: 1px solid #E6E6E1;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 ---
# 這裡我們直接使用妳提供的 URL，確保不被 Secrets 設定干擾
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit"

# 定義精確欄位名稱
COL_NAME = "name(姓名)"
COL_ID = "Student ID(預設密碼)"
COL_NICK = "Nickname(變更暱稱)"
COL_STATUS = "status(啟用狀況)"

# 建立連線並讀取資料
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10) # 暫時設為 10 秒，方便測試
def load_data():
    try:
        # 直接讀取 users 分頁
        return conn.read(spreadsheet=SHEET_URL, worksheet="users")
    except Exception as e:
        st.error(f"⚠️ 連線受阻：{e}")
        st.info("💡 請檢查 Google Sheets 是否已設為「知道連結的任何人」皆可「編輯」。")
        return None

df = load_data()

# --- 3. 登入系統邏輯 ---
if 'login' not in st.session_state:
    st.session_state.login = False

# 如果讀取失敗，就停止執行
if df is None:
    st.stop()

if not st.session_state.login:
    st.title("🍂 觀察員日誌：身分確認")
    st.write("請選擇您的身分並輸入學號以開啟紀錄")
    
    with st.container():
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        
        # 取得姓名清單
        name_list = df[COL_NAME].dropna().tolist()
        selected_name = st.selectbox("您的真實姓名", ["搜尋名字"] + name_list)
        
        # 輸入密碼 (學號)
        input_pwd = st.text_input("學號驗證 (Password)", type="password")
        
        if st.button("確認進入"):
            if selected_name != "搜尋名字":
                # 抓取該生整列資訊
                user_info = df[df[COL_NAME] == selected_name].iloc[0]
                # 強制轉換為字串並去除空白
                correct_id = str(user_info[COL_ID]).strip()
                
                if input_pwd.strip() == correct_id:
                    st.session_state.login = True
                    st.session_state.real_name = selected_name
                    st.session_state.student_id = correct_id
                    st.session_state.nickname = user_info[COL_NICK]
                    st.success("身分確認成功，載入中...")
                    st.rerun()
                else:
                    st.error("密碼（學號）錯誤，請重新輸入。")
            else:
                st.warning("請先選取您的姓名。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 4. 登入成功後的主畫面 ---
else:
    st.title(f"📝 {st.session_state.nickname} 的觀察計畫")
    st.write(f"目前身分：{st.session_state.real_name} 觀察員")

    tab1, tab2 = st.tabs(["觀察任務領取", "個人檔案設定"])
    
    with tab1:
        st.info("📡 任務派發系統建置中，敬請期待導生聚揭曉。")
        
    with tab2:
        st.subheader("⚙️ 檔案維護")
        new_nick = st.text_input("變更暱稱", value=st.session_state.nickname)
        if st.button("更新暱稱紀錄"):
            # 下一步我們要實作寫回 Google Sheets 的功能
            st.success(f"暱稱已暫時更新為：{new_nick}")
