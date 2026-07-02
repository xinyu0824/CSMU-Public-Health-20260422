import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time
from datetime import datetime, date

# --- 1. 配置 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

st.set_page_config(page_title="🧠 特工觀測站", layout="wide")

# 初始化顯示答案暫存與確認清除暫存
if 'reveal_cloze' not in st.session_state:
    st.session_state.reveal_cloze = {}
if 'confirm_clear_today' not in st.session_state:
    st.session_state.confirm_clear_today = False

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

for col in ['id', 'subject', 'unit', 'topic', 'content']:
    if col not in df_cloze.columns: df_cloze[col] = ""
for col in ['id', 'title', 'detail', 'execute_date', 'deadline_date', 'status']:
    if col not in df_memo.columns: df_memo[col] = ""

# --- 3. 酷炫樣式與隱形墨水 CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    
    /* 🟢 行內挖空點擊解鎖魔法 */
    .cloze-box {
        background-color: #4A90E2; 
        color: #4A90E2; /* 字體與背景同色，完美隱藏 */
        border-radius: 4px;
        padding: 2px 8px;
        cursor: pointer;
        user-select: none;
        outline: none; /* 移除點擊藍框 */
        transition: all 0.2s ease-in-out;
        font-weight: bold;
    }
    .cloze-box:focus, .cloze-box:active {
        background-color: #FFF3E0;
        color: #D32F2F !important; /* 點擊後顯示紅色解答 */
        border: 1px solid #D32F2F;
    }
    .cloze-box.show-all {
        background-color: #FFF3E0;
        color: #D32F2F !important;
        border: 1px solid #D32F2F;
    }
    
    .todo-card { background:#fff; padding:15px; border-radius:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom:10px; }
    .strike-text { text-decoration: line-through; color: #999; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 介面 ---
tabs = st.tabs(["🧠 精密考點挖空複習", "📋 深度任務備忘錄"])

# ==================== TAB 1: 挖空複習系統 ====================
with tabs[0]:
    st.title("🧠 醫學核心考點精密複習系統")
    
    with st.expander("➕ 建立新考點情報 (寫入資料庫)"):
        with st.form("add_cloze_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            i_sub = c1.text_input("科目 (例: 生理學)")
            i_unit = c2.text_input("單元 (例: 第二單元)")
            i_topic = c3.text_input("主題 (例: 腎臟結構)")
            i_content = st.text_area("知識點內容", placeholder="用 {{}} 標出要挖空的答案。例如：腎臟的基本單位是{{腎元}}。")
            
            if st.form_submit_button("寫入考點庫"):
                if i_content.strip() != "":
                    new_cloze = pd.DataFrame([{
                        'id': str(int(time.time())), 'subject': i_sub, 'unit': i_unit, 
                        'topic': i_topic, 'content': i_content
                    }])
                    df_cloze = pd.concat([df_cloze, new_cloze], ignore_index=True)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="cloze", data=df_cloze)
                    st.cache_data.clear(); st.success("✅ 考點寫入成功！"); st.rerun()

    st.write("---")

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
            
            # 🟢 判斷是否按下了一次公佈解答
            is_reveal_all = st.session_state.reveal_cloze.get(q_id, False)
            css_class = "cloze-box show-all" if is_reveal_all else "cloze-box"
            
            # 🟢 核心魔術：用帶有 tabindex 的 span 取代，達成點擊即顯示的效果！
            display_text = re.sub(r"\{\{(.*?)\}\}", rf'<span tabindex="0" class="{css_class}">\1</span>', raw)
            
            st.markdown(f"""
            <div style="background:#fff; padding:20px; border-radius:10px; border-left: 5px solid #4A90E2; margin-bottom:10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <span style="background:#E9ECEF; padding:3px 8px; border-radius:5px; font-size:0.8rem; color:#495057;">{safe_str(row['subject'])} > {safe_str(row['unit'])} > {safe_str(row['topic'])}</span><br><br>
                <span style="font-size:1.15rem; color:#333; line-height: 1.8;">{display_text}</span>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns([2, 8])
            with col_a:
                # 保留一鍵公佈全部答案的功能
                btn_text = "🙈 隱藏解答" if is_reveal_all else "💡 一鍵公佈"
                if st.button(btn_text, key=f"btn_{q_id}"):
                    st.session_state.reveal_cloze[q_id] = not is_reveal_all
                    st.rerun()
            with col_b:
                if st.button("🗑️ 刪除", key=f"del_cloze_{q_id}"):
                    df_cloze = df_cloze[df_cloze['id'].astype(str) != q_id]
                    conn.update(spreadsheet=GSHEET_URL, worksheet="cloze", data=df_cloze)
                    st.cache_data.clear(); st.rerun()
            st.write("---")

# ==================== TAB 2: 深度任務備忘錄 ====================
with tabs[1]:
    st.title("📋 特工專屬任務控制台")
    
    subtabs = st.tabs(["🔥 今日執行備忘錄 (Today)", "📆 全局死線行事曆 (Calendar)"])
    active_memos = df_memo[df_memo['title'].astype(str).str.strip() != ""] if not df_memo.empty else pd.DataFrame()

    # --- 視角 A: 今日執行清單 ---
    with subtabs[0]:
        st.subheader("📝 今日專屬小紙條 (Today Only)")
        st.caption("隨手記下的雜事，不汙染全局行事曆。未完成隔日也可繼續，完成就清掉！")
        
        # 1. 快速新增今日限定任務
        with st.form("add_today_task", clear_on_submit=True):
            cols = st.columns([4, 1])
            t_today_title = cols[0].text_input("新增今日瑣事", placeholder="例如：去超商取貨、回覆組員訊息...", label_visibility="collapsed")
            if cols[1].form_submit_button("➕ 新增"):
                if t_today_title.strip() != "":
                    new_data = pd.DataFrame([{
                        'id': str(int(time.time())), 'title': t_today_title, 'detail': "", 
                        'execute_date': str(date.today()), 'deadline_date': "今日限定", 'status': '未完成'
                    }])
                    df_memo = pd.concat([df_memo, new_data], ignore_index=True)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                    st.cache_data.clear(); st.rerun()

        # 2. 渲染今日小紙條清單
        today_memos = active_memos[active_memos['deadline_date'] == "今日限定"] if not active_memos.empty else pd.DataFrame()
        
        if not today_memos.empty:
            for idx, r in today_memos.iterrows():
                r_id = str(r['id'])
                is_done = (safe_str(r['status']) == "已完成")
                
                cc1, cc2, cc3 = st.columns([0.5, 4.5, 1])
                # 勾選框：快速劃記
                chk = cc1.checkbox("✔", value=is_done, key=f"chk_today_{r_id}", label_visibility="collapsed")
                if chk != is_done:
                    df_memo.loc[df_memo['id'].astype(str) == r_id, 'status'] = '已完成' if chk else '未完成'
                    conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                    st.cache_data.clear(); st.rerun()
                
                # 任務名稱：完成後加上刪除線
                title_html = f"<span class='strike-text'>{safe_str(r['title'])}</span>" if is_done else f"<span style='font-size:1.1rem;'>{safe_str(r['title'])}</span>"
                cc2.markdown(title_html, unsafe_allow_html=True)
                
                # 單一刪除鍵
                if cc3.button("🗑️", key=f"del_t_{r_id}"):
                    df_memo = df_memo[df_memo['id'].astype(str) != r_id]
                    conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                    st.cache_data.clear(); st.rerun()
            
            st.write("---")
            # 3. 雙重防呆：一鍵清除全部小紙條
            if not st.session_state.confirm_clear_today:
                if st.button("🧹 一鍵清空所有今日小紙條", use_container_width=True):
                    st.session_state.confirm_clear_today = True
                    st.rerun()
            else:
                st.warning("⚠️ 確定要清除所有今日小紙條嗎？這將無法復原喔！")
                btn1, btn2 = st.columns(2)
                if btn1.button("✅ 確定清空", type="primary", use_container_width=True):
                    df_memo = df_memo[df_memo['deadline_date'] != "今日限定"]
                    conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                    st.session_state.confirm_clear_today = False
                    st.cache_data.clear(); st.rerun()
                if btn2.button("❌ 點錯了，取消", use_container_width=True):
                    st.session_state.confirm_clear_today = False
                    st.rerun()
        else:
            st.success("🎉 今日紙條已清空！")

        # 4. 顯示全局行事曆中「今天該執行」的正式任務
        st.subheader("📌 全局專案：今日應執行進度")
        global_today = active_memos[(active_memos['deadline_date'] != "今日限定") & active_memos['execute_date'].apply(is_overdue_or_today)] if not active_memos.empty else pd.DataFrame()
        if not global_today.empty:
            for idx, row in global_today.iterrows():
                is_done = (safe_str(row['status']) == '已完成')
                bg_color = "#E8F5E9" if is_done else "#fff"
                border_color = "#28A745" if is_done else "#FF5722"
                title_format = f"<s style='color:#999;'>{safe_str(row['title'])}</s>" if is_done else safe_str(row['title'])
                
                st.markdown(f"""
                    <div style="background:{bg_color}; padding:15px; border-radius:10px; border-left: 5px solid {border_color}; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <h4 style="margin-top:0;">{title_format}</h4>
                        <p style="color:#555; font-size:0.95rem;"><b>細節：</b>{safe_str(row['detail'])}</p>
                        <span style="background:#DC3545; color:white; padding:2px 8px; border-radius:12px; font-size:0.8rem;">🚨 死線: {safe_str(row['deadline_date'])}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("今天沒有被排定的全局專案要推進。")

    # --- 視角 B: 全局死線行事曆 ---
    with subtabs[1]:
        st.subheader("📆 全局視角：Deadline 觀測站")
        
        with st.expander("➕ 新增大型專案/作業 (設定執行日與死線)"):
            with st.form("add_global_task", clear_on_submit=True):
                t_title = st.text_input("專案/作業名稱")
                t_detail = st.text_area("詳細備註/細節")
                c1, c2 = st.columns(2)
                t_exec = c1.date_input("🔥 預計『執行』日期")
                t_dead = c2.date_input("📆 任務『死線』 (Deadline)")
                
                if st.form_submit_button("寫入全局行事曆"):
                    if t_title.strip() != "":
                        new_data = pd.DataFrame([{
                            'id': str(int(time.time())), 'title': t_title, 'detail': t_detail, 
                            'execute_date': str(t_exec), 'deadline_date': str(t_dead), 'status': '未完成'
                        }])
                        df_memo = pd.concat([df_memo, new_data], ignore_index=True)
                        conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                        st.cache_data.clear(); st.success("專案排程成功！"); st.rerun()

        if not active_memos.empty:
            selected_date = st.date_input("選擇日期以查看當天到期的任務", value=date.today())
            target_tasks = active_memos[(active_memos['deadline_date'] == str(selected_date)) & (active_memos['deadline_date'] != "今日限定")]
            
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
                    
                    cc1, cc2 = st.columns([1, 5])
                    with cc1:
                        btn_txt = "復原未完成" if row['status'] == '已完成' else "✅ 標記完成"
                        if st.button(btn_txt, key=f"done_cal_{r_id}"):
                            df_memo.loc[df_memo['id'].astype(str) == r_id, 'status'] = '未完成' if row['status'] == '已完成' else '已完成'
                            conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                            st.cache_data.clear(); st.rerun()
                    with cc2:
                        if st.button("🗑️ 刪除", key=f"del_cal_{r_id}"):
                            df_memo = df_memo[df_memo['id'].astype(str) != r_id]
                            conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                            st.cache_data.clear(); st.rerun()
                    st.write("---")
