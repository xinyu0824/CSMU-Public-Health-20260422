import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time
from datetime import datetime, date

# --- 1. 配置 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

st.set_page_config(page_title="🧠 特工觀測站", layout="wide")

# 初始化 Session State (包含編輯模式追蹤)
if 'reveal_cloze' not in st.session_state:
    st.session_state.reveal_cloze = {}
if 'confirm_clear_today' not in st.session_state:
    st.session_state.confirm_clear_today = False
if 'edit_memo_id' not in st.session_state:
    st.session_state.edit_memo_id = None  # 追蹤當前正在編輯哪個任務

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
        m = pd.DataFrame(columns=['id', 'title', 'detail', 'execute_date', 'deadline_date', 'status', 'importance', 'difficulty'])
    return c, m

df_cloze, df_memo = get_fresh_data()

# 自動補齊缺失欄位防呆機制 (加入標籤欄位)
for col in ['id', 'subject', 'unit', 'topic', 'content']:
    if col not in df_cloze.columns: df_cloze[col] = ""
for col in ['id', 'title', 'detail', 'execute_date', 'deadline_date', 'status', 'importance', 'difficulty']:
    if col not in df_memo.columns: df_memo[col] = ""

# --- 3. 酷炫樣式與隱形墨水 CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    
    /* 🟢 行內挖空點擊解鎖魔法 */
    .cloze-box {
        background-color: #4A90E2; 
        color: #4A90E2; 
        border-radius: 4px; padding: 2px 8px; cursor: pointer; user-select: none;
        outline: none; transition: all 0.2s ease-in-out; font-weight: bold;
    }
    .cloze-box:focus, .cloze-box:active {
        background-color: #FFF3E0; color: #D32F2F !important; border: 1px solid #D32F2F;
    }
    .cloze-box.show-all {
        background-color: #FFF3E0; color: #D32F2F !important; border: 1px solid #D32F2F;
    }
    
    .todo-card { background:#fff; padding:15px; border-radius:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom:10px; }
    .strike-text { text-decoration: line-through; color: #999; }
    .tag-imp { background-color: #FFF0F2; color: #D32F2F; border: 1px solid #FFCDD2; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight:bold; margin-right: 5px; }
    .tag-diff { background-color: #F3E5F5; color: #4A148C; border: 1px solid #E1BEE7; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight:bold; margin-right: 5px; }
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
            is_reveal_all = st.session_state.reveal_cloze.get(q_id, False)
            css_class = "cloze-box show-all" if is_reveal_all else "cloze-box"
            display_text = re.sub(r"\{\{(.*?)\}\}", rf'<span tabindex="0" class="{css_class}">\1</span>', raw)
            
            st.markdown(f"""
            <div style="background:#fff; padding:20px; border-radius:10px; border-left: 5px solid #4A90E2; margin-bottom:10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <span style="background:#E9ECEF; padding:3px 8px; border-radius:5px; font-size:0.8rem; color:#495057;">{safe_str(row['subject'])} > {safe_str(row['unit'])} > {safe_str(row['topic'])}</span><br><br>
                <span style="font-size:1.15rem; color:#333; line-height: 1.8;">{display_text}</span>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns([2, 8])
            with col_a:
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

    # --- 選項清單 ---
    opt_imp = ["無", "🔥 極重要", "⭐ 重要"]
    opt_diff = ["無", "💀 地獄難度", "💪 具挑戰性"]

    # --- 視角 A: 今日執行清單 ---
    with subtabs[0]:
        st.subheader("📝 今日專屬小紙條 (Today Only)")
        st.caption("隨手記下的雜事，完成後打勾，下班前一鍵清除乾淨！")
        
        # 🟢 1. 新增今日限定任務 (加入動態標籤選擇)
        with st.form("add_today_task", clear_on_submit=True):
            cols = st.columns([3, 1, 1, 1])
            t_today_title = cols[0].text_input("新增今日瑣事", placeholder="例如：印講義、回覆教授信件...", label_visibility="collapsed")
            t_imp = cols[1].selectbox("重要性", opt_imp, label_visibility="collapsed")
            t_diff = cols[2].selectbox("難易度", opt_diff, label_visibility="collapsed")
            
            if cols[3].form_submit_button("➕ 新增"):
                if t_today_title.strip() != "":
                    new_data = pd.DataFrame([{
                        'id': str(int(time.time())), 'title': t_today_title, 'detail': "", 
                        'execute_date': str(date.today()), 'deadline_date': "今日限定", 'status': '未完成',
                        'importance': t_imp, 'difficulty': t_diff
                    }])
                    df_memo = pd.concat([df_memo, new_data], ignore_index=True)
                    conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                    st.cache_data.clear(); st.rerun()

        # 🟢 2. 渲染今日小紙條清單 (加入行內編輯機制)
        today_memos = active_memos[active_memos['deadline_date'] == "今日限定"] if not active_memos.empty else pd.DataFrame()
        
        if not today_memos.empty:
            for idx, r in today_memos.iterrows():
                r_id = str(r['id'])
                is_done = (safe_str(r['status']) == "已完成")
                
                # 判斷目前是否處於「編輯模式」
                if st.session_state.edit_memo_id == r_id:
                    with st.form(f"edit_form_{r_id}"):
                        st.write(f"✏️ **編輯任務**")
                        e_title = st.text_input("任務名稱", value=safe_str(r['title']))
                        e_detail = st.text_area("詳細備註", value=safe_str(r['detail']))
                        c_e1, c_e2 = st.columns(2)
                        
                        curr_imp = safe_str(r.get('importance', '無')); curr_imp = curr_imp if curr_imp in opt_imp else "無"
                        curr_diff = safe_str(r.get('difficulty', '無')); curr_diff = curr_diff if curr_diff in opt_diff else "無"
                        
                        e_imp = c_e1.selectbox("重要性", opt_imp, index=opt_imp.index(curr_imp))
                        e_diff = c_e2.selectbox("難易度", opt_diff, index=opt_diff.index(curr_diff))
                        
                        c_btn1, c_btn2 = st.columns(2)
                        if c_btn1.form_submit_button("💾 儲存修改", type="primary"):
                            df_memo.loc[df_memo['id'].astype(str) == r_id, 'title'] = e_title
                            df_memo.loc[df_memo['id'].astype(str) == r_id, 'detail'] = e_detail
                            df_memo.loc[df_memo['id'].astype(str) == r_id, 'importance'] = e_imp
                            df_memo.loc[df_memo['id'].astype(str) == r_id, 'difficulty'] = e_diff
                            conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                            st.session_state.edit_memo_id = None # 解除編輯模式
                            st.cache_data.clear(); st.rerun()
                        if c_btn2.form_submit_button("❌ 取消"):
                            st.session_state.edit_memo_id = None
                            st.rerun()
                else:
                    # 正常顯示模式
                    cc1, cc2, cc3 = st.columns([0.5, 4, 1.5])
                    chk = cc1.checkbox("✔", value=is_done, key=f"chk_today_{r_id}", label_visibility="collapsed")
                    if chk != is_done:
                        df_memo.loc[df_memo['id'].astype(str) == r_id, 'status'] = '已完成' if chk else '未完成'
                        conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                        st.cache_data.clear(); st.rerun()
                    
                    # 處理標籤顯示
                    tag_html = ""
                    imp_val = safe_str(r.get('importance', '無'))
                    diff_val = safe_str(r.get('difficulty', '無'))
                    if imp_val != "無" and imp_val != "": tag_html += f"<span class='tag-imp'>{imp_val}</span>"
                    if diff_val != "無" and diff_val != "": tag_html += f"<span class='tag-diff'>{diff_val}</span>"
                    
                    title_txt = f"<span class='strike-text'>{safe_str(r['title'])}</span>" if is_done else f"<span style='font-size:1.1rem;'>{safe_str(r['title'])}</span>"
                    cc2.markdown(f"{tag_html} {title_txt}", unsafe_allow_html=True)
                    
                    # 編輯與刪除按鈕
                    bc1, bc2 = cc3.columns(2)
                    if bc1.button("✏️", key=f"edit_btn_{r_id}"):
                        st.session_state.edit_memo_id = r_id
                        st.rerun()
                    if bc2.button("🗑️", key=f"del_t_{r_id}"):
                        df_memo = df_memo[df_memo['id'].astype(str) != r_id]
                        conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                        st.cache_data.clear(); st.rerun()
            
            st.write("---")
            # 雙重防呆：一鍵清除全部小紙條
            if not st.session_state.confirm_clear_today:
                if st.button("🧹 一鍵清空所有今日小紙條", use_container_width=True):
                    st.session_state.confirm_clear_today = True
                    st.rerun()
            else:
                st.warning("⚠️ 確定要清除所有今日小紙條嗎？無法復原喔！")
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

    # --- 視角 B: 全局死線行事曆 ---
    with subtabs[1]:
        st.subheader("📆 全局視角：Deadline 觀測站")
        
        with st.expander("➕ 新增大型專案/作業 (設定執行日與死線)"):
            with st.form("add_global_task", clear_on_submit=True):
                t_title = st.text_input("專案/作業名稱")
                t_detail = st.text_area("詳細備註/細節")
                c1, c2, c3, c4 = st.columns(4)
                t_exec = c1.date_input("🔥 預計執行日期")
                t_dead = c2.date_input("📆 任務死線 (Deadline)")
                t_imp_g = c3.selectbox("重要性", opt_imp)
                t_diff_g = c4.selectbox("難易度", opt_diff)
                
                if st.form_submit_button("寫入全局行事曆"):
                    if t_title.strip() != "":
                        new_data = pd.DataFrame([{
                            'id': str(int(time.time())), 'title': t_title, 'detail': t_detail, 
                            'execute_date': str(t_exec), 'deadline_date': str(t_dead), 'status': '未完成',
                            'importance': t_imp_g, 'difficulty': t_diff_g
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
                    
                    if st.session_state.edit_memo_id == r_id:
                        with st.form(f"edit_form_g_{r_id}"):
                            st.write(f"✏️ **編輯專案**")
                            e_title = st.text_input("任務名稱", value=safe_str(row['title']))
                            e_detail = st.text_area("詳細備註", value=safe_str(row['detail']))
                            c_e1, c_e2 = st.columns(2)
                            curr_imp = safe_str(row.get('importance', '無')); curr_imp = curr_imp if curr_imp in opt_imp else "無"
                            curr_diff = safe_str(row.get('difficulty', '無')); curr_diff = curr_diff if curr_diff in opt_diff else "無"
                            e_imp = c_e1.selectbox("重要性", opt_imp, index=opt_imp.index(curr_imp))
                            e_diff = c_e2.selectbox("難易度", opt_diff, index=opt_diff.index(curr_diff))
                            
                            c_btn1, c_btn2 = st.columns(2)
                            if c_btn1.form_submit_button("💾 儲存修改", type="primary"):
                                df_memo.loc[df_memo['id'].astype(str) == r_id, 'title'] = e_title
                                df_memo.loc[df_memo['id'].astype(str) == r_id, 'detail'] = e_detail
                                df_memo.loc[df_memo['id'].astype(str) == r_id, 'importance'] = e_imp
                                df_memo.loc[df_memo['id'].astype(str) == r_id, 'difficulty'] = e_diff
                                conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                                st.session_state.edit_memo_id = None
                                st.cache_data.clear(); st.rerun()
                            if c_btn2.form_submit_button("❌ 取消"):
                                st.session_state.edit_memo_id = None
                                st.rerun()
                    else:
                        status_color = "#28A745" if row['status'] == '已完成' else "#FFC107"
                        tag_html = ""
                        imp_val = safe_str(row.get('importance', '無'))
                        diff_val = safe_str(row.get('difficulty', '無'))
                        if imp_val != "無" and imp_val != "": tag_html += f"<span class='tag-imp'>{imp_val}</span>"
                        if diff_val != "無" and diff_val != "": tag_html += f"<span class='tag-diff'>{diff_val}</span>"
                        
                        st.markdown(f"""
                            <div style="background:#fff; padding:15px; border-radius:10px; border-left: 5px solid {status_color}; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                                <div style="display:flex; justify-content:space-between; align-items: center;">
                                    <h4 style="margin-top:0;">{tag_html} {safe_str(row['title'])}</h4>
                                    <span style="background:{status_color}; color:{'white' if status_color=='#28A745' else '#333'}; padding:2px 8px; border-radius:12px; font-size:0.8rem; height:fit-content;">{safe_str(row['status'])}</span>
                                </div>
                                <p style="color:#555; font-size:0.95rem;"><b>細節：</b>{safe_str(row['detail'])}</p>
                                <span style="background:#17A2B8; color:white; padding:2px 8px; border-radius:12px; font-size:0.8rem;">預計執行日: {safe_str(row['execute_date'])}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        cc1, cc2, cc3 = st.columns([1, 1, 4])
                        btn_txt = "復原未完成" if row['status'] == '已完成' else "✅ 標記完成"
                        if cc1.button(btn_txt, key=f"done_cal_{r_id}"):
                            df_memo.loc[df_memo['id'].astype(str) == r_id, 'status'] = '未完成' if row['status'] == '已完成' else '已完成'
                            conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                            st.cache_data.clear(); st.rerun()
                        if cc2.button("✏️ 修改", key=f"edit_g_{r_id}"):
                            st.session_state.edit_memo_id = r_id
                            st.rerun()
                        if cc3.button("🗑️ 刪除", key=f"del_cal_{r_id}"):
                            df_memo = df_memo[df_memo['id'].astype(str) != r_id]
                            conn.update(spreadsheet=GSHEET_URL, worksheet="memo", data=df_memo)
                            st.cache_data.clear(); st.rerun()
                        st.write("---")
