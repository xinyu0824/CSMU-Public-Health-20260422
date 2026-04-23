import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import random
import json
from datetime import datetime, timedelta

# --- 1. 配置與強效修復工具 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
COOLDOWN_HOURS = 12

st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")

# [安全數據轉換工具] 徹底解決 int(float(c)) 報錯
def safe_int(val, default=0):
    try:
        if pd.isna(val) or str(val).strip().lower() == "nan" or str(val).strip() == "":
            return default
        return int(float(val))
    except:
        return default

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
    .agent-badge { display: inline-block; padding: 4px 14px; background-color: #5F5F5F; color: #FFFFFF !important; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 12px; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); }
    .tutorial-box { background-color: #FFFFFF; padding: 22px; border-radius: 15px; border-left: 6px solid #FFC107; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 10px !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 50px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px; padding: 10px 0 !important; cursor: pointer; display: flex !important; justify-content: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 服務連線 ---
cloudinary.config(cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"], api_key=st.secrets["CLOUDINARY_API_KEY"], api_secret=st.secrets["CLOUDINARY_API_SECRET"], secure=True)
conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_logic_tickets(user_row):
    # 使用 safe_int 確保不崩潰
    m_base = (safe_int(user_row.get('done_A')) // 5) + (safe_int(user_row.get('done_B')) // 3) + \
             (safe_int(user_row.get('done_C')) // 2) + safe_int(user_row.get('done_D')) + (safe_int(user_row.get('done_E')) * 2)
    g_net = safe_int(user_row.get('gamble_balance'))
    g_gift = safe_int(user_row.get('extra_tickets'))
    return m_base, g_net, g_gift, max(0, m_base + g_net + g_gift)

@st.cache_data(ttl=1) # 強制極短快取，解決同步延遲
def load_data():
    try:
        # 強制重新讀取工作表
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except: return None, None

if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'locked_task': None, 'selected_lvl': "A"})

df_users, df_tasks = load_data()

# --- 3. 登入流程 ---
if df_users is not None:
    # 確保關鍵欄位存在，若不存在則補空欄位避免當機
    required_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set', 'gift_given', 'extra_tickets', 'gamble_balance', 'loss_count', 'task_cooldowns', 'Nickname(變更暱稱)']
    for col in required_cols:
        if col not in df_users.columns:
            df_users[col] = "0"

    def get_anon_label(row):
        nick = str(row.get("Nickname(變更暱稱)", "")).strip()
        return nick if (nick != "" and nick.lower() != "nan") else str(row["name(姓名)"])
    df_users["login_label"] = df_users.apply(get_anon_label, axis=1)

    if not st.session_state.login:
        st.title("🍂 公衛一甲：特工登入")
        login_list = df_users["login_label"].dropna().tolist()
        selected_label = st.selectbox("請選擇特工身份", ["搜尋代號/姓名"] + login_list)
        input_pwd = st.text_input("密碼 (預設學號)", type="password")
        if st.button("進入觀測站"):
            match = df_users[df_users["login_label"] == selected_label]
            if not match.empty:
                user_row = match.iloc[0]
                db_id = str(user_row["Student ID(預設密碼)"]).strip().split('.')[0]
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
        
        # 數據計算
        m_base, g_net, g_gift, total_tickets = calculate_logic_tickets(user)
        t_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set']
        done_count = sum([1 for c in t_cols if str(user.get(c, '0')) == '1'])
        
        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{get_agent_rank(total_tickets, 0)}</span><span class="main-title">{user["login_label"]} 的特工記憶庫</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("獎券總額", f"{total_tickets} 張")
            if st.button("🔄 強制重新整理資料"): # 手動同步按鈕
                st.cache_data.clear(); st.rerun()
            if st.button("🚪 登出系統"): st.session_state.login = False; st.rerun()

        tab1, tab2, tab4, tab3 = st.tabs(["🎯 任務挑選", "📊 進度追蹤", "🎰 地下博弈", "⚙️ 設定"])

        def mark_done(col):
            df_users[col] = df_users[col].astype(object)
            df_users.at[user_idx, col] = "1"
            # 領獎邏輯
            new_done = sum([1 for c in t_cols if str(df_users.at[user_idx, c]) == '1'])
            if new_done == 4 and str(user.get('gift_given', '0')) != '1':
                df_users['gift_given'] = df_users['gift_given'].astype(object)
                df_users['extra_tickets'] = df_users['extra_tickets'].astype(object)
                df_users.at[user_idx, 'gift_given'] = "1"
                df_users.at[user_idx, 'extra_tickets'] = str(safe_int(user.get('extra_tickets')) + 1)
                st.toast("🎁 新手獎勵已發放！")
            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
            st.cache_data.clear(); st.rerun()

        with tab1:
            if str(user.get('tuto_task', '0')) != '1':
                st.markdown(f'<div class="tutorial-box"><h3>🚩 任務導引</h3><p>鎖定任務並上傳照片即可獲得獎券。完成後有 12 小時冷卻期。</p><small>訓練進度 {done_count}/4</small></div>', unsafe_allow_html=True)
                if st.button("了解任務規則", use_container_width=True): mark_done('tuto_task')
            
            st.write("### 📍 選擇難度")
            lvl = st.radio("難度", ["A", "B", "C", "D", "E"], horizontal=True, label_visibility="collapsed")
            st.markdown(f"#### {lvl} 級任務")
            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == lvl]
            for idx, task in filtered.iterrows():
                with st.container():
                    st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if st.button("鎖定任務", key=f"lk_{idx}"): st.toast("已鎖定")

        with tab2:
            if str(user.get('tuto_prog', '0')) != '1':
                st.markdown(f'<div class="tutorial-box"><h3>📊 進度導引</h3><p>累積不同難度的任務可兌換抽獎券。</p><small>訓練進度 {done_count}/4</small></div>', unsafe_allow_html=True)
                if st.button("了解進度規則", use_container_width=True): mark_done('tuto_prog')
            
            st.subheader("📊 完成進度")
            for l in ["A", "B", "C", "D", "E"]:
                c_val = safe_int(user.get(f"done_{l}"))
                st.write(f"難度 {l}： {c_val} / 5")
                st.progress(min(c_val/5, 1.0))

        with tab4:
            if str(user.get('tuto_gamble', '0')) != '1':
                st.markdown(f'<div class="tutorial-box"><h3>🎰 博弈導引</h3><p>勝率 75% 的地下城，大獲全勝或一無所有。</p><small>訓練進度 {done_count}/4</small></div>', unsafe_allow_html=True)
                if st.button("了解博弈規則", use_container_width=True): mark_done('tuto_gamble')
            else:
                st.markdown('<div class="casino-zone"><h2>🎰 特工地下城</h2></div>', unsafe_allow_html=True)
                st.info("尚未開放博弈...")

        with tab3:
            if str(user.get('tuto_set', '0')) != '1':
                st.markdown(f'<div class="tutorial-box"><h3>⚙️ 設定導引</h3><p>修改暱稱隱藏本名，或自訂登入密碼。</p><small>訓練進度 {done_count}/4</small></div>', unsafe_allow_html=True)
                if st.button("了解設定規則", use_container_width=True): mark_done('tuto_set')
            
            st.subheader("⚙️ 帳號設定")
            new_nick = st.text_input("修改代號", value=user.get("Nickname(變更暱稱)", ""))
            if st.button("💾 更新"):
                df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object)
                df_users.at[user_idx, "Nickname(變更暱稱)"] = str(new_nick)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.success("同步成功")

        if done_count == 4 and str(user.get('gift_given', '0')) == '1':
            if 'shown_prize' not in st.session_state:
                st.balloons()
                st.markdown('<div style="text-align:center; padding:20px; background:#FFF9E6; border:2px solid #FFC107; border-radius:15px;"><h2>🎉 培訓完成！</h2><p>獲得 1 張獎券，快去小試身手吧！</p></div>', unsafe_allow_html=True)
                if st.button("立刻出發"): st.session_state.shown_prize = True; st.rerun()

else: st.error("❌ 無法讀取資料庫，請檢查 Google Sheets 分頁名稱是否為 'user' 與 'task'")
