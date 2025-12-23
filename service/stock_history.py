# 历史行情
import os

import yfinance as yf
import akshare as ak
import pandas as pd
import streamlit as st
import logging
import threading
from collections import OrderedDict
import baostock as bs
from typing import Dict, Any, List
from functools import partial
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
import time
import random
from enums.category import Category
from enums.history_type import StockHistoryType

from service.stock import get_codes, get_followed_codes
from utils.background_task import BackgroundTaskExecutor
from utils.convert import date_range_filter, parse_baostock_datetime, clean_numeric_value, format_date_by_type, \
    extend_end_date
from utils.fetch_handler import create_reload_handler
from models.stock_history import get_history_model, StockHistoryW, StockHistoryD, StockHistoryM,StockHistory30M
from utils.db import get_db_session

from utils.message import show_message
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionButton, ActionConfig
from utils.retry import retry_with_backoff, RATE_LIMIT_RETRY_CONFIG
from utils.session import get_session_key, SessionKeys, get_date_range
from utils.table import  format_percent, format_volume
from utils.rate_limiter import get_rate_limiter, RateLimiterConfig, BALANCED_CONFIG

KEY_PREFIX = "stock_history"


def show_page(stock, t: StockHistoryType):
    try:
        model = get_history_model(t)
        with get_db_session() as session:
            # 其他数据按日期排序
            query = session.query(model).filter(
                model.code == stock.code,
                model.removed == False
            ).order_by(model.date.desc())
            format_funcs = {
                'turnover_count': format_volume,
                'turnover_ratio': format_percent,
                'change': format_percent,
                'date': lambda x: format_date_by_type(x, t),
            }
            paginate_dataframe(
                query,
                10,
                columns_config={
                    'code': st.column_config.TextColumn('股票代码', help="股票代码"),
                    'date': st.column_config.TextColumn('日期（时间）', help="日期"),
                    'opening': st.column_config.NumberColumn('开盘', help="当日开盘价", format="%.3f"),
                    'closing': st.column_config.NumberColumn('收盘', help="当日收盘价", format="%.3f"),
                    'highest': st.column_config.NumberColumn('最高', help="当日最高价", format="%.3f"),
                    'lowest': st.column_config.NumberColumn('最低', help="当日最低价", format="%.3f"),
                    'turnover_count': st.column_config.TextColumn('成交量(手)', help="成交股数"),
                    'turnover_amount': st.column_config.TextColumn('成交额(元)', help="成交金额"),
                    'change': st.column_config.NumberColumn('涨跌幅', help="涨跌幅", format="%.2f%%"),
                    'turnover_ratio': st.column_config.NumberColumn('换手率', help="成交股数与流通股数之比", format="%.2f%%"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                },
                # 格式化函数
                format_funcs=format_funcs,
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="start_date",
                            label="开始日期",
                            type="date",
                            default=date.today() - timedelta(days=90),
                            max_date=date.today(),
                            placeholder="输入开始日期",
                            filter_func=lambda q, v: date_range_filter(q, 'start_date', v)  # 添加过滤函数
                        ),
                        SearchField(
                            field="end_date",
                            label="结束日期",
                            type="date",
                            default=date.today(),
                            max_date=date.today(),
                            placeholder="输入结束日期",
                            filter_func=lambda q, v: date_range_filter(q, 'end_date', v)  # 添加过滤函数
                        )
                    ],
                    layout=[1, 1, 1, 1]
                ),
                action_config=ActionConfig(
                    buttons=[
                        ActionButton(
                            icon="🐙",
                            label="更新",
                            handler=partial(manual_reload_by_code, category=stock.category, code=stock.code, t=t),
                            type="primary"
                        ),
                    ],
                    layout=[1, 0.1]  # 每个按钮占一列
                ),

                title=f'{stock.category} {stock.code} ({stock.name}) - [{t.text}]',
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_{t}_date', category=stock.category),
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_detail(stock):
    t = st.radio(
        "选择时间周期",
        ["天", "周", "月", "30分钟"],
        horizontal=True,
        key=f"{KEY_PREFIX}_{stock.code}_radio",
        label_visibility="collapsed"
    )
    handlers = {
        "天": lambda:  show_page(stock, StockHistoryType.D),
        "周": lambda:  show_page(stock, StockHistoryType.W),
        "月": lambda:  show_page(stock, StockHistoryType.M),
        "30分钟": lambda:  show_page(stock, StockHistoryType.THIRTY_M),
    }
    handlers.get(t, lambda: None)()

