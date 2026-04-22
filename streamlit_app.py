import streamlit as st
import pandas as pd
import random

# --- 1. 網頁質感設定 ---
st.set_page_config(page_title="📸 拍拍挑戰", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .mission-frame { border: 2px solid #D9D9D9; border-radius: 8px; padding: 20px; margin-bottom: 25px; background-color: #FFFFFF; }
    .gallery-item { background-color: white; border: 1px solid #E6E6E1; padding: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.03); }
    .gallery-text { font-size: 0.65rem; color: #8C8C8C; text-align: center; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 資料讀取 ---
SHEET_ID = "1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA"
USER_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=users"
TASK_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=tasks"

@st.cache_data(ttl=5) # 縮短快取時間，讓更新更有感
def load_data(url):
    try: return pd.read_csv(url)
    except: return None

df_users = load_data(USER_CSV)
df_tasks = load_data(TASK_CSV)

# --- 3. 初始化 Session ---
if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'current_task': "尚未領取任務", 'user_data': None})

# --- 4. 登入邏輯 ---
if df_users is not None:
    if not st.session_state.login:
        st.title("🍂 觀察員登入")
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼", type="password")
        if st.button("確認進入"):
            user_info = df_users[df_users["name(姓名)"] == selected_name].iloc[0]
            if input_pwd.strip() == str(user_info["Student ID(預設密碼)"]).strip():
                st.session_state.login = True
                st.session_state.user_data = user_info
                st.rerun()
    
    # --- 5. 登入後介面 ---
    else:
        user = st.session_state.user_data
        nickname = user["Nickname(變更暱稱)"]
        display_name = nickname if pd.notna(nickname) and str(nickname).strip() != "" else user["name(姓名)"]
        
        st.title(f"📝 {display_name} 的特工空間")

        # 【功能一：動態不規則照片牆】
        # 檢查是否有照片數據 (假設欄位名為 photo_list)
        if "photo_list" in user and pd.notna(user["photo_list"]):
            photos = str(user["photo_list"]).split(",")
            st.write("🖼️ 過去觀察紀錄")
            cols = st.columns([1, 1.2, 0.9, 1.1])
            for i, p_url in enumerate(photos):
                with cols[i % 4]:
                    st.markdown(f'<div class="gallery-item"><img src="{p_url.strip()}" style="width:100%; border-radius:2px;"></div>', unsafe_allow_html=True)
            st.write("---")

        tab1, tab2, tab3 = st.tabs(["🎯 領取任務", "🎁 進度結算", "⚙️ 個人設定"])

        # 【功能二：分級框格任務】
        with tab1:
            difficulty_map = {
                "A": "【初級滲透】 (5任務/1券)", "B": "【進階觀察】 (3任務/1券)",
                "C": "【深度諜對諜】 (2任務/1券)", "D": "【極限衝突】 (1任務/1券)", "E": "【傳奇成就】 (1任務/2券)"
            }
            for level, label in difficulty_map.items():
                level_tasks = df_tasks[df_tasks['difficulty'] == level]
                with st.container():
                    st.markdown(f'<div class="mission-frame"><h3>{label}</h3>', unsafe_allow_html=True)
                    if not level_tasks.empty:
                        for _, t in level_tasks.iterrows():
                            c1, c2 = st.columns([4, 1])
                            c1.markdown(f"**{t['title']}**")
                            c1.caption(t['content'])
                            if c2.button("選定", key=f"{level}_{t['title']}"):
                                st.session_state.current_task = f"【{t['title']}】\n{t['content']}"
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        # 【功能三：分級進度顯示】
        with tab2:
            st.subheader("📊 各級滲透進度")
            # 讀取 Google Sheets 中的各級完成數，若無則預設 0
            prog = {
                "A": int(user.get("done_A", 0)), "B": int(user.get("done_B", 0)),
                "C": int(user.get("done_C", 0)), "D": int(user.get("done_D", 0)), "E": int(user.get("done_E", 0))
            }
            
            # 顯示各級進度條
            st.write(f"A級：{prog['A']}/5")
            st.progress(min(prog['A']/5, 1.0))
            st.write(f"B級：{prog['B']}/3")
            st.progress(min(prog['B']/3, 1.0))
            st.write(f"C級：{prog['C']}/2")
            st.progress(min(prog['C']/2, 1.0))
            
            # 計算總票數
            tickets = (prog['A']//5) + (prog['B']//3) + (prog['C']//2) + prog['D'] + (prog['E']*2)
            st.metric("當前累計抽獎券", f"{tickets} 張")

        with tab3:
            st.write(f"真實姓名：{user['name(姓名)']}")
            st.info("若需永久修改暱稱或上傳照片，請聯繫班代。")

# --- 側邊欄固定顯示當前目標 ---
if st.session_state.login:
    with st.sidebar:
        st.markdown("### 📍 當前鎖定任務")
        st.info(st.session_state.current_task)
