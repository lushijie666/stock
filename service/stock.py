# 股票

from functools import partial
from typing import  Dict, Any, List
import akshare as ak
import streamlit_echarts
import logging
import pandas as pd
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
from utils.table import  format_pinyin_short

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
                            label="获取",
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