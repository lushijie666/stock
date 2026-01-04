import logging
from datetime import date, timedelta, datetime
from functools import partial
from typing import Dict, Any, List
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from models.stock_trade import StockTradeW, StockTrade30M, StockTradeM, StockTradeD, get_trade_model
from service.stock import reload, get_followed_codes, get_codes
from service.stock_chart import show_detail_dialog
from utils.convert import format_pattern_text
from utils.db import get_db_session
from utils.fetch_handler import create_reload_handler
from utils.message import show_message
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionConfig, ActionButton
from utils.session import get_session_key, SessionKeys, get_date_range
from utils.signal import  calculate_all_signals
from utils.table import format_pinyin_short

KEY_PREFIX = "stock_trade"

def show_detail(category: Category):
    t = st.radio(
        "选择时间周期",
        ["天", "周", "月", "30分钟"],
        horizontal=True,
        key=f"{KEY_PREFIX}_{category}_radio",
        label_visibility="collapsed"
    )
    handlers = {
        "天": lambda:  show_page(category, StockHistoryType.D),
        "周": lambda:  show_page(category, StockHistoryType.W),
        "月": lambda:  show_page(category, StockHistoryType.M),
        "30分钟": lambda:  show_page(category, StockHistoryType.THIRTY_M),
    }
    handlers.get(t, lambda: None)()

def show_page(category: Category, t: StockHistoryType):
    try:
        model = get_trade_model(t)
        # 获取所有策略类型的完整文本显示
        all_strategies = [strategy.fullText for strategy in StrategyType]
        strategy_options = ["策略类型"] + sorted(all_strategies)
        strategy_map = {strategy.fullText: strategy.code for strategy in StrategyType}
        strategy_map["策略类型"] = "全部"

        # 获取所有信号类型的完整文本显示
        all_signal_types = [signal_type.fullText for signal_type in SignalType]
        signal_type_options = ["信号类型"] + sorted(all_signal_types)
        signal_type_map = {signal_type.fullText: signal_type.value for signal_type in SignalType}
        signal_type_map["信号类型"] = "全部"

        # 获取所有信号强度的完整文本显示
        all_signal_strengths = [signal_strength.fullText for signal_strength in SignalStrength]
        signal_strength_options = ["信号强度"] + sorted(all_signal_strengths)
        signal_strength_map = {signal_strength.fullText: signal_strength.value for signal_strength in SignalStrength}
        signal_strength_map["信号强度"] = "全部"

        with get_db_session() as session:
            # 其他数据按日期排序
            query = session.query(
                model.code,
                Stock.name,
                Stock.pinyin,
                model.date,
                model.signal_type,
                model.signal_strength,
                model.strategy_type,
                model.pattern_name,
                model.updated_at,
            ).join(Stock, model.code == Stock.code).filter(
                model.category == category,
                model.removed == False
            ).order_by(model.date.desc())
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
                    'pattern_name': st.column_config.TextColumn('模式', help="K线形态名称", width="large"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                },
                # 格式化函数
                format_funcs={
                    'pinyin': format_pinyin_short,
                    'signal_type': lambda x: SignalType.lookup(x).fullText,
                    'signal_strength': lambda x: SignalStrength.lookup(x).fullText,
                    'strategy_type': lambda x: ', '.join([StrategyType.lookup(code.strip()).fullText for code in x.split(',')]) if x and ',' in x else ( StrategyType.lookup(x).fullText if x else ''),
                    'pattern_name': lambda x: x if x else '-'  # 形态名称，无形态时显示 -
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
                                    model.code.ilike(f"%{value}%"),
                                    Stock.name.ilike(f"%{value}%"),
                                    Stock.pinyin.ilike(f"%{value}%")
                                )
                            )
                        ),
                        SearchField(
                            field="strategy_type",
                            label="策略类型",
                            type="select",
                            options=strategy_options,
                            default="策略类型",
                            filter_func=lambda query, value: (
                                query.filter(
                                    or_(
                                        model.strategy_type.like(f"{strategy_map.get(value, value)},%"),  # 策略在开头
                                        model.strategy_type.like(f"%{strategy_map.get(value, value)},%"),  # 策略在中间
                                        model.strategy_type.like(f"%{strategy_map.get(value, value)}"),  # 策略在结尾
                                        model.strategy_type == strategy_map.get(value, value)  # 单一策略
                                    )
                                ) if value and value != "策略类型" and strategy_map.get(value,value) != "全部" else query
                            )
                        ),
                        SearchField(
                            field="signal_type",
                            label="信号类型",
                            type="select",
                            options=signal_type_options,
                            default="信号类型",
                            filter_func=lambda query, value: query.filter(
                                model.signal_type.like(f"%{signal_type_map.get(value, value)}%")
                            ) if value and value != "信号类型" else query
                        ),
                        SearchField(
                            field="signal_strength",
                            label="信号强度",
                            type="select",
                            options=signal_strength_options,
                            default="信号强度",
                            filter_func=lambda query, value: query.filter(
                                model.signal_strength.like(f"%{signal_strength_map.get(value, value)}%")
                            ) if value and value != "信号强度" else query
                        ),
                        SearchField(
                            field="start_date",
                            label="开始日期",
                            type="date",
                            default=date.today() - timedelta(days=365),
                            max_date=date.today(),
                            placeholder="输入开始日期",
                            filter_func=lambda q, v: q.filter(model.date >= datetime.combine(v, datetime.min.time())) if v else q
                        ),
                        SearchField(
                            field="end_date",
                            label="结束日期",
                            type="date",
                            default=date.today(),
                            max_date=date.today(),
                            placeholder="输入结束日期",
                            filter_func=lambda q, v: q.filter(model.date <= datetime.combine(v, datetime.max.time())) if v else q                        )
                    ],
                    layout=[1, 1, 1, 1, 1, 1]
                ),
                action_config=ActionConfig(
                    buttons=[
                        ActionButton(
                            icon="🐙",
                            label="更新",
                            handler=partial(reload, category=category, t=t,ignore_message=False),
                            type="primary"
                        ),
                    ],
                    layout=[1, 0.2]  # 每个按钮占一列
                ),
                title=category.fullText,
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}', category=category),
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
        selected_row = selected_rows[0]
        show_detail_dialog(selected_row['code'])


