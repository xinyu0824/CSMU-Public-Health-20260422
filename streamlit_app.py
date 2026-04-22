import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 建立連線 (建議 TTL 設短一點，這樣妳改 Excel 後網頁才會快點更新)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 定義欄位名稱變數 (避免之後打錯字)
COL_NAME = "name(姓名)"
COL_ID = "Student ID(預設密碼)"
COL_NICK = "Nickname(變更暱稱)"
COL_STATUS = "status(啟用狀況)"

# 3. 讀取名冊 (修改這段來抓出真兇)
try:
    df = conn.read(worksheet="users", ttl=0) # 先改為 0 測試
except Exception as e:
    st.error(f"❌ 偵錯訊息：{e}") # 這行會告訴我們真正的報錯原因
    st.stop()

# --- 無印良品 Muji 風格設定 ---
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: white; border-radius: 2px; }
    </style>
    """, unsafe_allow_html=True)

# 4. 登入邏輯
if 'login' not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("今天拍了沒")
    
    # 這裡使用妳指定的精確欄位名稱
    name_list = df[COL_NAME].dropna().tolist()
    selected_name = st.selectbox("帳號（預設為本名）", ["請選擇"] + name_list)
    
    # 這裡使用妳指定的學號欄位
    input_pwd = st.text_input("密碼（預設為學號）", type="password")
    
    if st.button("確認登入"):
        if selected_name != "請選擇":
            # 抓取該學生的整列資料
            user_info = df[df[COL_NAME] == selected_name].iloc[0]
            
            # 這裡特別處理：強迫將讀到的學號轉為字串進行比對，避免科學記號或浮點數問題
            correct_id = str(user_info[COL_ID]).strip()
            
            if input_pwd.strip() == correct_id:
                st.session_state.login = True
                st.session_state.real_name = selected_name
                st.session_state.student_id = correct_id
                st.session_state.nickname = user_info[COL_NICK]
                st.success("身分確認成功！")
                st.rerun()
            else:
                st.error("學號(密碼)錯誤，請重新輸入。")
        else:
            st.warning("請先在選單中找到您的名字。")

# --- 登入後的頁面 ---
else:
    st.title(f"📝 {st.session_state.nickname} 的觀察計畫")
    
    tab1, tab2 = st.tabs(["觀察任務", "個人設定"])
    
    with tab1:
        st.info("任務選單開發中，請稍後...")

    with tab2:
        st.subheader("觀察員資料設定")
        st.write(f"真實姓名：{st.session_state.real_name}")
        st.write(f"學號紀錄：{st.session_state.student_id}")
        
        # 顯示當前的狀態
        current_status = df[df[COL_NAME] == st.session_state.real_name][COL_STATUS].values[0]
        st.write(f"目前帳號狀態：**{current_status}**")
        
        # 讓同學改暱稱
        new_nick = st.text_input("想要變更的暱稱", value=st.session_state.nickname)
        if st.button("更新我的暱稱"):
            # 這裡之後會教妳如何用 conn.update 寫回 Google Sheets
            st.success(f"已暫時更新為：{new_nick} (存檔功能串接中)")
