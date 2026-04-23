import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection

# --- 1. 質感設定 ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 2px; width: 100%; }
    .mission-card { background-color: #FFFFFF; padding: 18px; border: 1px solid #E6E6E1; border-radius: 4px; margin-bottom: 12px; }
    .polaroid { background-color: white; padding: 12px; border: 1px solid #E6E6E1; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 配置 ---
cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)

# 試算表網址 (請確認已分享給 Service Account Email)
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        # 🚀 [最強大招]：不指定分頁名稱，直接讀取
        # 預設會讀取試算表中的「第一個分頁」
        df_all = conn.read(spreadsheet=GSHEET_URL)
        
        # 為了確保萬無一失，我們先嘗試用名字讀取，失敗了再用預設讀取
        try:
            users = conn.read(spreadsheet=GSHEET_URL, worksheet="user")
        except:
            users = conn.read(spreadsheet=GSHEET_URL) # 失敗就抓第一個分頁
            
        try:
            tasks = conn.read(spreadsheet=GSHEET_URL, worksheet="task")
        except:
            # 如果妳的 task 是第二個分頁，這行會嘗試抓取它 (部分版本支援)
            tasks = conn.read(spreadsheet=GSHEET_URL) 
            st.warning("⚠️ 找不到名為 'task' 的分頁，請確認您的分頁名稱。")

        return users, tasks
    except Exception as e:
        st.error(f"📡 總部連線失敗：{e}")
        return None, None

# --- 3. 邏輯 ---
level_info = {"A": "【 潛伏訊號 】", "B": "【 視角破解 】", "C": "【 迷霧追蹤 】", "D": "【 極限干蝕 】", "E": "【 傳奇解密 】"}

def calculate_total_tickets(user_row):
    try:
        def clean_val(v): return int(v) if pd.notna(v) else 0
        a, b, c, d, e = [clean_val(user_row.get(f'done_{k}', 0)) for k in "ABCDE"]
        return (a // 5) + (b // 3) + (c // 2) + (d * 1) + (e * 2)
    except: return 0

if 'login' not in st.session_state:
    st.session_state.update({'login': False, 'student_id': None, 'locked_task': None, 'locked_diff': None, 'selected_lvl': "A"})

# 執行讀取
df_users, df_tasks = load_data()

# --- 4. 流程分層 ---
if df_users is not None:
    if not st.session_state.login:
        st.title("🍂 拍照觀察員：身分登入")
        # 顯示抓到的資料欄位，方便確認
        if "name(姓名)" not in df_users.columns:
            st.error(f"❌ 找不到 'name(姓名)' 欄位。目前的欄位有：{list(df_users.columns)}")
            st.info("💡 請確認您的試算表第一列標題是否正確。")
            st.stop()
            
        name_list = df_users["name(姓名)"].dropna().tolist()
        selected_name = st.selectbox("帳號 (預設為姓名)", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼 (預設為學號)", type="password")
        if st.button("確認進入"):
            match = df_users[df_users["name(姓名)"] == selected_name]
            if not match.empty:
                user_row = match.iloc[0]
                try:
                    raw_pwd = user_row.get("password(自訂密碼)", None)
                    correct_pwd = str(raw_pwd).strip() if (pd.notna(raw_pwd) and str(raw_pwd).strip() != "") else str(user_row["Student ID(預設密碼)"]).strip()
                except: correct_pwd = str(user_row["Student ID(預設密碼)"]).strip()
                
                if input_pwd.strip() == correct_pwd:
                    st.session_state.login, st.session_state.student_id = True, str(user_row["Student ID(預設密碼)"]).strip()
                    st.rerun()
                else: st.error("密碼錯誤。")
    else:
        # 已登入介面
        user_idx = df_users[df_users["Student ID(預設密碼)"].astype(str).str.strip() == st.session_state.student_id].index[0]
        user = df_users.iloc[user_idx]
        st.title(f"📝 {user['name(姓名)']} 的特工空間")
        
        # [其餘代碼保持不變...]
        tab1, tab2, tab3 = st.tabs(["🎯 任務挑選", "📊 進度瀏覽", "⚙️ 設定"])
        with tab1:
            if df_tasks is not None:
                btn_cols = st.columns(5)
                for i, lvl in enumerate(["A", "B", "C", "D", "E"]):
                    if btn_cols[i].button(lvl, key=f"btn_{lvl}"): st.session_state.selected_lvl = lvl
                
                curr_lvl = st.session_state.selected_lvl
                filtered = df_tasks[df_tasks['difficulty'].astype(str).str.strip() == curr_lvl]
                for _, task in filtered.iterrows():
                    with st.container():
                        st.markdown(f'<div class="mission-card"><b>{task["title"]}</b><br><small>{task["content"]}</small></div>', unsafe_allow_html=True)
                        if st.button("鎖定此目標", key=f"lock_{task['title']}"):
                            st.session_state.locked_task, st.session_state.locked_diff = task['title'], curr_lvl
                            st.toast(f"已選定：{task['title']}")
                
                if st.session_state.locked_task:
                    up_file = st.file_uploader("上傳觀察證物", type=['png', 'jpg', 'jpeg'])
                    if up_file:
                        if st.button("🚀 正式回傳"):
                            try:
                                res = cloudinary.uploader.upload(up_file, folder="CSMU_AGENT")
                                img_url = res["secure_url"]
                                
                                # 更新 df_users 並寫回
                                df_users.at[user_idx, "photo_list"] = img_url # 簡化邏輯供測試
                                # 注意：這裡的 worksheet 名稱必須跟讀取時一致
                                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_users)
                                st.success("回傳成功！")
                                st.rerun()
                            except Exception as e: st.error(f"回傳失敗：{e}")

else: st.error("❌ 無法連線至總部資料庫。")
