from enums.category import Category
from service.real_time_data import show_page
import streamlit as st


# 实时行情
def index():
    tabs = st.tabs(Category.fullTexts())
    for tab, category in zip(tabs, Category):
        with tab:
            show_page(category=category)


