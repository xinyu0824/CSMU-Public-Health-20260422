import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import json
from datetime import datetime, timedelta

# --- 1. 配置與強效修復工具 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"
COOLDOWN_HOURS = 12

st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")

# [數據安全轉換器] 確保 NaN 或空值不會導致當機
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
    .tutorial-box {
        background-color: #FFFFFF; padding: 22px; border-radius: 15px; border-left: 6px solid #FFC107;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px;
    }
    .tutorial-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; font-size: 0.85rem; color: #8C8C8C; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 10px !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 50px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px; padding: 10px 0 !important; cursor: pointer; display: flex !important; justify-content: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 服務連線 ---
cloudinary.config(cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"], api_key=st.secrets["CLOUDINARY_API_KEY"], api_secret=st.secrets["CLOUDINARY_API_SECRET"], secure=True)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except: return None, None

# 初始化 Session State 用於「即時記憶」
if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'selected_lvl': "A", 't_done': {}})

df_users, df_tasks = load_data()

# --- 3. 流程 ---
if df_users is not None:
    # 確保關鍵欄位
    required_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set', 'gift_given', 'extra_tickets', 'gamble_balance', 'done_A', 'done_B', 'done_C', 'done_D', 'done_E']
    for c in required_cols:
        if c not in df_users.columns: df_users[c] = "0"

    # 登入標籤
    df_users["login_label"] = df_users.apply(lambda r: str(r["Nickname(變更暱稱)"]) if (pd.notna(r["Nickname(變更暱稱)"]) and str(r["Nickname(變更暱稱)"]).strip() != "" and str(r["Nickname(變更暱稱)"]).lower() != "nan") else str(r["name(姓名)"]), axis=1)

    if not st.session_state.login:
        st.title("🍂 公衛一甲：特工登入")
        login_list = df_users["login_label"].dropna().tolist()
        sel = st.selectbox("請選擇特工身份", ["搜尋代號/姓名"] + login_list)
        pwd = st.text_input("密碼", type="password")
        if st.button("進入觀測站"):
            match = df_users[df_users["login_label"] == sel]
            if not match.empty:
                user_row = match.iloc[0]
                db_id = str(user_row["Student ID(預設密碼)"]).strip().split('.')[0]
                db_pwd = str(user_row.get("password(自訂密碼)", "")).strip()
                correct = db_pwd if (db_pwd != "" and db_pwd != "nan") else db_id
                if pwd.strip() == correct:
                    st.session_state.login, st.session_state.student_id = True, db_id
                    st.rerun()
                else: st.error("密碼錯誤")
    else:
        # 已登入
        u_match = df_users[df_users["Student ID(預設密碼)"].astype(str).str.contains(st.session_state.student_id)]
        user = u_match.iloc[0]
        u_idx = u_match.index[0]
        
        # --- [關鍵記憶邏輯] 每次載入時，將資料庫數值同步到暫存記憶 ---
        for col in ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set']:
            if safe_str(user.get(col)) == "1":
                st.session_state.t_done[col] = True

        m_base, g_net, g_gift, total_tickets = (safe_int(user.get('done_A')) // 5) + (safe_int(user.get('done_B')) // 3) + \
                                               (safe_int(user.get('done_C')) // 2) + safe_int(user.get('done_D')) + (safe_int(user.get('done_E')) * 2), \
                                               safe_int(user.get('gamble_balance')), safe_int(user.get('extra_tickets')), 0
        total_tickets = max(0, m_base + g_net + g_gift)
        
        # 教學完成總數
        done_count = sum(1 for v in st.session_state.t_done.values() if v)

        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{get_agent_rank(total_tickets, 0)}</span><span class="main-title">{user["login_label"]} 的特工記憶庫</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("抽獎券總額", f"{total_tickets} 張")
            if st.button("🔄 同步雲端"): st.cache_data.clear(); st.rerun()
            if st.button("🚪 登出系統"): st.session_state.login = False; st.rerun()

        tabs = st.tabs(["🎯 任務挑選", "📊 進度追蹤", "🎰 地下博弈", "⚙️ 設定"])

        # 教學點擊更新邏輯 (強效同步版)
        def handle_tutorial(col):
            # 1. 先更新暫存記憶 (確保 UI 立刻反應)
            st.session_state.t_done[col] = True
            
            # 2. 準備更新雲端
            df_users[col] = df_users[col].astype(object)
            df_users.at[u_idx, col] = "1"
            
            # 3. 領獎檢查
            if len(st.session_state.t_done) == 4 and safe_str(user.get('gift_given')) != "1":
                df_users['gift_given'] = df_users['gift_given'].astype(object)
                df_users['extra_tickets'] = df_users['extra_tickets'].astype(object)
                df_users.at[u_idx, 'gift_given'] = "1"
                df_users.at[u_idx, 'extra_tickets'] = str(safe_int(user.get('extra_tickets')) + 1)
                st.toast("🎁 培訓完成，獎勵 +1！")
            
            # 4. 同步雲端並重整
            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
            st.cache_data.clear()
            st.rerun()

        # --- Tab 1: 任務 ---
        with tabs[0]:
            is_locked = not st.session_state.t_done.get('tuto_task', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>🚩 任務導引</h3><p>點擊鎖定任務後上傳照片。完成後進入 12 小時冷卻期。</p><div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解任務規則", key="btn_t1", use_container_width=True): handle_tutorial('tuto_task')
            
            st.write("### 📍 步驟一：選擇難度")
            lvl = st.radio("分級", ["A", "B", "C", "D", "E"], horizontal=True, label_visibility="collapsed")
            st.markdown(f"#### {lvl} 級任務區域")
            # 這裡即便 is_locked 也要顯示，但按鈕會被警告攔截
            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == lvl]
            for idx, task in filtered.iterrows():
                with st.container():
                    st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if st.button("鎖定此任務", key=f"lock_{idx}"):
                        if is_locked: st.warning("⚠️ 請先閱讀上方功能指引並按下確認鍵")
                        else: st.toast("任務已鎖定")

        # --- Tab 2: 進度 ---
        with tabs[1]:
            is_locked = not st.session_state.t_done.get('tuto_prog', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>📊 進度導引</h3><p>不同難度任務獎勵不同，達成數量可兌換抽獎券。</p><div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解進度規則", key="btn_t2", use_container_width=True): handle_tutorial('tuto_prog')
            
            st.subheader("📊 任務完成度")
            for l in ["A", "B", "C", "D", "E"]:
                val = safe_int(user.get(f"done_{l}"))
                st.write(f"難度 {l}： {val} / 5"); st.progress(min(val/5, 1.0))

        # --- Tab 3: 賭場 ---
        with tabs[2]:
            is_locked = not st.session_state.t_done.get('tuto_gamble', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>🎰 博弈導引</h3><p>消耗獎券即可參與博弈，勝率 75%。</p><div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解博弈規則", key="btn_t4", use_container_width=True): handle_tutorial('tuto_gamble')
            
            st.info("🎰 地下博弈尚未開放...")
            if st.button("🔥 下注一把", use_container_width=True):
                if is_locked: st.warning("⚠️ 請先閱讀上方功能指引並按下確認鍵")
                else: st.info("功能維護中")

        # --- Tab 4: 設定 ---
        with tabs[3]:
            is_locked = not st.session_state.t_done.get('tuto_set', False)
            if is_locked:
                st.markdown(f'<div class="tutorial-box"><h3>⚙️ 設定導引</h3><p>修改代號隱藏本名，或自訂登入密碼。</p><div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div></div>', unsafe_allow_html=True)
                if st.button("我已了解設定功能", key="btn_t3", use_container_width=True): handle_tutorial('tuto_set')
            
            st.subheader("⚙️ 帳號設定")
            new_nick = st.text_input("代號", value=safe_str(user.get("Nickname(變更暱稱)", "")))
            if st.button("💾 更新資料"):
                if is_locked: st.warning("⚠️ 請先閱讀上方功能指引並按下確認鍵")
                else:
                    df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object)
                    df_users.at[u_idx, "Nickname(變更暱稱)"] = str(new_nick)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                    st.success("更新成功，下次登入生效")

        # --- 全套教學獎勵顯示 ---
        if done_count == 4 and safe_str(user.get('gift_given', '0')) == '1':
            if 'p_win' not in st.session_state:
                st.balloons()
                st.markdown('<div style="text-align:center; padding:25px; background:#FFF9E6; border:2px solid #FFC107; border-radius:15px;"><h2>🎉 培訓完成！</h2><p>獲得 1 張獎券獎勵，已存入檔案。<br>快去執行任務，或者去地下城試試手氣吧！</p></div>', unsafe_allow_html=True)
                if st.button("立刻行動"): st.session_state.p_win = True; st.rerun()

else: st.error("❌ 無法連線至總部資料庫")
