import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import json
import random
from datetime import datetime, timedelta

# --- 1. 配置與環境 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
COOLDOWN_HOURS = 12

st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")

# --- 數據安全轉換器 ---
def safe_str(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return "0"
    return str(val).strip()

def safe_int(val):
    try: return int(float(safe_str(val)))
    except: return 0

def get_agent_rank(tickets, photo_count):
    if photo_count == 0: return "🆕 待命特工"
    if tickets >= 11: return "🌌 傳奇拍拍"
    elif tickets >= 7: return "🎖️ 大師拍拍"
    elif tickets >= 4: return "🛡️ 菁英拍拍"
    else: return "🌱 實習拍拍"

st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .agent-badge { display: inline-block; padding: 4px 14px; background-color: #5F5F5F; color: #FFFFFF !important; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 12px; }
    
    /* 🟢 綠色進度勳章 */
    .t-badge { 
        background-color: #28a745; color: white !important; padding: 4px 12px; 
        border-radius: 12px; font-size: 0.85rem; font-weight: bold; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    
    .tutorial-box {
        background-color: #FFFFFF; padding: 22px; border-radius: 15px; border-left: 6px solid #FFC107;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px;
    }
    .tutorial-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; }
    
    .leaderboard-card {
        background-color: #FFFFFF; padding: 15px; border-radius: 12px; border: 1px solid #E6E6E1; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .rank-num { font-weight: bold; font-size: 1.2rem; color: #FFC107; width: 30px; }
    
    .casino-zone { background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%); color: #FFC107 !important; padding: 30px; border-radius: 20px; border: 3px solid #FFC107; text-align: center; margin-bottom: 25px; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 12px !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 65px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px; padding: 15px 0 !important; cursor: pointer; display: flex !important; justify-content: center !important; }
    div[role="radiogreb"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 連線 ---
cloudinary.config(cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"], api_key=st.secrets["CLOUDINARY_API_KEY"], api_secret=st.secrets["CLOUDINARY_API_SECRET"], secure=True)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except: return None, None

# 初始化記憶
if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'selected_lvl': "A", 't_done': {}, 'g_res': None, 'p_shown': False})

df_users, df_tasks = load_data()

# --- 3. 核心流程 ---
if df_users is not None:
    # 確保欄位齊全
    req_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set', 'gift_given', 'extra_tickets', 'gamble_balance', 'done_A', 'done_B', 'done_C', 'done_D', 'done_E', 'gamble_profit', 'photo_list', 'task_list', 'task_cooldowns', 'Nickname(變更暱稱)', 'password(自訂密碼)']
    for col in req_cols:
        if col not in df_users.columns: df_users[col] = "0" if "done" in col or "tickets" in col else ("{}" if "cooldowns" in col else "")

    if not st.session_state.login:
        st.title("🍂 公衛一甲：特工登入")
        # 登入用標籤 (暱稱優先)
        login_labels = df_users.apply(lambda r: f"{safe_str(r['Nickname(變更暱稱)'])} ({r['name(姓名)']})" if (safe_str(r['Nickname(變更暱稱)']) != "0" and safe_str(r['Nickname(變更暱稱)']) != "") else r['name(姓名)'], axis=1).tolist()
        sel = st.selectbox("請選擇特工身份", ["搜尋中..."] + login_labels)
        pwd = st.text_input("密碼", type="password")
        if st.button("進入觀測站"):
            match = df_users[(df_users['name(姓名)'] == sel) | (df_users.apply(lambda r: f"{safe_str(r['Nickname(變更暱稱)'])} ({r['name(姓名)']})", axis=1) == sel)]
            if not match.empty:
                u_row = match.iloc[0]; db_id = str(u_row["Student ID(預設密碼)"]).strip().split('.')[0]
                db_pwd = safe_str(u_row.get("password(自訂密碼)", "")); correct = db_pwd if (db_pwd != "" and db_pwd != "0") else db_id
                if pwd.strip() == correct:
                    st.session_state.login, st.session_state.student_id = True, db_id; st.rerun()
                else: st.error("密碼錯誤")
    else:
        # 已登入：資料同步
        u_match = df_users[df_users["Student ID(預設密碼)"].astype(str).str.contains(st.session_state.student_id)]
        user = u_match.iloc[0]; u_idx = u_match.index[0]
        
        # 同步教學暫存
        for col in ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set']:
            if safe_str(user.get(col)) == "1": st.session_state.t_done[col] = True

        m_count = sum(safe_int(user.get(f'done_{l}')) for l in "ABCDE")
        m_base = (safe_int(user.get('done_A')) // 5) + (safe_int(user.get('done_B')) // 3) + (safe_int(user.get('done_C')) // 2) + safe_int(user.get('done_D')) + (safe_int(user.get('done_E')) * 2)
        total_tickets = max(0, m_base + safe_int(user.get('gamble_balance')) + safe_int(user.get('extra_tickets')))
        p_list = [u for u in safe_str(user.get("photo_list")).split(",") if u.strip() != "" and u != "0"]
        photo_count = len(p_list)
        rank_label = get_agent_rank(total_tickets, photo_count)
        done_count = sum(1 for v in st.session_state.t_done.values() if v)

        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{rank_label}</span><span class="main-title">{safe_str(user.get("Nickname(變更暱稱)")) if safe_str(user.get("Nickname(變更暱稱)")) != "0" else user["name(姓名)"]} 的特工記憶庫</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("抽獎券總額", f"{total_tickets} 張")
            st.write(f"🃏 博弈次數：{safe_int(user.get('gamble_count',0))} 次")
            if st.button("🔄 同步資料"): st.cache_data.clear(); st.rerun()
            if st.button("🚪 登出系統"): st.session_state.login = False; st.rerun()

        tabs = st.tabs(["🎯 任務挑選", "📊 進度追蹤", "🏆 榮譽榜", "🎰 地下博弈", "⚙️ 設定"])

        def mark_tuto_done(col):
            df_users[col] = df_users[col].astype(object)
            df_users.at[u_idx, col] = "1"
            st.session_state.t_done[col] = True
            if len(st.session_state.t_done) == 4 and safe_str(user.get('gift_given')) != "1":
                df_users['gift_given'] = df_users['gift_given'].astype(object)
                df_users['extra_tickets'] = df_users['extra_tickets'].astype(object)
                df_users.at[u_idx, 'gift_given'] = "1"
                df_users.at[u_idx, 'extra_tickets'] = str(safe_int(user.get('extra_tickets')) + 1)
            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
            st.cache_data.clear(); st.rerun()

        # --- Tab 1: 實戰化任務教學 ---
        with tabs[0]:
            is_locked = not st.session_state.t_done.get('tuto_task', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>🚀 實戰教學：首場觀測</h3><p>特工，請拍攝一張「校園角落」或「具有藝術感」的照片並回傳。這將計入 A 級難度完成度。</p><div class="tutorial-footer"><span class="t-badge">訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                up_newbie = st.file_uploader("點擊上傳實戰照片", type=['png','jpg','jpeg'], key="up_newbie")
                if up_newbie:
                    if st.button("✨ 送出首場觀測並了解規則", use_container_width=True):
                        try:
                            res = cloudinary.uploader.upload(up_newbie, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                            df_users['photo_list'] = df_users['photo_list'].astype(object); df_users['task_list'] = df_users['task_list'].astype(object); df_users['done_A'] = df_users['done_A'].astype(object)
                            cur_p = safe_str(user.get("photo_list"))
                            df_users.at[u_idx, "photo_list"] = str(res["secure_url"] if (cur_p == "0" or cur_p == "") else f"{cur_p},{res['secure_url']}")
                            cur_t = safe_str(user.get("task_list"))
                            df_users.at[u_idx, "task_list"] = str("實戰教學：校園之眼" if (cur_t == "0" or cur_t == "") else f"{cur_t},實戰教學：校園之眼")
                            df_users.at[u_idx, "done_A"] = str(safe_int(user.get("done_A")) + 1)
                            mark_tuto_done('tuto_task')
                        except: st.error("上傳失敗")
            else:
                st.write("### 📍 步驟一：選擇難度")
                lvl = st.radio("難度", ["A", "B", "C", "D", "E"], horizontal=True, label_visibility="collapsed")
                filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == lvl]
                for idx, task in filtered.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        if st.button("鎖定任務", key=f"lk_{idx}"): st.toast(f"已鎖定：{task['title']}")

        # --- Tab 2: 進度 ---
        with tabs[1]:
            is_locked = not st.session_state.t_done.get('tuto_prog', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>📊 進度導引</h3><p>達成各階級任務數量即可獲得聚會當天的抽獎券。</p><div class="tutorial-footer"><span class="t-badge">訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解進度規則", key="btn_t2", use_container_width=True): mark_tuto_done('tuto_prog')
            st.subheader("📊 任務完成度")
            for l in ["A", "B", "C", "D", "E"]:
                v = safe_int(user.get(f"done_{l}")); st.write(f"難度 {l}： {v} / 5"); st.progress(min(v/5, 1.0))

        # --- Tab 3: 🏆 榮譽榜 (新功能) ---
        with tabs[2]:
            st.write("### 🏆 特工榮譽殿堂")
            # 篩選條件：有拍照過的人才上榜
            active_agents = df_users[df_users['photo_list'].apply(lambda x: safe_str(x) != "0" and safe_str(x) != "")]
            
            def get_display_name(row):
                nick = safe_str(row.get("Nickname(變更暱稱)", ""))
                return nick if (nick != "0" and nick != "") else f"匿名特工 {str(row['name(姓名)'])[0]}*"

            col_rank1, col_rank2 = st.columns(2)
            
            with col_rank1:
                st.markdown("#### 📸 觀測王 (任務總量)")
                active_agents['total_done'] = active_agents.apply(lambda r: sum(safe_int(r.get(f'done_{l}')) for l in "ABCDE"), axis=1)
                top_missions = active_agents.sort_values(by='total_done', ascending=False).head(8)
                for i, (_, row) in enumerate(top_missions.iterrows()):
                    st.markdown(f'<div class="leaderboard-card"><span class="rank-num">{i+1}</span><span>{get_display_name(row)}</span><span>{int(row["total_done"])} 次</span></div>', unsafe_allow_html=True)

            with col_rank2:
                st.markdown("#### 🎰 賭神榜 (博弈收益)")
                top_gamblers = active_agents.sort_values(by='gamble_profit', ascending=False).head(8)
                for i, (_, row) in enumerate(top_gamblers.iterrows()):
                    st.markdown(f'<div class="leaderboard-card"><span class="rank-num">{i+1}</span><span>{get_display_name(row)}</span><span>{int(row["gamble_profit"])} 張</span></div>', unsafe_allow_html=True)

        # --- Tab 4: 賭場 ---
        with tabs[3]:
            is_locked = not st.session_state.t_done.get('tuto_gamble', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>🎰 博弈導引</h3><p>消耗獎券即可參與博弈，勝率 75%。</p><div class="tutorial-footer"><span class="t-badge">訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解博弈規則", key="btn_t4", use_container_width=True): mark_tuto_done('tuto_gamble')
            else:
                st.markdown('<div class="casino-zone"><h2>🎰 特工地下城</h2><p>這裡是命運的分叉路。勝率 75%</p></div>', unsafe_allow_html=True)
                if total_tickets < 1: st.error("❌ 餘額不足，無法下注。")
                else:
                    if st.button("🧧 消耗 1 張下注！", use_container_width=True):
                        roll = random.random() * 100
                        gain = -1 
                        if roll < 10: gain += 4; r_t, r_m, r_s = "💎 奇蹟！", "你贏得了 4 張獎券！", "win"
                        elif roll < 35: gain += 3; r_t, r_m, r_s = "🔥 大勝！", "你贏得了 3 張獎券！", "win"
                        elif roll < 75: gain += 2; r_t, r_m, r_s = "✨ 小贏！", "你贏得了 2 張獎券！", "win"
                        elif roll < 85: gain += 1; r_t, r_m, r_s = "⚖️ 持平", "本金退回。", "draw"
                        else: gain += 0; r_t, r_m, r_s = "💀 慘賠...", "獎券化為烏有。", "loss"
                        
                        for col in ['gamble_balance', 'loss_count', 'gamble_count', 'gamble_profit']:
                            df_users[col] = df_users[col].astype(object)
                        
                        cur_l = safe_int(user.get('loss_count')); new_l = cur_l + 1 if r_s == "loss" else cur_l
                        bonus = 0; if new_l >= 4: bonus = 2; new_l = 0; st.toast("🛡️ 保底補貼入帳！")
                        
                        df_users.at[u_idx, "gamble_balance"] = str(safe_int(user.get('gamble_balance')) + gain + bonus)
                        df_users.at[u_idx, "loss_count"] = str(new_l)
                        df_users.at[u_idx, "gamble_count"] = str(safe_int(user.get('gamble_count')) + 1)
                        df_users.at[u_idx, "gamble_profit"] = str(safe_int(user.get('gamble_profit')) + gain)
                        
                        conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                        st.session_state.g_res = {"t": r_t, "m": r_m, "s": r_s}
                        st.cache_data.clear(); st.rerun()

            if 'g_res' in st.session_state and st.session_state.g_res:
                res = st.session_state.g_res
                if res['s'] == "win": st.balloons(); st.markdown(f'<div class="win-card"><h2>{res["t"]}</h2><p>{res["m"]}</p></div>', unsafe_allow_html=True)
                elif res['s'] == "draw": st.info(res['m'])
                else: st.error(res['m'])
                if st.button("關閉"): st.session_state.g_res = None; st.rerun()

        # --- Tab 5: 設定 ---
        with tabs[4]:
            is_locked = not st.session_state.t_done.get('tuto_set', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>⚙️ 設定導引</h3><p>在此修改代號以匿蹤，或自訂登入密碼。</p><div class="tutorial-footer"><span class="t-badge">訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解設定功能", key="btn_t3", use_container_width=True): mark_tuto_done('tuto_set')
            
            st.subheader("⚙️ 帳號身份設定")
            new_nick = st.text_input("修改特工代號 (匿蹤用)", value=safe_str(user.get("Nickname(變更暱稱)", "")))
            new_pwd = st.text_input("自訂登入密碼", type="password", placeholder="留空則不修改")
            if st.button("💾 更新設定"):
                if is_locked: st.warning("⚠️ 請先點擊上方確認按鈕")
                else:
                    df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object)
                    df_users['password(自訂密碼)'] = df_users['password(自訂密碼)'].astype(object)
                    df_users.at[u_idx, "Nickname(變開暱稱)"] = str(new_nick); 
                    if new_pwd.strip() != "": df_users.at[u_idx, "password(自訂密碼)"] = str(new_pwd)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                    st.success("✅ 更新成功！")

        # --- 結業看板 ---
        if done_count == 4 and safe_str(user.get('gift_given')) == "1":
            if not st.session_state.p_shown:
                st.balloons()
                st.markdown("""<div style="background-color:#FFF9E6; padding:35px; border-radius:20px; text-align:center; border:4px solid #FFC107; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                    <h1 style="color:#FFC107; margin:0;">🎊 培訓合格 🎊</h1><p style="font-size:1.2rem; margin-top:10px;">你已完成實戰教學並集齊說明，正式晉升！</p>
                    <h2 style="background:#FFC107; color:white; display:inline-block; padding:5px 20px; border-radius:10px;">🎁 獎勵：+1 張抽獎券</h2></div>""", unsafe_allow_html=True)
                if st.button("立即出動！", use_container_width=True): st.session_state.p_shown = True; st.rerun()
else: st.error("❌ 連線失敗")
