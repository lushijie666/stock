import logging

import pandas as pd
import streamlit as st


from service.stock import show_category_pie_chart
from utils.message import show_message


def index():
    with st.expander("股票分类分布", expanded=True):
        show_category_pie_chart()

    #st.divider()  # 分隔线



