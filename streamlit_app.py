import streamlit as st
import pandas as pd
import random

# --- 1. 視覺美學設定 (Muji 暖米色調) ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 2px; width: 100%; }
    .stButton>button:hover { border: 1px solid #8C8C8C; background-color: #F9F9F9; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 4px; margin-bottom: 12px; }
    .polaroid { background-color: white; padding: 8px; border: 1px solid #E6E6E1; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 資料讀取設定 ---
SHEET_ID = "1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA"
USER_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=users"
TASK_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=tasks"

@st.cache_data(ttl=5) # 5秒刷新一次，確保進度條會動
def load_data(url):
    try: 
        data = pd.read_csv(url)
        return data
    except: 
        return None

# --- 3. 核心邏輯 ---
level_info = {
    "A": "【 潛伏訊號 】", "B": "【 視角破解 】", "C": "【 迷霧追蹤 】", 
    "D": "【 極限干涉 】", "E": "【 傳奇解密 】"
}

def calculate_total_tickets(user_row):
    try:
        # 確保抓到的是數字，如果是空的就給 0
        def clean_val(v): return int(v) if pd.notna(v) else 0
        a = clean_val(user_row.get('done_A', 0))
        b = clean_val(user_row.get('done_B', 0))
        c = clean_val(user_row.get('done_C', 0))
        d = clean_val(user_row.get('done_D', 0))
        e = clean_val(user_row.get('done_E', 0))
        return (a // 5) + (b // 3) + (c // 2) + (d * 1) + (e * 2)
    except: return 0

# --- 4. 初始化 Session State ---
if 'login' not in st.session_state:
    st.session_state.update({
        'login': False, 'student_id': None, 'current_task': "尚未鎖定任務", 'selected_lvl': "A"
    })

# --- 5. 程式流程 ---
df_users = load_data(USER_CSV)
df_tasks = load_data(TASK_CSV)

if df_users is not None:
    # A. 登入介面
    if not st.session_state.login:
        st.title("🍂 拍照觀察員：身分登入")
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號 (預設為姓名)", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼 (預設為學號)", type="password")

        if st.button("確認進入"):
            match = df_users[df_users["name(姓名)"] == selected_name]
            if not match.empty:
                user_row = match.iloc[0]
                # 判斷密碼 (自訂優先 > 學號)
                try:
                    raw_pwd = user_row.get("password(自訂密碼)", None)
                    if pd.notna(raw_pwd) and str(raw_pwd).strip() != "" and str(raw_pwd).lower() != "nan":
                        correct_pwd = str(raw_pwd).strip()
                    else:
                        correct_pwd = str(user_row["Student ID(預設密碼)"]).strip()
                except:
                    correct_pwd = str(user_row["Student ID(預設密碼)"]).strip()

                if input_pwd.strip() == correct_pwd:
                    st.session_state.login = True
                    st.session_state.student_id = str(user_row["Student ID(預設密碼)"]).strip()
                    st.rerun()
                else:
                    st.error("密碼錯誤，請重新輸入。")

    # B. 已登入介面
    else:
        # 重要：每次都從 df_users 重新抓取該學生的最新資料
        current_user_df = df_users[df_users["Student ID(預設密碼)"].astype(str).str.strip() == st.session_state.student_id]
        if current_user_df.empty:
            st.error("找不到使用者資料，請重新登入。")
            st.session_state.login = False
            st.stop()
        
        user = current_user_df.iloc[0]
        
        # 暱稱顯示
        display_name = user["Nickname(變更暱稱)"] if pd.notna(user["Nickname(變更暱稱)"]) and str(user["Nickname(變更暱稱)"]).strip() != "" else user["name(姓名)"]
        st.title(f"📝 {display_name} 今天拍了沒📸")
        st.markdown(f"<p style='color: #8C8C8C; font-size: 0.8rem; margin-top:-15px;'>特工 ID: {st.session_state.student_id}</p>", unsafe_allow_html=True)

        # --- 第一區：照片牆 ---
        st.subheader("🖼️ 任務照片記錄")
        photo_val = user.get("photo_list")
        if pd.isna(photo_val) or str(photo_val).strip() == "":
            st.info("🌑 尚未完成任何任務，快去挑選一個吧！")
        else:
            p_urls = str(photo_val).split(",")
            t_names = str(user.get("task_list", "")).split(",")
            cols = st.columns([1, 1.1, 0.9])
            for i, u in enumerate(p_urls):
                label = t_names[i] if i < len(t_names) else "未命名任務"
                with cols[i % 3]:
                    st.markdown(f'<div class="polaroid"><img src="{u.strip()}" style="width:100%;"><div style="font-size:0.7rem; color:#5F5F5F; margin-top:5px;">{label}</div></div>', unsafe_allow_html=True)
        
        st.write("---")

        # --- 第二區：任務與進度 ---
        tab1, tab2, tab3 = st.tabs(["🎯 任務挑選", "📊 進度瀏覽", "⚙️ 設定"])

        with tab1:
            st.write("點擊級別切換查閱區域：")
            btn_cols = st.columns(5)
            for i, lvl in enumerate(["A", "B", "C", "D", "E"]):
                if btn_cols[i].button(lvl, key=f"btn_{lvl}", help=level_info[lvl]):
                    st.session_state.selected_lvl = lvl
            
            curr_lvl = st.session_state.selected_lvl
            st.markdown(f"**當前查閱：{level_info[curr_lvl]}**")
            
            if df_tasks is not None:
                # 關鍵修正：確保比對時沒有多餘空格
                df_tasks['difficulty'] = df_tasks['difficulty'].astype(str).str.strip()
                filtered = df_tasks[df_tasks['difficulty'] == curr_lvl]
                
                if filtered.empty:
                    st.warning(f"目前 {curr_lvl} 等級中沒有任務，請確認試算表任務分頁。")
                else:
                    for _, task in filtered.iterrows():
                        with st.container():
                            st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                            if st.button("鎖定此任務", key=f"lock_{task['title']}"):
                                st.session_state.current_task = f"【{task['title']}】 {task['content']}"
                                st.toast(f"已鎖定目標：{task['title']}")
            else:
                st.error("任務清單加載失敗，請檢查 Task 分頁。")

        with tab2:
            st.subheader("🎁 抽獎券結算進度")
            for lvl in ["A", "B", "C", "D", "E"]:
                count = int(user.get(f"done_{lvl}", 0)) if pd.notna(user.get(f"done_{lvl}")) else 0
                st.write(f"{level_info[lvl]}： {count} / 5")
                st.progress(min(count/5, 1.0))
            
            total = calculate_total_tickets(user)
            st.metric("當前獲得抽獎券總數", f"{total} 張")

        with tab3:
            st.subheader("⚙️ 檔案維護")
            st.info("若需修改暱稱或密碼，請填寫後點擊同步。")
            st.text_input("更換暱稱", value=user["Nickname(變更暱稱)"] if pd.notna(user["Nickname(變更暱稱)"]) else "", key="new_nick")
            st.text_input("修改自訂密碼", type="password", key="new_pwd")
            if st.button("同步至總部檔案"):
                st.success("申請已送出！請聯繫班代確認更新。")
    
    # 側邊欄
    if st.session_state.login:
        with st.sidebar:
            st.markdown("### 📍 目前選定任務")
            st.info(st.session_state.current_task)
else:
    st.error("❌ 連線資料庫失敗。")
