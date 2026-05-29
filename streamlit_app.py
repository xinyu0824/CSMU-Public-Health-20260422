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

        # 🟢 [整數防禦版絕對指令] 全面相容 1, 1.0, "1"
        show_tuto_task = False if (safe_int(user.get('tuto_task')) == 1 or st.session_state.t_done.get('tuto_task', False)) else True
        st.session_state.t_done['tuto_task'] = not show_tuto_task

        show_tuto_prog = False if (safe_int(user.get('tuto_prog')) == 1 or st.session_state.t_done.get('tuto_prog', False)) else True
        st.session_state.t_done['tuto_prog'] = not show_tuto_prog

        show_tuto_gamble = False if (safe_int(user.get('tuto_gamble')) == 1 or st.session_state.t_done.get('tuto_gamble', False)) else True
        st.session_state.t_done['tuto_gamble'] = not show_tuto_gamble

        show_tuto_set = False if (safe_int(user.get('tuto_set')) == 1 or st.session_state.t_done.get('tuto_set', False)) else True
        st.session_state.t_done['tuto_set'] = not show_tuto_set

        # 🟢 [核心新增：被動補發捕獲防線] 如果四個指引在雲端都是 1，但 gift_given 還不是 1，立刻在後台直接發券更新！
        if safe_int(user.get('tuto_task')) == 1 and safe_int(user.get('tuto_prog')) == 1 and \
           safe_int(user.get('tuto_gamble')) == 1 and safe_int(user.get('tuto_set')) == 1:
            if safe_int(user.get('gift_given')) != 1:
                df_users['gift_given'] = df_users['gift_given'].astype(str)
                df_users['extra_tickets'] = df_users['extra_tickets'].astype(str)
                df_users.at[u_idx, 'gift_given'] = "1"
                df_users.at[u_idx, 'extra_tickets'] = str(safe_int(user.get('extra_tickets')) + 1)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.cache_data.clear()
                st.rerun()

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
            
            # 🟢 使用 safe_int 同步判定按鈕按下去的瞬間是否集滿 4 個
            db_task = 1 if col == 'tuto_task' else safe_int(df_users.at[u_idx, 'tuto_task'])
            db_prog = 1 if col == 'tuto_prog' else safe_int(df_users.at[u_idx, 'tuto_prog'])
            db_gamble = 1 if col == 'tuto_gamble' else safe_int(df_users.at[u_idx, 'tuto_gamble'])
            db_set = 1 if col == 'tuto_set' else safe_int(df_users.at[u_idx, 'tuto_set'])
            
            if db_task == 1 and db_prog == 1 and db_gamble == 1 and db_set == 1:
                if safe_int(df_users.at[u_idx, 'gift_given']) != 1:
                    df_users['gift_given'] = df_users['gift_given'].astype(str)
                    df_users['extra_tickets'] = df_users['extra_tickets'].astype(str)
                    df_users.at[u_idx, 'gift_given'] = "1"
                    df_users.at[u_idx, 'extra_tickets'] = str(safe_int(df_users.at[u_idx, 'extra_tickets']) + 1)
                
            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
            st.cache_data.clear()
            st.rerun()

        # 🟢 [核心修復：結業大型攔截小視窗] 徹底轉換成 safe_int 驗證，防止 1.0 導致彈窗失效
        if safe_int(user.get('tuto_task')) == 1 and safe_int(user.get('tuto_prog')) == 1 and \
           safe_int(user.get('tuto_gamble')) == 1 and safe_int(user.get('tuto_set')) == 1 and \
           safe_int(user.get('gift_given')) == 1 and not st.session_state.p_shown:
            st.balloons()
            st.markdown("""
                <div style="background-color:#FFF9E6; padding:35px; border-radius:20px; text-align:center; border:4px solid #FFC107; box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 25px;">
                    <h1 style="color:#FFC107; margin:0; font-size: 2.2rem;">🎊 新手特訓合格 🎊</h1>
                    <p style="font-size:1.2rem; margin-top:12px; color: #5F5F5F; font-weight: bold;">你已完全瀏覽 4 個新手任務，特發放一張抽獎券！</p>
                    <div style="background:#FFC107; color:white; display:inline-block; padding:8px 25px; border-radius:10px; font-size: 1.4rem; font-weight: bold; margin: 15px 0;">
                        🎁 獎勵已入庫：抽獎券 +1 張
                    </div>
                    <p style="color:#8C8C8C; font-size: 0.95rem; margin-top: 5px;">本金已自動存入你的特工終端。點擊下方按鈕正式解除鎖定！</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("進入（點擊解鎖全部功能）", use_container_width=True):
                st.session_state.p_shown = True; st.rerun()
            st.stop()

        # --- Tab 1: 任務挑選 ---
        with tabs[0]:
            if show_tuto_task: 
                st.markdown(f'<div class="tutorial-box"><h3>🚀新手指引：操作教學</h3><p>請上傳任意一張圖片測試功能。完成後將解鎖四種難度等級任務，此任務將計入「初階」進度 +1。</p><div class="tutorial-footer"><span class="t-badge">教學進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                up_n = st.file_uploader("上傳
