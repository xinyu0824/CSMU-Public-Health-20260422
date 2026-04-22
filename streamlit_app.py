import streamlit as st
import pandas as pd

# --- 1. 無印風美學設定 ---
st.set_page_config(page_title="甲班生活觀察計畫", layout="centered")
st.markdown("""<style>.stApp { background-color: #F5F5F0; } h1, h2, p, label { color: #5F5F5F !important; }</style>""", unsafe_allow_html=True)

# --- 2. 淨化後的連結 (這是關鍵) ---
# 我們把 /edit 換成 /export?format=csv，這會讓 Google 直接吐出資料
SHEET_ID = "1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA"
SHEET_NAME = "users"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# --- 3. 讀取資料 ---
@st.cache_data(ttl=10)
def get_data():
    try:
        # 直接用 pandas 讀取，這不經過 Secrets，最直覺
        return pd.read_csv(CSV_URL)
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return None

df = get_data()

# --- 4. 登入邏輯 ---
if 'login' not in st.session_state:
    st.session_state.login = False

if df is not None:
    # 定義妳的欄位名稱 (請確保 Google Sheet 第一列完全符合)
    COL_NAME = "name(姓名)"
    COL_ID = "Student ID(預設密碼)"
    COL_NICK = "Nickname(變更暱稱)"

    if not st.session_state.login:
        st.title("🍂 觀察員日誌：身分確認")
        
        # 檢查欄位是否存在
        if COL_NAME not in df.columns:
            st.error(f"找不到欄位 '{COL_NAME}'，請檢查 Excel 第一列。")
            st.write("目前的欄位有：", list(df.columns))
            st.stop()

        name_list = df[COL_NAME].dropna().tolist()
        selected_name = st.selectbox("您的真實姓名", ["搜尋名字"] + name_list)
        input_pwd = st.text_input("學號驗證", type="password")

        if st.button("確認進入"):
            user_info = df[df[COL_NAME] == selected_name].iloc[0]
            correct_id = str(user_info[COL_ID]).strip()
            
            if input_pwd.strip() == correct_id:
                st.session_state.login = True
                st.session_state.nickname = user_info[COL_NICK]
                st.rerun()
            else:
                st.error("密碼錯誤")
    else:
        st.title(f"📝 {st.session_state.nickname} 的觀察計畫")
        st.write("連線成功！歡迎開始觀察。")
