from enums.category import Category
from service.stock import show_page
import streamlit as st

# 股票信息
def index():
    tabs = st.tabs(Category.fullTexts())
    for tab, category in zip(tabs, Category):
        with tab:
            show_page(category=category)



