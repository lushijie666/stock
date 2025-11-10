import streamlit as st
from menu import dashboard, real_time_data
import logging
from config.database import check_db
from menu.pages import Pages

# 页面配置
st.set_page_config(
    page_title="股票数据分析系统",
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
    """渲染现代化侧边栏菜单"""
    with st.sidebar:
        # 现代化侧边栏头部
        st.markdown("""
        <div class="sidebar-header-modern">
            <span class="sidebar-icon">💹</span>
            <span class="sidebar-title">股票分析系统</span>
        </div>
        """, unsafe_allow_html=True)

        # 菜单项容器
        st.markdown('<div class="menu-container">', unsafe_allow_html=True)

        page_names = Pages.get_page_names()
        for page_name in page_names:
            page_config = Pages.configs[page_name]
            icon = page_config.icon
            
            # 图标映射
            icon_map = {
                "house": "🏠",
                "heart-fill": "❤️",
                "grid": "📊",
                "graph-up": "📈",
                "clipboard2-data": "📋",
                "terminal-split": "📄"
            }
            icon_emoji = icon_map.get(icon, "📌")
            
            # 判断是否选中
            is_selected = st.session_state.selected_page == page_name
            button_key = f"menu_btn_{page_name}"
            
            # 创建按钮，文本包含图标和菜单名称
            button_text = f"{icon_emoji} {page_name}"
            button_type = "primary" if is_selected else "secondary"
            
            if st.button(button_text, key=button_key, use_container_width=True, type=button_type):
                st.session_state.selected_page = page_name
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

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
    <div class="breadcrumb-container">
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