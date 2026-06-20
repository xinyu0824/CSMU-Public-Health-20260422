import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time
from datetime import datetime, date

# --- 1. 配置與強效初始化 ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1cxSA5qvLKmu2FjYR2xZI3fdSocXS_VCOXYUdk6C0YVA/edit?usp=sharing"

st.set_page_config(page_title="🧠 特工觀測站：終極複習備忘終端", layout="wide")

# 初始化顯示答案的暫存
if 'reveal_cloze' not in st.session_state:
    st.session_state.reveal_cloze = {}

# --- 數據安全工具 ---
def safe_str(val):
    if pd.isna(val) or str(val).strip().lower() == "nan": return ""
    return str(val).strip()

def safe_int(val):
    try:
        s = safe_str(val)
        return int(float(s)) if s != "" else 0
    except: return 0

# --- 2. 科技感流線樣式 ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    h1, h2, h3, p, label { color: #4A4A4A !important; font-family: 'Noto Sans TC', sans-serif; }
    .cloze-card { background-color: #FFFFFF; padding: 25px; border-radius: 15px; border-left: 6px solid #4A90E2; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; font-size: 1.15rem; line-height: 1.8; }
    .todo-card { background-color: #FFFFFF; padding: 20px; border-radius: 12px; border: 1px solid #E6E6E1; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; color: white !important; margin-right: 5px; margin-bottom: 5px; }
    .badge-high { background-color: #DC3545; }
    .badge-mid { background-color: #FFC107; color: #4A4A4A !important; }
    .badge-low { background-color: #28A745; }
    .badge-cat { background-color: #6C757D; }
    .badge-date { background-color: #17A2B8; }
    .dependency-text { color: #8C8C8C; font-size: 0.85rem; font-style: italic; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 雲端資料庫連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1)
def load_data():
    try:
        c = conn.read(spreadsheet=GSHEET_URL, worksheet="cloze")
        m = conn.read(spreadsheet=GSHEET_URL, worksheet="memo")
        return c, m
    except:
        return pd.DataFrame(columns=['id', 'subject', 'unit', 'topic', 'content']), pd.DataFrame(columns=['id', 'title', 'detail', 'category', 'urgency', 'importance', 'status', 'parent_id', 'order_num', 'target_date'])

df_cloze, df_memo = load_data()

# 確保基礎欄位存在（新增了科目、單元、主題與自訂日期欄位）
for col in ['id', 'subject', 'unit', 'topic', 'content']:
    if col not in df_cloze.columns: df_cloze[col] = ""
for col in ['id', 'title', 'detail', 'category', 'urgency', 'importance', 'status', 'parent_id', 'order_num', 'target_date']:
    if col not in df_memo.columns: df_memo[col] = ""

# --- 4. 主介面分頁架構 ---
tabs = st.tabs(["🧠 精密考點挖空複習", "📋 深度任務備忘錄"])

# ==================== TAB 1: 挖空複習系統 ====================
with tabs[0]:
    st.title("🧠 醫學核心考點精密複習系統")
    
    if df_cloze.empty or len(df_cloze) == 0:
        st.info("💡 目前題庫空空如也，請先去 Google Sheets 的 `cloze` 工作表添加含有 {{關鍵字}} 的句子唷！")
    else:
        # 🟢 階層式精密連動篩選面板
        st.write("### 🔍 考點精準打擊篩選")
        c1, c2, c3 = st.columns(3)
        
        # 1. 科目篩選
        subject_list = ["全部科目"] + sorted([x for x in df_cloze['subject'].dropna().unique() if safe_str(x) != ""])
        with c1:
            sel_subject = st.selectbox("選擇醫學科目", subject_list)
        
        df_filtered = df_cloze.copy()
        if sel_subject != "全部科目":
            df_filtered = df_filtered[df_filtered['subject'] == sel_subject]
            
        # 2. 單元篩選
        unit_list = ["全部單元"] + sorted([x for x in df_filtered['unit'].dropna().unique() if safe_str(x) != ""])
        with c2:
            sel_unit = st.selectbox("選擇講義單元", unit_list)
            
        if sel_unit != "全部單元":
            df_filtered = df_filtered[df_filtered['unit'] == sel_unit]
            
        # 3. 主題篩選
        topic_list = ["全部主題"] + sorted([x for x in df_filtered['topic'].dropna().unique() if safe_str(x) != ""])
        with c3:
            sel_topic = st.selectbox("選擇知識點主題", topic_list)
            
        if sel_topic != "全部主題":
            df_filtered = df_filtered[df_filtered['topic'] == sel_topic]

        st.write("---")
        
        # 渲染篩選後的題目
        if df_filtered.empty:
            st.warning("⚠️ 目前選定的分類下沒有任何考點，請調整篩選條件。")
        else:
            for idx, row in df_filtered.iterrows():
                q_id = str(row['id'])
                raw_content = safe_str(row['content'])
                if not raw_content: continue
                
                answers = re.findall(r"\{\{(.*?)\}\}", raw_content)
                display_text = re.sub(r"\{\{.*?\}\}", " [ ______ ] ", raw_content)
                
                with st.container():
                    # 顯示該題目的階層標籤，一眼看懂進度
                    st.markdown(f"""
                        <span class="badge badge-cat">{row['subject']}</span>
                        <span class="badge badge-mid">{row['unit']}</span>
                        <span class="badge" style="background-color:#4A90E2;">{row['topic']}</span>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f'<div class="cloze-card"><b>考點：</b> {display_text}</div>', unsafe_allow_html=True)
                    
                    # 動態生成填空輸入框
                    cols = st.columns(max(1, len(answers)))
                    for i, ans in enumerate(answers):
                        with cols[i]:
                            st.text_input(f"填空輸入 ({i+1})", key=f"guess_{q_id}_{i}")
                    
                    # 查看答案控制
                    col_btn, col_ans = st.columns([1, 5])
                    with col_btn:
                        if st.button("查看解答", key=f"btn_show_{q_id}"):
                            st.session_state.reveal_cloze[q_id] = True
                    with col_ans:
                        if st.session_state.reveal_cloze.get(q_id, False):
                            ans_str = " │ ".join([f"({i+1}) {a}" for i, a in enumerate(answers)])
                            st.success(f"🔑 正確解答：{ans_str}")
                    st.write("---")

# ==================== TAB 2: 深度任務備忘錄 ====================
with tabs[1]:
    st.title("📋 特工專屬深度任務相依備忘錄")
    
    # --- 新增任務區塊 ---
    with st.expander("➕ 新增極詳細待辦事項（支援自訂時間軸）"):
        with st.form("add_task_form"):
            t_title = st.text_input("任務或作業名稱*", placeholder="寫下要做的事...")
            t_detail = st.text_area("行動精密細節 (詳細寫下執行步驟，更有動力執行！)", placeholder="例如：1.先查閱3篇文獻 2.跟組員確認框架...")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                t_cat = st.selectbox("所屬群組 (分組)", ["課業修讀", "系學會", "GDGOC CSMU", "私人生活", "其他工作"])
            with c2:
                t_urg = st.radio("急迫性", ["高", "中", "低"], horizontal=True)
            with c3:
                t_imp = st.radio("重要性", ["高", "中", "低"], horizontal=True)
            with c4:
                # 🟢 使用者自定義日期時間軸（Date Input）
                t_date = st.date_input("自訂時間軸 / Deadline", value=date.today())
                
            # 相依性接續選擇
            parent_options = {"無前置任務 (獨立事件)": ""}
            for _, r in df_memo.iterrows():
                if safe_str(r['title']) and safe_str(r['status']) != "已完成":
                    parent_options[f"【{r['category']}】{r['title']}"] = str(r['id'])
                    
            t_parent = st.selectbox("🔗 前置接續任務 (必須先做完哪一項，才能執行這件事？)", list(parent_options.keys()))
            
            submit_task = st.form_submit_input("💾 寫入精密密庫", use_container_width=True)
            
            if submit_task and t_title.strip() != "":
                new_id = str(int(time.time()))
                max_order = safe_int(df_memo['order_num'].max()) if not df_memo.empty else 0
                
                new_row = pd.DataFrame([{
                    'id': new_id, 'title': t_title, 'detail': t_detail,
                    'category': t_cat, 'urgency': t_urg, 'importance': t_imp,
                    'status': "未開始", 'parent_id': parent_options[t_parent],
                    'order_num': max_order + 1,
                    'target_date': str(t_date) # 儲存自訂日期字串
                }])
                
                df_memo = pd.concat([df_memo, new_row], ignore_index=True)
                conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_memo) # 注意：此處依原本工作表名稱寫入
                st.cache_data.clear()
                st.success(f"✅ 任務【{t_title}】已排入時間軸序列！")
                st.rerun()

    # --- 備忘錄主面板過濾器 ---
    st.write("### 🔍 觀測視窗篩選")
    f_cat = st.multiselect("按群組篩選", ["課業修讀", "系學會", "GDGOC CSMU", "私人生活", "其他工作"], default=["課業修讀", "系學會", "GDGOC CSMU", "私人生活", "其他工作"])
    f_status = st.multiselect("按狀態顯示", ["未開始", "進行中", "已完成"], default=["未開始", "進行中"])
    
    if not df_memo.empty:
        df_display = df_memo[df_memo['category'].isin(f_cat) & df_memo['status'].isin(f_status)].copy()
        df_display['order_num'] = df_display['order_num'].apply(safe_int)
        df_display = df_display.sort_values(by='order_num', ascending=True)
    else:
        df_display = pd.DataFrame()

    # --- 任務渲染清單 ---
    st.write("---")
    if df_display.empty:
        st.info("🌟 當前篩選條件下沒有待辦事項。妳的版面很乾淨！")
    else:
        for idx_disp, current_task in df_display.iterrows():
            t_id = str(current_task['id'])
            p_id = safe_str(current_task['parent_id'])
            t_date_val = safe_str(current_task['target_date']) if safe_str(current_task['target_date']) != "" else "未設定"
            
            is_blocked = False
            parent_title = ""
            if p_id != "":
                parent_match = df_memo[df_memo['id'].astype(str) == p_id]
                if not parent_match.empty:
                    p_status = safe_str(parent_match.iloc[0]['status'])
                    parent_title = safe_str(parent_match.iloc[0]['title'])
                    if p_status != "已完成":
                        is_blocked = True

            with st.container():
                st.markdown(f'<div class="todo-card">', unsafe_allow_html=True)
                c_info, c_action = st.columns([4, 1])
                
                with c_info:
                    u_class = "badge-high" if current_task['urgency'] == "高" else ("badge-mid" if current_task['urgency'] == "中" else "badge-low")
                    i_class = "badge-high" if current_task['importance'] == "高" else ("badge-mid" if current_task['importance'] == "中" else "badge-low")
                    
                    # 🟢 顯示使用者自定義日期時間軸標籤
                    st.markdown(f"""
                        <span class="badge badge-cat">{current_task['category']}</span>
                        <span class="badge badge-date">📅 時程: {t_date_val}</span>
                        <span class="badge {u_class}">急迫:{current_task['urgency']}</span>
                        <span class="badge {i_class}">重要:{current_task['importance']}</span>
                        <span class="badge" style="background-color:#007BFF;">{current_task['status']}</span>
                    """, unsafe_allow_html=True)
                    
                    if is_blocked:
                        st.markdown(f"#### 🔒 ~~{current_task['title']}~~ <span style='color:red; font-size:0.85rem;'>[ 順序鎖定中 ]</span>", unsafe_allow_html=True)
                        st.markdown(f'<p class="dependency-text">⚠️ 必須先完成前置任務：【{parent_title}】才能解鎖此項目執行權限。</p>', unsafe_allow_html=True)
                    else:
                        st.markdown(f"#### 🔓 {current_task['title']}")
                        if parent_title:
                            st.markdown(f'<p class="dependency-text">⛓️ 接續關係：承接在【{parent_title}】之後</p>', unsafe_allow_html=True)
                    
                    if safe_str(current_task['detail']):
                        with st.expander("🔎 檢視精密行動細節說明"):
                            st.info(current_task['detail'])
                            
                with c_action:
                    current_status = current_task['status']
                    if current_status == "未開始":
                        if st.button("▶️ 開始執行", key=f"start_{t_id}", disabled=is_blocked, use_container_width=True):
                            df_memo.loc[df_memo['id'].astype(str) == t_id, 'status'] = "進行中"
                            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_memo); st.cache_data.clear(); st.rerun()
                    elif current_status == "進行中":
                        if st.button("✅ 劃記完成", key=f"done_{t_id}", use_container_width=True):
                            df_memo.loc[df_memo['id'].astype(str) == t_id, 'status'] = "已完成"
                            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_memo); st.cache_data.clear(); st.rerun()
                    
                    # 排序移位按鈕
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("▲", key=f"up_{t_id}", help="將此任務順序上移", use_container_width=True):
                            curr_idx = df_memo[df_memo['id'].astype(str) == t_id].index[0]
                            curr_order = safe_int(df_memo.at[curr_idx, 'order_num'])
                            df_memo.at[curr_idx, 'order_num'] = max(1, curr_order - 1.5)
                            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_memo); st.cache_data.clear(); st.rerun()
                    with cc2:
                        if st.button("▼", key=f"down_{t_id}", help="將此任務順序下移", use_container_width=True):
                            curr_idx = df_memo[df_memo['id'].astype(str) == t_id].index[0]
                            curr_order = safe_int(df_memo.at[curr_idx, 'order_num'])
                            df_memo.at[curr_idx, 'order_num'] = curr_order + 1.5
                            conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_memo); st.cache_data.clear(); st.rerun()
                            
                    if st.button("🗑️ 拔除任務", key=f"del_{t_id}", use_container_width=True):
                        df_memo = df_memo[df_memo['id'].astype(str) != t_id]
                        conn.update(spreadsheet=GSHEET_URL, worksheet="user", data=df_memo); st.cache_data.clear(); st.rerun()
                        
                st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("❌ 無法讀取密庫，請檢查 Google Sheets 連線與分頁名稱是否正確。")
