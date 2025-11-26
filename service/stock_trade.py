from functools import partial
from sqlalchemy import or_
import streamlit as st
from enums.category import Category
from enums.signal import SignalType, SignalStrength
from enums.strategy import StrategyType
from models.stock import Stock
from models.stock_trade import StockTrade
from service.stock import reload
from utils.db import get_db_session
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionConfig, ActionButton
from utils.session import get_session_key, SessionKeys
from utils.table import format_pinyin_short

KEY_PREFIX = "stock_trade"


def show_page(category: Category):
    try:
        with get_db_session() as session:
            # 其他数据按日期排序
            query = session.query(
                StockTrade.code,
                Stock.name,
                Stock.pinyin,
                StockTrade.date,
                StockTrade.signal_type,
                StockTrade.signal_strength,
                StockTrade.strategy_type,
            ).join(Stock, StockTrade.code == Stock.code).filter(
                StockTrade.category == category,
                StockTrade.removed == False
            ).order_by(StockTrade.date.desc())
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
                    'date': st.column_config.DateColumn('日期', help="日期"),
                    'signal_type': st.column_config.TextColumn('信号类型', help="信号类型"),
                    'signal_strength': st.column_config.TextColumn('信号强度', help="信号强度"),
                    'strategy_type': st.column_config.TextColumn('策略类型', help="策略类型"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                },
                # 格式化函数
                format_funcs={
                    'pinyin': format_pinyin_short,
                        'signal_type': lambda x: SignalType.lookup(x).fullText,
                        'signal_strength': lambda x: SignalStrength.lookup(x).fullText,
                        'strategy_type': lambda x: StrategyType.lookup(x).fullText,
                },
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="keyword",
                            label="股票代码/名称/简拼",
                            type="text",
                            placeholder="输入股票代码/名称/简拼",
                            filter_func=lambda query, value: query.filter(
                                or_(
                                    StockTrade.code.ilike(f"%{value}%"),
                                    Stock.name.ilike(f"%{value}%"),
                                    Stock.pinyin.ilike(f"%{value}%")
                                )
                            )
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
                title=category.fullText,
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}', category=category),
                model=Stock,
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")

def reload(category: Category):
    return ""