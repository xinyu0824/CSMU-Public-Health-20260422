import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection

# --- 1. 視覺與稱號樣式設定 ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")

# [核心功能] 定義稱號邏輯
def get_agent_rank(tickets):
    if tickets >= 11: return "🌌 傳奇拍"
    elif tickets >= 7: return "🎖️ 大師拍"
    elif tickets >= 4: return "🛡️ 菁英拍"
    elif tickets >= 0: return "🌱 實習拍"
    return "尚未獲得稱號"

# CSS 美化
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 4px; width: 100%; height: 45px; }
    .stButton>button:hover { border: 1px solid #8C8C8C; background-color: #F9F9F9; }
    /* 任務卡片樣式 */
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 4px; margin-bottom: 12px; }
    .polaroid { background-color: white; padding: 12px; border: 1px solid #E6E6E1; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: center; }
    /* 選中的難度按鈕樣式 */
    .active-lvl { background-color: #5F5F5F !important; color: white !important; font-weight: bold; }
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

# 全局難度名稱
level_info = {"A": "【 潛伏訊號 】", "B": "【 視角破解 】", "C": "【 迷霧追蹤 】", "D": "【 極限干蝕 】", "E": "【 傳奇解密 】"}

# --- 核心邏輯：數據清理與計算 ---
def super_clean(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def calculate_total_tickets(user_row):
    try:
        def to_int(v):
            try: return int(float(v)) if pd.notna(v) and str(v) != "" else 0
            except: return 0
        a, b, c, d, e = [to_int(user_row.get(f'done_{k}', 0)) for k in "ABCDE"]
        return (a // 5) + (b // 3) + (c // 2) + (d * 1) + (e * 2)
    except: return 0

@st.cache_data(ttl=5)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except Exception as e:
        st.error(f"📡 總部連線失敗：{e}")
        return None, None

# --- 3. 初始化 Session State ---
if 'login' not in st.session_state:
    st.session_state.update({
        'login': False, 'student_id': None, 
        'locked_task': None, 'locked_diff': None,
        'selected_lvl': "A"
    })

df_users, df_tasks = load_data()

# --- 4. 流程分層 ---
if df_users is not None:
    if not st.session_state.login:
        st.title("🍂 拍照觀察員：身分登入")
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號 (姓名)", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼 (預設學號)", type="password")
        
        if st.button("確認進入"):
            match = df_users[df_users["name(姓名)"] == selected_name]
            if not match.empty:
                user_row = match.iloc[0]
                db_id = super_clean(user_row["Student ID(預設密碼)"])
                db_custom_pwd = super_clean(user_row.get("password(自訂密碼)", ""))
                correct_ans = db_custom_pwd if db_custom_pwd != "" else db_id
                
                if input_pwd.strip() == correct_ans:
                    st.session_state.login, st.session_state.student_id = True, db_id
                    st.rerun()
                else: st.error("密碼錯誤。")
    else:
        # 已登入：計算資料
        df_users["Student ID(預設密碼)"] = df_users["Student ID(預設密碼)"].apply(super_clean)
        user = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id].iloc[0]
        user_idx = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id].index[0]
        
        # --- 計算稱號 ---
        total_tickets = calculate_total_tickets(user)
        rank_label = get_agent_rank(total_tickets)
        
        # --- 首頁標題 (包含稱號) ---
        disp_name = user["Nickname(變更暱稱)"] if user["Nickname(變更暱稱)"] != "" else user["name(姓名)"]
        st.title(f"📝 {rank_label} {disp_name} 的特工記憶庫")

        # 左側收縮介面 (Sidebar)
        with st.sidebar:
            st.markdown("### 🗂️ 特工檔案")
            st.write(f"**當前稱號：** \n{rank_label}")
            st.write(f"**累計抽獎券：** {total_tickets} 張")
            st.write("---")
            st.markdown("### 📍 目前鎖定目標")
            if st.session_state.locked_task:
                st.info(st.session_state.locked_task)
            else:
                st.write("尚未鎖定任何任務")

        # 觀察紀錄展示
        with st.expander("🖼️ 查看我的已上傳紀錄"):
            p_val = str(user.get("photo_list", "")).strip()
            if p_val == "" or p_val.lower() == "nan":
                st.info("🌑 尚未有紀錄。")
            else:
                p_urls = [u.strip() for u in p_val.split(",") if u.strip() != ""]
                t_names = str(user.get("task_list", "")).split(",")
                cols = st.columns(3)
                for i, url in enumerate(p_urls):
                    with cols[i % 3]:
                        thumb = url.replace("/upload/", "/upload/w_400,q_auto:eco/")
                        st.markdown(f'<div class="polaroid"><img src="{thumb}" style="width:100%;"></div>', unsafe_allow_html=True)
                        st.caption(t_names[i] if i < len(t_names) else "")

        tab1, tab2, tab3 = st.tabs(["🎯 任務挑選", "📊 進度結算", "⚙️ 設定"])

        with tab1:
            # 難度選擇按鈕
            btn_cols = st.columns(5)
            for i, lvl in enumerate(["A", "B", "C", "D", "E"]):
                # 如果是當前選中的難度，幫按鈕加一個星星標記
                label = f"★ {lvl}" if st.session_state.selected_lvl == lvl else lvl
                if btn_cols[i].button(label, key=f"btn_{lvl}"):
                    st.session_state.selected_lvl = lvl
                    st.rerun()
            
            curr_lvl = st.session_state.selected_lvl
            st.markdown(f"#### {level_info[curr_lvl]}")
            
            # 任務卡片
            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == curr_lvl]
            for _, task in filtered.iterrows():
                with st.container():
                    st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if st.button("鎖定此目標", key=f"lock_{task['title']}"):
                        st.session_state.locked_task, st.session_state.locked_diff = task['title'], curr_lvl
                        st.toast(f"已選定：{task['title']}")

            # 回傳區：使用動態 Key 解決圖片不清除問題
            if st.session_state.locked_task:
                st.write("---")
                st.subheader(f"📡 情報回傳：{st.session_state.locked_task}")
                # 關鍵：當 locked_task 改變時，uploader_key 就會變，這會強制重置上傳元件
                uploader_key = f"uploader_{st.session_state.locked_task}"
                up_file = st.file_uploader("選取證物照片", type=['png', 'jpg', 'jpeg'], key=uploader_key)
                
                if up_file:
                    if st.button("🚀 正式回傳"):
                        with st.spinner("同步中..."):
                            try:
                                res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                                img_url = res["secure_url"]
                                
                                # 更新數據
                                cur_p = str(df_users.at[user_idx, "photo_list"]).strip()
                                df_users.at[user_idx, "photo_list"] = img_url if cur_p == "" or cur_p.lower() == "nan" else f"{cur_p},{img_url}"
                                cur_t = str(df_users.at[user_idx, "task_list"]).strip()
                                df_users.at[user_idx, "task_list"] = st.session_state.locked_task if cur_t == "" or cur_t.lower() == "nan" else f"{cur_t},{st.session_state.locked_task}"
                                
                                diff_col = f"done_{st.session_state.locked_diff}"
                                try:
                                    val = int(float(df_users.at[user_idx, diff_col])) if pd.notna(df_users.at[user_idx, diff_col]) else 0
                                except: val = 0
                                df_users.at[user_idx, diff_col] = val + 1
                                
                                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                st.balloons(); st.success("回傳成功！"); st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"同步失敗：{e}")

        with tab2:
            st.subheader(f"📊 {rank_label} 的進度報表")
            for lvl in ["A", "B", "C", "D", "E"]:
                c = user.get(f"done_{lvl}", 0)
                try: val = int(float(c))
                except: val = 0
                st.write(f"{level_info[lvl]}： {val} / 5")
                st.progress(min(val/5, 1.0))
            st.metric("抽獎券累計", f"{total_tickets} 張")

        with tab3:
            st.subheader("⚙️ 設定")
            new_nick = st.text_input("更換暱稱", value=user["Nickname(變更暱稱)"])
            new_pwd = st.text_input("自訂密碼", type="password", placeholder="留空不修改")
            if st.button("同步設定"):
                df_users.at[user_idx, "Nickname(變更暱稱)"] = new_nick
                if new_pwd.strip() != "":
                    df_users.at[user_idx, "password(自訂密碼)"] = new_pwd
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.success("同步完成！"); st.cache_data.clear(); st.rerun()
            if st.button("🚪 登出"):
                st.session_state.login = False; st.rerun()

else: st.error("❌ 無法連線至總部")