def reload(category: Category, t: StockHistoryType, ignore_message: bool = False):
    # 获取选择的日期范围
    prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{t}', category=category)
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
            reload_by_code(code, t, start_date, end_date, ignore_message)
        except Exception as e:
            logging.error(f"股票: {code} 处理时出错: {str(e)}")
            continue


def reload_by_code(code: str, t: StockHistoryType, start_date: Any = None, end_date: Any = None, ignore_message: bool = False):
    if start_date is None:
        start_date = date.today() - timedelta(days=365)
    if end_date is None:
        end_date = date.today()
    with get_db_session() as session:
        model = get_trade_model(t)
        session.query(model).filter(
            model.code == code,
        ).delete()
        session.commit()
    handler = _create_trade_handler(t)
    if ignore_message :
        handler.refresh_ignore_message(
            code=code,
            t=t,
            start_date=start_date,
            end_date=end_date,
            limit=200,
        )
    else:
        handler.refresh(
            code=code,
            t=t,
            start_date=start_date,
            end_date=end_date,
            limit=200,
        )

def _create_trade_handler(t: StockHistoryType):
    model = get_trade_model(t)
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        """构建过滤条件"""
        code = args.get('code')
        filters = [model.code == code]
        return filters
    return create_reload_handler(
        model=model,
        fetch_func=fetch,
        unique_fields=['code', 'date', 'strategy_type'],
        build_filter=build_filter,
        with_date_range=False  # 我们已经在fetch_func中处理了日期范围
    )

