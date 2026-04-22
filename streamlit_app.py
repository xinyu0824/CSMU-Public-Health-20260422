import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 定義妳的精確欄位名稱
COL_NAME = "name(姓名)"
COL_ID = "Student ID(預設密碼)"
COL_NICK = "Nickname(變更暱稱)"
COL_STATUS = "status(啟用狀況)"

# 3. 直接使用硬編碼網址進行測試 (已移除 ?usp=sharing)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit"

try:
    # 注意：這裡我們直接傳入 spreadsheet 參數，暫時不用管 Secrets
    df = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
    st.success("🎉 太棒了！資料庫成功連線！")
except Exception as e:
    st.error(f"❌ 依然失敗，偵錯訊息：{e}")
    st.stop()

# --- 後續登入邏輯保持不變 ---
st.title("🍂 甲班生活日誌：身分確認")

name_list = df[COL_NAME].dropna().tolist()
selected_name = st.selectbox("請選擇您的姓名", ["請選擇"] + name_list)
input_pwd = st.text_input("請輸入學號驗證 (Student ID)", type="password")

if st.button("確認進入系統"):
    if selected_name != "請選擇":
        user_info = df[df[COL_NAME] == selected_name].iloc[0]
        correct_id = str(user_info[COL_ID]).strip()
        
        if input_pwd.strip() == correct_id:
            st.session_state.login = True
            st.session_state.real_name = selected_name
            st.session_state.nickname = user_info[COL_NICK]
            st.success("登入成功！")
            st.rerun()
        else:
            st.error("密碼錯誤，請檢查學號。")
