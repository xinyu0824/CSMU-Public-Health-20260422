import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取資料庫 (強烈建議：先不用 try-except，讓我們看看真正的報錯是什麼)
# 如果這次還是報 400，代表是 URL ID 或 Google 權限的問題
df = conn.read(worksheet="users", ttl=0)

st.success("✅ 連線成功！")
st.write(df.head()) # 先印出前幾行確認