def manual_reload_by_code(category: Category, code: str, t: StockHistoryType):
    prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{code}_{t}_date', category=category)
    date_range = get_date_range(prefix=prefix)
    if not date_range:
        return
    start_date, end_date = date_range
    handler = _create_history_handler(t)
    handler.refresh(
        code=code,
        start_date=start_date,
        end_date=end_date,
        t=t)

def reload_by_code(code: str, start_date: str, end_date: str, t: StockHistoryType, ignore_message: bool = False):
    handler = _create_history_handler(t)
    if ignore_message:
        handler.refresh_ignore_message(
            code=code,
            start_date=start_date,
            end_date=end_date,
            t=t)
    else:
        handler.refresh(
            code=code,
            start_date=start_date,
            end_date=end_date,
            t=t)

def reload_by_category(category: Category, start_date: str, end_date: str, t: StockHistoryType, is_all: bool, ignore_message: bool = False):
    codes = get_codes(category)
    if not is_all:
        codes = get_followed_codes(category)
    handler = _create_history_handler(t)
    for code in codes:
        if ignore_message:
            handler.refresh_ignore_message(
                code=code,
                start_date=start_date,
                end_date=end_date,
                t=t)
        else:
            handler.refresh(
                code=code,
                start_date=start_date,
                end_date=end_date,
                t=t)
def _create_history_handler(t: StockHistoryType):
    model = get_history_model(t)
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        code = args.get('code')
        start_date = args.get('start_date')
        end_date = args.get('end_date')
        end_date = extend_end_date(end_date)
        return [
            model.code == code,
            model.date >= start_date,
            model.date <= end_date,
        ]

    return create_reload_handler(
        model=model,
        fetch_func=fetch,
        unique_fields=['code', 'date'],
        build_filter=build_filter,
        with_date_range=True
    )


def fetch(code: str, start_date: str, end_date: str, t: StockHistoryType) -> list:
    # 拉取 http://www.baostock.com/mainContent?file=stockKData.md
    category = Category.from_stock_code(code)
    if category == Category.X_XX or category == Category.A_BJ: # 暂不支持这两种
        logging.info(f"获取[{KEY_PREFIX}]数据暂不支持..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}")
        return []
    if category == Category.US_XX:
        return _fetch_us_stock_data(code, start_date, end_date, t)
    return _fetch_a_stock_data(code, start_date, end_date, t)



