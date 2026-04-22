import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import datetime

# --- 1. 質感設定 (Muji 暖米色調) ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 2px; width: 100%; }
    .stButton>button:hover { border: 1px solid #8C8C8C; background-color: #F9F9F9; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 4px; margin-bottom: 12px; }
    .polaroid { background-color: white; padding: 12px; border: 1px solid #E6E6E1; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: center; }
    .upload-zone { border: 2px dashed #D9D9D9; padding: 20px; border-radius: 4px; background-color: #FCFCFA; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 外部服務配置 (Cloudinary & GSheets) ---
cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)

# [核心功能] 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    # [核心功能] 從雲端讀取最新的使用者與任務表
    users = conn.read(worksheet="users")
    tasks = conn.read(worksheet="tasks")
    return users, tasks

# --- 3. 核心邏輯 ---
level_info = {
    "A": "【 潛伏訊號 】", "B": "【 視角破解 】", "C": "【 迷霧追蹤 】", 
    "D": "【 極限干蝕 】", "E": "【 傳奇解密 】"
}

def calculate_total_tickets(user_row):
    try:
        def clean_val(v): return int(v) if pd.notna(v) else 0
        a, b, c, d, e = [clean_val(user_row.get(f'done_{k}', 0)) for k in "ABCDE"]
        return (a // 5) + (b // 3) + (c // 2) + (d * 1) + (e * 2)
    except: return 0

# --- 4. 初始化 Session State ---
if 'login' not in st.session_state:
    st.session_state.update({
        'login': False, 'student_id': None, 
        'locked_task': None, 'locked_diff': None,
        'selected_lvl': "A"
    })

# 執行讀取
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
                try:
                    raw_pwd = user_row.get("password(自訂密碼)", None)
                    correct_pwd = str(raw_pwd).strip() if (pd.notna(raw_pwd) and str(raw_pwd).strip() != "") else str(user_row["Student ID(預設密碼)"]).strip()
                except: correct_pwd = str(user_row["Student ID(預設密碼)"]).strip()
                
                if input_pwd.strip() == correct_pwd:
                    st.session_state.login, st.session_state.student_id = True, str(user_row["Student ID(預設密碼)"]).strip()
                    st.rerun()
                else: st.error("密碼錯誤。")

    else:
        # --- 已登入：特工個人空間 ---
        # 找到當前用戶在 DataFrame 中的位置 (Index)
        user_idx = df_users[df_users["Student ID(預設密碼)"].astype(str).str.strip() == st.session_state.student_id].index[0]
        user = df_users.iloc[user_idx]
        
        display_name = user["Nickname(變更暱稱)"] if pd.notna(user["Nickname(變更暱稱)"]) and str(user["Nickname(變更暱稱)"]).strip() != "" else user["name(姓名)"]
        st.title(f"📝 {display_name} 的特工記憶庫")

        # --- 記憶庫展示 ---
        with st.expander("🖼️ 查看我已回傳的觀察紀錄"):
            photo_val = user.get("photo_list")
            if pd.isna(photo_val) or str(photo_val).strip() == "":
                st.info("🌑 尚未有解碼紀錄。")
            else:
                p_urls = str(photo_val).split(",")
                t_names = str(user.get("task_list", "")).split(",")
                cols = st.columns(3)
                for i, u in enumerate(p_urls):
                    with cols[i % 3]:
                        thumb = u.replace("/upload/", "/upload/w_400,q_auto:eco/")
                        st.markdown(f'<div class="polaroid"><img src="{thumb}" style="width:100%;"></div>', unsafe_allow_html=True)
                        st.caption(t_names[i] if i < len(t_names) else "未知任務")

        st.write("---")
        tab1, tab2, tab3 = st.tabs(["🎯 任務挑選", "📊 進度瀏覽", "⚙️ 設定"])

        with tab1:
            btn_cols = st.columns(5)
            for i, lvl in enumerate(["A", "B", "C", "D", "E"]):
                if btn_cols[i].button(lvl, key=f"btn_{lvl}", help=level_info[lvl]):
                    st.session_state.selected_lvl = lvl
            
            curr_lvl = st.session_state.selected_lvl
            st.markdown(f"**當前查閱：{level_info[curr_lvl]}**")
            
            # 顯示任務列表
            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == curr_lvl]
            for _, task in filtered.iterrows():
                with st.container():
                    st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if st.button("鎖定此目標", key=f"lock_{task['title']}"):
                        st.session_state.locked_task = task['title']
                        st.session_state.locked_diff = curr_lvl
                        st.toast(f"已選定：{task['title']}")

            # --- [核心整合] 情報回傳區 ---
            if st.session_state.locked_task:
                st.markdown(f'<div class="upload-zone">', unsafe_allow_html=True)
                st.subheader(f"📡 情報回傳：{st.session_state.locked_task}")
                up_file = st.file_uploader("上傳觀察證物", type=['png', 'jpg', 'jpeg'], key="agent_upload")
                
                if up_file:
                    st.image(up_file, width=200, caption="準備回傳的草稿")
                    if st.button("🚀 正式回傳總部 (更新數據)"):
                        with st.spinner("正在將情報同步至雲端資料庫..."):
                            try:
                                # 1. 先上傳到 Cloudinary
                                res = cloudinary.uploader.upload(
                                    up_file,
                                    folder="CSMU_AGENT",
                                    transformation=[{'width': 800, 'crop': "limit"}, {'quality': "auto:eco"}]
                                )
                                img_url = res["secure_url"]
                                
                                # 2. [核心功能] 更新本地 DataFrame 資料
                                # 更新照片清單
                                old_p = str(user.get("photo_list", ""))
                                df_users.at[user_idx, "photo_list"] = img_url if old_p in ["nan", ""] else f"{old_p},{img_url}"
                                
                                # 更新任務標題清單
                                old_t = str(user.get("task_list", ""))
                                df_users.at[user_idx, "task_list"] = st.session_state.locked_task if old_t in ["nan", ""] else f"{old_t},{st.session_state.locked_task}"
                                
                                # [核心功能] 更新對應難度的達成數量 (done_A, done_B 等)
                                diff_col = f"done_{st.session_state.locked_diff}"
                                current_count = int(user.get(diff_col, 0)) if pd.notna(user.get(diff_col)) else 0
                                df_users.at[user_idx, diff_col] = current_count + 1
                                
                                # 3. [核心功能] 將整份 DataFrame 直接寫回 Google Sheets
                                conn.update(worksheet="users", data=df_users)
                                
                                st.balloons()
                                st.success("✅ 情報同步完成！您的進度已更新。")
                                st.cache_data.clear() # 清除快取，確保下次讀取的是最新資料
                                st.rerun()
                            except Exception as e:
                                st.error(f"同步失敗：{e}")
                st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            # 進度結算
            for lvl in ["A", "B", "C", "D", "E"]:
                count = int(user.get(f"done_{lvl}", 0)) if pd.notna(user.get(f"done_{lvl}")) else 0
                st.write(f"{level_info[lvl]}： {count} / 5")
                st.progress(min(count/5, 1.0))
            st.metric("當前累計抽獎券", f"{calculate_total_tickets(user)} 張")

        with tab3:
            st.subheader("⚙️ 檔案維護")
            st.write(f"真實姓名：{user['name(姓名)']}")
            st.info("若需修改暱稱或密碼，請填寫後點擊同步。")
            new_nick = st.text_input("更換暱稱", value=user["Nickname(變更暱稱)"] if pd.notna(user["Nickname(變更暱稱)"]) else "")
            new_pwd = st.text_input("修改自訂密碼", type="password")
            
            if st.button("同步至總部檔案"):
                # 這裡同樣可以使用 conn.update 來實作暱稱修改
                df_users.at[user_idx, "Nickname(變更暱稱)"] = new_nick
                if new_pwd.strip() != "":
                    df_users.at[user_idx, "password(自訂密碼)"] = new_pwd
                conn.update(worksheet="users", data=df_users)
                st.success("✅ 設定已同步！")
                st.rerun()

    # 側邊欄
    if st.session_state.login:
        with st.sidebar:
            st.markdown("### 📍 目前選定目標")
            st.info(st.session_state.locked_task if st.session_state.locked_task else "尚未鎖定")

else: st.error("❌ 資料庫連線中斷")
