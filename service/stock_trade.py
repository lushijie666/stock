import logging
from datetime import date, timedelta, datetime
from functools import partial
from pyexpat.errors import messages
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from requests.sessions import Session
from sqlalchemy import or_
import streamlit as st
from enums.category import Category
from enums.history_type import StockHistoryType
from enums.signal import SignalType, SignalStrength
from enums.strategy import StrategyType
from models.stock import Stock
from models.stock_history import get_history_model
from models.stock_trade import StockTrade
from service.stock import reload, get_followed_codes
from utils.db import get_db_session
from utils.fetch_handler import create_reload_handler
from utils.message import show_message
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionConfig, ActionButton
from utils.session import get_session_key, SessionKeys, get_date_range
from utils.signal import  calculate_all_signals
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
                StockTrade.removed == False,
                StockTrade.date >= date.today() - timedelta(days=30),
                StockTrade.date <= date.today()
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
                    'strategy_type': st.column_config.TextColumn('策略', help="策略类型"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                },
                # 格式化函数
                format_funcs={
                    'pinyin': format_pinyin_short,
                        'signal_type': lambda x: SignalType.lookup(x).fullText,
                        'signal_strength': lambda x: SignalStrength.lookup(x).fullText,
                        'strategy_type': lambda x: ', '.join([StrategyType.lookup(code.strip()).fullText for code in x.split(',')]) if x and ',' in x else ( StrategyType.lookup(x).fullText if x else '')
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
                        ),
                        SearchField(
                            field="start_date",
                            label="开始日期",
                            type="date",
                            default=date.today() - timedelta(days=30),
                            max_date=date.today(),
                            placeholder="输入开始日期",
                            filter_func=lambda q, v: q.filter(StockTrade.date >= v) if v else q
                        ),
                        SearchField(
                            field="end_date",
                            label="结束日期",
                            type="date",
                            default=date.today(),
                            max_date=date.today(),
                            placeholder="输入结束日期",
                            filter_func=lambda q, v: q.filter(StockTrade.date <= v) if v else q
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
                model=StockTrade,
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def reload(category: Category):
    try:
        # 获取日期范围
        prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}', category=category)
        date_range = get_date_range(prefix=prefix)

        if date_range:
            start_date, end_date = date_range
        else:
            # 如果没有设置日期范围，使用默认值
            start_date = date.today() - timedelta(days=30)
            end_date = date.today()

        # 创建处理句柄
        handler = _create_trade_handler()
        # 获取分类下的所有股票
        with get_db_session() as session:
            codes = get_followed_codes(category)
            # 循环处理每只股票
            for code in codes:
                try:
                    # 显示正在处理的股票信息
                    show_message(f"正在处理股票: {code}", type="warning")
                    # 使用处理句柄刷新数据
                    handler.refresh(
                        code=code,
                        category=category,
                        history_type=StockHistoryType.D,
                        start_date=start_date,
                        end_date=end_date
                    )
                    show_message(f"股票: {code} 处理完成", type="success")
                except Exception as e:
                    show_message(f"股票: {code} 处理时出错: {str(e)}", type="error")
                    continue
                logging.info(f"同步[{KEY_PREFIX}]的数据完成...，分类: {category.fullText}, 股票: {code}")
    except Exception as e:
        st.error(f"更新失败：{str(e)}")


def _create_trade_handler():
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        """构建过滤条件"""
        code = args.get('code')
        start_date = args.get('start_date')
        end_date = args.get('end_date')
        category = args.get('category')
        filters = [StockTrade.code == code]
        if category:
            filters.append(StockTrade.category == category)
        if start_date:
            filters.append(StockTrade.date >= start_date)
        if end_date:
            filters.append(StockTrade.date <= end_date)
        return filters

    def fetch_func(code: str, category: Category, history_type: StockHistoryType, start_date: Any, end_date: Any) -> list:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        # 获取历史数据模型类
        model = get_history_model(history_type)
        with get_db_session() as session:
            # 查询并直接提取需要的数据，避免保留模型实例引用
            query = session.query(
                model.date,
                model.opening,
                model.closing,
                model.highest,
                model.lowest,
                model.turnover_count
            ).filter(model.code == code)
            if start_date:
                query = query.filter(model.date >= start_date)
            if end_date:
                query = query.filter(model.date <= end_date)
            query = query.order_by(model.date)
            rows = query.all()

        if not rows:
            return []

        # 转换为DataFrame，使用元组解包而不是模型实例属性访问
        df = pd.DataFrame([{
            'date': row[0],  # date
            'opening': float(row[1]),  # opening
            'closing': float(row[2]),  # closing
            'highest': float(row[3]),  # highest
            'lowest': float(row[4]),  # lowest
            'turnover_count': float(row[5])  # turnover_count
        } for row in rows])

        # 计算信号
        signals = calculate_all_signals(df, merge_and_filter=True)
        
        # 转换为StockTrade对象
        stock_trades_data = []

        for signal in signals:
            signal_date = signal['date']
            if start_date <= signal_date <= end_date:
                stock_trade = StockTrade(
                    code=code,
                    category=category.value,
                    date=signal_date,
                    signal_type=signal['type'].value,
                    signal_strength=signal['strength'].value,
                    strategy_type=signal['strategy_code'],
                    removed=False
                )
                stock_trades_data.append(stock_trade)
        return stock_trades_data
    return create_reload_handler(
        model=StockTrade,
        fetch_func=fetch_func,
        unique_fields=['code', 'date', 'strategy_type'],
        build_filter=build_filter,
        with_date_range=False  # 我们已经在fetch_func中处理了日期范围
    )