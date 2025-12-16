# 历史行情
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
from enums.category import Category
from enums.history_type import StockHistoryType

from service.stock import get_codes, get_followed_codes
from utils.background_task import BackgroundTaskExecutor
from utils.convert import date_range_filter, parse_baostock_datetime, clean_numeric_value, format_date_by_type
from utils.fetch_handler import create_reload_handler
from models.stock_history import get_history_model, StockHistoryW, StockHistoryD, StockHistoryM,StockHistory30M
from utils.db import get_db_session

from utils.message import show_message
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionButton, ActionConfig
from utils.session import get_session_key, SessionKeys, get_date_range
from utils.table import  format_percent, format_volume

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

# 为baostock API创建线程锁，确保同一时间只有一个线程在使用API
_baostock_lock = threading.Lock()



def fetch(code: str, start_date: str, end_date: str, t: StockHistoryType) -> list:
    # 拉取 http://www.baostock.com/mainContent?file=stockKData.md
    category = Category.from_stock_code(code)
    if category == Category.X_XX or category == Category.A_BJ: # 暂不支持这两种
        logging.info(f"获取[{KEY_PREFIX}]数据暂不支持..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}")
        return []
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

            logging.info(f"开始获取[{KEY_PREFIX}]数据..., 股票:{code}, 开始日期: {start_date}, 结束日期: {end_date}")
            fields = fields.get(t)
            rs = bs.query_history_k_data_plus(category.get_full_code(code, "."),
                                            fields,
                                            start_date=start_date, end_date=end_date, frequency=t.bs_frequency, adjustflag="1")
            logging.info( f"获取[{KEY_PREFIX}]数据结果为..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, code: {rs.error_code}, msg: {rs.error_msg}")
            if rs.error_code != '0':
                logging.error( f"获取[{KEY_PREFIX}]数据失败..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, code: {rs.error_code}, msg: {rs.error_msg}")
                return None
            data_list = []
            while (rs.error_code == '0') & rs.next():
                row_data = rs.get_row_data()
                logging.info(
                    f"获取[{KEY_PREFIX}]数据为..., 分类: {category.fullText}, 股票:{code}, 日期: {row_data[0]}, 信息为: {row_data}")
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
                        #turnover_ratio=row_data[9],
                        #change=row_data[9]
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
            logging.info( f"获取[{KEY_PREFIX}]数据成功..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, 共{len(data_list)}条记录")
            bs.logout()
        return data_list
    except Exception as e:
        logging.error(f"获取[{KEY_PREFIX}]数据异常: {str(e)}")
        # 确保在异常情况下也能正确登出
        with _baostock_lock:
            bs.logout()
        return data_list

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
    logging.info(f"开始同步[{KEY_PREFIX}]数据, 时间范围：{start_date_str} 至 {end_date_str}")
    
    # 收集所有需要同步的任务
    tasks = []
    categories = Category.get_all()
    
    for category in categories:
        logging.info(f"开始同步[{KEY_PREFIX}]数据，分类: {category.fullText}")
        codes = get_codes(category)
        if not is_all:
            codes = get_followed_codes(category)
        
        # 为每个股票代码创建任务
        for code in codes:
            tasks.append((code, category, start_date_str, end_date_str, t))
    
    # 获取总任务数
    total_tasks = len(tasks)
    logging.info(f"总共有 {total_tasks} 个股票需要同步")
    
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
            logging.info(f"股票: {code} 处理完成，耗时: {stock_elapsed_time:.2f}秒，还剩 {remaining} 个股票")
            return True, code, None
        except Exception as e:
            # 计算单个股票处理耗时
            stock_elapsed_time = time.time() - stock_start_time
            with count_lock:
                failed_count += 1
                processed_count += 1
                remaining = total_tasks - processed_count
            logging.error(f"股票: {code} 处理时出错: {str(e)}，耗时: {stock_elapsed_time:.2f}秒，还剩 {remaining} 个股票")
            return False, code, error_msg
    
    # 使用线程池并行处理任务
    max_workers = min(30, len(tasks) if tasks else 1)  # 设置最大线程数，避免资源耗尽
    
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
    logging.info(f"完成同步[{KEY_PREFIX}]数据, 时间范围：{start_date_str} 至 {end_date_str}")
    logging.info(f"总处理股票数: {total_tasks}, 成功: {success_count}, 失败: {failed_count}")
    logging.info(f"总耗时: {total_elapsed_time:.2f}秒, 平均每个股票耗时: {total_elapsed_time/total_tasks:.2f}秒")
    return {
        "success_count": success_count,
        "failed_count": failed_count
    }

