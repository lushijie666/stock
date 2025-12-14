
import streamlit as st

from enums.category import Category
from service.stock_trade import show_page, KEY_PREFIX, show_detail


# 买卖记录
def index():
    tabs = st.tabs(Category.fullTexts())
    for tab, category in zip(tabs, Category):
        with tab:
            show_detail(category=category)