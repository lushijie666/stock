import pandas as pd
import streamlit as st

from enums.category import Category
from service.stock_history import show_detail, KEY_PREFIX
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found


# 历史行情
def index():
    tabs = st.tabs(Category.fullTexts())
    selectors = {}
    # 先创建所有的 selectors
    for category in Category:
        selector = create_stock_selector(
            category=category,
            prefix=KEY_PREFIX,
            on_select=show_detail,
            on_error=handle_error,
            on_not_found=handle_not_found
        )
        selectors[category] = selector

    # 在每个 tab 中显示对应的 selector 和详情
    for tab, category in zip(tabs, Category):
        with tab:
            # 股票选择
            selectors[category].show_selector()
            # 显示详情
            selectors[category].handle_current_stock()

