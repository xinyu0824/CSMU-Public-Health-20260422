import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import json
import random
from datetime import datetime, timedelta

# --- 1. 配置與強效初始化 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
COOLDOWN_HOURS = 12

st.set_page_config(page_title="📸 導生聚：拍拍挑戰", layout="centered")

# [鋼鐵初始化] 防止 AttributeError 導致全頁崩潰
if 'init_done' not in st.session_state:
    st.session_state.update({
        'login': False, 'student_id': None, 'selected_lvl': "A", 
        't_done': {}, 'g_res': None, 'p_shown': False, 'init_done': True
    })

# --- 數據安全工具 ---
def safe_str(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return ""
    return str(val).strip()

def safe_int(val):
    try: return int(float(safe_str(val)))
    except: return 0

def get_agent_rank(tickets, photo_count):
    if photo_count == 0: return "尚未獲得稱號"
    if tickets >= 11: return "🌌 傳奇拍拍"
    elif tickets >= 7: return "🎖️ 大師拍拍"
    elif tickets >= 4: return "🛡️ 菁英拍拍"
    else: return "🌱 實習拍拍"

st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .agent-badge { display: inline-block; padding: 4px 14px; background-color: #5F5F5F; color: #FFFFFF !important; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 12px; }
    
    /* 🟢 綠底白字進度勳章 */
    .t-badge { 
        background-color: #28a745; color: white !important; padding: 4px 14px; 
        border-radius: 12px; font-size: 0.9rem; font-weight: bold; box-shadow: 1px 1px 4px rgba(0,0,0,0.1);
    }
    
    .tutorial-box {
        background-color: #FFFFFF; padding: 22px; border-radius: 15px; border-left: 6px solid #FFC107;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px;
    }
    .tutorial-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; }
    
    /* 🏆 榮譽榜質感設計 */
    .leaderboard-card {
        background-color: #FFFFFF; padding: 15px; border-radius: 12px; border: 1px solid #E6E6E1; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .rank-num { font-weight: bold; font-size: 1.2rem; color: #FFC107; width: 35px; }

    .casino-zone { background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%); color: #FFC107 !important; padding: 30px; border-radius: 20px; border: 3px solid #FFC107; text-align: center; margin-bottom: 25px; }
    .win-card { background: linear-gradient(135deg, #FFD700 0%, #FFC107 100%); color: white !important; padding: 30px; border-radius: 20px; text-align: center; box-shadow: 0 10px 25px rgba(255,193,7,0.4); margin: 20px 0; }
    
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 12px !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 65px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px; padding: 15px 0 !important; cursor: pointer; display: flex !important; justify-content: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 服務連線 ---
cloudinary.config(cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"], api_key=st.secrets["CLOUDINARY_API_KEY"], api_secret=st.secrets["CLOUDINARY_API_SECRET"], secure=True)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1)
def load_data():
    try:
        u = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        t = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return u, t
    except: return None, None

df_users, df_tasks = load_data()

# --- 3. 核心流程 ---
if df_users is not None:
    # 欄位預防性補全
    req_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set', 'gift_given', 'extra_tickets', 'gamble_balance', 'done_A', 'done_B', 'done_C', 'done_D', 'done_E', 'gamble_profit', 'photo_list', 'task_list', 'task_cooldowns', 'Nickname(變更暱稱)', 'password(自訂密碼)', 'gamble_count', 'loss_count']
    for c in req_cols:
        if c not in df_users.columns: df_users[c] = "0" if c != "task_cooldowns" else "{}"

    if not st.session_state.login:
        st.title("🍂 公衛二甲：導生聚活動")
        # 修正登入邏輯：Nickname(變更暱稱) 修正 typo
        login_labels = df_users.apply(lambda r: f"{safe_str(r['Nickname(變更暱稱)'])} ({r['name(姓名)']})" if safe_str(r['Nickname(變更暱稱)']) != "" else r['name(姓名)'], axis=1).tolist()
        sel = st.selectbox("帳號（預設為本名） *可於登入後，修改暱稱", ["搜尋姓名..."] + login_labels)
        pwd = st.text_input("密碼（預設為學號） *可於登入後，自訂密碼", type="password")
        if st.button("登入"):
            # 匹配逻辑修正
            match = df_users[(df_users['name(姓名)'] == sel) | (df_users.apply(lambda r: f"{safe_str(r['Nickname(變更暱稱)'])} ({r['name(姓名)']})", axis=1) == sel)]
            if not match.empty:
                u_row = match.iloc[0]; db_id = str(u_row["Student ID(預設密碼)"]).strip().split('.')[0]
                db_pwd = safe_str(u_row.get("password(自訂密碼)", "")); correct = db_pwd if db_pwd != "" else db_id
                if pwd.strip() == correct:
                    st.session_state.login, st.session_state.student_id = True, db_id; st.rerun()
                else: st.error("密碼錯誤")
    else:
        # 已登入
        u_match = df_users[df_users["Student ID(預設密碼)"].astype(str).str.contains(st.session_state.student_id)]
        user = u_match.iloc[0]; u_idx = u_match.index[0]
        
        # 同步教學進度
        for col in ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set']:
            if safe_str(user.get(col)) == "1": st.session_state.t_done[col] = True

        m_base = (safe_int(user.get('done_A')) // 5) + (safe_int(user.get('done_B')) // 3) + (safe_int(user.get('done_C')) // 2) + safe_int(user.get('done_D')) + (safe_int(user.get('done_E')) * 2)
        total_tickets = max(0, m_base + safe_int(user.get('gamble_balance')) + safe_int(user.get('extra_tickets')))
        p_list = [u for u in safe_str(user.get("photo_list")).split(",") if u.strip() != ""]
        done_count = sum(1 for v in st.session_state.t_done.values() if v)

        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{get_agent_rank(total_tickets, len(p_list))}</span><span class="main-title">{safe_str(user.get("Nickname(變更暱稱)")) if safe_str(user.get("Nickname(變更暱稱)")) != "" else user["name(姓名)"]}</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("抽獎券總額", f"{total_tickets} 張")
            if st.button("🚪 帳號登出"): st.session_state.login = False; st.rerun()

        tabs = st.tabs(["🎯 任務挑選", "📊 進度追蹤", "🏆 排行榜", "🎰 地下博弈", "⚙️ 帳號設定"])

        def mark_tuto_step(col):
            st.session_state.t_done[col] = True
            df_users[col] = df_users[col].astype(object)
            df_users.at[u_idx, col] = "1"
            if len(st.session_state.t_done) == 4 and safe_str(user.get('gift_given')) != "1":
                df_users['gift_given'] = df_users['gift_given'].astype(object); df_users['extra_tickets'] = df_users['extra_tickets'].astype(object)
                df_users.at[u_idx, 'gift_given'] = "1"
                df_users.at[u_idx, 'extra_tickets'] = str(safe_int(user.get('extra_tickets')) + 1)
            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users); st.cache_data.clear(); st.rerun()

        # --- Tab 1: 實戰任務教學 ---
        with tabs[0]:
            is_locked = not st.session_state.t_done.get('tuto_task', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>🚀新手指引：操作教學</h3><p>請上傳任意一張圖片，不限主題，不可涉及違法、色情。</h3><p>完成後將解鎖A~E難度分級，完成此任務將計入 A 級難度進度 +1。</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                up_n = st.file_uploader("上傳任務照片", type=['png','jpg','jpeg'], key="up_newbie")
                if up_n and st.button("確認送出，解鎖完整任務系統", use_container_width=True):
                    try:
                        res = cloudinary.uploader.upload(up_n, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                        df_users['photo_list'] = df_users['photo_list'].astype(object); df_users['task_list'] = df_users['task_list'].astype(object); df_users['done_A'] = df_users['done_A'].astype(object)
                        cp = safe_str(user.get("photo_list")); ct = safe_str(user.get("task_list"))
                        df_users.at[u_idx, "photo_list"] = str(res["secure_url"] if cp == "" else f"{cp},{res['secure_url']}")
                        df_users.at[u_idx, "task_list"] = str("新手指引：操作教學" if ct == "" else f"{ct},新手指引：操作教學")
                        df_users.at[u_idx, "done_A"] = str(safe_int(user.get("done_A")) + 1)
                        mark_tuto_step('tuto_task')
                    except: st.error("上傳失敗，請重試")
            else:
                st.write("### 📍選擇任務難度")
                lvl = st.radio("難度分級", ["A", "B", "C", "D", "E"], horizontal=True, label_visibility="collapsed")
                filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == lvl]
                for idx, task in filtered.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        if st.button("選擇此任務", key=f"lk_{idx}"): st.toast(f"已鎖定：{task['title']}")

        # --- Tab 2: 進度 ---
        with tabs[1]:
            is_locked = not st.session_state.t_done.get('tuto_prog', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>📊 新手指引：操作教學</h3><p>任務數量依照難度而有不同，完成對應數量，可獲得導生聚當天的禮物抽獎券，可重複完成任務，領取多張抽獎券。</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已閱讀完畢", key="btn_t2", use_container_width=True): mark_tuto_step('tuto_prog')
            st.subheader("📊 任務完成度統計")
            for l in ["A", "B", "C", "D", "E"]:
                v = safe_int(user.get(f"done_{l}")); st.write(f"難度 {l}： {v} / 5"); st.progress(min(v/5, 1.0))

        # --- Tab 3: 🏆 排行榜 (前 8 名) ---
        with tabs[2]:
            st.write("### 🏆 榮譽殿堂")
            # 門檻：必須上傳過照片
            active_u = df_users[df_users['photo_list'].apply(lambda x: safe_str(x) != "")]
            def get_nick(row):
                n = safe_str(row.get("Nickname(變更暱稱)", ""))
                return n if n != "" else f"{str(row['name(姓名)'])[0]}* 特工"

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 📸 「任」勞「任」怨 (完成任務數量)")
                active_u['total'] = active_u.apply(lambda r: sum(safe_int(r.get(f'done_{l}')) for l in "ABCDE"), axis=1)
                for i, (_, r) in enumerate(active_u.sort_values(by='total', ascending=False).head(8).iterrows()):
                    st.markdown(f'<div class="leaderboard-card"><span class="rank-num">{i+1}</span><span>{get_nick(r)}</span><span>{int(r["total"])} 次</span></div>', unsafe_allow_html=True)
            with c2:
                st.markdown("#### 🎰 Let me 賭 it for you (透過博弈獲取最高抽獎券數量)")
                for i, (_, r) in enumerate(active_u.sort_values(by='gamble_profit', ascending=False).head(8).iterrows()):
                    st.markdown(f'<div class="leaderboard-card"><span class="rank-num">{i+1}</span><span>{get_nick(r)}</span><span>{int(r["gamble_profit"])} 張</span></div>', unsafe_allow_html=True)

        # --- Tab 4: 賭場 ---
        with tabs[3]:
            is_locked = not st.session_state.t_done.get('tuto_gamble', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>🎰 新手指引：操作教學</h3><p>透過完成任務所獲得抽獎券，可於此進行博弈，每次博次消耗一張，最高可獲得4張，最低擇一無所獲</h3><p>當累積 4 次血本無歸時，將贈送兩張抽獎券！</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已閱讀完畢", key="btn_t4", use_container_width=True): mark_tuto_step('tuto_gamble')
            st.markdown('<div class="casino-zone"><h2>🎰 特工地下城</h2><p>這裡是命運的分叉路，無所不有或是一無所有。</p></div>', unsafe_allow_html=True)
            if total_tickets < 1: st.error("❌ 目前尚未有一張抽獎券")
            else:
                if st.button("🧧 消耗 1 張抽獎券！", use_container_width=True):
                    roll = random.random() * 100
                    gain = -1 
                    if roll < 10: gain += 4; r_t, r_m, r_s = "💎 奇蹟！", "獲得 4 張！", "win"
                    elif roll < 35: gain += 3; r_t, r_m, r_s = "🔥 大勝！", "獲得 3 張！", "win"
                    elif roll < 75: gain += 2; r_t, r_m, r_s = "✨ 小贏！", "獲得 2 張！", "win"
                    elif roll < 85: gain += 1; r_t, r_m, r_s = "⚖️ 持平", "本金退回。", "draw"
                    else: gain += 0; r_t, r_m, r_s = "💀 慘賠...", "獎券化為烏有。", "loss"
                    
                    for col in ['gamble_balance', 'loss_count', 'gamble_count', 'gamble_profit']: df_users[col] = df_users[col].astype(object)
                    cl = safe_int(user.get('loss_count')); nl = cl + 1 if r_s == "loss" else cl
                    bonus = 0; 
                    if nl >= 4: bonus = 2; nl = 0; st.toast("🛡️ 運氣差不要緊，給你額外兩張抽獎券！")
                    
                    df_users.at[u_idx, "gamble_balance"] = str(safe_int(user.get('gamble_balance')) + gain + bonus)
                    df_users.at[u_idx, "loss_count"] = str(nl)
                    df_users.at[u_idx, "gamble_count"] = str(safe_int(user.get('gamble_count')) + 1)
                    df_users.at[u_idx, "gamble_profit"] = str(safe_int(user.get('gamble_profit')) + gain)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users); st.session_state.g_res = {"t": r_t, "m": r_m, "s": r_s}; st.cache_data.clear(); st.rerun()

            if st.session_state.g_res:
                res = st.session_state.g_res
                if res['s'] == "win": st.balloons(); st.markdown(f'<div class="win-card"><h2>{res["t"]}</h2><p>{res["m"]}</p></div>', unsafe_allow_html=True)
                elif res['s'] == "draw": st.info(res['m'])
                else: st.error(res['m'])
                if st.button("關閉"): st.session_state.g_res = None; st.rerun()

        # --- Tab 5: 設定 ---
        with tabs[4]:
            is_locked = not st.session_state.t_done.get('tuto_set', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>⚙️ 新手指引：操作教學</h3><p>可在此修改帳號名稱，後續他人僅可見你的暱稱，也可以在此自訂登入密碼學</h3><p>後續若忘記帳號或者密碼，可聯繫班代潘芯渝，我會幫你恢復預設密碼嘻嘻。</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已閱讀完畢", key="btn_t3", use_container_width=True): mark_tuto_step('tuto_set')
            st.subheader("⚙️ 帳號設定")
            nn = st.text_input("變更暱稱", value=safe_str(user.get("Nickname(變更暱稱)")))
            np = st.text_input("自訂密碼", type="password", placeholder="留空不修改")
            if st.button("💾 更新資料"):
                df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object); df_users['password(自訂密碼)'] = df_users['password(自訂密碼)'].astype(object)
                df_users.at[u_idx, "Nickname(變更暱稱)"] = str(nn)
                if np.strip() != "": df_users.at[u_idx, "password(自訂密碼)"] = str(np)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users); st.success("修改成功")

        # --- 結業大看板 ---
        if done_count == 4 and safe_str(user.get('gift_given')) == "1":
            if not st.session_state.p_shown:
                st.balloons()
                st.markdown("""<div style="background-color:#FFF9E6; padding:35px; border-radius:20px; text-align:center; border:4px solid #FFC107;">
                    <h1 style="color:#FFC107; margin:0;">🎊 培訓合格 🎊</h1><p style="font-size:1.2rem; margin-top:10px;">你已完成實戰教學並集齊說明！</p>
                    <h2 style="background:#FFC107; color:white; display:inline-block; padding:5px 20px; border-radius:10px;">🎁 獎勵：+1 張抽獎券</h2></div>""", unsafe_allow_html=True)
                if st.button("立刻出動！", use_container_width=True): st.session_state.p_shown = True; st.rerun()
else: st.error("❌ 連線失敗")
