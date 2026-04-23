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

# --- 2. 配置 ---
cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)

GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        # 強制讀取特定分頁，若失敗則報錯
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except Exception as e:
        st.error(f"📡 總部連線失敗：{e}")
        return None, None

# --- 輔助函式：處理學號變浮點數的問題 ---
def clean_string(val):
    if pd.isna(val): return ""
    # 如果是 112001.0 這種格式，先轉成整數再轉字串
    try:
        float_val = float(val)
        if float_val == int(float_val):
            return str(int(float_val))
    except:
        pass
    return str(val).strip()

# --- 3. 邏輯 ---
level_info = {"A": "【 潛伏訊號 】", "B": "【 視角破解 】", "C": "【 迷霧追蹤 】", "D": "【 極限干蝕 】", "E": "【 傳奇解密 】"}

if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'locked_task': None, 'locked_diff': None, 'selected_lvl': "A"})

df_users, df_tasks = load_data()

# --- 4. 流程分層 ---
if df_users is not None:
    if not st.session_state.login:
        st.title("🍂 拍照觀察員：身分登入")
        
        # 欄位檢查
        if "name(姓名)" not in df_users.columns:
            st.error(f"❌ 找不到 'name(姓名)' 欄位。目前有的欄位：{list(df_users.columns)}")
            st.stop()
            
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號 (預設為姓名)", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼 (預設為學號)", type="password")
        
        if st.button("確認進入"):
            match = df_users[df_users["name(姓名)"] == selected_name]
            if not match.empty:
                user_row = match.iloc[0]
                
                # 取得正確的 ID 和自訂密碼（並清理格式）
                real_id = clean_string(user_row.get("Student ID(預設密碼)"))
                raw_custom_pwd = user_row.get("password(自訂密碼)")
                
                # 決定正確密碼是哪一個
                if pd.notna(raw_custom_pwd) and str(raw_custom_pwd).strip() != "":
                    correct_pwd = str(raw_custom_pwd).strip()
                else:
                    correct_pwd = real_id
                
                # 比對輸入
                if input_pwd.strip() == correct_pwd:
                    st.session_state.login = True
                    st.session_state.student_id = real_id
                    st.success("登入成功！正在跳轉...")
                    st.rerun()
                else:
                    st.error(f"密碼錯誤。")
            else:
                st.warning("請選擇姓名。")
    else:
        # --- 已登入：特工空間 ---
        # 再次清理 ID 以確保搜尋索引正確
        df_users["Student ID(預設密碼)"] = df_users["Student ID(預設密碼)"].apply(clean_string)
        user_matches = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id]
        
        if user_matches.empty:
            st.error("找不到您的資料，請嘗試重新登入。")
            if st.button("重新登入"):
                st.session_state.login = False
                st.rerun()
            st.stop()
            
        user = user_matches.iloc[0]
        user_idx = user_matches.index[0]
        
        st.title(f"📝 {user['name(姓名)']} 的特工空間")
        
        # [接下來的分頁 Tab 邏輯...]
        tab1, tab2, tab3 = st.tabs(["🎯 任務挑選", "📊 進度瀏覽", "⚙️ 設定"])
        
        with tab1:
            if df_tasks is not None:
                btn_cols = st.columns(5)
                for i, lvl in enumerate(["A", "B", "C", "D", "E"]):
                    if btn_cols[i].button(lvl, key=f"btn_{lvl}"): st.session_state.selected_lvl = lvl
                
                curr_lvl = st.session_state.selected_lvl
                st.markdown(f"**當前查閱：{level_info[curr_lvl]}**")
                
                # 顯示任務
                df_tasks['difficulty'] = df_tasks['difficulty'].astype(str).str.strip()
                filtered = df_tasks[df_tasks['difficulty'] == curr_lvl]
                
                for _, task in filtered.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        if st.button("鎖定此目標", key=f"lock_{task['title']}"):
                            st.session_state.locked_task, st.session_state.locked_diff = task['title'], curr_lvl
                            st.toast(f"已選定：{task['title']}")
                
                if st.session_state.locked_task:
                    st.write("---")
                    st.subheader(f"📡 情報回傳：{st.session_state.locked_task}")
                    up_file = st.file_uploader("上傳觀察證物", type=['png', 'jpg', 'jpeg'])
                    if up_file:
                        if st.button("🚀 正式回傳"):
                            with st.spinner("同步中..."):
                                try:
                                    res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT")
                                    img_url = res["secure_url"]
                                    
                                    # 讀取現有照片清單
                                    old_p = str(user.get("photo_list", ""))
                                    new_p = img_url if old_p in ["nan", ""] else f"{old_p},{img_url}"
                                    
                                    old_t = str(user.get("task_list", ""))
                                    new_t = st.session_state.locked_task if old_t in ["nan", ""] else f"{old_t},{st.session_state.locked_task}"
                                    
                                    # 更新對應欄位
                                    df_users.at[user_idx, "photo_list"] = new_p
                                    df_users.at[user_idx, "task_list"] = new_t
                                    
                                    diff_col = f"done_{st.session_state.locked_diff}"
                                    current_count = int(user.get(diff_col, 0)) if pd.notna(user.get(diff_col)) else 0
                                    df_users.at[user_idx, diff_col] = current_count + 1
                                    
                                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                    st.balloons()
                                    st.success("回傳成功！")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e: st.error(f"回傳失敗：{e}")

        with tab2:
            st.subheader("📊 任務完成度")
            for lvl in ["A", "B", "C", "D", "E"]:
                count = int(user.get(f"done_{lvl}", 0)) if pd.notna(user.get(f"done_{lvl}")) else 0
                st.write(f"{level_info[lvl]}： {count} / 5")
                st.progress(min(count/5, 1.0))

        with tab3:
            if st.button("登出系統"):
                st.session_state.login = False
                st.rerun()

else: st.error("❌ 無法連線至總部資料庫。")
