import streamlit as st
from menu import dashboard
import logging
from config.database import check_db
from menu.pages import Pages
# 导入模型以确保数据库表创建
from models import stock, stock_history

# 页面配置
st.set_page_config(
    page_title="股票分析系统",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# css设置
with open('static/style.css', encoding='utf-8') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# 初始化选中的页面
if 'selected_page' not in st.session_state:
    st.session_state.selected_page = Pages.get_page_names()[0]

# 自定义菜单组件
def render_custom_menu():
    """渲染侧边栏菜单"""
    with st.sidebar:
        # 侧边栏头部
        st.markdown("""
        <div class="sidebar-header">
            <div class="logo-container">
                <h1 class="logo-text">💰股票量化交易</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 创建直接的Streamlit按钮菜单
        page_names = Pages.get_page_names()
        
        for page_name in page_names:
            page_config = Pages.configs[page_name]
            
            # 判断是否选中
            is_selected = st.session_state.selected_page == page_name
            
            # 根据是否选中应用不同的按钮类型
            button_type = "primary" if is_selected else "secondary"
            
            # 创建直接的Streamlit按钮
            if st.button(
                f"{page_name}",
                key=f"menu_{page_name}",
                use_container_width=True,
                type=button_type
            ):
                # 按钮点击时更新状态并刷新页面
                st.session_state.selected_page = page_name
                st.rerun()
    

# 渲染菜单
render_custom_menu()

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

# 检查并初始化数据库
try:
    check_db()
except Exception as e:
    st.error(f"数据库检查/初始化失败：{str(e)}")
    st.stop()

# 主程序逻辑
def main():
    selected = st.session_state.selected_page
    st.markdown(f"""
    <div class="location-header">
        <div class="breadcrumb-content">
            <span class="breadcrumb-icon">📍</span>
            <span class="breadcrumb-label">当前位置</span>
            <span class="breadcrumb-separator">></span>
            <span class="breadcrumb-current">{selected}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    Pages.render_page(selected)



if __name__ == "__main__":
    main()