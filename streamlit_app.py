import streamlit as st

# 1. 網頁基本設定
st.set_page_config(page_title="甲班生活觀察計畫", layout="centered")

# 2. 無印良品 (Muji) 極簡風 CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #F5F5F0; /* 暖米色背景 */
    }
    .stButton>button {
        background-color: #FFFFFF;
        color: #5F5F5F;
        border: 1px solid #D9D9D9;
        border-radius: 2px;
        width: 100%;
    }
    .stTextInput>div>div>input {
        background-color: #FFFFFF;
        border-radius: 2px;
    }
    h1, h2, p {
        color: #5F5F5F !important;
        font-family: 'Noto Sans TC', sans-serif;
    }
    /* 任務卡片樣式 */
    .task-card {
        background-color: #FFFFFF;
        padding: 20px;
        border: 1px solid #E6E6E1;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 登入邏輯 ---
if 'login' not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🍂 甲班生活觀察計畫")
    st.write("Observer's Log - 請輸入您的專屬身分以開啟紀錄")
    
    with st.container():
        st.markdown('<div class="task-card">', unsafe_allow_html=True)
        user_id = st.text_input("學號 (預設密碼)")
        if st.button("確認進入"):
            if user_id: # 之後對接 Google Sheets 的學號清單
                st.session_state.login = True
                st.session_state.user_id = user_id
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 主程式面 ---
else:
    st.title("📝 觀察員日誌")
    st.write(f"當前登入：{st.session_state.user_id}")
    
    # 橫向導覽列（Streamlit 新功能）
    tab1, tab2, tab3 = st.tabs(["領取任務", "我的進度", "關於計畫"])
    
    with tab1:
        st.subheader("選擇您的觀察難度")
        level = st.radio("難度將影響需完成的任務數量", ["容易 (需5張)", "中等 (需3張)", "挑戰 (需1張)"], horizontal=True)
        
        st.markdown('---')
        
        # 根據難度動態顯示任務 (這裡之後可以改成從 Excel 讀取)
        if "容易" in level:
            task = st.selectbox("請選擇一個初級任務", ["拍到兩杯一模一樣的飲料", "拍到三雙白布鞋", "拍到大家都在滑手機"])
        elif "中等" in level:
            task = st.selectbox("請選擇一個中級任務", ["拍到教授的板書筆誤", "拍到有人上課看 Netflix", "拍到五個人同時抬頭"])
        else:
            task = st.selectbox("請選擇一個挑戰任務", ["拍到兩位教授同時在場", "拍到全班一起看鏡頭"])
            
        uploaded_file = st.file_uploader("上傳觀察照片", type=['jpg', 'png', 'jpeg'])
        
        if st.button("提交觀察結果"):
            with st.status("正在將情報加密傳送至後台..."):
                # 這裡就是寫入 Google Sheets 的地方
                st.success("提交成功！照片已安全存檔。")
                st.balloons() # 小小的儀式感慶祝

    with tab2:
        st.write("🔒 本階段照片已加密處理。")
        st.info("您的所有觀察紀錄將在「大型導生聚」當天統一現場解密。")
        # 這裡可以顯示該學號已完成的數量進度條
        st.progress(0.4, text="目前達成進度：40%")
