import streamlit as st
import pandas as pd
import random

# --- 1. 網頁質感設定 (Muji 暖米色調) ---
st.set_page_config(page_title="📸 拍拍挑戰：特工觀察", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F0; }
    h1, h2, h3, p, label { color: #5F5F5F !important; font-family: 'Noto Sans TC', sans-serif; }
    .task-box { background-color: #FFFFFF; padding: 20px; border: 1px solid #E6E6E1; border-radius: 4px; margin-bottom: 15px; }
    .stButton>button { background-color: #FFFFFF; color: #5F5F5F; border: 1px solid #D9D9D9; border-radius: 2px; }
    
    /* 照片牆不規則排列效果 */
    .gallery-container { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }
    .gallery-item { background-color: white; border: 1px solid #E6E6E1; padding: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .gallery-text { font-size: 0.7rem; color: #8C8C8C; text-align: center; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 資料讀取設定 ---
SHEET_ID = "1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA"
USER_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=users"
TASK_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=tasks"

@st.cache_data(ttl=10)
def load_data(url):
    try:
        return pd.read_csv(url)
    except:
        return None

# --- 3. 核心邏輯：抽獎券計算機 ---
def calculate_tickets(a, b, c, d, e):
    # 依照妳的要求：A:5/1, B:3/1, C:2/1, D:1/1, E:1/2
    tickets = (a // 5) + (b // 3) + (c // 2) + (d * 1) + (e * 2)
    return int(tickets)

# --- 4. 初始化 Session ---
if 'login' not in st.session_state:
    st.session_state.login = False
    st.session_state.current_task = "尚未領取任務"

# --- 5. 程式主邏輯 ---
df_users = load_data(USER_CSV)

if df_users is not None:
    COL_NAME = "name(姓名)"
    COL_ID = "Student ID(預設密碼)"
    COL_NICK = "Nickname(變更暱稱)"

    if not st.session_state.login:
        st.title("🍂 拍照觀察員：身分登入")
        name_list = df_users[COL_NAME].dropna().tolist()
        selected_name = st.selectbox("帳號（預設為姓名）", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("密碼（預設為學號）", type="password")

        if st.button("確認進入"):
            user_info = df_users[df_users[COL_NAME] == selected_name].iloc[0]
            if input_pwd.strip() == str(user_info[COL_ID]).strip():
                st.session_state.login = True
                st.session_state.real_name = selected_name
                st.session_state.student_id = user_info[COL_ID]
                nick = user_info[COL_NICK]
                st.session_state.nickname = "" if pd.isna(nick) else str(nick)
                st.rerun()
            else:
                st.error("密碼錯誤")

    else:
        # 已登入介面
        display_name = st.session_state.nickname if st.session_state.nickname.strip() != "" else st.session_state.real_name
        st.title(f"📝 {display_name} 今天拍了沒📸")
        
        # --- [新增] 照片拼貼牆區域 (不須向下滑，放在最上方) ---
        # 這裡假設未來從 Google Sheet 讀取到的任務照片 (示範用)
        # 每一項是 (任務簡稱, 圖片網址)
        completed_photos = [
            ("白鞋陣列", "https://via.placeholder.com/150/EBEBE6/5F5F5F?text=TASK+1"),
            ("制式補給", "https://via.placeholder.com/150/E6E6E1/5F5F5F?text=TASK+2"),
            ("學術分歧", "https://via.placeholder.com/180/F0F0EB/5F5F5F?text=TASK+3"),
            ("酒精防線", "https://via.placeholder.com/140/EBEBE6/5F5F5F?text=TASK+4"),
        ]
        
        st.write("🖼️ 我的觀察記憶庫")
        cols = st.columns([1, 1.2, 0.8, 1.1]) # 不規則寬度創造隨機感
        for i, (task_name, img_url) in enumerate(completed_photos):
            with cols[i % 4]:
                st.markdown(f"""
                    <div class="gallery-item">
                        <img src="{img_url}" style="width: 100%; height: auto; border-radius: 2px;">
                        <div class="gallery-text">{task_name}</div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.write("---")

        tab1, tab2, tab3 = st.tabs(["🎯 領取任務", "🎁 抽獎進度", "⚙️ 個人設定"])

        with tab1:
        with tab1:
            st.subheader("🕵️ 任務檔案庫 (Mission Dossier)")
            st.write("點擊各級檔案，查看詳細滲透目標：")

            # 讀取任務資料
            df_tasks = load_data(TASK_CSV)

            if df_tasks is not None:
                # 定義難度等級與對應名稱
                difficulty_map = {
                    "A": "【初級滲透】 (5任務換1券)",
                    "B": "【進階觀察】 (3任務換1券)",
                    "C": "【深度諜對諜】 (2任務換1券)",
                    "D": "【極限衝突】 (1任務換1券)",
                    "E": "【傳奇成就】 (1任務換2券)"
                }

                # 依序產生 A 到 E 的大框格
                for level, label in difficulty_map.items():
                    # 篩選該難度的任務
                    level_tasks = df_tasks[df_tasks['difficulty'] == level]
                    
                    if not level_tasks.empty:
                        # 這是「大框格」的開始
                        with st.container():
                            st.markdown(f"""
                                <div style="border: 2px solid #D9D9D9; border-radius: 8px; padding: 15px; margin-bottom: 20px; background-color: #FFFFFF;">
                                    <h3 style="color: #5F5F5F; border-bottom: 1px solid #E6E6E1; padding-bottom: 10px;">{label}</h3>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 在大框格內列出所有任務
                            for _, task in level_tasks.iterrows():
                                col_task, col_btn = st.columns([4, 1])
                                with col_task:
                                    st.markdown(f"**{task['title']}**")
                                    st.caption(task['content'])
                                with col_btn:
                                    # 讓同學可以點擊「選定」這個任務
                                    if st.button("鎖定", key=f"btn_{level}_{task['title']}"):
                                        st.session_state.current_task = f"【{task['title']}】\n{task['content']}"
                                        st.success(f"已選定任務：{task['title']}")
                                        st.rerun()
                            st.write("") # 增加間隔
                    else:
                        # 如果該難度沒任務，可以顯示一個灰色的占位框
                        st.markdown(f"""
                            <div style="border: 1px dashed #D9D9D9; border-radius: 8px; padding: 15px; margin-bottom: 20px; opacity: 0.5;">
                                <h3 style="color: #8C8C8C;">{label} (情報蒐集中...)</h3>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("目前無法讀取任務檔案，請檢查 Google Sheet 的 'tasks' 分頁。")
           
        with tab2:
            st.subheader("抽獎結算")
            # 這裡假設從 df_users 讀取到的數值
            # 妳可以在 Google Sheet 增加 done_A, done_B 等欄位
            a, b, c, d, e = 5, 3, 0, 1, 0 # 範例數據
            total_tickets = calculate_tickets(a, b, c, d, e)
            
            st.metric("當前可領取抽獎券", f"{total_tickets} 張")
            st.write(f"進度：A級({a}) B級({b}) C級({c}) D級({d}) E級({e})")
            st.progress(min((a+b+c+d+e)/20, 1.0), text="特工積分累積中")

        with tab3:
            st.subheader("帳號設定")
            new_nick = st.text_input("更換暱稱", value=st.session_state.nickname)
            if st.button("確認修改"):
                st.session_state.nickname = new_nick
                st.rerun()

else:
    st.error("連線資料庫失敗")