_baostock_lock = threading.Lock()
def _fetch_a_stock_data(code: str, start_date: str, end_date: str, t: StockHistoryType) -> list:
    # 拉取 http://www.baostock.com/mainContent?file=stockKData.md
    category = Category.from_stock_code(code)
    fields = {
        StockHistoryType.D: "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
        StockHistoryType.W: "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
        StockHistoryType.M: "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
        StockHistoryType.THIRTY_M: "date,time,code,open,high,low,close,volume,amount,adjustflag"
    }
    try:
        # 使用线程锁确保baostock API的调用是线程安全的
        with _baostock_lock:
            lg = bs.login()
            logging.info(f"登录结果为, code: {lg.error_code}, msg: {lg.error_msg}")

            logging.info(
                f"开始获取[{KEY_PREFIX}][{t.text}]数据..., 股票:{code}, 开始日期: {start_date}, 结束日期: {end_date}")
            fields = fields.get(t)
            rs = bs.query_history_k_data_plus(category.get_full_code(code, "."),
                                              fields,
                                              start_date=start_date, end_date=end_date, frequency=t.bs_frequency,
                                              adjustflag="1")
            logging.info(
                f"获取[{KEY_PREFIX}][{t.text}]数据结果为..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, code: {rs.error_code}, msg: {rs.error_msg}")
            if rs.error_code != '0':
                logging.error(
                    f"获取[{KEY_PREFIX}][{t.text}]数据失败..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, code: {rs.error_code}, msg: {rs.error_msg}")
                return None
            data_list = []
            while (rs.error_code == '0') & rs.next():
                row_data = rs.get_row_data()
                logging.info(
                    f"获取[{KEY_PREFIX}][{t.text}]数据为..., 分类: {category.fullText}, 股票:{code}, 日期: {row_data[0]}, 信息为: {row_data}")
                model_instance = None
                if t == StockHistoryType.W:
                    model_instance = StockHistoryW(
                        category=category,
                        code=code,
                        date=row_data[0],
                        opening=clean_numeric_value(row_data[2]),
                        highest=clean_numeric_value(row_data[3]),
                        lowest=clean_numeric_value(row_data[4]),
                        closing=clean_numeric_value(row_data[5]),
                        turnover_count=clean_numeric_value(row_data[6]),
                        turnover_amount=clean_numeric_value(row_data[7]),
                        turnover_ratio=clean_numeric_value(row_data[9]),
                        change=clean_numeric_value(row_data[10])
                    )
                elif t == StockHistoryType.M:
                    model_instance = StockHistoryM(
                        category=category,
                        code=code,
                        date=row_data[0],
                        opening=clean_numeric_value(row_data[2]),
                        highest=clean_numeric_value(row_data[3]),
                        lowest=clean_numeric_value(row_data[4]),
                        closing=clean_numeric_value(row_data[5]),
                        turnover_count=clean_numeric_value(row_data[6]),
                        turnover_amount=clean_numeric_value(row_data[7]),
                        turnover_ratio=clean_numeric_value(row_data[9]),
                        change=clean_numeric_value(row_data[10])
                    )
                elif t == StockHistoryType.THIRTY_M:
                    model_instance = StockHistory30M(
                        category=category,
                        code=code,
                        date=parse_baostock_datetime(row_data[1]),
                        opening=clean_numeric_value(row_data[3]),
                        highest=clean_numeric_value(row_data[4]),
                        lowest=clean_numeric_value(row_data[5]),
                        closing=clean_numeric_value(row_data[6]),
                        turnover_count=clean_numeric_value(row_data[7]),
                        turnover_amount=clean_numeric_value(row_data[8]),
                        # turnover_ratio=row_data[9],
                        # change=row_data[9]
                    )
                else:
                    model_instance = StockHistoryD(
                        category=category,
                        code=code,
                        date=row_data[0],
                        opening=clean_numeric_value(row_data[2]),
                        highest=clean_numeric_value(row_data[3]),
                        lowest=clean_numeric_value(row_data[4]),
                        closing=clean_numeric_value(row_data[5]),
                        turnover_count=clean_numeric_value(row_data[6]),
                        turnover_amount=clean_numeric_value(row_data[7]),
                        turnover_ratio=clean_numeric_value(row_data[9]),
                        change=clean_numeric_value(row_data[10])
                    )
                data_list.append(model_instance)
            logging.info(
                f"获取[{KEY_PREFIX}][{t.text}]数据成功..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, 共{len(data_list)}条记录")
            bs.logout()
        return data_list
    except Exception as e:
        logging.error(f"获取[{KEY_PREFIX}][{t.text}]数据异常: {str(e)}")
        # 确保在异常情况下也能正确登出
        with _baostock_lock:
            bs.logout()
        return data_list



# 美股数据获取使用通用限流器
# 使用平衡模式配置（可根据需要调整为 AGGRESSIVE_CONFIG 或 CONSERVATIVE_CONFIG）
_us_stock_limiter = get_rate_limiter("akshare_us_stock", BALANCED_CONFIG)


