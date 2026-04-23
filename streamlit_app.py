import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import random
from datetime import datetime

# --- 1. 定時設定 (請設定妳聚會前一天的日期) ---
# 格式：YYYY-MM-DD
GAMBLE_OPEN_DATE = "2026-04-25" 

# --- 2. 視覺美學設定 ---
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
    .agent-badge { display: inline-block; padding: 4px 14px; background-color: #5F5F5F; color: #FFFFFF !important; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 12px; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); }
    .title-wrapper { display: flex; align-items: center; margin-bottom: 25px; gap: 10px; }
    .main-title { font-size: 1.6rem; margin: 0; font-weight: bold; }
    div[role="radiogroup"] { display: flex !important; flex-direction: row !important; justify-content: center !important; gap: 12px !important; width: 100% !important; padding: 10px 0 !important; }
    div[role="radiogroup"] > label { flex: 1 !important; min-width: 60px !important; background-color: #FFFFFF !important; border: 1px solid #D9D9D9 !important; border-radius: 10px !important; padding: 15px 0 !important; cursor: pointer; transition: all 0.2s ease; display: flex !important; justify-content: center !important; align-items: center !important; }
    div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child { display: none !important; }
    div[role="radiogroup"] label p { font-size: 1.3rem !important; font-weight: bold !important; color: #5F5F5F !important; margin: 0 !important; }
    div[role="radiogroup"] label[aria-checked="true"] { background-color: #FFC107 !important; border-color: #FFB300 !important; box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3) !important; }
    div[role="radiogroup"] label[aria-checked="true"] p { color: #FFFFFF !important; }
    .casino-zone { background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%); color: #FFC107 !important; padding: 30px; border-radius: 20px; border: 3px solid #FFC107; text-align: center; margin-bottom: 25px; }
    .casino-title { color: #FFC107 !important; font-size: 2.2rem !important; text-shadow: 0 0 10px #FFC107; }
    .casino-stat { background: rgba(255,255,255,0.1); padding: 10px; border-radius: 10px; margin: 5px; min-width: 120px; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 6px; margin-bottom: 12px; border-left: 6px solid #FFC107; }
    .tutorial-card { background-color: #FFF9E6; padding: 25px; border: 2px dashed #FFC107; border-radius: 12px; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 服務配置 ---
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
        # 任務獲得
        base = (to_int(user_row.get('done_A', 0)) // 5) + (to_int(user_row.get('done_B', 0)) // 3) + \
               (to_int(user_row.get('done_C', 0)) // 2) + to_int(user_row.get('done_D', 0)) + (to_int(user_row.get('done_E', 0)) * 2)
        # 賭博損益 (含初始贈送)
        extra = to_int(user_row.get('extra_tickets', 0))
        return max(0, base + extra)
    except: return 0

@st.cache_data(ttl=2)
def load_data():
    try:
        users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        return users, tasks
    except Exception as e:
        st.error(f"📡 連線失敗：{e}"); return None, None

if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'locked_task': None, 'locked_diff': None, 'selected_lvl': "A"})

df_users, df_tasks = load_data()

# --- 4. 流程 ---
if df_users is not None:
    def get_anonymous_label(row):
        nick = str(row.get("Nickname(變更暱稱)", "")).strip()
        return nick if (nick != "" and nick.lower() != "nan") else str(row["name(姓名)"])
    df_users["login_label"] = df_users.apply(get_anonymous_label, axis=1)

    if not st.session_state.login:
        st.title("🍂 公衛一甲：身分登入")
        login_list = df_users["login_label"].dropna().tolist()
        selected_label = st.selectbox("請選擇特工身份", ["搜尋代號/姓名"] + login_list)
        input_pwd = st.text_input("密碼", type="password")
        if st.button("確認進入"):
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
        df_users["Student ID(預設密碼)"] = df_users["Student ID(預設密碼)"].apply(clean_id_logic)
        user = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id].iloc[0]
        user_idx = df_users[df_users["Student ID(預設密碼)"] == st.session_state.student_id].index[0]
        
        total_tickets = calculate_total_tickets(user)
        p_val = str(user.get("photo_list", "")).strip()
        photo_count = 0 if (p_val == "" or p_val.lower() == "nan") else len([u for u in p_val.split(",") if u.strip() != ""])
        is_newbie = (photo_count == 0)
        rank_label = get_agent_rank(total_tickets, photo_count)
        
        st.markdown(f'<div class="title-wrapper"><span class="agent-badge">{rank_label}</span><span class="main-title">{user["login_label"]} 的特工記憶庫</span></div>', unsafe_allow_html=True)

        with st.sidebar:
            st.markdown(f"### 🎖️ 個人檔案\n**稱號：** {rank_label}\n**目前抽獎券：** {total_tickets} 張")
            st.write("---")
            if st.button("🚪 登出系統"): st.session_state.login = False; st.rerun()

        # --- 時間檢查：判定是否顯示賭博分頁 ---
        is_casino_open = datetime.now() >= datetime.strptime(GAMBLE_OPEN_DATE, "%Y-%m-%d")
        
        tab_list = ["🎯 任務挑選", "📊 進度追蹤"]
        if is_casino_open: tab_list.append("🎰 地下博弈")
        tab_list.append("⚙️ 設定")
        
        tabs = st.tabs(tab_list)

        with tabs[0]: # 任務挑選
            if is_newbie:
                st.markdown('<div class="tutorial-card"><h3>👋 哈囉特工，歡迎加入！</h3><p>完成新手引導任務後即可正式解鎖正式分區。</p><hr><b>🚩 任務：初試身心</b><br><small>拍攝校園一角即可！</small></div>', unsafe_allow_html=True)
                if st.button("鎖定引導任務", key="lock_newbie"):
                    st.session_state.locked_task, st.session_state.locked_diff = "新手引導：初試身心", "A"
            else:
                st.write("### 📍 步驟一：選擇難度")
                selected_lvl = st.radio("難度", options=["A", "B", "C", "D", "E"], index=["A", "B", "C", "D", "E"].index(st.session_state.selected_lvl), horizontal=True, label_visibility="collapsed")
                if selected_lvl != st.session_state.selected_lvl: 
                    st.session_state.selected_lvl, st.session_state.locked_task = selected_lvl, None; st.rerun()
                st.markdown(f"#### {level_info[st.session_state.selected_lvl]}")
                filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == st.session_state.selected_lvl]
                for idx, task in filtered.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        if st.button("鎖定此任務", key=f"lock_{st.session_state.selected_lvl}_{idx}"):
                            st.session_state.locked_task, st.session_state.locked_diff = task['title'], st.session_state.selected_lvl
                            st.toast(f"已選定：{task['title']}")

            if st.session_state.locked_task:
                st.write("---")
                st.subheader(f"情報回傳：{st.session_state.locked_task}")
                up_file = st.file_uploader("選取照片", type=['png', 'jpg', 'jpeg'], key=f"up_{st.session_state.locked_task}")
                if up_file and st.button("🚀 正式回傳", key="btn_upload"):
                    try:
                        res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT", transformation=[{'width': 800, 'quality': "auto:eco"}])
                        df_users['photo_list'] = df_users['photo_list'].astype(object)
                        df_users['task_list'] = df_users['task_list'].astype(object)
                        cur_p = str(df_users.at[user_idx, "photo_list"]).strip()
                        df_users.at[user_idx, "photo_list"] = str(res["secure_url"] if (cur_p == "" or cur_p.lower() == "nan") else f"{cur_p},{res['secure_url']}")
                        cur_t = str(df_users.at[user_idx, "task_list"]).strip()
                        df_users.at[user_idx, "task_list"] = str(st.session_state.locked_task if (cur_t == "" or cur_t.lower() == "nan") else f"{cur_t},{st.session_state.locked_task}")
                        diff_col = f"done_{st.session_state.locked_diff}"
                        try: val = int(float(df_users.at[user_idx, diff_col])) if pd.notna(df_users.at[user_idx, diff_col]) else 0
                        except: val = 0
                        df_users.at[user_idx, diff_col] = str(val + 1)
                        conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                        st.balloons(); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"同步失敗：{e}")

        with tabs[1]: # 進度追蹤
            st.subheader("📊 任務完成度")
            for lvl in ["A", "B", "C", "D", "E"]:
                c = user.get(f"done_{lvl}", 0)
                try: val = int(float(c))
                except: val = 0
                st.write(f"{level_info[lvl]}： {val} / 5")
                st.progress(min(val/5, 1.0))
            st.metric("當前獎券總額", f"{total_tickets} 張")

        # 根據時間動態判斷 Tab 的內容
        if is_casino_open:
            with tabs[2]: # 🎰 地下博弈
                st.markdown("""
                    <div class="casino-zone">
                        <div class="casino-title">🎰 特工地下城</div>
                        <p>這裡是命運的分叉路。消耗 1 張抽獎券下注，勝率 75%！</p>
                    </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(3)
                cols[0].metric("🃏 累積下注", f"{int(float(user.get('gamble_count', 0)))} 次")
                cols[1].metric("💰 累計盈虧", f"{int(float(user.get('gamble_profit', 0)))} 張")
                cur_loss = int(float(user.get("loss_count", 0)))
                cols[2].metric("🛡️ 保底進度", f"{cur_loss}/4")

                if total_tickets < 1:
                    st.error("❌ 你的抽獎券不足！趕快去執行任務賺取籌碼吧。")
                else:
                    if st.button("🧧 消耗 1 張下注！ (慎選)", use_container_width=True):
                        roll = random.random() * 100
                        gain = -1 
                        is_total_loss = False
                        if roll < 10: gain += 4; msg = "💎 奇蹟現身！獲得 4 張獎券！"
                        elif roll < 35: gain += 3; msg = "🔥 手氣大發！獲得 3 張獎券！"
                        elif roll < 75: gain += 2; msg = "✨ 贏得任務！獲得 2 張獎券！"
                        elif roll < 85: gain += 1; msg = "⚖️ 不賺不賠，本金退回。"
                        else: gain += 0; msg = "💀 血本無歸！這就是特務的宿命..."; is_total_loss = True
                        
                        # 更新
                        for col in ['extra_tickets', 'loss_count', 'gamble_count', 'gamble_profit']:
                            df_users[col] = df_users[col].astype(object)
                        
                        old_extra = int(float(user.get("extra_tickets", 0)))
                        new_loss_count = cur_loss + (1 if is_total_loss else 0)
                        final_gain = gain
                        
                        if new_loss_count >= 4:
                            final_gain += 2; new_loss_count = 0; st.toast("🛡️ 總部保底補貼已入帳！")
                        
                        df_users.at[user_idx, "extra_tickets"] = str(old_extra + final_gain)
                        df_users.at[user_idx, "loss_count"] = str(new_loss_count)
                        df_users.at[user_idx, "gamble_count"] = str(int(float(user.get('gamble_count', 0))) + 1)
                        df_users.at[user_idx, "gamble_profit"] = str(int(float(user.get('gamble_profit', 0))) + gain)
                        
                        conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                        if gain > 0: st.balloons(); st.success(msg)
                        elif is_total_loss: st.error(msg)
                        else: st.info(msg)
                        st.cache_data.clear(); st.rerun()
            
            with tabs[3]: # 設定
                st.subheader("⚙️ 設定")
                new_nick = st.text_input("修改特工代號", value=user.get("Nickname(變更暱稱)", ""))
                if st.button("💾 儲存"):
                    df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object)
                    df_users.at[user_idx, "Nickname(變更暱稱)"] = str(new_nick)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                    st.success("✅ 更新成功！"); st.cache_data.clear(); st.rerun()
        else:
            with tabs[2]: # 當賭場未開時的設定 Tab
                st.subheader("⚙️ 設定")
                new_nick = st.text_input("修改特工代號", value=user.get("Nickname(變更暱稱)", ""))
                if st.button("💾 儲存"):
                    df_users['Nickname(變更暱稱)'] = df_users['Nickname(變更暱稱)'].astype(object)
                    df_users.at[user_idx, "Nickname(變更暱稱)"] = str(new_nick)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                    st.success("✅ 更新成功！"); st.cache_data.clear(); st.rerun()

else: st.error("❌ 無法連線")
