import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time
from datetime import date

# --- 1. 設定與配置 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

st.set_page_config(page_title="🧠 特工觀測站：終極複習備忘終端", layout="wide")

# 初始化 Session State
if 'reveal_cloze' not in st.session_state:
    st.session_state.reveal_cloze = {}

# 工具函數
def safe_str(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return ""
    return str(val).strip()

def safe_int(val):
    try:
        s = safe_str(val)
        return int(float(s)) if s != "" else 0
    except: return 0

# --- 2. 樣式 ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    .cloze-card { background-color: #FFFFFF; padding: 25px; border-radius: 15px; border-left: 6px solid #4A90E2; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; font-size: 1.15rem; }
    .todo-card { background-color: #FFFFFF; padding: 20px; border-radius: 12px; border: 1px solid #E6E6E1; margin-bottom: 15px; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; color: white !important; margin-right: 5px; margin-bottom: 5px; }
    .badge-cat { background-color: #6C757D; }
    .badge-date { background-color: #17A2B8; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 連線與數據讀取 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1)
def load_data():
    try:
        c = conn.read(spreadsheet=GSHEET_URL, worksheet="cloze")
        m = conn.read(spreadsheet=GSHEET_URL, worksheet="memo")
        return c, m
    except:
        return pd.DataFrame(), pd.DataFrame()

df_cloze, df_memo = load_data()

# --- 4. 主介面 ---
tabs = st.tabs(["🧠 精密考點挖空複習", "📋 深度任務備忘錄"])

with tabs[0]:
    st.title("🧠 醫學核心考點精密複習系統")
    if not df_cloze.empty:
        # 下拉選單篩選
        c1, c2, c3 = st.columns(3)
        subjects = ["全部"] + sorted([str(x) for x in df_cloze['subject'].dropna().unique()])
        sel_sub = c1.selectbox("科目", subjects)
        
        df_f = df_cloze.copy()
        if sel_sub != "全部": df_f = df_f[df_f['subject'] == sel_sub]
        
        units = ["全部"] + sorted([str(x) for x in df_f['unit'].dropna().unique()])
        sel_unit = c2.selectbox("單元", units)
        if sel_unit != "全部": df_f = df_f[df_f['unit'] == sel_unit]
        
        for idx, row in df_f.iterrows():
            q_id = str(row['id'])
            raw = safe_str(row['content'])
            answers = re.findall(r"\{\{(.*?)\}\}", raw)
            display = re.sub(r"\{\{.*?\}\}", " [ ______ ] ", raw)
            
            st.markdown(f'<div class="cloze-card"><b>考點：</b> {display}</div>', unsafe_allow_html=True)
            if st.button("查看解答", key=f"ans_{q_id}"):
                st.success(f"答案：{', '.join(answers)}")
            st.write("---")

with tabs[1]:
    st.title("📋 特工專屬深度任務備忘錄")
    # 新增任務表單
    with st.expander("➕ 新增待辦事項"):
        with st.form("add_form"):
            t = st.text_input("任務名稱")
            d = st.date_input("目標日期")
            if st.form_submit_button("寫入"):
                new_row = pd.DataFrame([{'title': t, 'target_date': str(d), 'status': '未開始', 'order_num': 1}])
                df_memo = pd.concat([df_memo, new_row], ignore_index=True)
                conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                st.rerun()
    
    # 顯示清單
    if not df_memo.empty:
        for idx, row in df_memo.iterrows():
            st.markdown(f"""
                <div class="todo-card">
                    <h4>{row['title']}</h4>
                    <span class="badge badge-date">📅 {row['target_date']}</span>
                </div>
            """, unsafe_allow_html=True)