def _aggregate_minute_to_30min(df: pd.DataFrame) -> pd.DataFrame:
    """
    将1分钟数据聚合为30分钟数据

    Args:
        df: 1分钟数据，包含列：时间、开盘、收盘、最高、最低、成交量、成交额

    Returns:
        30分钟聚合数据
    """
    if df is None or df.empty:
        return df

    # 确保时间列是 datetime 类型
    df['时间'] = pd.to_datetime(df['时间'])

    # 设置时间为索引
    df.set_index('时间', inplace=True)

    # 按30分钟重采样
    # 开盘价：取第一个值
    # 最高价：取最大值
    # 最低价：取最小值
    # 收盘价：取最后一个值
    # 成交量：求和
    # 成交额：求和
    agg_rules = {
        '开盘': 'first',
        '最高': 'max',
        '最低': 'min',
        '收盘': 'last',
        '成交量': 'sum',
        '成交额': 'sum',
    }

    # 如果有最新价，也聚合
    if '最新价' in df.columns:
        agg_rules['最新价'] = 'last'

    # 重采样为30分钟
    df_30min = df.resample('30min').agg(agg_rules)

    # 移除空值行（可能在某些时间段没有交易）
    df_30min = df_30min.dropna()

    # 重置索引，将时间列恢复
    df_30min.reset_index(inplace=True)

    # 处理开盘价为0的情况：用前一条记录的收盘价代替
    # 使用 shift() 获取前一行的收盘价
    df_30min['前收盘'] = df_30min['收盘'].shift(1)

    # 记录需要修复的数量（用于日志）
    zero_open_count = (df_30min['开盘'] == 0).sum()

    # 当开盘价为0时，使用前一条的收盘价
    # 第一条记录如果开盘价为0，则使用当前的收盘价（因为没有前一条）
    df_30min['开盘'] = df_30min.apply(
        lambda row: row['前收盘'] if row['开盘'] == 0 and pd.notna(row['前收盘'])
                    else (row['收盘'] if row['开盘'] == 0 else row['开盘']),
        axis=1
    )

    # 删除临时列
    df_30min.drop(columns=['前收盘'], inplace=True)

    if zero_open_count > 0:
        logging.info(f"修复了 {zero_open_count} 条开盘价为0的记录（使用前一条收盘价）")

    logging.info(f"聚合分钟数据: 原始 {len(df)} 条 → 30分钟 {len(df_30min)} 条")

    return df_30min


