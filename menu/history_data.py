import pandas as pd
import streamlit as st

from enums.category import Category
from service.history_data import show_stock_detail, KEY_PREFIX, reload_by_category_date
from utils.message import show_message
from utils.session import get_session_key, SessionKeys
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found


# 历史行情
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

            # 全量更新操作
            col1, col2 = st.columns([4, 1])
            with col1:
                date_range = st.date_input(
                    "",
                    value=(pd.Timestamp.now().date(), pd.Timestamp.now().date()),
                    key=f"date_range_{category.value}"  # 为每个tab添加唯一的key
                )
            with col2:
                st.write("")
                st.write("")
                if st.button("全量更新", type="primary", use_container_width=True, key=f"update_btn_{category.value}"):
                    if len(date_range) != 2:
                        show_message(f"日期范围选择错误", type="error")
                        return
                    start_date, end_date = date_range
                    start_str = start_date.strftime('%Y-%m-%d')
                    end_str = end_date.strftime('%Y-%m-%d')
                    reload_by_category_date(category, start_str, end_str)
                    show_message("正在后台更新，请稍后直接查看数据", type="success")

            st.divider()  # 分隔线

            # 股票选择
            selectors[category].show_selector()


            # 显示详情
            selectors[category].handle_current_stock()

