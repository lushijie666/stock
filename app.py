import streamlit as st
from streamlit_option_menu import option_menu
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

# 菜单
with st.sidebar:
    st.markdown("## 💹  股票分析系统  💹")
    selected = option_menu(
        menu_title=None,
        options=Pages.get_page_names(),
        icons=[Pages.configs[page].icon for page in Pages.get_page_names()],
        default_index=0,
        menu_icon="cast",
        styles={
            "container": {"padding": "0!important"},
            "icon": {"font-size": "1rem"},
            "nav-link": {
                "font-size": "0.9rem",
                "padding": "0.8rem 1rem",
                "--hover-color": "#eee",
            },
            "nav-link-selected": {"background-color": "#1677ff"},
        },
    )

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

# 检查并初始化数据库
try:
    check_db()
except Exception as e:
    st.error(f"数据库检查/初始化失败：{str(e)}")
    st.stop()

# 主程序逻辑
def main():
    st.markdown(f'<p class="custom-caption">当前位置 > {selected}</p>', unsafe_allow_html=True)
    Pages.render_page(selected)



if __name__ == "__main__":
    main()
