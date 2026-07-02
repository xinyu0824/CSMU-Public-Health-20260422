import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time
from datetime import datetime, date

# --- 1. 配置 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

st.set_page_config(page_title="🧠 特工觀測站", layout="wide")

# 初始化顯示答案暫存
if 'reveal_cloze' not in st.session_state:
    st.session_state.reveal_cloze = {}

# --- 數據安全工具 ---
def safe_str(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return ""
    return str(val).strip()

def is_overdue_or_today(date_str):
    try:
        task_date = datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
        return task_date <= date.today()
    except:
        return False

# --- 2. 數據連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_fresh_data():
    try:
        c = conn.read(spreadsheet=GSHEET_URL, worksheet="cloze")
        m = conn.read(spreadsheet=GSHEET_URL, worksheet="memo")
    except:
        c = pd.DataFrame(columns=['id', 'subject', 'unit', 'topic', 'content'])
        m = pd.DataFrame(columns=['id', 'title', 'detail', 'execute_date', 'deadline_date', 'status'])
    return c, m

df_cloze, df_memo = get_fresh_data()

# 自動補齊缺失欄位防呆機制
for col in ['id', 'subject', 'unit', 'topic', 'content']:
    if col not in df_cloze.columns: df_cloze[col] = ""
for col in ['id', 'title', 'detail', 'execute_date', 'deadline_date', 'status']:
    if col not in df_memo.columns: df_memo[col] = ""

# --- 3. 介面 ---
tabs = st.tabs(["🧠 精密考點挖空複習", "📋 深度任務備忘錄"])

# ==================== TAB 1: 挖空複習系統 ====================
with tabs[0]:
    st.title("🧠 醫學核心考點精密複習系統")
    
    # 🟢 1. 前端新增考點區塊
    with st.expander("➕ 建立新考點情報 (寫入資料庫)"):
        with st.form("add_cloze_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            i_sub = c1.text_input("科目 (例: 生理學)")
            i_unit = c2.text_input("單元 (例: 第二單元)")
            i_topic = c3.text_input("主題 (例: 腎臟結構)")
            i_content = st.text_area("知識點內容", placeholder="請輸入完整句子，並用 {{}} 標出要挖空的答案。例如：腎臟的基本功能單位是{{腎元}}。")
            
            if st.form_submit_button("寫入考點庫"):
                if i_content.strip() != "":
                    new_cloze = pd.DataFrame([{
                        'id': str(int(time.time())), 'subject': i_sub, 'unit': i_unit, 
                        'topic': i_topic, 'content': i_content
                    }])
                    df_cloze = pd.concat([df_cloze, new_cloze], ignore_index=True)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="cloze", data=df_cloze)
                    st.cache_data.clear()
                    st.success("✅ 考點寫入成功！")
                    st.rerun()
                else:
                    st.error("內容不可為空！")

    st.write("---")

    # 🟢 2. 考點複習面板
    if not df_cloze.empty and len(df_cloze[df_cloze['content'].astype(str).str.strip() != ""]) > 0:
        valid_cloze = df_cloze[df_cloze['content'].astype(str).str.strip() != ""]
        cols = st.columns(3)
        sub_list = ["全部"] + sorted([x for x in valid_cloze['subject'].dropna().unique() if safe_str(x)])
        sub = cols[0].selectbox("選擇科目", sub_list)
        
        df_f = valid_cloze.copy()
        if sub != "全部": df_f = df_f[df_f['subject'] == sub]
        
        unit_list = ["全部"] + sorted([x for x in df_f['unit'].dropna().unique() if safe_str(x)])
        unit = cols[1].selectbox("選擇單元", unit_list)
        if unit != "全部": df_f = df_f[df_f['unit'] == unit]
        
        for idx, row in df_f.iterrows():
            q_id = str(row['id'])
            raw = str(row['content'])
            ans = re.findall(r"\{\{(.*?)\}\}", raw)
            display = re.sub(r"\{\{.*?\}\}", " [ ______ ] ", raw)
            
            st.markdown(f"""
            <div style="background:#fff; padding:20px; border-radius:10px; border-left: 5px solid #4A90E2; margin-bottom:15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <span style="background:#E9ECEF; padding:3px 8px; border-radius:5px; font-size:0.8rem; color:#495057;">{safe_str(row['subject'])} > {safe_str(row['unit'])} > {safe_str(row['topic'])}</span><br><br>
                <span style="font-size:1.1rem; color:#333;">{display}</span>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"查看解答", key=f"btn_{q_id}"):
                st.session_state.reveal_cloze[q_id] = not st.session_state.reveal_cloze.get(q_id, False)
                
            if st.session_state.reveal_cloze.get(q_id, False):
                st.success(f"🔑 解答：{', '.join(ans)}")
                
            # 刪除按鈕
            if st.button("🗑️ 刪除此考點", key=f"del_cloze_{q_id}"):
                df_cloze = df_cloze[df_cloze['id'].astype(str) != q_id]
                conn.update(spreadsheet=GSHEET_URL, worksheet="cloze", data=df_cloze)
                st.cache_data.clear()
                st.rerun()
            st.write("---")
    else:
        st.info("💡 題庫目前為空，請使用上方按鈕新增考點！")

# ==================== TAB 2: 深度任務備忘錄 ====================
with tabs[1]:
    st.title("📋 特工專屬任務控制台")
    
    # 🟢 1. 新增事項區塊 (拆分執行日與死線)
    with st.expander("➕ 新增排程 (設定執行日與Deadline)"):
        with st.form("add_task", clear_on_submit=True):
            t_title = st.text_input("任務名稱")
            t_detail = st.text_area("詳細備註/細節")
            c1, c2 = st.columns(2)
            t_exec = c1.date_input("🔥 預計『執行』日期 (哪天要著手做)")
            t_dead = c2.date_input("📆 任務『死線』 (Deadline)")
            
            if st.form_submit_button("寫入任務控制台"):
                if t_title.strip() != "":
                    new_data = pd.DataFrame([{
                        'id': str(int(time.time())), 'title': t_title, 'detail': t_detail, 
                        'execute_date': str(t_exec), 'deadline_date': str(t_dead), 'status': '未完成'
                    }])
                    df_memo = pd.concat([df_memo, new_data], ignore_index=True)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                    st.cache_data.clear()
                    st.success("任務排程成功！")
                    st.rerun()
                else:
                    st.error("請輸入任務名稱！")

    # 🟢 2. 雙重視角切換 (Today vs Calendar)
    subtabs = st.tabs(["🔥 今日執行備忘錄 (Today)", "📆 全局死線行事曆 (Calendar)"])
    
    # 清理掉空白行
    active_memos = df_memo[df_memo['title'].astype(str).str.strip() != ""] if not df_memo.empty else pd.DataFrame()

    # --- 視角 A: 今日執行清單 ---
    with subtabs[0]:
        st.subheader("🔥 專注當下：今天該搞定的事")
        st.caption("顯示「執行日為今日(或已逾期)」且「尚未完成」的任務")
        
        if not active_memos.empty:
            # 篩選條件：執行日 <= 今天 且 status != '已完成'
            today_tasks = active_memos[
                active_memos['execute_date'].apply(is_overdue_or_today) & 
                (active_memos['status'] != '已完成')
            ]
            
            if today_tasks.empty:
                st.success("🎉 太棒了！今天排定的任務都已清理完畢，或是今天沒有排程。")
            else:
                for idx, row in today_tasks.iterrows():
                    r_id = str(row['id'])
                    st.markdown(f"""
                        <div style="background:#fff; padding:15px; border-radius:10px; border-left: 5px solid #FF5722; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <h4 style="margin-top:0;">{safe_str(row['title'])}</h4>
                            <p style="color:#555; font-size:0.95rem;"><b>細節：</b>{safe_str(row['detail'])}</p>
                            <span style="background:#DC3545; color:white; padding:2px 8px; border-radius:12px; font-size:0.8rem;">🚨 死線: {safe_str(row['deadline_date'])}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        if st.button("✅ 標記完成", key=f"done_today_{r_id}"):
                            df_memo.loc[df_memo['id'].astype(str) == r_id, 'status'] = '已完成'
                            conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                            st.cache_data.clear(); st.rerun()
                    with c2:
                        if st.button("🗑️ 刪除", key=f"del_today_{r_id}"):
                            df_memo = df_memo[df_memo['id'].astype(str) != r_id]
                            conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                            st.cache_data.clear(); st.rerun()
                    st.write("---")
        else:
            st.info("尚無任何排程任務。")

    # --- 視角 B: 全局死線行事曆 ---
    with subtabs[1]:
        st.subheader("📆 全局視角：Deadline 觀測站")
        
        if not active_memos.empty:
            # 建立日曆選擇器來篩選特定日期的 Deadline
            selected_date = st.date_input("選擇日期以查看當天到期的任務", value=date.today())
            
            target_tasks = active_memos[active_memos['deadline_date'] == str(selected_date)]
            
            st.markdown(f"#### 📍 {selected_date} 的死線任務")
            if target_tasks.empty:
                st.write("這天沒有即將到期的死線，你可以鬆一口氣。")
            else:
                for idx, row in target_tasks.iterrows():
                    r_id = str(row['id'])
                    status_color = "#28A745" if row['status'] == '已完成' else "#FFC107"
                    
                    st.markdown(f"""
                        <div style="background:#fff; padding:15px; border-radius:10px; border-left: 5px solid {status_color}; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <div style="display:flex; justify-content:space-between;">
                                <h4 style="margin-top:0;">{safe_str(row['title'])}</h4>
                                <span style="background:{status_color}; color:{'white' if status_color=='#28A745' else '#333'}; padding:2px 8px; border-radius:12px; font-size:0.8rem; height:fit-content;">{safe_str(row['status'])}</span>
                            </div>
                            <p style="color:#555; font-size:0.95rem;"><b>細節：</b>{safe_str(row['detail'])}</p>
                            <span style="background:#17A2B8; color:white; padding:2px 8px; border-radius:12px; font-size:0.8rem;">預計執行日: {safe_str(row['execute_date'])}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 在全域視角依然可以刪除
                    if st.button("🗑️ 刪除此任務", key=f"del_cal_{r_id}"):
                        df_memo = df_memo[df_memo['id'].astype(str) != r_id]
                        conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                        st.cache_data.clear(); st.rerun()
                    st.write("---")
        else:
            st.info("尚無任何排程任務。")
