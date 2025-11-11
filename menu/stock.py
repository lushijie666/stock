from enums.category import Category
from service.stock import show_page, show_follow_page
from service.stock_chart import show_detail
import streamlit as st

from service.stock_chart import KEY_PREFIX, show_detail
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found


# 股票信息
def index():
    tabs = st.tabs(Category.fullTexts())
    for tab, category in zip(tabs, Category):
        with tab:
            show_page(category=category)

# 关注股票
def followIndex():
    tabs = st.tabs(Category.fullTexts())
    for tab, category in zip(tabs, Category):
        with tab:
            show_follow_page(category=category)


def chartIndex():
    tabs = st.tabs(Category.fullTexts())
    selectors = {}
    for tab, category in zip(tabs, Category):
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
