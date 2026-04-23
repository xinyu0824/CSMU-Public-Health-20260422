import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection

# --- 1. 視覺與稱號樣式設定 (特工總部 4.7 匿名版) ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")

def get_agent_rank(tickets, photo_count):
    if photo_count == 0: return "🆕 尚未獲得稱號"
    if tickets >= 11: return "🌌 傳奇拍拍"
    elif tickets >= 7: return "🎖️ 大師拍拍"
    elif tickets >= 4: return "🛡️ 菁英拍拍"
    else: return "🌱 實習拍拍"

st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .agent-badge { 
        display: inline-block; padding: 4px 14px; background-color: #5F5F5F; 
        color: #FFFFFF !important; border-radius: 20px; font-size: 0.85rem; 
        font-weight: bold; margin-right: 12px; box-shadow: 1px 1px 4px rgba(0,0,0,0.1);
    }
    .title-wrapper { display: flex; align-items: center; margin-bottom: 25px; gap: 10px; }
    .main-title { font-size: 1.6rem; margin: 0; font-weight: bold; }

    /* 難度方格樣式：橫向寬闊對稱 */
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 15px !important; width: 100% !important; padding: 10px 0 !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 60px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px !important; padding: 15px 0 !important; cursor: pointer; transition: all 0.25s ease; display: flex !important; justify-content: center !important; align-items: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    div[role="radiogroup"] label p { font-size: 1.3rem !important; font-weight: bold !important; color: #5F5F5F !important; margin: 0 !important; }
    div[role="radiogroup"] label[aria-checked="true"] { background-color: #FFC107 !important; border-color: #FFB300 !important; box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3) !important; }
    div[role="radiogroup"] label[aria-checked="true"] p { color: #FFFFFF !important; }

    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    .tutorial-card { background-color: #FFF9E6; padding: 25px; border: 2px dashed #FFC107; border-radius: 12px; margin-bottom: 25px; }
    .polaroid { background-color: white; padding: 12px; border: 1px solid #E6E6E1; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 配置與連線 ---
cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)
level_info = {"A": "【初階】", "B": "【 中下階 】", "C": "【 中上階 】", "D": "【 高階 】", "E": "【 傳奇 】"}

def clean_id_logic(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return ""
    s = str(val).strip(); return s[:-2] if s.endswith('.0') else s

def calculate_total_tickets(user_row):
    try:
        def to_int(v): return int(float(v)) if pd.notna(v) and str(v) != "" and str(v).lower() != "nan" else 0
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
        st.error(f"📡 總部連線失敗：{e}"); return None, None

if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'locked_task': None, 'locked_diff': None, 'selected_lvl': "A"})

df_users, df_tasks = load_data()

# --- 4. 登入流程 ---
if df_users is not None:
    # [核心修正] 匿名登入邏輯：如果已有暱稱，則不顯示本名
    def get_anonymous_label(row):
        real_name = str(row["name(姓名)"])
        nickname = str(row.get("Nickname(變更暱稱)", "")).strip()
        # 若暱稱欄位有內容，則只顯示暱稱，達到隱蔽效果
        if nickname != "" and nickname.lower() != "nan":
            return nickname 
        return real_name

    df_users["login_label"] = df_users.apply(get_anonymous_label, axis=1)

    if not st.session_state.login:
        st.title("🍂 公衛一甲：身分登入")
        login_list = df_users["login_label"].dropna().tolist()
        
        selected_label = st.selectbox("請選擇你的身份 (代號或本名)", ["搜尋代號/姓名"] + login_list)
        input_pwd = st.text_input("密碼 (預設為學號)", type="password")
        
        if st.button("確認進入"):
            # 注意：若多個特工用同個代號，這裡會取第一個匹配項，提醒同學設定唯一代號
            match = df_users[df_users["login_label"] == selected_label]
            if not match.empty:
                user_row = match.iloc[0]
                db_id = clean_id_logic(user_row["Student ID(預設密碼)"])
                db_custom_pwd = str(user_row.get("password(自訂密碼)", "")).strip()
                correct_ans = db_custom_pwd if (db_custom_pwd != "" and db_custom_pwd != "nan") else db_id
                
                if input_pwd.strip() == correct_ans:
                    st.session_state.login, st.session_state.student_id = True, db_id
                    st.rerun()
                else: st.error("密碼錯誤。")
    else:
        # 已登入介面
        df_users["Student ID(預設密碼)"] = df_users["Student ID(預設密碼)"].apply(clean_id_logic)
        user = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id].iloc[0]
        user_idx = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id].index[0]
        
        p_val = str(user.get("photo_list", "")).strip()
        photo_count = 0 if (p_val == "" or p_val.lower() == "nan") else len([u for u in p_val.split(",") if u.strip() != ""])
        is_newbie = (photo_count == 0)
        total_tickets = calculate_total_tickets(user)
        rank_label = get_agent_rank(total_tickets, photo_count)
        
        nick = str(user.get("Nickname(變更暱稱)", "")).strip()
        disp_name = nick if (nick != "" and nick.lower() != "nan") else user["name(姓名)"]
        
        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{rank_label}</span><span class="main-title">{disp_name} 的特工記憶庫</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.markdown(f"### 🎖️ 個人檔案\n**稱號：** {rank_label}\n**獎券：** {total_tickets} 張")
            st.write("---")
            if st.session_state.locked_task: st.info(f"鎖定：{st.session_state.locked_task}")
            if st.button("🚪 登出系統"): st.session_state.login = False; st.rerun()

        with st.expander("🖼️ 我的紀錄 (已上傳圖片)"):
            if photo_count == 0: st.info("🌑 尚未有紀錄。")
            else:
                p_urls = [u.strip() for u in p_val.split(",") if u.strip() != ""]
                t_names = str(user.get("task_list", "")).split(",")
                cols = st.columns(3)
                for i, url in enumerate(p_urls):
                    with cols[i % 3]:
                        thumb = url.replace("/upload/", "/upload/w_400,q_auto:eco/")
                        st.markdown(f'<div class="polaroid"><img src="{thumb}" style="width:100%;"></div>', unsafe_allow_html=True)
                        st.caption(t_names[i] if i < len(t_names) else "")

        tab1, tab2, tab3 = st.tabs(["🎯 任務選取", "📊 進度追蹤", "⚙️ 設定"])

        with tab1:
            if is_newbie:
                st.markdown('<div class="tutorial-card"><h3>👋 哈囉特工，歡迎加入！</h3><p>完成新手引導任務後即可正式解鎖正式分區。</p><hr><b>🚩 任務：快試試看</b><br><small>拍攝一張校園內角落或具有學習氛圍的照片，完成你的首場觀測！</small></div>', unsafe_allow_html=True)
                st.session_state.locked_task, st.session_state.locked_diff = "新手引導：初試身心", "A"
            else:
                st.write("### 📍 步驟一：選擇難度")
                diff_opts = ["A", "B", "C", "D", "E"]
                selected_lvl = st.radio("難度", options=diff_opts, index=diff_opts.index(st.session_state.selected_lvl), horizontal=True, label_visibility="collapsed")
                if selected_lvl != st.session_state.selected_lvl:
                    st.session_state.selected_lvl, st.session_state.locked_task = selected_lvl, None
                    st.rerun()
                st.markdown(f"#### {level_info[st.session_state.selected_lvl]}")
                filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == st.session_state.selected_lvl]
                for _, task in filtered.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        if st.button("鎖定此任務", key=f"lock_{task['title']}"):
                            st.session_state.locked_task, st.session_state.locked_diff = task['title'], st.session_state.selected_lvl
                            st.toast(f"已鎖定：{task['title']}")

            if st.session_state.locked_task:
                st.write("---")
                st.subheader(f"回傳中：{st.session_state.locked_task}")
                up_file = st.file_uploader("選取照片", type=['png', 'jpg', 'jpeg'], key=f"up_{st.session_state.locked_task}")
                if up_file:
                    if st.button("🚀 正式回傳總部"):
                        with st.spinner("同步中..."):
                            try:
                                res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                                img_url = res["secure_url"]
                                df_users['photo_list'] = df_users['photo_list'].astype(object)
                                df_users['task_list'] = df_users['task_list'].astype(object)
                                cur_p = str(df_users.at[user_idx, "photo_list"]).strip()
                                df_users.at[user_idx, "photo_list"] = str(img_url if (cur_p == "" or cur_p.lower() == "nan") else f"{cur_p},{img_url}")
                                cur_t = str(df_users.at[user_idx, "task_list"]).strip()
                                df_users.at[user_idx, "task_list"] = str(st.session_state.locked_task if (cur_t == "" or cur_t.lower() == "nan") else f"{cur_t},{st.session_state.locked_task}")
                                diff_col = f"done_{st.session_state.locked_diff}"
                                try: val = int(float(df_users.at[user_idx, diff_col])) if pd.notna(df_users.at[user_idx, diff_col]) else 0
                                except: val = 0
                                df_users.at[user_idx, diff_col] = str(val + 1)
                                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                st.balloons(); st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"同步失敗：{e}")

        with tab2:
            st.subheader("📊 進度報表")
            for lvl in ["A", "B", "C", "D", "E"]:
                c = user.get(f"done_{lvl}", 0)
                try: val = int(float(c))
                except: val = 0
                st.write(f"{level_info[lvl]}： {val} / 5")
                st.progress(min(val/5, 1.0))
            st.metric("當前累計獎券", f"{total_tickets} 張")

        with tab3:
            st.subheader("⚙️ 設定")
            new_nick = st.text_input("修改特工代號 (設定後登入名單將隱藏本名)", value=nick)
            new_pwd = st.text_input("修改密碼", type="password", placeholder="留空不修改")
            if st.button("💾 儲存設定"):
                df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object)
                df_users['password(自訂密碼)'] = df_users['password(自訂密碼)'].astype(object)
                df_users.at[user_idx, "Nickname(變更暱稱)"] = str(new_nick)
                if new_pwd.strip() != "": df_users.at[user_idx, "password(自訂密碼)"] = str(new_pwd)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.success("✅ 代號已更新，下次登入生效！"); st.cache_data.clear(); st.rerun()

else: st.error("❌ 無法連線")
