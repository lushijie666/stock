import streamlit as st

# 控制台页面
def index():
    # 数据统计卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div class="stCard">
                <h3>总股票数</h3>
                <h2>2,534</h2>
                <p>较昨日 +12</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class="stCard">
                <h3>今日交易额</h3>
                <h2>￥8,432.21M</h2>
                <p>较昨日 +2.3%</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class="stCard">
                <h3>数据更新时间</h3>
                <h2>15:00:00</h2>
                <p>2024-03-14</p>
            </div>
        """, unsafe_allow_html=True)