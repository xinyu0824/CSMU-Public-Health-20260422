import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
from datetime import date

# --- 1. 配置 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

st.set_page_config(page_title="🧠 特工觀測站", layout="wide")

# --- 2. 數據連線 (不使用過度緩存以確保即時顯示) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_fresh_data():
    c = conn.read(spreadsheet=GSHEET_URL, worksheet="cloze")
    m = conn.read(spreadsheet=GSHEET_URL, worksheet="memo")
    return c, m

df_cloze, df_memo = get_fresh_data()

# --- 3. 介面 ---
tabs = st.tabs(["🧠 精密考點挖空複習", "📋 深度任務備忘錄"])

with tabs[0]:
    st.title("🧠 醫學核心考點精密複習系統")
    if not df_cloze.empty:
        # 修正後的篩選器：確保欄位名稱正確 (建議檢查試算表欄位是否為 subject, unit, topic)
        cols = st.columns(3)
        sub = cols[0].selectbox("選擇科目", ["全部"] + sorted(df_cloze['subject'].dropna().unique().tolist()))
        
        df_f = df_cloze.copy()
        if sub != "全部": df_f = df_f[df_f['subject'] == sub]
        
        for idx, row in df_f.iterrows():
            raw = str(row['content'])
            ans = re.findall(r"\{\{(.*?)\}\}", raw)
            display = re.sub(r"\{\{.*?\}\}", " [ ______ ] ", raw)
            
            st.markdown(f"**考點：** {display}")
            if st.button(f"查看解答_{idx}", key=f"btn_{idx}"):
                st.success(f"答案：{', '.join(ans)}")
            st.write("---")
    else:
        st.info("💡 請確保 `cloze` 工作表內有內容 (欄位需包含 subject, content)")

with tabs[1]:
    st.title("📋 特工專屬深度任務備忘錄")
    
    # 新增事項區塊
    with st.expander("➕ 新增待辦事項 (含詳細備註)"):
        with st.form("add_task", clear_on_submit=True):
            t_title = st.text_input("任務名稱")
            t_detail = st.text_area("詳細備註/細節")
            t_date = st.date_input("日期")
            if st.form_submit_button("寫入密庫"):
                new_data = pd.DataFrame([{'title': t_title, 'detail': t_detail, 'target_date': str(t_date), 'status': '未開始'}])
                # 直接寫入並重新獲取
                updated_df = pd.concat([df_memo, new_data], ignore_index=True)
                conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=updated_df)
                st.success("寫入成功！")
                st.rerun() # 點擊後立刻重載頁面，保證看到新資料

    # 渲染清單
    if not df_memo.empty:
        for idx, row in df_memo.iterrows():
            st.markdown(f"""
                <div style="background:#fff; padding:15px; border-radius:10px; border-left: 5px solid #17A2B8; margin-bottom:10px;">
                    <h4>{row['title']}</h4>
                    <p><b>備註：</b> {row.get('detail', '無')}</p>
                    <small>📅 {row['target_date']}</small>
                </div>
            """, unsafe_allow_html=True)