def _fetch_us_stock_data(code: str, start_date: str, end_date: str, t: StockHistoryType) -> list:
    """使用 akshare 抓取美股数据（东财数据源，国内网络友好）"""
    def _fetch_data():
        # 使用通用限流器：请求前智能等待
        _us_stock_limiter.wait_before_request()

        logging.info(f"开始获取美股[{KEY_PREFIX}][{t.text}]数据..., 股票:{code}, 开始日期: {start_date}, 结束日期: {end_date}")

        # akshare 需要带前缀的股票代码（如 105.AAPL）
        # 根据测试，大部分美股使用 105 前缀
        symbol = f"105.{code}"

        try:
            # 30分钟数据使用分时接口
            if t == StockHistoryType.THIRTY_M:
                # stock_us_hist_min_em 返回1分钟数据，需要指定时间范围
                # 格式: YYYY-MM-DD HH:MM:SS
                start_datetime = f"{start_date} 00:00:00"
                end_datetime = f"{end_date} 23:59:59"

                df = ak.stock_us_hist_min_em(
                    symbol=symbol,
                    start_date=start_datetime,
                    end_date=end_datetime
                )

                if df is None or df.empty:
                    logging.warning(f"获取美股[{KEY_PREFIX}][{t.text}]分时数据为空, 股票: {code}, symbol: {symbol}")
                    _us_stock_limiter.handle_success()
                    return []

                # 将1分钟数据聚合为30分钟数据
                df = _aggregate_minute_to_30min(df)

            else:
                # 日线、周线、月线使用 stock_us_hist 接口
                period_map = {
                    StockHistoryType.D: "daily",
                    StockHistoryType.W: "weekly",
                    StockHistoryType.M: "monthly",
                }

                period = period_map.get(t, "daily")

                # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
                start_date_fmt = start_date.replace('-', '')
                end_date_fmt = end_date.replace('-', '')

                df = ak.stock_us_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    adjust="hfq"
                )
            if df is None or df.empty:
                logging.warning(f"获取美股[{KEY_PREFIX}][{t.text}]数据为空, 股票: {code}, symbol: {symbol}")
                # 数据为空也算成功（可能是该时间段没有交易数据）
                _us_stock_limiter.handle_success()
                return []

            # 请求成功，重置失败计数
            _us_stock_limiter.handle_success()

            data_list = []
            for index, row in df.iterrows():
                # 根据不同的时间类型创建相应的模型实例
                model_instance = None

                # 30分钟数据的字段名不同（来自分时接口）
                if t == StockHistoryType.THIRTY_M:
                    # 分时接口返回字段：时间、开盘、收盘、最高、最低、成交量、成交额
                    # 注意：时间列可能是索引，也可能是普通列
                    if '时间' in row:
                        date_str = str(row['时间'])
                    else:
                        date_str = str(index)

                    model_instance = StockHistory30M(
                        category=Category.US_XX,
                        code=code,
                        date=date_str,
                        opening=clean_numeric_value(row['开盘']),
                        highest=clean_numeric_value(row['最高']),
                        lowest=clean_numeric_value(row['最低']),
                        closing=clean_numeric_value(row['收盘']),
                        turnover_count=clean_numeric_value(row['成交量']),
                        turnover_amount=clean_numeric_value(row.get('成交额')),
                    )
                else:
                    # 日线、周线、月线数据字段：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
                    date_str = str(row['日期'])

                    if t == StockHistoryType.W:
                        model_instance = StockHistoryW(
                            category=Category.US_XX,
                            code=code,
                            date=date_str,
                            opening=clean_numeric_value(row['开盘']),
                            highest=clean_numeric_value(row['最高']),
                            lowest=clean_numeric_value(row['最低']),
                            closing=clean_numeric_value(row['收盘']),
                            turnover_count=clean_numeric_value(row['成交量']),
                            turnover_amount=clean_numeric_value(row['成交额']),
                            turnover_ratio=clean_numeric_value(row['换手率']),
                            change=clean_numeric_value(row['涨跌幅'])
                        )
                    elif t == StockHistoryType.M:
                        model_instance = StockHistoryM(
                            category=Category.US_XX,
                            code=code,
                            date=date_str,
                            opening=clean_numeric_value(row['开盘']),
                            highest=clean_numeric_value(row['最高']),
                            lowest=clean_numeric_value(row['最低']),
                            closing=clean_numeric_value(row['收盘']),
                            turnover_count=clean_numeric_value(row['成交量']),
                            turnover_amount=clean_numeric_value(row['成交额']),
                            turnover_ratio=clean_numeric_value(row['换手率']),
                            change=clean_numeric_value(row['涨跌幅'])
                        )
                    else:  # 日线数据
                        model_instance = StockHistoryD(
                            category=Category.US_XX,
                            code=code,
                            date=date_str,
                            opening=clean_numeric_value(row['开盘']),
                            highest=clean_numeric_value(row['最高']),
                            lowest=clean_numeric_value(row['最低']),
                            closing=clean_numeric_value(row['收盘']),
                            turnover_count=clean_numeric_value(row['成交量']),
                            turnover_amount=clean_numeric_value(row['成交额']),
                            turnover_ratio=clean_numeric_value(row['换手率']),
                            change=clean_numeric_value(row['涨跌幅'])
                        )
                data_list.append(model_instance)
            logging.info(
                f"获取美股[{KEY_PREFIX}][{t.text}]数据成功..., 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, 共{len(data_list)}条记录")
            return data_list

        except Exception as e:
            # 请求失败，触发冷却机制
            _us_stock_limiter.handle_failure()
            logging.error(f"获取美股[{KEY_PREFIX}][{t.text}]数据异常: {str(e)}, 股票: {code}")
            raise  # 重新抛出异常，让重试机制处理

    try:
        # 使用重试工具处理频率限制问题
        return retry_with_backoff(
            func=_fetch_data,
            max_retries=RATE_LIMIT_RETRY_CONFIG.max_retries,
            base_delay=RATE_LIMIT_RETRY_CONFIG.base_delay,
            max_delay=RATE_LIMIT_RETRY_CONFIG.max_delay,
            backoff_factor=RATE_LIMIT_RETRY_CONFIG.backoff_factor,
            jitter=RATE_LIMIT_RETRY_CONFIG.jitter,
            exceptions=(Exception,),
            logger=logging
        )
    except Exception as e:
        logging.error(f"获取美股[{KEY_PREFIX}][{t.text}]数据异常: {str(e)}")
        return []

