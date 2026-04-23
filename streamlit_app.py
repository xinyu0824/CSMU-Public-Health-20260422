import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection

# --- 1. 稱號定義與視覺美學模組 (特工總部 3.0) ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")

# [核心邏輯] 特工稱號門檻：實習0-3, 菁英4-6, 大師7-10, 傳奇11+
def get_agent_rank(tickets):
    if tickets >= 11: return "🌌 傳奇拍"
    elif tickets >= 7: return "🎖️ 大師拍"
    elif tickets >= 4: return "🛡️ 菁英拍"
    elif tickets >= 0: return "🌱 實習拍"
    return "尚未獲得稱號"

# CSS 美化 (質感 Muji 特工調)
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    
    /* 稱號小標籤 (Badge) */
    .agent-badge { 
        display: inline-block; 
        padding: 4px 12px; 
        background-color: #5F5F5F; /* Muji 特工灰深 */
        color: #FFFFFF; 
        border-radius: 20px; 
        font-size: 0.8rem; 
        font-weight: bold; 
        margin-right: 12px; 
        vertical-align: middle;
    }
    
    /* 首頁標題排版調整 */
    .title-wrapper { display: flex; align-items: center; margin-bottom: 25px; }
    .main-title { font-size: 1.8rem; margin: 0; }
    
    /* 榮譽標誌顯示 */
    .rank-display-label { 
        padding: 10px; 
        background-color: #FFFFFF; 
        border: 1px dashed #D9D9D9; 
        border-radius: 4px; 
        margin-top: 10px;
        color: #8C8C8C;
    }

    /* 難度選擇區域樣式 - 模擬黃底白字填充 */
    .stRadio div[role="radiogroup"] { display: flex; gap: 10px; }
    .stRadio div[role="radiogroup"] > label {
        padding: 10px 18px; 
        background-color: #FFFFFF; 
        color: #5F5F5F; 
        border: 1px solid #D9D9D9; 
        border-radius: 4px; 
        cursor: pointer; 
        transition: all 0.3s;
        height: 45px; 
        display: flex; 
        align-items: center; 
        justify-content: center;
        width: 100% !important;
    }
    .stRadio div[role="radiogroup"] > label:hover { border: 1px solid #8C8C8C; background-color: #F9F9F9; }
    
    /* [關鍵視覺] 被選中的單選選項變色為 Muji 特工黃 (填充顏色) */
    .stRadio div[role="radiogroup"] > label[data-baseweb="radio"] {
        display: flex; /* 保持 flex */
    }
    /* 隱藏原生單選圓圈 */
    .stRadio div[role="radiogroup"] > label[data-baseweb="radio"] div:first-child {
        display: none !important;
    }
    
    /* [關鍵修正] 選取後的背景顏色與字體顏色 (填充顏色在此框中) */
    .stRadio div[role="radiogroup"] > label[aria-checked="true"] {
        background-color: #FFC107 !important; /* Muji 特工黃 */
        color: #FFFFFF !important; /* 白字 */
        border-color: #FFC107 !important;
        font-weight: bold;
    }
    /* 確保字體顏色 */
    .stRadio div[role="radiogroup"] > label[aria-checked="true"] p {
        color: #FFFFFF !important;
    }

    /* 其餘介面樣式 */
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 2px; height: 45px; }
    .stButton>button:hover { border: 1px solid #8C8C8C; background-color: #F9F9F9; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 4px; margin-bottom: 12px; }
    .polaroid { background-color: white; padding: 12px; border: 1px solid #E6E6E1; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 服務配置 ---
cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)

GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 全局難度資訊
level_info = {"A": "【 潛伏訊號 】", "B": "【 視角破解 】", "C": "【 迷霧追蹤 】", "D": "【 極限干蝕 】", "E": "【 傳奇解密 】"}

# --- 核心邏輯：型別隔離數據清理 ---
def clean_id_logic(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def calculate_total_tickets(user_row):
    try:
        def to_int(v):
            try: return int(float(v)) if pd.notna(v) and str(v) != "" else 0
            except: return 0
        # 這裡會精準計算各難度進度並依照權重計算總分
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
        # --- 登入介面 ---
        st.title("🍂 拍照觀察員：身分登入")
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號 (姓名)", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼 (預設學號)", type="password")
        
        if st.button("確認進入"):
            match = df_users[df_users["name(姓名)"] == selected_name]
            if not match.empty:
                user_row = match.iloc[0]
                # 比對前同時進行清理，解決小數點 Bug
                db_id = clean_id_logic(user_row["Student ID(預設密碼)"])
                db_custom_pwd = str(user_row.get("password(自訂密碼)", "")).strip()
                if db_custom_pwd.lower() == "nan": db_custom_pwd = ""
                correct_answer = db_custom_pwd if db_custom_pwd != "" else db_id
                
                if input_pwd.strip() == correct_answer:
                    st.session_state.login = True
                    st.session_state.student_id = db_id
                    st.rerun()
                else: st.error("密碼錯誤，請檢查學號格式。")
    else:
        # 已登入：精準抓取索引
        # 先幫表格裡的學號欄位全部「去 0 化」進行文字比對
        temp_ids = df_users["Student ID(預設密碼)"].apply(clean_id_logic)
        user_matches = df_users[temp_ids == st.session_state.student_id]
        
        if user_matches.empty:
            st.error("資料同步中..."); st.session_state.login = False; st.rerun(); st.stop()
            
        user = user_matches.iloc[0]
        user_idx = user_matches.index[0]
        
        # 暱稱與稱號計算
        total_tickets = calculate_total_tickets(user)
        rank_label = get_agent_rank(total_tickets)
        nick = str(user.get("Nickname(變更暱稱)", "")).strip()
        disp_name = nick if (nick != "" and nick.lower() != "nan") else user["name(姓名)"]
        
        # --- 首頁標題 (小標籤裝飾成功！) ---
        # 構建小標籤 +保留 暱稱的特工記憶庫
        title_html = f"""
        <div class="title-wrapper">
            <div class="agent-badge">{rank_label}</div>
            <div class="main-title">{disp_name} 的特工記憶庫</div>
        </div>
        """
        st.markdown(title_html, unsafe_allow_html=True)

        # 收縮介面 (Sidebar)
        with st.sidebar:
            st.markdown("### 🎖️ 檔案")
            # 在 Sidebar 也放稱號 (軍銜) 顯示
            st.info(f"當前稱號：\n{rank_label}")
            st.write(f"當前抽獎券：{total_tickets} 張")
            st.write("---")
            st.markdown("### 📍 目標")
            st.info(st.session_state.locked_task if st.session_state.locked_task else "無選取")

        # 觀察紀錄展示
        with st.expander("🖼️ 我的觀察紀錄 (已上傳情報)"):
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
            st.write("### 📍 步驟一：選擇難度區域")
            
            # [核心升級] 使用 st.radio 並樣式化為黃底填充填充方格
            difficulty_options = list(level_info.keys())
            
            # 使用單選框但外觀呈現按鈕狀
            selected_option = st.radio(
                "選擇難度區域", # 隱藏標籤
                options=difficulty_options,
                index=difficulty_options.index(st.session_state.selected_lvl),
                horizontal=True, # 水平排列
                key="diff_radio_selection",
                label_visibility="collapsed" # 隱藏 label，避免干擾
            )
            
            # 如果選項改變，更新 Session State
            if selected_option != st.session_state.selected_lvl:
                st.session_state.selected_lvl = selected_option
                st.session_state.locked_task = None # 切換難度時重置所定任務
                st.rerun() # 確保視覺與圖片區立刻重置
            
            curr_lvl = st.session_state.selected_lvl
            st.markdown(f"**當前查閱：{level_info[curr_lvl]}**")
            
            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == curr_lvl]
            for _, task in filtered.iterrows():
                with st.container():
                    st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if st.button("鎖定此目標", key=f"lock_{task['title']}"):
                        st.session_state.locked_task, st.session_state.locked_diff = task['title'], curr_lvl
                        st.toast(f"已選定：{task['title']}")
            
            # [核心升級] 掃描區只在鎖定任務後才顯示 (if st.session_state.locked_task:)
            if st.session_state.locked_task:
                st.write("---")
                st.write("### 📍 步驟二：情報回傳")
                st.subheader(f"📡 當前任務：{st.session_state.locked_task}")
                
                # [核心修正] 關鍵防呆模組：使用動態 Key
                # 當 locked_task 改變時，uploader_key 就會變，這會強制重新生成 Uploader，清空舊檔案。
                uploader_key = f"uploader_{st.session_state.locked_task}"
                
                up_file = st.file_uploader("選取觀察照片 (建議縮小尺寸)", type=['png', 'jpg', 'jpeg'], key=uploader_key)
                
                if up_file:
                    st.image(up_file, width=200, caption="準備同步的照片草稿")
                    if st.button("🚀 正式同步至總部"):
                        with st.spinner("情報傳送中..."):
                            try:
                                res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                                img_url = res["secure_url"]
                                
                                # --- 關鍵數據更新策略 ---
                                # 1. 處理照片網址 (強迫轉字串)
                                current_p = str(df_users.at[user_idx, "photo_list"]).strip()
                                if current_p.lower() == "nan": current_p = ""
                                df_users.at[user_idx, "photo_list"] = str(img_url if current_p == "" else f"{current_p},{img_url}")
                                
                                # 2. 處理任務名稱 (強迫轉字串)
                                current_t = str(df_users.at[user_idx, "task_list"]).strip()
                                if current_t.lower() == "nan": current_t = ""
                                df_users.at[user_idx, "task_list"] = str(st.session_state.locked_task if current_t == "" else f"{current_t},{st.session_state.locked_task}")
                                
                                # 3. 處理進度次數 (強迫轉數字)
                                diff_col = f"done_{st.session_state.locked_diff}"
                                try:
                                    raw_val = df_users.at[user_idx, diff_col]
                                    val = int(float(raw_val)) if (pd.notna(raw_val) and str(raw_val).lower() != "nan" and str(raw_val) != "") else 0
                                except: val = 0
                                df_users.at[user_idx, diff_col] = val + 1
                                
                                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                st.balloons(); st.success("回傳成功！"); st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"同步失敗：{e}")

        with tab2:
            st.subheader(f"📊 {rank_label} {disp_name} 的進度結算")
            for lvl in ["A", "B", "C", "D", "E"]:
                c = user.get(f"done_{lvl}", 0)
                try: val = int(float(c)) if pd.notna(c) else 0
                except: val = 0
                st.write(f"{level_info[lvl]}： {val} / 5")
                st.progress(min(val/5, 1.0))
            st.metric("當前累計獲得抽獎券", f"{total_tickets} 張")

        with tab3:
            st.subheader("⚙️ 設定中心")
            new_nick = st.text_input("更換代號 (暱稱)", value=disp_name)
            new_pwd = st.text_input("自訂密碼", type="password", placeholder="留空不修改")
            if st.button("💾 同步設定"):
                df_users.at[user_idx, "Nickname(變更暱稱)"] = str(new_nick)
                if new_pwd.strip() != "":
                    df_users.at[user_idx, "password(自訂密碼)"] = str(new_pwd)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.success("同步完成！"); st.cache_data.clear(); st.rerun()
            if st.button("🚪 登出系統"):
                st.session_state.login = False; st.rerun()

else: st.error("❌ 無法連線至總部。")
