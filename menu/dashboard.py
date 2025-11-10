import streamlit as st
from service.stock import show_category_pie_chart, show_follow_chart, get_total_stocks_count, get_followed_stocks_count
from enums.category import Category
from service.history_data import show_chart_page, KEY_PREFIX
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found



def index():
    # 主要统计指标
    show_main_metrics()

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 股票分类  ", "❤️ 关注股票  ", "📈 K线图  "])

    with tab1:
        show_category_pie_chart()

    with tab2:
        show_follow_chart()

    with tab3:
        show_kline_chart()


def show_main_metrics():
    total_stocks = get_total_stocks_count()
    followed_stocks = get_followed_stocks_count()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">总股票数</div>
            <div class="metric-value">{total_stocks:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card metric-card-secondary">
            <div class="metric-label">关注股票</div>
            <div class="metric-value">{followed_stocks}</div>
        </div>
        """, unsafe_allow_html=True)


def show_kline_chart():
    categories = list(Category)
    tab_labels = [f"{category.value}" for category in categories]

    tabs = st.tabs(tab_labels)
    # 创建股票选择器字典
    selectors = {}
    for category in Category:
        selector = create_stock_selector(
            category=category,
            prefix=KEY_PREFIX,
            on_select=show_chart_page,
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