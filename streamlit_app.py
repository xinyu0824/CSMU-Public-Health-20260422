import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import json
import random
from datetime import datetime, date

# --- 1. 配置與強效初始化 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

st.set_page_config(page_title="📸 導生聚：拍拍挑戰", layout="centered")

if 'init_done' not in st.session_state:
    st.session_state.update({
        'login': False, 'student_id': None, 'selected_lvl': "初階", 
        't_done': {}, 'g_res': None, 'p_shown': False, 'init_done': True,
        'daily_seed': None, 'daily_date': ""
    })

# --- 數據安全工具 ---
def safe_str(val):
    if pd.isna(val) or str(val).strip().lower() == "nan" or str(val).strip() == "0": return ""
    return str(val).strip()

def safe_int(val):
    try: 
        s = safe_str(val)
        return int(float(s)) if s != "" else 0
    except: return 0

def get_agent_rank(tickets, photo_count):
    if photo_count == 0: return "🆕尚未獲得稱號"
    if tickets >= 11: return "🌌 傳奇拍拍"
    elif tickets >= 7: return "🎖️ 大師拍拍"
    elif tickets >= 4: return "🛡️ 菁英拍拍"
    else: return "🌱 實習拍拍"

st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .agent-badge { display: inline-block; padding: 4px 14px; background-color: #5F5F5F; color: #FFFFFF !important; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 12px; }
    .t-badge { background-color: #28a745; color: white !important; padding: 4px 14px; border-radius: 12px; font-size: 0.9rem; font-weight: bold; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); }
    .tutorial-box { background-color: #FFFFFF; padding: 22px; border-radius: 15px; border-left: 6px solid #FFC107; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px; }
    .tutorial-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 5px; border-left: 6px solid #FFC107; }
    .leaderboard-card { background-color: #FFFFFF; padding: 15px; border-radius: 12px; border: 1px solid #E6E6E1; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
    .rank-num { font-weight: bold; font-size: 1.2rem; color: #FFC107; width: 35px; }
    .casino-zone { background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%); color: #FFC107 !important; padding: 30px; border-radius: 20px; border: 3px solid #FFC107; text-align: center; margin-bottom: 25px; }
    .win-card { background: linear-gradient(135deg, #FFD700 0%, #FFC107 100%); color: white !important; padding: 30px; border-radius: 20px; text-align: center; box-shadow: 0 10px 25px rgba(255,193,7,0.4); margin: 20px 0; }
    div[role="radiogroup"] { display: flex !important; justify-content: center !important; gap: 12px !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 65px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px; padding: 15px 0 !important; cursor: pointer; display: flex !important; justify-content: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    /* 微調 Expander 樣式使其貼合卡片 */
    [data-testid="stExpander"] { border: 1px solid #E6E6E1; border-top: none; border-radius: 0 0 6px 6px; margin-bottom: 15px; }
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
    req_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set', 'gift_given', 'extra_tickets', 'gamble_balance', 'done_初階', 'done_中階', 'done_高階', 'done_傳奇', 'gamble_profit', 'photo_list', 'task_list', 'task_cooldowns', 'Nickname(變更暱稱)', 'password(自訂密碼)', 'gamble_count', 'loss_count']
    for c in req_cols:
        if c not in df_users.columns: df_users[c] = ""

    if not st.session_state.login:
        st.title("公衛二甲：導生聚活動")
        
        def get_clean_login_label(row):
            nick = safe_str(row.get("Nickname(變更暱稱)", ""))
            return nick if nick != "" else str(row['name(姓名)'])
            
        login_labels = df_users.apply(get_clean_login_label, axis=1).dropna().tolist()
        sel = st.selectbox("帳號選擇（預設為姓名，可於登入後變更暱稱）", ["你是誰..."] + login_labels)
        pwd = st.text_input("密碼（預設為學號）", type="password")
        
        if st.button("登入"):
            match = df_users[(df_users['name(姓名)'] == sel) | (df_users['Nickname(變更暱稱)'] == sel)]
            if not match.empty:
                u_row = match.iloc[0]
                db_id = str(u_row["Student ID(預設密碼)"]).strip().split('.')[0]
                db_pwd = safe_str(u_row.get("password(自訂密碼)", ""))
                correct = db_pwd if db_pwd != "" else db_id
                if pwd.strip() == correct:
                    st.session_state.login, st.session_state.student_id = True, db_id
                    st.session_state.t_done = {} # 登入清除舊記憶
                    st.rerun()
                else: st.error("密碼錯誤")
    else:
        # 已登入
        u_match = df_users[df_users["Student ID(預設密碼)"].astype(str).str.contains(st.session_state.student_id)]
        user = u_match.iloc[0]; u_idx = u_match.index[0]

        # 🟢 [最高防禦] 4 條絕對指令：精準判讀雲端與本地數值，0 (或空值) 顯示，1 隱藏
        # 1. 任務挑選指引
        show_tuto_task = False if (safe_str(user.get('tuto_task')) == "1" or st.session_state.t_done.get('tuto_task', False)) else True
        st.session_state.t_done['tuto_task'] = not show_tuto_task

        # 2. 進度追蹤指引
        show_tuto_prog = False if (safe_str(user.get('tuto_prog')) == "1" or st.session_state.t_done.get('tuto_prog', False)) else True
        st.session_state.t_done['tuto_prog'] = not show_tuto_prog

        # 3. 地下博弈指引
        show_tuto_gamble = False if (safe_str(user.get('tuto_gamble')) == "1" or st.session_state.t_done.get('tuto_gamble', False)) else True
        st.session_state.t_done['tuto_gamble'] = not show_tuto_gamble

        # 4. 帳號設定指引
        show_tuto_set = False if (safe_str(user.get('tuto_set')) == "1" or st.session_state.t_done.get('tuto_set', False)) else True
        st.session_state.t_done['tuto_set'] = not show_tuto_set

        # 強效盲讀重算機制
        m_base = (safe_int(user.get('done_初階')) // 4) + \
                 (safe_int(user.get('done_中階')) // 3) + \
                 (safe_int(user.get('done_高階')) // 2) + \
                 (safe_int(user.get('done_傳奇')) * 1)
                 
        total_tickets = max(0, m_base + safe_int(user.get('gamble_balance')) + safe_int(user.get('extra_tickets')))
        p_str = safe_str(user.get("photo_list"))
        p_list = [u for u in p_str.split(",") if u.strip() != ""]
        done_count = sum(1 for v in st.session_state.t_done.values() if v)

        display_title_name = safe_str(user.get("Nickname(變更暱稱)")) if safe_str(user.get("Nickname(變更暱稱)")) != "" else user["name(姓名)"]
        
        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{get_agent_rank(total_tickets, len(p_list))}</span><span class="main-title">{display_title_name} 的觀測終端</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("抽獎券總額", f"{total_tickets} 張")
            if st.button("🚪 帳號登出"): 
                st.session_state.login = False
                st.session_state.t_done = {}
                st.rerun()

        tabs = st.tabs(["🎯 任務挑選", "📊 進度追蹤", "🏆 排行榜", "🎰 地下博弈", "⚙️ 帳號設定"])

        def mark_tuto_step(col):
            st.session_state.t_done[col] = True
            df_users[col] = df_users[col].astype(str)
            df_users.at[u_idx, col] = "1"
            
            current_total_done = sum(1 for c in ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set'] if safe_str(df_users.at[u_idx, c]) == "1" or c == col)
            if current_total_done == 4 and safe_str(user.get('gift_given')) != "1":
                df_users['gift_given'] = df_users['gift_given'].astype(str)
                df_users['extra_tickets'] = df_users['extra_tickets'].astype(str)
                df_users.at[u_idx, 'gift_given'] = "1"
                df_users.at[u_idx, 'extra_tickets'] = str(safe_int(user.get('extra_tickets')) + 1)
                
            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
            st.cache_data.clear()
            st.rerun()

        if done_count == 4 and safe_str(user.get('gift_given')) == "1" and not st.session_state.p_shown:
            st.balloons()
            st.markdown("""
                <div style="background-color:#FFF9E6; padding:35px; border-radius:20px; text-align:center; border:4px solid #FFC107; box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 25px;">
                    <h1 style="color:#FFC107; margin:0; font-size: 2.2rem;">🎊 新手特訓合格 🎊</h1>
                    <p style="font-size:1.2rem; margin-top:12px; color: #5F5F5F;">你已完成 4 項功能指引，已發放一張抽獎券！</p>
                    <div style="background:#FFC107; color:white; display:inline-block; padding:8px 25px; border-radius:10px; font-size: 1.4rem; font-weight: bold; margin: 15px 0;">
                        🎁 完成新手指引：抽獎券 +1 張
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("進入（點擊解鎖全部功能）", use_container_width=True):
                st.session_state.p_shown = True; st.rerun()
            st.stop()

        # --- Tab 1: 任務挑選 ---
        with tabs[0]:
            if show_tuto_task:  # 🟢 絕對指令判定
                st.markdown(f'<div class="tutorial-box"><h3>🚀新手指引：操作教學</h3><p>請上傳任意一張圖片測試功能。完成後將解鎖四種難度等級任務，此任務將計入「初階」進度 +1。</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                up_n = st.file_uploader("上傳任務照片", type=['png','jpg','jpeg'], key="up_newbie")
                if up_n and st.button("確認送出，解鎖四種難度等級", use_container_width=True):
                    is_success = False 
                    try:
                        res = cloudinary.uploader.upload(up_n, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                        df_users['photo_list'] = df_users['photo_list'].astype(str)
                        df_users['task_list'] = df_users['task_list'].astype(str)
                        df_users['done_初階'] = df_users['done_初階'].astype(str)
                        cp = safe_str(user.get("photo_list")); ct = safe_str(user.get("task_list"))
                        df_users.at[u_idx, "photo_list"] = str(res["secure_url"] if cp == "" else f"{cp},{res['secure_url']}")
                        df_users.at[u_idx, "task_list"] = str("新手指引：操作教學" if safe_str(user.get("task_list")) == "" else f"{safe_str(user.get('task_list'))},新手指引：操作教學")
                        df_users.at[u_idx, "done_初階"] = str(safe_int(user.get("done_初階")) + 1)
                        
                        st.session_state.t_done['tuto_task'] = True
                        df_users['tuto_task'] = df_users['tuto_task'].astype(str)
                        df_users.at[u_idx, 'tuto_task'] = "1"
                        
                        conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                        st.cache_data.clear()
                        is_success = True 
                    except Exception as e:
                        st.error(f"上傳失敗，錯誤原因：{e}") 
                    
                    if is_success:
                        st.rerun() 
            else:
                st.write("### 📍選擇任務難度")
                lvl = st.radio("難度分級", ["初階", "中階", "高階", "傳奇"], horizontal=True, label_visibility="collapsed")
                
                lvl_map = {"初階": "A", "中階": "B", "高階": "C", "傳奇": "D"}
                target_letter = lvl_map.get(lvl, "A")
                
                filtered = df_tasks[
                    (df_tasks['difficulty'].astype(str).str.strip().str.upper() == target_letter) |
                    (df_tasks['difficulty'].astype(str).str.strip() == lvl)
                ].copy()
                
                filtered = filtered[~filtered['title'].astype(str).str.contains("新手|操作教學", na=False, regex=True)]
                if filtered.empty: 
                    filtered = df_tasks.copy()
                    filtered = filtered[~filtered['title'].astype(str).str.contains("新手|操作教學", na=False, regex=True)]
                
                current_today_str = str(date.today())
                if st.session_state.daily_date != current_today_str or st.session_state.daily_seed is None:
                    st.session_state.daily_date = current_today_str
                    st.session_state.daily_seed = int(datetime.now().strftime("%Y%m%d"))
                
                if len(filtered) > 4:
                    rng = random.Random(st.session_state.daily_seed + ord(lvl[0]))
                    display_tasks = filtered.sample(n=4, random_state=rng.randint(0, 10000))
                else:
                    display_tasks = filtered
                
                st.caption(f"📅 今日「{lvl}」任務清單已刷新，限額展示 {len(display_tasks)} 題")
                
                for idx, task in display_tasks.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        with st.expander("📸 執行此任務 (上傳情報)"):
                            up_task = st.file_uploader("選擇照片", type=['png','jpg','jpeg'], key=f"up_task_{idx}")
                            if up_task and st.button("確認達成任務", key=f"btn_task_{idx}", use_container_width=True):
                                is_success = False 
                                try:
                                    res = cloudinary.uploader.upload(up_task, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                                    
                                    df_users['photo_list'] = df_users['photo_list'].astype(str)
                                    df_users['task_list'] = df_users['task_list'].astype(str)
                                    target_done_col = f"done_{lvl}"
                                    df_users[target_done_col] = df_users[target_done_col].astype(str)
                                    
                                    cp = safe_str(user.get("photo_list"))
                                    ct = safe_str(user.get("task_list"))
                                    
                                    df_users.at[u_idx, "photo_list"] = str(res["secure_url"] if cp == "" else f"{cp},{res['secure_url']}")
                                    df_users.at[u_idx, "task_list"] = str(task["title"] if ct == "" else f"{ct},{task['title']}")
                                    df_users.at[u_idx, target_done_col] = str(safe_int(user.get(target_done_col)) + 1)
                                    
                                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                    st.cache_data.clear()
                                    is_success = True 
                                except Exception as e: 
                                    st.error(f"上傳失敗，錯誤原因：{e}") 
                                
                                if is_success:
                                    st.toast(f"✅ 【{task['title']}】情報已成功回傳總部！進度 +1")
                                    st.rerun() 

        # --- Tab 2: 進度 ---
        with tabs[1]:
            if show_tuto_prog:  # 🟢 絕對指令判定
                st.markdown(f'<div class="tutorial-box"><h3>📊 新手指引：操作教學</h3><p>任務數量依照難度而有不同，完成對應數量可獲得抽獎券一張，不限完成次數，可無限次累積完成任務！。</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已閱讀完畢", key="btn_t2", use_container_width=True): mark_tuto_step('tuto_prog')
            st.subheader("📊 任務進度")
            bars = [("初階", 4), ("中階", 3), ("高階", 2), ("傳奇", 1)]
            for title, limit in bars:
                v = safe_int(user.get(f"done_{title}"))
                st.write(f"**{title}任務** 進度： {v} / {limit} （每滿 {limit} 個可換 1 張券）")
                st.progress(min(v / limit, 1.0))

        # --- Tab 3: 🏆 排行榜 ---
        with tabs[2]:
            st.write("### 🏆 排行榜")
            active_u = df_users[df_users['photo_list'].apply(lambda x: safe_str(x) != "")]
            def get_nick(row):
                n = safe_str(row.get("Nickname(變更暱稱)", ""))
                return n if n != "" else f"{str(row['name(姓名)'])[0]}* 同學"

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 📸任勞任怨 (完成任務數量)")
                active_u['total'] = active_u.apply(lambda r: sum(safe_int(r.get(f'done_{l}')) for l in ["初階", "中階", "高階", "傳奇"]), axis=1)
                for i, (_, r) in enumerate(active_u.sort_values(by='total', ascending=False).head(8).iterrows()):
                    st.markdown(f'<div class="leaderboard-card"><span class="rank-num">{i+1}</span><span>{get_nick(r)}</span><span>{int(r["total"])} 次</span></div>', unsafe_allow_html=True)
            with c2:
                st.markdown("#### 🎰 Let me 賭 it for you (博弈獲得數量)")
                for i, (_, r) in enumerate(active_u.sort_values(by='gamble_profit', ascending=False).head(8).iterrows()):
                    st.markdown(f'<div class="leaderboard-card"><span class="rank-num">{i+1}</span><span>{get_nick(r)}</span><span>{int(r["gamble_profit"])} 張</span></div>', unsafe_allow_html=True)

        # --- Tab 4: 地下城 ---
        with tabs[3]:
            if show_tuto_gamble:  # 🟢 絕對指令判定
                st.markdown(f'<div class="tutorial-box"><h3>🎰 新手指引：操作教學</h3><p>每次博弈消耗一張，最高可獲得4張，最低則一無所獲。累積 4 次失敗有保底！</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已閱讀完畢", key="btn_t4", use_container_width=True): mark_tuto_step('tuto_gamble')
            st.markdown('<div class="casino-zone"><h2>🎰 賭賭賭</h2><p>命運的分叉路，翻倍或一無所有。</p></div>', unsafe_allow_html=True)
            
            if total_tickets < 1: 
                st.error("❌ 目前你手上沒有多餘的抽獎券可以下注。快去解任務賺籌碼！")
            else:
                if st.button("🧧 消耗 1 張抽獎券下注！", use_container_width=True):
                    roll = random.random() * 100
                    gain = -1
                    if roll < 10: gain += 4; r_t, r_m, r_s = "💎 奇蹟！", "獲得 4 張！", "win"
                    elif roll < 35: gain += 3; r_t, r_m, r_s = "🔥 大勝！", "獲得 3 張！", "win"
                    elif roll < 75: gain += 2; r_t, r_m, r_s = "✨ 小贏！", "獲得 2 張！", "win"
                    elif roll < 85: gain += 1; r_t, r_m, r_s = "⚖️ 不賺不賠", "獲得 1 張。", "draw"
                    else: gain += 0; r_t, r_m, r_s = "💀 慘賠...", "獎券化為烏有。", "loss"
                    
                    df_users['gamble_balance'] = df_users['gamble_balance'].astype(str)
                    df_users['loss_count'] = df_users['loss_count'].astype(str)
                    df_users['gamble_count'] = df_users['gamble_count'].astype(str)
                    df_users['gamble_profit'] = df_users['gamble_profit'].astype(str)
                    
                    cl = safe_int(user.get('loss_count'))
                    nl = cl + 1 if r_s == "loss" else cl
                    bonus = 0; 
                    if nl >= 4: bonus = 2; nl = 0; st.toast("🛡️ 運氣差不要緊，給你額外兩張抽獎券！")
                    
                    df_users.at[u_idx, "gamble_balance"] = str(safe_int(user.get('gamble_balance')) + gain + bonus)
                    df_users.at[u_idx, "loss_count"] = str(nl)
                    df_users.at[u_idx, "gamble_count"] = str(safe_int(user.get('gamble_count')) + 1)
                    df_users.at[u_idx, "gamble_profit"] = str(safe_int(user.get('gamble_profit')) + gain)
                    
                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                    st.session_state.g_res = {"t": r_t, "m": r_m, "s": r_s}
                    st.cache_data.clear(); st.rerun()

            if st.session_state.g_res:
                res = st.session_state.g_res
                if res['s'] == "win": st.balloons(); st.markdown(f'<div class="win-card"><h2>{res["t"]}</h2><p>{res["m"]}</p></div>', unsafe_allow_html=True)
                elif res['s'] == "draw": st.info(res['m'])
                else: st.error(res['m'])
                if st.button("關閉"): st.session_state.g_res = None; st.rerun()

        # --- Tab 5: 設定 ---
        with tabs[4]:
            if show_tuto_set:  # 🟢 絕對指令判定
                st.markdown(f'<div class="tutorial-box"><h3>⚙️ 新手指引：操作教學</h3><p>可在此修改帳號名稱，後續他人僅可見你的暱稱。</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解設定功能", key="btn_t3", use_container_width=True): mark_tuto_step('tuto_set')
            st.subheader("⚙️ 帳號設定")
            nn = st.text_input("變更暱稱", value=safe_str(user.get("Nickname(變更暱稱)")))
            np = st.text_input("自訂密碼", type="password", placeholder="留空不修改")
            if st.button("💾 更新資料"):
                df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(str)
                df_users['password(自訂密碼)'] = df_users['password(自訂密碼)'].astype(str)
                df_users.at[u_idx, "Nickname(變更暱稱)"] = str(nn)
                if np.strip() != "": df_users.at[u_idx, "password(自訂密碼)"] = str(np)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users); st.success("修改成功")

else: st.error("❌ 連線失敗")
