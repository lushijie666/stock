import logging
from datetime import date, timedelta, datetime
from functools import partial
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
from service.stock import reload, get_followed_codes, get_codes
from service.stock_chart import show_detail_dialog
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
                            default=date.today() - timedelta(days=365),
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
                on_row_select=handle_row_click

            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


# 添加行点击处理函数
def handle_row_click(selected_rows):
    """
    处理行点击事件
    :param selected_rows: 选中的行数据
    """
    if selected_rows:
        # 获取选中的第一行数据
        selected_row = selected_rows[0]
        try:
            with get_db_session() as session:
                stock = session.query(Stock).filter(Stock.code == selected_row['code']).first()
                if stock:
                    show_detail_dialog(stock)
                else:
                    st.error(f"未找到股票代码为 {selected_row['code']} 的股票信息")
        except Exception as e:
            st.error(f"加载股票信息失败：{str(e)}")

def reload(category: Category):
    # 获取选择的日期范围
    prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}', category=category)
    date_range = get_date_range(prefix=prefix)

    if date_range:
        start_date, end_date = date_range
    else:
        # 如果没有设置日期范围，使用默认值
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()

    codes = get_codes(category)
    #codes = get_followed_codes(category)
    for code in codes:
        try:
            reload_by_code(code, StockHistoryType.D, start_date, end_date)
        except Exception as e:
            logging.error(f"股票: {code} 处理时出错: {str(e)}")
            continue


def reload_by_code(code: str, t: StockHistoryType = StockHistoryType.D, start_date: Any = None, end_date: Any = None):
    if start_date is None:
        start_date = date.today() - timedelta(days=365)
    if end_date is None:
        end_date = date.today()
    with get_db_session() as session:
        session.query(StockTrade).filter(
            StockTrade.code == code,
        ).delete()
        session.commit()
    # 使用处理句柄刷新数据
    _create_trade_handler().refresh(
        code=code,
        history_type=t,
        start_date=start_date,
        end_date=end_date,
        limit=200,
    )

def _create_trade_handler():
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        """构建过滤条件"""
        code = args.get('code')
        filters = [StockTrade.code == code]
        return filters
    return create_reload_handler(
        model=StockTrade,
        fetch_func=fetch,
        unique_fields=['code', 'date', 'strategy_type'],
        build_filter=build_filter,
        with_date_range=False  # 我们已经在fetch_func中处理了日期范围
    )



def fetch(code: str, history_type: StockHistoryType, start_date: Any = None, end_date: Any =  None, limit: int = 200) -> list:
    logging.info(f"开始获取[{KEY_PREFIX}]数据..., 股票:{code}")
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
        if start_date is not None and start_date != '':
            # 处理字符串类型的日期
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(model.date >= start_date)

        if end_date is not None and end_date != '':
            # 处理字符串类型的日期
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(model.date <= end_date)
        #query = query.order_by(model.date.desc()).limit(limit)
        query = query.order_by(model.date.desc())
        rows = query.all()
    logging.info(f"获取[{KEY_PREFIX}]数据的历史数据[{history_type.text}]完成..., 股票:{code}, 共{len(rows)}条")
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

    category = Category.from_stock_code(code)
    # 计算信号
    signals = calculate_all_signals(df, merge_and_filter=True)
    logging.info(f"获取[{KEY_PREFIX}]数据的信号数据完成..., 股票:{code}, 共{len(signals)}条")
    # 转换为StockTrade对象
    stock_trades = []
    for signal in signals:
        signal_date = signal['date']
        stock_trade = StockTrade(
            code=code,
            category=category.value,
            date=signal_date,
            signal_type=signal['type'].value,
            signal_strength=signal['strength'].value,
            strategy_type=signal['strategy_code'],
            removed=False
        )
        stock_trades.append(stock_trade)
    return stock_trades


def sync(is_all: bool) -> Dict[str, Any]:
    success_count = 0
    failed_count = 0

    logging.info(f"开始同步[{KEY_PREFIX}]数据")
    categories = Category.get_all()
    for category in categories:
        logging.info(f"开始同步[{KEY_PREFIX}]数据，分类: {category.fullText}")
        codes = get_codes(category)
        if not is_all:
            codes = get_followed_codes(category)
        for code in codes:
            show_message(f"正在处理股票: {code}", type="warning")
            try:
                reload_by_code(code,  StockHistoryType.D,None, None)
                success_count += 1
                show_message(f"股票: {code} 处理完成", type="success")
            except Exception as e:
                failed_count += 1
                show_message(f"股票: {code} 处理时出错: {str(e)}", type="error")
            logging.info(f"同步[{KEY_PREFIX}]的数据完成...，分类: {category.fullText}, 股票: {code}")
    logging.info(f"同步[{KEY_PREFIX}]数据完成，成功数: {success_count}, 失败数: {failed_count}")
    return {
        "success_count": success_count,
        "failed_count": failed_count
    }