def fetch(code: str, t: StockHistoryType, start_date: Any = None, end_date: Any =  None, limit: int = 200) -> list:
    logging.info(f"开始获取[{KEY_PREFIX}][{t.text}]数据..., 股票:{code}")
    # 获取历史数据模型类
    model = get_history_model(t)
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
    logging.info(f"获取[{KEY_PREFIX}]数据的历史数据[{t.text}]完成..., 股票:{code}, 共{len(rows)}条")
    if not rows:
        return []

    # 转换为DataFrame，使用元组解包而不是模型实例属性访问
    df = pd.DataFrame([{
        'date': row[0],  # date
        'opening': float(row[1]) if row[1] is not None else 0.0,  # opening
        'closing': float(row[2]) if row[2] is not None else 0.0,  # closing
        'highest': float(row[3]) if row[3] is not None else 0.0,  # highest
        'lowest': float(row[4]) if row[4] is not None else 0.0,  # lowest
        'turnover_count': float(row[5]) if row[5] is not None else 0.0  # turnover_count
    } for row in rows])

    category = Category.from_stock_code(code)
    # 计算信号
    signals = calculate_all_signals(df, merge_and_filter=True)
    logging.info(f"计算[{KEY_PREFIX}][{t.text}]数据的买卖信号完成..., 股票:{code}, 共{len(signals)}条")
    # 转换为StockTrade对象
    stock_trades = []
    for signal in signals:
        signal_date = signal['date']
        # 格式化模式文本
        formatted_pattern = format_pattern_text(signal)

        model_instance = None
        if t == StockHistoryType.W:
            model_instance = StockTradeW(
                code=code,
                category=category.value,
                date=signal_date,
                signal_type=signal['type'].value,
                signal_strength=signal['strength'].value,
                strategy_type=signal['strategy_code'],
                pattern_name=formatted_pattern,
                removed=False
            )
        elif t == StockHistoryType.M:
            model_instance = StockTradeM(
                code=code,
                category=category.value,
                date=signal_date,
                signal_type=signal['type'].value,
                signal_strength=signal['strength'].value,
                strategy_type=signal['strategy_code'],
                pattern_name=formatted_pattern,
                removed=False
            )
        elif t == StockHistoryType.THIRTY_M:
            model_instance = StockTrade30M(
                code=code,
                category=category.value,
                date=signal_date,
                signal_type=signal['type'].value,
                signal_strength=signal['strength'].value,
                strategy_type=signal['strategy_code'],
                pattern_name=formatted_pattern,
                removed=False
            )
        else:
            model_instance = StockTradeD(
                code=code,
                category=category.value,
                date=signal_date,
                signal_type=signal['type'].value,
                signal_strength=signal['strength'].value,
                strategy_type=signal['strategy_code'],
                pattern_name=formatted_pattern,
                removed=False
            )
        stock_trades.append(model_instance)
    return stock_trades


def sync(t: StockHistoryType, is_all: bool, start_date=None, end_date=None) -> Dict[str, Any]:
    # 如果没有提供时间范围，默认为近7天
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    success_count = 0
    failed_count = 0
    processed_count = 0
    count_lock = threading.Lock()

    # 记录总开始时间
    total_start_time = time.time()

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    logging.info(f"开始同步[{KEY_PREFIX}][{t.text}]数据, 时间范围：{start_date_str} 至 {end_date_str}")

    # 收集所有需要同步的任务
    tasks = []
    categories = Category.get_all()

    for category in categories:
        logging.info(f"准备同步[{KEY_PREFIX}][{t.text}]数据，分类: {category.fullText}")
        codes = get_codes(category)
        if not is_all:
            codes = get_followed_codes(category)

        # 为每个股票代码创建任务
        for code in codes:
            tasks.append((code, category, start_date, end_date))
    # 获取总任务数
    total_tasks = len(tasks)
    logging.info(f"同步[{KEY_PREFIX}][{t.text}]数据, 总共有 {total_tasks} 个股票需要同步")

    # 定义单个股票同步的工作函数
    def sync_single_stock(task):
        code, category, start_date_str, end_date_str = task
        nonlocal success_count, failed_count, processed_count
        # 记录单个股票开始时间
        stock_start_time = time.time()
        try:
            reload_by_code(code, t, start_date_str, end_date_str, True)
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
            logging.error(f"股票: {code} 处理[{KEY_PREFIX}][{t.text}]数据时出错: {str(e)}，耗时: {stock_elapsed_time:.2f}秒，还剩 {remaining} 个股票")
            return False, code, str(e)

    # 使用线程池并行处理任务
    max_workers = min(30, len(tasks) if tasks else 1)  # 设置最大线程数，避免资源耗尽

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {executor.submit(sync_single_stock, task): task for task in tasks}

        # 处理任务结果
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            code = task[0]
            try:
                future.result()
            except Exception as e:
                with count_lock:
                    failed_count += 1
                    processed_count += 1
                    remaining = total_tasks - processed_count
                logging.error(f"股票: {code} 任务[{KEY_PREFIX}][{t.text}]数据执行异常: {str(e)}，还剩 {remaining} 个股票")

    # 计算总耗时
    total_elapsed_time = time.time() - total_start_time
    logging.info(f"完成同步[{KEY_PREFIX}][{t.text}]数据")
    logging.info(f"总处理股票数: {total_tasks}, 成功: {success_count}, 失败: {failed_count}")
    logging.info(
        f"总耗时: {total_elapsed_time:.2f}秒, 平均每个股票耗时: {total_elapsed_time / total_tasks:.2f}秒" if total_tasks > 0 else "无任务需要处理")

    return {
        "success_count": success_count,
        "failed_count": failed_count
    }