import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection

# --- 1. 質感設定 ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 2px; width: 100%; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 4px; margin-bottom: 12px; }
    .polaroid { background-color: white; padding: 12px; border: 1px solid #E6E6E1; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 外部服務配置 ---
cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)

GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 核心邏輯：究極文字清理 ---
def super_clean(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    # 處理小數點 112001.0 -> 112001
    if s.endswith('.0'): s = s[:-2]
    # 處理科學符號或奇怪格式
    return s

@st.cache_data(ttl=5)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        
        # 強制將關鍵欄位全部轉為字串並清理
        for col in users.columns:
            users[col] = users[col].apply(super_clean)
        return users, tasks
    except Exception as e:
        st.error(f"📡 總部連線失敗：{e}")
        return None, None

def calculate_total_tickets(user_row):
    try:
        def to_int(v):
            try: return int(float(v))
            except: return 0
        a = to_int(user_row.get('done_A', 0))
        b = to_int(user_row.get('done_B', 0))
        c = to_int(user_row.get('done_C', 0))
        d = to_int(user_row.get('done_D', 0))
        e = to_int(user_row.get('done_E', 0))
        return (a // 5) + (b // 3) + (c // 2) + (d * 1) + (e * 2)
    except: return 0

# --- 4. 初始化 Session State ---
if 'login' not in st.session_state:
    st.session_state.update({
        'login': False, 'student_id': None, 
        'locked_task': None, 'locked_diff': None,
        'selected_lvl': "A"
    })

df_users, df_tasks = load_data()

# --- 5. 流程分層 ---
if df_users is not None:
    if not st.session_state.login:
        st.title("🍂 拍照觀察員：身分登入")
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號 (預設為姓名)", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼 (預設為學號)", type="password")
        
        if st.button("確認進入"):
            match = df_users[df_users["name(姓名)"] == selected_name]
            if not match.empty:
                user_row = match.iloc[0]
                
                # 取得正確的 ID 和自訂密碼
                real_id = super_clean(user_row["Student ID(預設密碼)"])
                custom_pwd = super_clean(user_row.get("password(自訂密碼)", ""))
                
                # 決定正確密碼
                correct_pwd = custom_pwd if custom_pwd != "" else real_id
                
                # [除錯區] 如果密碼錯誤，顯示比對資訊 (活動結束後可刪除這行)
                if input_pwd.strip() == correct_pwd:
                    st.session_state.login = True
                    st.session_state.student_id = real_id
                    st.rerun()
                else:
                    st.error("密碼錯誤。")
                    # 下面這行是為了讓妳看出為什麼不對
                    st.write(f"🔍 系統內部的密碼長度為 {len(correct_pwd)}，妳輸入的長度為 {len(input_pwd.strip())}")
                    if input_pwd.strip() == real_id:
                        st.info("提示：系統內似乎有設定自訂密碼，請嘗試使用自訂密碼。")
    else:
        # 已登入後續邏輯...
        user_matches = df_users[df_users["Student ID(預設密碼)"].apply(super_clean) == st.session_state.student_id]
        if user_matches.empty:
            st.error("資料同步中，請重新登入"); st.session_state.login = False; st.stop()
            
        user = user_matches.iloc[0]
        user_idx = user_matches.index[0]
        
        disp_name = user["Nickname(變更暱稱)"] if user["Nickname(變更暱稱)"] != "" else user["name(姓名)"]
        st.title(f"📝 {disp_name} 的特工記憶庫")

        # --- 顯示照片與 Tab 邏輯 (省略以便於閱讀，保持原狀即可) ---
        tab1, tab2, tab3 = st.tabs(["🎯 任務挑選", "📊 進度瀏覽", "⚙️ 設定"])
        
        with tab1:
            # 任務挑選區 (保持原本 Cloudinary 上傳邏輯，但增加欄位格式保護)
            if df_tasks is not None:
                btn_cols = st.columns(5)
                for i, lvl in enumerate(["A", "B", "C", "D", "E"]):
                    if btn_cols[i].button(lvl, key=f"btn_{lvl}"): st.session_state.selected_lvl = lvl
                
                curr_lvl = st.session_state.selected_lvl
                st.markdown(f"**當前查閱：{level_info[curr_lvl]}**")
                
                filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == curr_lvl]
                for _, task in filtered.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        if st.button("鎖定此目標", key=f"lock_{task['title']}"):
                            st.session_state.locked_task, st.session_state.locked_diff = task['title'], curr_lvl
                            st.toast(f"已選定：{task['title']}")

                if st.session_state.locked_task:
                    up_file = st.file_uploader("上傳證物", type=['png', 'jpg', 'jpeg'])
                    if up_file:
                        if st.button("🚀 正式回傳"):
                            with st.spinner("同步中..."):
                                try:
                                    res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                                    img_url = res["secure_url"]
                                    
                                    # 寫入前再次確保為文字型態
                                    old_p = str(user.get("photo_list", "")).replace('nan', '').strip()
                                    df_users.at[user_idx, "photo_list"] = img_url if old_p == "" else f"{old_p},{img_url}"
                                    
                                    old_t = str(user.get("task_list", "")).replace('nan', '').strip()
                                    df_users.at[user_idx, "task_list"] = st.session_state.locked_task if old_t == "" else f"{old_t},{st.session_state.locked_task}"
                                    
                                    diff_col = f"done_{st.session_state.locked_diff}"
                                    try: val = int(float(user.get(diff_col, 0)))
                                    except: val = 0
                                    df_users.at[user_idx, diff_col] = val + 1
                                    
                                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                    st.balloons(); st.success("回傳成功！"); st.cache_data.clear(); st.rerun()
                                except Exception as e: st.error(f"回傳失敗，可能是資料型態錯誤：{e}")

        with tab2:
            # 進度瀏覽... (保持原狀)
            for lvl in ["A", "B", "C", "D", "E"]:
                c = user.get(f"done_{lvl}", 0)
                try: val = int(float(c))
                except: val = 0
                st.write(f"{level_info[lvl]}： {val} / 5")
                st.progress(min(val/5, 1.0))
            st.metric("抽獎券總數", f"{calculate_total_tickets(user)} 張")

        with tab3:
            st.subheader("⚙️ 個人設定")
            new_nick = st.text_input("更換暱稱", value=user["Nickname(變更暱稱)"])
            new_pwd = st.text_input("修改自訂密碼", type="password", placeholder="留空則不修改")
            
            if st.button("💾 同步設定至總部"):
                df_users.at[user_idx, "Nickname(變更暱稱)"] = new_nick
                if new_pwd.strip() != "":
                    df_users.at[user_idx, "password(自訂密碼)"] = new_pwd
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.success("✅ 設定同步成功！"); st.cache_data.clear(); st.rerun()
            
            if st.button("🚪 登出系統"):
                st.session_state.login = False; st.rerun()

    with st.sidebar:
        if st.session_state.login:
            st.markdown("### 📍 目前選定目標")
            st.info(st.session_state.locked_task if st.session_state.locked_task else "尚未鎖定")

else: st.error("❌ 無法連線")
