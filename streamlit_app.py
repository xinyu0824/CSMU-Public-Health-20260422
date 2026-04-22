import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 讀取名冊 (快取 10 分鐘，避免頻繁刷網頁)
df = conn.read(worksheet="users", ttl=600)

# --- 無印風 CSS 保持質感 ---
st.markdown("""<style>.stApp { background-color: #F5F5F0; }</style>""", unsafe_allow_html=True)

# 3. 登入邏輯
if 'login' not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🍂 甲班生活日誌：身分確認")
    
    # 讓同學用選單選名字，不用自己打字
    name_list = df['name'].tolist()
    selected_name = st.selectbox("請選擇您的姓名", ["請選擇"] + name_list)
    
    input_pwd = st.text_input("請輸入學號驗證", type="password")
    
    if st.button("登入系統"):
        if selected_name != "請選擇":
            # 找到該同學在那一行
            user_data = df[df['name'] == selected_name].iloc[0]
            
            # 驗證學號是否正確
            if input_pwd == str(user_data['student_id']):
                st.session_state.login = True
                st.session_state.student_id = user_data['student_id']
                st.session_state.nickname = user_data['nickname']
                st.success("身分確認成功！正在載入...")
                st.rerun()
            else:
                st.error("學號輸入錯誤，請重新確認。")
        else:
            st.warning("請先選擇您的姓名。")

# --- 登入後的主畫面 ---
else:
    st.title(f"📝 {st.session_state.nickname} 的觀察計畫")
    # 之後這裡可以加上「修改暱稱」與「領取任務」的功能
