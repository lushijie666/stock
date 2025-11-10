# 股票

from functools import partial
from typing import  Dict, Any, List
import akshare as ak
import streamlit_echarts
import logging
import pandas as pd
from datetime import datetime as dt
import streamlit as st
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import func
from pyecharts.charts import Pie
from pyecharts import options as opts
from enums.category import Category
from models.stock import Stock
from utils.chart import ChartBuilder
from utils.convert import get_column_value, clean_number_value,clean_name
from utils.db import get_db_session
from utils.fetch_handler import create_reload_handler
from utils.message import show_message

from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionConfig, ActionButton
from utils.session import get_session_key, SessionKeys
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found
from utils.table import  format_pinyin_short
from utils.uuid import generate_key

KEY_PREFIX = "stock"


def get_codes(category: Category) -> List[str]:
    try:
        with get_db_session() as session:
            return Stock.get_codes_by_category(session, category)
    except Exception as e:
        logging.error(f"获取股票失败: {str(e)}")
        return []


def show_category_pie_chart():
    try:
        with get_db_session() as session:
            result = (
                session.query(
                    Stock.category,
                    func.count(Stock.id).label('count')
                )
                .filter(Stock.removed == False)
                .group_by(Stock.category)
                .all()
            )
            df = pd.DataFrame(result, columns=['分类', '数量'])
            df['分类'] = df['分类'].apply(lambda x: Category(x).fullText)
            if df.empty:
                st.warning("暂无数据")
                return

            total_stocks = df['数量'].sum()
            data_pairs = [(cat, num) for cat, num in zip(df['分类'], df['数量'])]

            pie = ChartBuilder.create_pie_chart(data_pairs, total_stocks)
            # 显示图表
            streamlit_echarts.st_pyecharts(pie, height="500px")

            # 添加一个分隔线
            st.markdown("---")

            # 添加百分比列并显示数据表
            df['占比'] = (df['数量'] / total_stocks * 100).round(1)
            st.dataframe(
                df,
                column_config={
                    "分类": st.column_config.TextColumn("分类"),
                    "数量": st.column_config.NumberColumn("股票数量", format="%d"),
                    "占比": st.column_config.NumberColumn("占比", format="%.1f%%"
                    )
                },
                hide_index=True,
                use_container_width=True
            )

    except Exception as e:
        st.error(f"显示股票分类分布图表失败: {str(e)}")


