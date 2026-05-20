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
    .t-badge { background-color: #28a745; color: white !important; padding: 4px 14px; border-radius: 12px; font-size: 0.9rem; font-weight: bold; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); }
    .tutorial-box { background-color: #FFFFFF; padding: 22px; border-radius: 15px; border-left: 6px solid #FFC107; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px; }
    .tutorial-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    .leaderboard-card { background-color: #FFFFFF; padding: 15px; border-radius: 12px; border: 1px solid #E6E6E1; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
    .rank-num { font-weight: bold; font-size: 1.2rem; color: #FFC107; width: 35px; }
    .casino-zone { background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%); color: #FFC107 !important; padding: 30px; border-radius: 20px; border: 3px solid #FFC107; text-align: center; margin-bottom: 25px; }
    .win-card { background: linear-gradient(135deg, #FFD700 0%, #FFC107 100%); color: white !important; padding: 30px; border-radius: 20px; text-align: center; box-shadow: 0 10px 25px rgba(255,193,7,0.4); margin: 20px 0; }
    div[role="radiogroup"] { display: flex !important; justify-content: center !important; gap: 12px !important; }
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
    req_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set', 'gift_given', 'extra_tickets', 'gamble_balance', 'done_初階', 'done_中階', 'done_高階', 'done_傳奇', 'gamble_profit', 'photo_list', 'task_list', 'task_cooldowns', 'Nickname(變更暱稱)', 'password(自訂密碼)', 'gamble_count', 'loss_count']
    for c in req_cols:
        if c not in df_users.columns: df_users[c] = ""

    if not st.session_state.login:
        st.title("🍂 公衛二甲：導生聚活動")
        
        def get_clean_login_label(row):
            nick = safe_str(row.get("Nickname(變更暱稱)", ""))
            return nick if nick != "" else str(row['name(姓名)'])
            
        login_labels = df_users.apply(get_clean_login_label, axis=1).dropna().tolist()
        sel = st.selectbox("帳號選擇（若已變更暱稱，請尋找你的暱稱代號）", ["請選擇身份..."] + login_labels)
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
                    st.rerun()
                else: st.error("密碼錯誤")
    else:
        # 已登入
        u_match = df_users[df_users["Student ID(預設密碼)"].astype(str).str.contains(st.session_state.student_id)]
        user = u_match.iloc[0]; u_idx = u_match.index[0]

        # 獨立記憶讀取
        for col in ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set']:
            if safe_str(user.get(col)) == "1":
                st.session_state.t_done[col] = True
            else:
                st.session_state.t_done[col] = False

        # 🟢 [強效盲讀重算機制] 登入瞬間直接重新抓取最新狀態，防範後台刪數據沒刪乾淨的殘留狀況
        m_base = (safe_int(user.get('done_初階')) // 4) + \
                 (safe_int(user.get('done_中階')) // 3) + \
                 (safe_int(user.get('done_高階')) // 2) + \
                 (safe_int(user.get('done_傳奇')) * 1)
                 
        # 即使後台欄位被清空成 NaN，safe_int 也能強制抓回 0 進行加總，不對稱的數據不會造成計算錯誤
        total_tickets = max(0, m_base + safe_int(user.get('gamble_balance')) + safe_int(user.get('extra_tickets')))
        p_str = safe_str(user.get("photo_list"))
        p_list = [u for u in p_str.split(",") if u.strip() != ""]
        done_count = sum(1 for v in st.session_state.t_done.values() if v)

        display_title_name = safe_str(user.get("Nickname(變更暱稱)")) if safe_str(user.get("Nickname(變更暱稱)")) != "" else user["name(姓名)"]
        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{get_agent_rank(total_tickets, len(p_list))}</span><span class="main-title">{display_title_name} 的觀測終端</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("抽獎券總額", f"{total_tickets} 張")
            if st.button("🚪 帳號登出"): st.session_state.login = False; st.rerun()

        tabs = st.tabs(
