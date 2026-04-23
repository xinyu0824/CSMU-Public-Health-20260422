import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection

# --- 1. 視覺美學設定 ---
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

# --- [重要] 全局變數定義：解決 NameError ---
level_info = {
    "A": "【 潛伏訊號 】", 
    "B": "【 視角破解 】", 
    "C": "【 迷霧追蹤 】", 
    "D": "【 極限干蝕 】", 
    "E": "【 傳奇解密 】"
}

# --- 核心邏輯：文字清理與計算 ---
def super_clean(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def calculate_total_tickets(user_row):
    try:
        def to_int(v):
            try: return int(float(v))
            except: return 0
        a, b, c, d, e = [to_int(user_row.get(f'done_{k}', 0)) for k in "ABCDE"]
        return (a // 5) + (b // 3) + (c // 2) + (d * 1) + (e * 2)
    except: return 0

@st.cache_data(ttl=5)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        # 強制轉換關鍵欄位為字串，避免 float64 錯誤
        str_cols = ['photo_list', 'task_list', 'Nickname(變更暱稱)', 'password(自訂密碼)', 'Student ID(預設密碼)']
        for col in str_cols:
            if col in users.columns:
                users[col] = users[col].astype(str).replace(['nan', 'None', ''], '')
        return users, tasks
    except Exception as e:
        st.error(f"📡 總部連線失敗：{e}")
        return None, None

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
        # --- 登入介面 ---
        st.title("🍂 拍照觀察員：身分登入")
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號 (預設為姓名)", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼 (預設為學號)", type="password")
        
        if st.button("確認進入"):
            match = df_users[df_users["name(姓名)"] == selected_name]
            if not match.empty:
                user_row = match.iloc[0]
                real_id = super_clean(user_row["Student ID(預設密碼)"])
                custom_pwd = super_clean(user_row.get("password(自訂密碼)", ""))
                correct_pwd = custom_pwd if custom_pwd != "" else real_id
                
                if input_pwd.strip() == correct_pwd:
                    st.session_state.login = True
                    st.session_state.student_id = real_id
                    st.rerun()
                else:
                    st.error("密碼錯誤。")
    else:
        # --- 已登入：特工個人空間 ---
        df_users["Student ID(預設密碼)"] = df_users["Student ID(預設密碼)"].apply(super_clean)
        user_matches = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id]
        
        if user_matches.empty:
            st.error("找不到資料，請重新登入。")
            if st.button("登出"): st.session_state.login = False; st.rerun()
            st.stop()
            
        user = user_matches.iloc[0]
        user_idx = user_matches.index[0]
        
        disp_name = user["Nickname(變更暱稱)"] if user["Nickname(變更暱稱)"] != "" else user["name(姓名)"]
        st.title(f"📝 {disp_name} 的特工記憶庫")

        with st.expander("🖼️ 我的觀察紀錄"):
            p_val = user["photo_list"]
            if p_val == "":
                st.info("🌑 尚未有解碼紀錄，快去挑選任務吧！")
            else:
                p_urls = p_val.split(",")
                t_names = str(user.get("task_list", "")).split(",")
                cols = st.columns(3)
                for i, url in enumerate(p_urls):
                    if url.strip() != "":
                        with cols[i % 3]:
                            thumb = url.strip().replace("/upload/", "/upload/w_400,q_auto:eco/")
                            st.markdown(f'<div class="polaroid"><img src="{thumb}" style="width:100%;"></div>', unsafe_allow_html=True)
                            st.caption(t_names[i] if i < len(t_names) else "")

        st.write("---")
        tab1, tab2, tab3 = st.tabs(["🎯 任務挑選", "📊 進度瀏覽", "⚙️ 設定"])

        with tab1:
            btn_cols = st.columns(5)
            for i, lvl in enumerate(["A", "B", "C", "D", "E"]):
                if btn_cols[i].button(lvl, key=f"btn_{lvl}"): 
                    st.session_state.selected_lvl = lvl
            
            curr_lvl = st.session_state.selected_lvl
            # 這裡就不會再報 NameError 了
            st.markdown(f"**當前查閱：{level_info[curr_lvl]}**")
            
            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == curr_lvl]
            for _, task in filtered.iterrows():
                with st.container():
                    st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if st.button("鎖定此目標", key=f"lock_{task['title']}"):
                        st.session_state.locked_task, st.session_state.locked_diff = task['title'], curr_lvl
                        st.toast(f"已選定：{task['title']}")
            
            if st.session_state.locked_task:
                st.write("---")
                st.subheader(f"📡 情報回傳：{st.session_state.locked_task}")
                up_file = st.file_uploader("上傳觀察證物", type=['png', 'jpg', 'jpeg'], key="agent_upload")
                if up_file:
                    if st.button("🚀 正式回傳總部"):
                        with st.spinner("同步中..."):
                            try:
                                res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                                img_url = res["secure_url"]
                                
                                # 更新數據 (處理字串拼接)
                                current_p = str(df_users.at[user_idx, "photo_list"]).strip()
                                df_users.at[user_idx, "photo_list"] = img_url if current_p == "" else f"{current_p},{img_url}"
                                current_t = str(df_users.at[user_idx, "task_list"]).strip()
                                df_users.at[user_idx, "task_list"] = st.session_state.locked_task if current_t == "" else f"{current_t},{st.session_state.locked_task}"
                                
                                # 更新計數
                                diff_col = f"done_{st.session_state.locked_diff}"
                                try: val = int(float(df_users.at[user_idx, diff_col]))
                                except: val = 0
                                df_users.at[user_idx, diff_col] = val + 1
                                
                                # 寫回資料庫
                                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                st.balloons(); st.success("回傳成功！"); st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"同步失敗：{e}")

        with tab2:
            st.subheader("📊 任務完成度")
            for lvl in ["A", "B", "C", "D", "E"]:
                count = user.get(f"done_{lvl}", 0)
                try: val = int(float(count))
                except: val = 0
                st.write(f"{level_info[lvl]}： {val} / 5")
                st.progress(min(val/5, 1.0))
            st.metric("抽獎券總數", f"{calculate_total_tickets(user)} 張")

        with tab3:
            st.subheader("⚙️ 個人設定")
            new_nick = st.text_input("更換暱稱", value=user["Nickname(變更暱稱)"])
            new_pwd = st.text_input("修改自訂密碼", type="password", placeholder="留空則不修改")
            if st.button("💾 同步設定至總部"):
                with st.spinner("更新中..."):
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
else: st.error("❌ 無法讀取資料庫。")