def show_page(category: Category):
    try:
        with get_db_session() as session:
            # 构建查询
            query = session.query(Stock).filter(
                Stock.category == category,
                Stock.removed == False
            ).order_by(Stock.code.asc())
            # 使用通用的分页
            paginate_dataframe(
                query,
                100,
                columns_config={
                    # 基础信息
                    # 'category': st.column_config.TextColumn('分类', help="股票分类"),
                    'code': st.column_config.TextColumn('股票代码', help="股票代码"),
                    'name': st.column_config.TextColumn('股票名称', help="股票名称"),
                    'pinyin': st.column_config.TextColumn('股票简拼', help="股票拼音简称"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                    'full_name': st.column_config.TextColumn('全称', help="公司名称"),
                    'ipo_at': st.column_config.DatetimeColumn('上市时间', help="上市时间"),
                    'total_capital': st.column_config.TextColumn('总股本(股)', help="总股本"),
                    'flow_capital': st.column_config.TextColumn('流通股本(股)', help="流通股本"),
                    'industry': st.column_config.TextColumn('行业', help="行业"),
                },
                # 格式化函数
                format_funcs={
                    'pinyin': format_pinyin_short,
                },
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="keyword",
                            label="股票代码/名称/简拼",
                            type="text",
                            placeholder="输入股票代码/名称/简拼",
                            search_fields = ["code", "name", "pinyin"]
                        )
                    ],
                    layout=[1, 1, 1, 1]
                ),
                action_config=ActionConfig(
                    buttons=[
                        ActionButton(
                            icon="🐙",
                            label="更新",
                            handler=partial(reload, category=category),
                            type="primary"
                        ),
                    ],
                    layout=[1, 0.2]  # 每个按钮占一列
                ),
                title= category.fullText,
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}', category=category),
                model=Stock,
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_follow_chart():
    try:
        with get_db_session() as session:
            # 查询所有被关注的股票，按分类和代码排序
            stocks = session.query(Stock).filter(
                Stock.removed == False,
                Stock.is_followed == True
            ).order_by(Stock.category.asc(), Stock.code.asc()).all()

            if not stocks:
                st.info("暂无关注的股票")
                return

            # 按分类组织数据
            category_stocks = {}
            for stock in stocks:
                category_enum = Category(stock.category)
                category_name = category_enum.fullText
                if category_name not in category_stocks:
                    category_stocks[category_name] = []
                category_stocks[category_name].append(stock)

            # 使用 st.tabs 或直接显示多个表格来避免嵌套 expander
            categories = list(category_stocks.keys())

            tab_labels = [f"{category} - ({len(category_stocks[category])}只)" for category in categories]
            tabs = st.tabs(tab_labels)
            for i, (category_name, stocks_list) in enumerate(category_stocks.items()):
                with tabs[i]:
                    # 显示该分类下的关注股票
                    data = [{
                        'code': stock.code,
                        'name': stock.name,
                        'pinyin': format_pinyin_short(stock.pinyin),
                        'full_name': stock.full_name or '-',
                        'ipo_at': stock.ipo_at.strftime('%Y-%m-%d') if stock.ipo_at else '-',
                        'industry': stock.industry or '-',
                        'followed_at': stock.followed_at.strftime('%Y-%m-%d %H:%M:%S') if stock.followed_at else '-',
                    } for stock in stocks_list]
                    df = pd.DataFrame(data)
                    st.dataframe(
                        df,
                        column_config={
                            "code": st.column_config.TextColumn("股票代码"),
                            "name": st.column_config.TextColumn("股票名称"),
                            "pinyin": st.column_config.TextColumn("股票简拼"),
                            "full_name": st.column_config.TextColumn("公司全称"),
                            "ipo_at": st.column_config.TextColumn("上市时间"),
                            "industry": st.column_config.TextColumn("行业"),
                            "followed_at": st.column_config.TextColumn("关注时间"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )
    except Exception as e:
        st.error(f"加载关注股票数据失败：{str(e)}")


def show_follow_page(category: Category):
    show_add_follow(category=category)
    st.divider()
    try:
        with get_db_session() as session:
            query = session.query(Stock).filter(
                Stock.category == category,
                Stock.removed == False,
                Stock.is_followed == True
            ).order_by(Stock.code.asc())

            # 获取所有关注的股票
            stocks = query.all()
            if not stocks:
                st.info("暂无关注的股票")
                return

            # 手动渲染表格 + 按钮
            st.markdown("<h5>已关注的股票</h5>", unsafe_allow_html=True)
            for stock in stocks:
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.markdown(f"**{stock.name}** ({stock.code})")
                    st.caption(f"全称: {stock.full_name}")
                    st.caption(f"上市时间: {stock.ipo_at}")
                    st.caption(f"行业: {stock.industry}")
                    st.caption(f"关注时间: {stock.followed_at.strftime('%Y-%m-%d %H:%M:%S') if stock.followed_at else '-'}")
                with col2:
                    if st.button("移除关注", key=f"remove_{stock.code}", type="secondary"):
                        remove_follow(category, stock.code)
                        st.rerun()  # 刷新页面
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_add_follow(category: Category):
    with st.expander("添加关注股票"):
        prefix = f'add_follow_{KEY_PREFIX}_{category.value}'
        selected_stock_key = f'selected_stock_{prefix}'  # 用于存储选中的股票对象

        # 创建股票选择器
        selector = create_stock_selector(
            category=category,
            prefix=prefix,
            on_select=lambda stock: st.session_state.update({selected_stock_key: stock.code}),
            on_error=handle_error,
            on_not_found=handle_not_found
        )
        selector.show_selector()
        selector.handle_current_stock()
        # 添加确定和取消按钮
        col1, = st.columns([1])  # 调整按钮布局
        with col1:
            if st.button("确定", key=f'confirm_follow_{KEY_PREFIX}_{category.value}', type="primary", use_container_width=True):
                if stock_code := st.session_state.get(selected_stock_key):
                    add_follow(category, stock_code)
                    # 清理状态并刷新
                    st.session_state.pop(selected_stock_key, None)
                    st.rerun()
                else:
                    show_message("请先选择股票", type="warning")


def add_follow(category: Category, stock_code: str):
    try:
        with get_db_session() as session:
            stock = session.query(Stock).filter(
                Stock.code == stock_code,
                Stock.category == category,
            ).first()
            if stock:
                stock.is_followed = True
                stock.followed_at = dt.now()
                session.commit()
                show_message(f"已添加关注：{stock.name}({stock.code})", type="success")
            else:
                show_message("未找到选中的股票", type="warning")
    except Exception as e:
        show_message(f"添加关注失败：{str(e)}", type="error")

def remove_follow(category: Category, stock_code: str):
    try:
        with get_db_session() as session:
            stock = session.query(Stock).filter(
                Stock.code == stock_code,
                Stock.category == category,
            ).first()
            if stock:
                stock.is_followed = False
                stock.followed_at = None
                session.commit()
                show_message(f"已取消关注：{stock.name}({stock.code})", type="success")
                st.rerun()  # 刷新页面以更新显示
            else:
                show_message("未找到选中的股票", type="warning")
    except Exception as e:
        show_message(f"取消关注失败：{str(e)}", type="error")

def reload(category: Category):
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        return [
            Stock.category == category,
        ]
    history_handler = create_reload_handler(
        model=Stock,
        fetch_func=fetch,
        unique_fields=['code'],
        build_filter=build_filter,
        mark_existing=True,
    )
    return history_handler.refresh(
        category=category)

def fetch(category: Category) -> list:
    # 拉取 https://akshare.akfamily.xyz/data/stock/stock.html#id11
    fetch_functions = {
        Category.A_SH: partial(ak.stock_info_sh_name_code, symbol="主板A股"),
        Category.A_SZ: partial(ak.stock_info_sz_name_code, symbol="A股列表"),
        Category.A_BJ: partial(ak.stock_info_bj_name_code),
    }
    try:
        if fetch_func := fetch_functions.get(category):
            logging.info(f"开始获取[{KEY_PREFIX}]数据..., 分类: {category.text}")
            df = fetch_func()
            logging.info(f"成功获取[{KEY_PREFIX}]数据，分类: {category.text}, 共 {len(df)} 条记录")
            data = []
            for _, row in df.iterrows():
                try:
                    code = get_column_value(row, "code")
                    s = Stock(
                        category=Category.from_stock_code(code),
                        code=code,
                        name=clean_name(get_column_value(row, "name")),
                        full_name=row.get("公司全称"),
                        ipo_at=get_column_value(row, "ipo_at"),
                        total_capital=clean_number_value(get_column_value(row, "total_capital")),
                        flow_capital=clean_number_value(get_column_value(row, "flow_capital")),
                        industry=row.get("所属行业"),
                    )
                    s.pinyin = s.generate_pinyin()
                    data.append(s)
                except Exception as row_error:
                    logging.error(f"Error processing row: {row}, Error: {str(row_error)}")
                    continue
            return data
        else:
            show_message(f"不支持的分类: {category}", type="error")
            return None
    except Exception as e:
        logging.error(f"Error fetching data: {str(e)}")
        return None


def get_total_stocks_count():
    """获取总股票数"""
    try:
        with get_db_session() as session:
            count = session.query(func.count(Stock.id)).filter(Stock.removed == False).scalar()
            return count or 0
    except Exception as e:
        logging.error(f"获取总股票数失败: {str(e)}")
        return 0


def get_followed_stocks_count():
    """获取关注股票数"""
    try:
        with get_db_session() as session:
            count = session.query(func.count(Stock.id)).filter(
                Stock.removed == False,
                Stock.is_followed == True
            ).scalar()
            return count or 0
    except Exception as e:
        logging.error(f"获取关注股票数失败: {str(e)}")
        return 0