def sync(t: StockHistoryType, is_all: bool, start_date=None, end_date=None) -> Dict[str, Any]:
    # 使用线程安全的计数器
    success_count = 0
    failed_count = 0
    processed_count = 0
    count_lock = threading.Lock()
    
    # 记录总开始时间
    total_start_time = time.time()
    
    # 如果没有提供时间范围，默认为近7天
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    # 转换为字符串格式
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    logging.info(f"开始同步[{KEY_PREFIX}][{t.text}]数据, 时间范围：{start_date_str} 至 {end_date_str}")
    
    # 收集所有需要同步的任务
    tasks = []
    categories = Category.get_all()

    for category in categories:
        logging.info(f"开始同步[{KEY_PREFIX}][{t.text}]数据，分类: {category.fullText}")
        codes = get_codes(category)
        if not is_all:
            codes = get_followed_codes(category)

        # 为每个股票代码创建任务
        for code in codes:
            tasks.append((code, category, start_date_str, end_date_str, t))

    # 获取总任务数
    total_tasks = len(tasks)
    logging.info(f"同步[{KEY_PREFIX}][{t.text}]数据, 总共有 {total_tasks} 个股票需要同步")

    # 定义单个股票同步的工作函数
    def sync_single_stock(task):
        code, category, start_date_str, end_date_str, t = task
        nonlocal success_count, failed_count, processed_count

        # 记录单个股票开始时间
        stock_start_time = time.time()

        try:
            # 每个线程使用独立的数据库会话
            with get_db_session() as session:
                reload_by_code(code, start_date_str, end_date_str, t, True)

            # 计算单个股票处理耗时
            stock_elapsed_time = time.time() - stock_start_time

            with count_lock:
                success_count += 1
                processed_count += 1
                remaining = total_tasks - processed_count
            logging.info(f"股票: {code} 处理[{KEY_PREFIX}][{t.text}]数据完成，耗时: {stock_elapsed_time:.2f}秒，还剩 {remaining} 个股票")
            return True, code, None
        except Exception as e:
            # 计算单个股票处理耗时
            stock_elapsed_time = time.time() - stock_start_time
            with count_lock:
                failed_count += 1
                processed_count += 1
                remaining = total_tasks - processed_count
            error_msg = str(e)
            logging.error(f"股票: {code} 处理[{KEY_PREFIX}][{t.text}]数据时出错: {error_msg}，耗时: {stock_elapsed_time:.2f}秒，还剩 {remaining} 个股票")
            return False, code, error_msg

    # 防封策略：根据分类动态调整并发数
    # 美股使用较低的并发数（因为 akshare 容易被限流）
    # A股使用较高的并发数（因为 baostock 相对稳定）
    us_stock_count = sum(1 for task in tasks if task[1] == Category.US_XX)
    if us_stock_count > 0:
        # 如果包含美股，使用低并发（串行或2-3个线程）
        max_workers = min(3, len(tasks) if tasks else 1)
        logging.info(f"检测到 {us_stock_count} 只美股，降低并发数至 {max_workers} 以防止被封")
    else:
        # 纯A股数据，使用正常并发
        max_workers = min(30, len(tasks) if tasks else 1)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {executor.submit(sync_single_stock, task): task for task in tasks}
        
        # 处理任务结果（移除所有UI消息显示）
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            code = task[0]
            try:
                # 只获取结果，不显示任何消息
                future.result()
            except Exception as e:
                with count_lock:
                    failed_count += 1
                    processed_count += 1
                    remaining = total_tasks - processed_count
                error_msg = f"股票: {code} 任务执行异常: {str(e)}，还剩 {remaining} 个股票"
                logging.error(error_msg)
    
    # 计算总耗时
    total_elapsed_time = time.time() - total_start_time
    logging.info(f"完成同步[{KEY_PREFIX}][{t.text}]数据, 时间范围：{start_date_str} 至 {end_date_str}")
    logging.info(f"总处理股票数: {total_tasks}, 成功: {success_count}, 失败: {failed_count}")
    logging.info(f"总耗时: {total_elapsed_time:.2f}秒, 平均每个股票耗时: {total_elapsed_time/total_tasks:.2f}秒")
    return {
        "success_count": success_count,
        "failed_count": failed_count
    }

