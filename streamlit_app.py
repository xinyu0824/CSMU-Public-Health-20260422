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
    
    /* 質感教學簡報框 */
    .tutorial-box {
        background-color: #FFFFFF;
        padding: 22px;
        border-radius: 15px;
        border: 1px solid #E6E6E1;
        border-left: 6px solid #FFC107;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 25px;
        position: relative;
    }
    .tutorial-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 15px;
        font-size: 0.85rem;
        color: #8C8C8C;
    }
    
    /* A-E 方格寬度與對稱 */
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 12px !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 65px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px !important; padding: 15px 0 !important; cursor: pointer; display: flex !important; justify-content: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    div[role="radiogroup"] label p { font-size: 1.3rem !important; font-weight: bold !important; color: #5F5F5F !important; }
    div[role="radiogroup"] label[aria-checked="true"] { background-color: #FFC107 !important; border-color: #FFB300 !important; }
    div[role="radiogroup"] label[aria-checked="true"] p { color: #FFFFFF !important; }
    
    .casino-zone { background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%); color: #FFC107 !important; padding: 25px; border-radius: 20px; border: 3px solid #FFC107; text-align: center; margin-bottom: 25px; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 服務配置 ---
cloudinary.config(cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"], api_key=st.secrets["CLOUDINARY_API_KEY"], api_secret=st.secrets["CLOUDINARY_API_SECRET"], secure=True)
conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_logic_tickets(user_row):
    try:
        def to_int(v): return int(float(v)) if pd.notna(v) and str(v) != "" and str(v).lower() != "nan" else 0
        m_base = (to_int(user_row.get('done_A', 0)) // 5) + (to_int(user_row.get('done_B', 0)) // 3) + \
                 (to_int(user_row.get('done_C', 0)) // 2) + to_int(user_row.get('done_D', 0)) + (to_int(user_row.get('done_E', 0)) * 2)
        g_net = to_int(user_row.get('gamble_balance', 0))
        g_gift = to_int(user_row.get('extra_tickets', 0))
        return m_base, g_net, g_gift, max(0, m_base + g_net + g_gift)
    except: return 0, 0, 0, 0

@st.cache_data(ttl=2)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except: return None, None

if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'locked_task': None, 'selected_lvl': "A"})

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
        selected_label = st.selectbox("請選擇特工身份", ["搜尋代號..."] + login_list)
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
                else: st.error("密碼不正確。")
    else:
        # 已登入：精準鎖定使用者資料
        user_match = df_users[df_users["Student ID(預設密碼)"].astype(str).str.contains(st.session_state.student_id)]
        if user_match.empty: st.error("同步失敗"); st.stop()
        user = user_match.iloc[0]
        user_idx = user_match.index[0]
        
        # 教學計數器 (邏輯)
        t_cols = ['tuto_task', 'tuto_prog', 'tuto_gamble', 'tuto_set']
        done_count = sum([1 for c in t_cols if str(user.get(c, '0')) == '1'])
        
        m_base, g_net, g_gift, total_tickets = calculate_logic_tickets(user)
        photo_count = len([u for u in str(user.get("photo_list", "")).split(",") if u.strip() != "" and u.lower() != "nan"])
        rank_label = get_agent_rank(total_tickets, photo_count)
        
        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{rank_label}</span><span class="main-title">{user["login_label"]} 的特工記憶庫</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.metric("抽獎券總額", f"{total_tickets} 張")
            if st.button("🚪 登出系統"): st.session_state.login = False; st.rerun()

        # 分頁系統
        tab1, tab2, tab4, tab3 = st.tabs(["🎯 任務挑選", "📊 進度追蹤", "🎰 地下博弈", "⚙️ 設定"])

        # 教學更新函數 (防護版)
        def mark_tutorial(col):
            if col in df_users.columns:
                df_users[col] = df_users[col].astype(object)
                df_users.at[user_idx, col] = "1"
                
                # 重新計算總進度以判斷是否領獎
                new_done = sum([1 for c in t_cols if str(df_users.at[user_idx, c]) == '1'])
                if new_done == 4 and str(user.get('gift_given', '0')) != '1':
                    df_users['gift_given'] = df_users['gift_given'].astype(object)
                    df_users['extra_tickets'] = df_users['extra_tickets'].astype(object)
                    df_users.at[user_idx, 'gift_given'] = "1"
                    df_users.at[user_idx, 'extra_tickets'] = str(int(float(user.get('extra_tickets', 0))) + 1)
                    st.toast("🎉 恭喜完成全套訓練！獎勵已發放。")

                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.cache_data.clear(); st.rerun()
            else:
                st.error(f"資料表缺少欄位: {col}，請聯繫指揮官。")

        with tab1:
            if str(user.get('tuto_task', '0')) != '1':
                st.markdown(f"""
                    <div class="tutorial-box">
                        <h3>🚩 任務導引：首場觀測</h3>
                        <p>點擊鎖定任務後，上傳對應照片即可獲得獎券。注意：每個任務完成後將進入 12 小時冷卻期。</p>
                        <div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("了解任務規則", key="btn_t1", use_container_width=True): mark_tutorial('tuto_task')
            
            st.write("### 📍 步驟一：選擇難度")
            selected_lvl = st.radio("難度", options=["A", "B", "C", "D", "E"], horizontal=True, label_visibility="collapsed")
            st.markdown(f"#### {selected_lvl} 級任務區域")
            # 任務清單顯示 (即便沒看過教學也看得到，增加探索感)
            filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == selected_lvl]
            for idx, task in filtered.iterrows():
                with st.container():
                    st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                    if st.button("鎖定此任務", key=f"lock_{idx}"):
                        st.session_state.locked_task = task['title']; st.toast(f"已鎖定：{task['title']}")

        with tab2:
            if str(user.get('tuto_prog', '0')) != '1':
                st.markdown(f"""
                    <div class="tutorial-box">
                        <h3>📊 進度導引：階級晉升</h3>
                        <p>不同難度的任務獎勵不同。達成各階段數量要求，即可在聚會當天獲得更多抽獎機會！</p>
                        <div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("了解進度規則", key="btn_t2", use_container_width=True): mark_tutorial('tuto_prog')
            
            st.subheader("📊 特工進度統計")
            for lvl in ["A", "B", "C", "D", "E"]:
                c = user.get(f"done_{lvl}", 0)
                st.write(f"難度 {lvl} 完成度： {int(float(c))} / 5")
                st.progress(min(int(float(c))/5, 1.0))

        with tab4:
            if str(user.get('tuto_gamble', '0')) != '1':
                st.markdown(f"""
                    <div class="tutorial-box">
                        <h3>🎰 賭場導引：高風險情報</h3>
                        <p>每一張抽獎券都可以在此博弈。你有 75% 的機率翻倍，但也可能一無所有。累積 4 次失敗有總部補貼！</p>
                        <div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("了解博弈規則", key="btn_t4", use_container_width=True): mark_tutorial('tuto_gamble')
            
            st.markdown('<div class="casino-zone"><h2>🎰 特工地下城</h2><p>博弈結果將直接增減抽獎券餘額。</p></div>', unsafe_allow_html=True)
            if total_tickets < 1: st.error("籌碼不足，請先執行任務。")
            else:
                if st.button("🔥 消耗 1 張下注"): st.info("執行博弈中...")

        with tab3:
            if str(user.get('tuto_set', '0')) != '1':
                st.markdown(f"""
                    <div class="tutorial-box">
                        <h3>⚙️ 設定導引：身份匿蹤</h3>
                        <p>在此修改代號（Nickname）即可在登入名單中隱藏本名。自訂密碼則可取代學號登入。</p>
                        <div class="tutorial-footer"><span>訓練進度 {done_count}/4</span></div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("了解設定功能", key="btn_t3", use_container_width=True): mark_tutorial('tuto_set')
            
            st.subheader("⚙️ 帳號設定")
            new_nick = st.text_input("修改特工代號", value=user.get("Nickname(變更暱稱)", ""))
            if st.button("💾 更新設定"):
                df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object)
                df_users.at[user_idx, "Nickname(變更暱稱)"] = str(new_nick)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                st.success("更新成功")

        # --- 全套教學完成獎勵視窗 ---
        if done_count == 4 and str(user.get('gift_given', '0')) == '1':
            # 只在第一次領完獎勵時顯示大型慶賀框 (透過 session_state 控制)
            if 'just_finished' not in st.session_state:
                st.balloons()
                st.markdown("""
                    <div style="background-color:#FFF9E6; padding:30px; border-radius:20px; text-align:center; border:2px solid #FFC107;">
                        <h2 style="color:#FFC107;">🎉 恭喜！特務培訓結業</h2>
                        <p>你已完整瀏覽所有觀測站說明。我們已發放 <b>1 張額外抽獎券</b> 存入你的檔案。</p>
                        <p>現在，你可以先去「🎰 地下博弈」小試身手，或是開始執行首場觀測任務！</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("收到！立即出動"): 
                    st.session_state.just_finished = True
                    st.rerun()

else: st.error("❌ 無法連線")
