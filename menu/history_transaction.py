import json
import streamlit as st

from enums.category import Category
from service.history_transaction import show_stock_detail, KEY_PREFIX
from utils.session import get_session_key, SessionKeys
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found


# 历史分笔
def index():
    # 获取当前选中的 tab
    current_tab_key = get_session_key(SessionKeys.CURRENT_TAB, prefix=KEY_PREFIX)
    if current_tab_key not in st.session_state:
        st.session_state[current_tab_key] = Category.A_SH

    tabs = st.tabs(Category.fullTexts())
    selectors = {}
    # 先创建所有的 selectors
    for category in Category:
        selector = create_stock_selector(
                category=category,
                prefix=KEY_PREFIX,
                on_select=show_stock_detail,
                on_error=handle_error,
                on_not_found=handle_not_found
            )
        selectors[category] = selector

    # 在每个 tab 中显示对应的 selector 和详情
    for tab, category in zip(tabs, Category):
        with tab:
            st.session_state[current_tab_key] = category
            selectors[category].show_selector()

            # 显示详情
            selectors[category].handle_current_stock()