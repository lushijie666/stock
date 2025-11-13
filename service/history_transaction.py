# 历史分笔
import datetime
from datetime import datetime, date, timedelta, time

import streamlit as st
import akshare as ak
import logging
from typing import  Dict, Any, List
from functools import partial

from sqlalchemy.orm import Session

from service.stock import get_codes
from utils.convert import date_range_filter, parse_datetime
from utils.fetch_handler import create_reload_handler
from utils.message import show_message
from models.history_transaction import HistoryTransaction
from enums.category import Category
from utils.db import get_db_session, upsert_objects
from datetime import date, timedelta
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionButton, ActionConfig
from utils.session import SessionKeys, get_session_key

KEY_PREFIX = "history_transaction"

def show_page(stock):
    try:
        with get_db_session() as session:
            # 构建查询
            query = session.query(HistoryTransaction).filter(
                HistoryTransaction.code == stock.code,
                HistoryTransaction.removed == False
            ).order_by(HistoryTransaction.turnover_time.desc())
            paginate_dataframe(
                query,
                10,
                columns_config={
                    'code': st.column_config.TextColumn('股票代码', help="股票代码"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                    'turnover_time': st.column_config.DatetimeColumn('成交时间', help="成交时间"),
                    'turnover_price': st.column_config.NumberColumn('成交价格(元)', help="成交价", format="%.3f"),
                    'price_change': st.column_config.NumberColumn('价格变动(元)', help="价格变动", format="%.3f"),
                    'turnover_count': st.column_config.TextColumn('成交量(手)', help="成交股数"),
                    'turnover_amount': st.column_config.TextColumn('成交金额(元)', help="成交金额"),
                    'turnover_type': st.column_config.TextColumn('性质', help="性质"),
                },
                # 格式化函数
                format_funcs={},
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="start_date",
                            label="开始日期",
                            type="datetime",
                            default=datetime(
                                date.today().year,
                                date.today().month,
                                date.today().day,
                                0, 0, 0  # 时、分、秒
                            ),
                            placeholder="输入开始日期",
                            filter_func=lambda q, v: date_range_filter(q, 'start_date', v, date_field='turnover_time'),
                        ),
                        SearchField(
                            field="end_date",
                            label="结束日期",
                            type="datetime",
                            default=datetime(
                                date.today().year,
                                date.today().month,
                                date.today().day,
                                23, 59, 59  # 时、分、秒
                            ),
                            placeholder="输入结束日期",
                            filter_func=lambda q, v: date_range_filter(q, 'end_date', v, date_field='turnover_time')
                        )
                    ],
                    layout=[1, 1, 1, 1]
                ),
                action_config=ActionConfig(
                    buttons=[
                        ActionButton(
                            icon="🐙",
                            label="获取",
                            handler=partial(reload, code=stock.code),
                            type="primary"
                        ),
                    ],
                    layout=[1, 0.1]  # 每个按钮占一列
                ),
                title=f'{stock.category} {stock.code} ({stock.name})',
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}', category=stock.category),
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")

def show_stock_detail(stock):
    """显示详情"""
    show_page(stock)


def reload_by_category(category: Category):
    codes = get_codes(category)
    for code in codes:
        logging.info(f"开始处理[{code}]数据...")
        reload(code)
        logging.info(f"结束处理[{code}]数据...")
# reload
def reload(code: str) -> list:
    today_str = datetime.now().date().strftime('%Y-%m-%d')
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        return [
            HistoryTransaction.code == code,
        ]
    history_handler = create_reload_handler(
        model=HistoryTransaction,
        fetch_func=fetch,
        unique_fields=['code', 'turnover_time'],
        build_filter=build_filter,
        mark_existing=True,
    )
    return history_handler.refresh(
        code=code,
        date_str=today_str)


def fetch(code: str, date_str: str) -> list:
    # 拉取 https://akshare.akfamily.xyz/data/stock/stock.html#id31
    category = Category.from_stock_code(code)
    full_code = category.get_full_code(code)
    fetch_functions = {
        Category.A_SH: partial(ak.stock_zh_a_tick_tx_js, symbol=full_code),
        Category.A_SZ: partial(ak.stock_zh_a_tick_tx_js, symbol=full_code),
        Category.A_BJ: partial(ak.stock_zh_a_tick_tx_js, symbol=full_code),
    }
    try:
        if fetch_func := fetch_functions.get(category):
            logging.info(f"开始获取[{KEY_PREFIX}]数据..., 股票:{code}, {full_code}")
            df = fetch_func()
            logging.info(f"成功获取[{KEY_PREFIX}]数据..., 股票:{code}, {full_code}, 共{len(df)}条记录")
            data = []
            for _, row in df.iterrows():
                try:
                    # 获取时间并转换
                    time_str = row.get("成交时间")
                    if not time_str:
                        logging.warning(f"Missing turnover time for row: {row}")
                        continue
                    turnover_time = parse_datetime(date_str, time_str)
                    if not turnover_time:
                        continue
                    data.append(HistoryTransaction(
                        category=category,
                        code=code,
                        turnover_time=turnover_time,
                        turnover_price=row.get("成交价格"),
                        price_change=row.get("价格变动"),
                        turnover_count=row.get("成交量"),
                        turnover_amount=row.get("成交金额"),
                        turnover_type=row.get("性质"),
                    ))
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


def sync_history_transactions() -> Dict[str, Any]:
    success_count = 0
    failed_count = 0
    logging.info(f"开始同步历史分笔数据")
    try:
        categories = Category.get_all()
        for category in categories:
            try:
                logging.info(f"处理分类 {category.fullText} 的历史分笔数据")
                reload_by_category(category)
                success_count += 1
                logging.info(f"成功同步分类 {category.fullText} 的历史分笔数据")
            except Exception as e:
                failed_count += 1
                logging.error(f"同步分类 {category.fullText} 的历史分笔数据失败: {str(e)}")

        logging.info(f"历史分笔数据同步完成，成功: {success_count}, 失败: {failed_count}")
        return {
            "success_count": success_count,
            "failed_count": failed_count
        }

    except Exception as e:
        logging.error(f"历史分笔同步过程中发生错误: {str(e)}")
        return {
            "success_count": success_count,
            "failed_count": failed_count
        }
