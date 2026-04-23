import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import random
import json
from datetime import datetime, timedelta

# --- 1. 定時與環境設定 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
COOLDOWN_HOURS = 12

st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")

# [稱號邏輯]
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
    .agent-badge { display: inline-block; padding: 4px 14px; background-color: #5F5F5F; color: #FFFFFF !important; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 12px; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); }
    
    /* 炫耀用：勝利卡片 */
    .win-card {
        background: linear-gradient(135deg, #FFD700 0%, #FFC107 100%);
        color: #FFFFFF !important;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        border: 4px solid #FFFFFF;
        box-shadow: 0 10px 20px rgba(255, 193, 7, 0.4);
        margin: 20px 0;
    }
    .win-card h2 { color: #FFFFFF !important; margin: 0; }

    /* 賭場風格 */
    .casino-zone { background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%); color: #FFC107 !important; padding: 25px; border-radius: 20px; border: 3px solid #FFC107; text-align: center; margin-bottom: 25px; }
    
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 12px !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 65px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px !important; padding: 15px 0 !important; cursor: pointer; display: flex !important; justify-content: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    div[role="radiogroup"] label p { font-size: 1.3rem !important; font-weight: bold !important; color: #5F5F5F !important; }
    div[role="radiogroup"] label[aria-checked="true"] { background-color: #FFC107 !important; border-color: #FFB300 !important; }
    div[role="radiogroup"] label[aria-checked="true"] p { color: #FFFFFF !important; }

    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    .onboarding-box { background-color: #FFFFFF; padding: 30px; border-radius: 20px; border: 2px solid #FFC107; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 配置 ---
cloudinary.config(cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"], api_key=st.secrets["CLOUDINARY_API_KEY"], api_secret=st.secrets["CLOUDINARY_API_SECRET"], secure=True)
conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_logic_tickets(user_row):
    try:
        def to_int(v): return int(float(v)) if pd.notna(v) and str(v) != "" and str(v).lower() != "nan" else 0
        # 1. 任務獲得
        mission_base = (to_int(user_row.get('done_A', 0)) // 5) + (to_int(user_row.get('done_B', 0)) // 3) + \
                       (to_int(user_row.get('done_C', 0)) // 2) + to_int(user_row.get('done_D', 0)) + (to_int(user_row.get('done_E', 0)) * 2)
        # 2. 博弈累積 (gamble_balance)
        gamble_net = to_int(user_row.get('gamble_balance', 0))
        # 3. 大禮包額外券 (extra_tickets)
        gift_bonus = to_int(user_row.get('extra_tickets', 0))
        
        return mission_base, gamble_net, gift_bonus, max(0, mission_base + gamble_net + gift_bonus)
    except: return 0, 0, 0, 0

@st.cache_data(ttl=2)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except: return None, None

if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'locked_task': None, 'selected_lvl': "A", 'gamble_result': None})

df_users, df_tasks = load_data()

# --- 3. 流程 ---
if df_users is not None:
    def get_anonymous_label(row):
        nick = str(row.get("Nickname(變更暱稱)", "")).strip()
        return nick if (nick != "" and nick.lower() != "nan") else str(row["name(姓名)"])
    df_users["login_label"] = df_users.apply(get_anonymous_label, axis=1)

    if not st.session_state.login:
        st.title("🍂 公衛一甲：特工登入")
        login_list = df_users["login_label"].dropna().tolist()
        selected_label = st.selectbox("請選擇身份", ["搜尋代號/姓名"] + login_list)
        input_pwd = st.text_input("密碼 (預設學號)", type="password")
        if st.button("確認進入"):
            match = df_users[df_users["login_label"] == selected_label]
            if not match.empty:
                user_row = match.iloc[0]
                db_id = str(user_row["Student ID(預設密碼)"]).strip()
                if db_id.endswith('.0'): db_id = db_id[:-2]
                db_custom_pwd = str(user_row.get("password(自訂密碼)", "")).strip()
                correct_ans = db_custom_pwd if (db_custom_pwd != "" and db_custom_pwd != "nan") else db_id
                if input_pwd.strip() == correct_ans:
                    st.session_state.login, st.session_state.student_id = True, db_id
                    st.rerun()
                else: st.error("密碼錯誤。")
    else:
        # 已登入
        user_match = df_users[df_users["Student ID(預設密碼)"].astype(str).str.contains(st.session_state.student_id)]
        user = user_match.iloc[0]
        user_idx = user_match.index[0]
        
        # 讀取教學與錢包
        try: has_done_tutorial = int(float(user.get("tutorial_done", 0))) == 1
        except: has_done_tutorial = False
        
        m_base, g_net, g_gift, total_tickets = calculate_logic_tickets(user)

        if not has_done_tutorial:
            st.markdown("""
                <div class="onboarding-box">
                    <h2>👋 歡迎！特工觀測站守則</h2>
                    <p>開始任務前，請詳閱任務說明：</p>
                    <ul>
                        <li><b>📸 拍拍任務</b>：完成任務後有 12 小時冷卻期。</li>
                        <li><b>🎰 地下賭場</b>：勝率 75%！累積 4 次血本無歸有保底。</li>
                        <li><b>🧧 雙重獎勵</b>：除任務獲得外，聚會前夕將有驚喜大禮包。</li>
                        <li><b>🛡️ 專業操守</b>：請尊重隱私，勿拍攝他人清晰面孔。</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            if st.button("✅ 了解規則 (並領取開賽獎勵)", use_container_width=True):
                df_users['tutorial_done'] = df_users['tutorial_done'].astype(object)
                df_users['extra_tickets'] = df_users['extra_tickets'].astype(object)
                df_users.at[user_idx, "tutorial_done"] = "1"
                df_users.at[user_idx, "extra_tickets"] = str(int(float(user.get("extra_tickets", 0))) + 1)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.balloons(); st.cache_data.clear(); st.rerun()
            st.stop()

        photo_count = len(str(user.get("photo_list", "")).split(",")) if str(user.get("photo_list", "")).strip() != "" and str(user.get("photo_list", "")).lower() != "nan" else 0
        rank_label = get_agent_rank(total_tickets, photo_count)
        
        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{rank_label}</span><span class="main-title">{user["login_label"]} 的特工記憶庫</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("當前獎券總數", f"{total_tickets} 張")
            st.write(f"└ 任務累積：{m_base} 張")
            st.write(f"└ 博弈損益：{g_net} 張")
            if g_gift > 0: st.write(f"└ 🎁 大禮包：{g_gift} 張")
            st.write("---")
            if st.button("🚪 登出系統"): st.session_state.login = False; st.rerun()

        tab1, tab2, tab4, tab3 = st.tabs(["🎯 任務挑選", "📊 進度追蹤", "🎰 地下博弈", "⚙️ 設定"])

        with tab1:
            st.write("### 📍 步驟一：選擇難度")
            selected_lvl = st.radio("難度", options=["A", "B", "C", "D", "E"], index=["A", "B", "C", "D", "E"].index(st.session_state.selected_lvl), horizontal=True, label_visibility="collapsed")
            if selected_lvl != st.session_state.selected_lvl: 
                st.session_state.selected_lvl, st.session_state.locked_task = selected_lvl, None; st.rerun()
            
            # 冷卻邏輯
            cooldown_str = str(user.get("task_cooldowns", "{}")).strip()
            if cooldown_str == "" or cooldown_str.lower() == "nan": cooldown_str = "{}"
            try: cooldown_dict = json.loads(cooldown_str)
            except: cooldown_dict = {}

            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == st.session_state.selected_lvl]
            for idx, task in filtered.iterrows():
                title = task["title"]
                is_cd = False
                if title in cooldown_dict:
                    last_time = datetime.fromisoformat(cooldown_dict[title])
                    if datetime.now() < last_time + timedelta(hours=COOLDOWN_HOURS): is_cd = True
                
                with st.container():
                    st.markdown(f'<div class="mission-card" style="opacity: {"0.5" if is_cd else "1"};"><b>{title} {"(冷卻中)" if is_cd else ""}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if not is_cd and st.button("鎖定此任務", key=f"lock_{idx}"):
                        st.session_state.locked_task = title; st.toast(f"已鎖定：{title}")

            if st.session_state.locked_task:
                st.write("---")
                st.subheader(f"回傳：{st.session_state.locked_task}")
                up_file = st.file_uploader("選取照片", type=['png', 'jpg', 'jpeg'], key="up_main")
                if up_file and st.button("🚀 正式回傳"):
                    try:
                        res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                        df_users['photo_list'] = df_users['photo_list'].astype(object)
                        df_users['task_list'] = df_users['task_list'].astype(object)
                        df_users['task_cooldowns'] = df_users['task_cooldowns'].astype(object)
                        cur_p = str(df_users.at[user_idx, "photo_list"]).strip()
                        df_users.at[user_idx, "photo_list"] = str(res["secure_url"] if (cur_p == "" or cur_p.lower() == "nan") else f"{cur_p},{res['secure_url']}")
                        cur_t = str(df_users.at[user_idx, "task_list"]).strip()
                        df_users.at[user_idx, "task_list"] = str(st.session_state.locked_task if (cur_t == "" or cur_t.lower() == "nan") else f"{cur_t},{st.session_state.locked_task}")
                        
                        cooldown_dict[st.session_state.locked_task] = datetime.now().isoformat()
                        df_users.at[user_idx, "task_cooldowns"] = json.dumps(cooldown_dict)
                        
                        conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                        st.balloons(); st.cache_data.clear(); st.rerun()
                    except: st.error("連線錯誤")

        with tab4:
            st.markdown('<div class="casino-zone"><h2>🎰 特工地下城</h2><p>搏一搏，獎券變摩托！勝率 75%</p></div>', unsafe_allow_html=True)
            
            if total_tickets < 1:
                st.error("❌ 你的抽獎券不足！")
            else:
                if st.button("🔥 消耗 1 張下注！", use_container_width=True):
                    roll = random.random() * 100
                    gain = -1 
                    if roll < 10: gain += 4; title="💎 奇蹟降臨！"; msg = "你獲得了 4 張獎券！"; res="win"
                    elif roll < 35: gain += 3; title="🔥 大發橫財！"; msg = "你獲得了 3 張獎券！"; res="win"
                    elif roll < 75: gain += 2; title="✨ 小有斬獲！"; msg = "你獲得了 2 張獎券！"; res="win"
                    elif roll < 85: gain += 1; title="⚖️ 收支平衡"; msg = "本金退回。"; res="draw"
                    else: gain += 0; title="💀 血本無歸..."; msg = "這就是代價。"; res="loss"
                    
                    # 數據存回
                    df_users['gamble_balance'] = df_users['gamble_balance'].astype(object)
                    df_users['loss_count'] = df_users['loss_count'].astype(object)
                    
                    cur_loss = int(float(user.get("loss_count", 0)))
                    new_loss = cur_loss + (1 if res=="loss" else 0)
                    bonus = 0
                    if new_loss >= 4:
                        bonus = 2; new_loss = 0; st.toast("🛡️ 保底觸發！+2")
                    
                    df_users.at[user_idx, "gamble_balance"] = str(int(float(user.get("gamble_balance", 0))) + gain + bonus)
                    df_users.at[user_idx, "loss_count"] = str(new_loss)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                    
                    # --- 炫耀用結果展示 ---
                    st.session_state.gamble_result = {"title": title, "msg": msg, "res": res}
                    st.rerun()

            if st.session_state.gamble_result:
                res = st.session_state.gamble_result
                if res['res'] == "win":
                    st.balloons()
                    st.markdown(f'<div class="win-card"><h2>{res["title"]}</h2><p>{res["msg"]}</p><br><small>#CSMU特工博弈 #公衛賭神</small></div>', unsafe_allow_html=True)
                elif res['res'] == "draw": st.info(res['msg'])
                else: st.error(res['msg'])
                if st.button("繼續挑戰"): 
                    st.session_state.gamble_result = None; st.rerun()

        with tab2:
            st.subheader("📊 特工進度")
            st.write(f"任務獲得：{m_base} 張")
            st.write(f"博弈累計：{g_net} 張")
            st.write(f"禮包補貼：{g_gift} 張")
            st.write(f"### 總計可用：{total_tickets} 張")
            st.write("---")
            for lvl in ["A", "B", "C", "D", "E"]:
                c = user.get(f"done_{lvl}", 0)
                st.write(f"難度 {lvl} 進度： {int(float(c))} / 5")
                st.progress(min(int(float(c))/5, 1.0))

else: st.error("❌ 無法連線")
