# 历史行情
import streamlit as st
import logging
from collections import OrderedDict
import baostock as bs
from typing import Dict, Any, List
from functools import partial
from sqlalchemy.orm import Session
from enums.category import Category
from enums.history_type import StockHistoryType

from service.stock import get_codes, get_followed_codes
from utils.convert import date_range_filter, parse_baostock_datetime
from utils.fetch_handler import create_reload_handler
from models.stock_history import get_history_model, StockHistoryW, StockHistoryD, StockHistoryM,StockHistory30M
from utils.db import get_db_session
from datetime import date, timedelta
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionButton, ActionConfig
from utils.session import get_session_key, SessionKeys, get_date_range
from utils.table import  format_percent, format_volume

KEY_PREFIX = "stock_history"


def show_page(stock, t: StockHistoryType):
    try:
        model = get_history_model(t)
        with get_db_session() as session:
            if t == StockHistoryType.THIRTY_M:
                query = session.query(model).filter(
                    model.code == stock.code,
                    model.removed == False
                ).order_by(model.date.desc(), model.time.desc())
            else:
                # 其他数据按日期排序
                query = session.query(model).filter(
                    model.code == stock.code,
                    model.removed == False
                ).order_by(model.date.desc())

                # 使用 OrderedDict 按指定顺序构建列配置
            columns_config = OrderedDict([
                ('code', st.column_config.TextColumn('股票代码', help="股票代码")),
                ('date', st.column_config.DateColumn('日期', help="日期")),
            ])

            # 如果是30分钟类型，插入time字段
            if t == StockHistoryType.THIRTY_M:
                columns_config['time'] = st.column_config.TimeColumn('时间', help="交易时间", width="small")

            # 继续添加其他字段
            columns_config.update({
                'opening': st.column_config.NumberColumn('开盘', help="当日开盘价", format="%.3f"),
                'closing': st.column_config.NumberColumn('收盘', help="当日收盘价", format="%.3f"),
                'highest': st.column_config.NumberColumn('最高', help="当日最高价", format="%.3f"),
                'lowest': st.column_config.NumberColumn('最低', help="当日最低价", format="%.3f"),
                'turnover_count': st.column_config.TextColumn('成交量(手)', help="成交股数"),
                'turnover_amount': st.column_config.TextColumn('成交额(元)', help="成交金额"),
                'change': st.column_config.NumberColumn('涨跌幅', help="涨跌幅", format="%.2f%%"),
                'turnover_ratio': st.column_config.NumberColumn('换手率', help="成交股数与流通股数之比", format="%.2f%%"),
                'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
            })

            paginate_dataframe(
                query,
                10,
                columns_config=columns_config,
                # 格式化函数
                format_funcs={
                    'turnover_count': format_volume,
                    'turnover_ratio': format_percent,
                    'change': format_percent,
                },
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="start_date",
                            label="开始日期",
                            type="date",
                            default=date.today() - timedelta(days=30),
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
                title=f'{stock.category} {stock.code} ({stock.name}) - 「{t.text}」',
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_{t}_date', category=stock.category),
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_detail(stock):
    t = st.radio(
        "",
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

def reload_by_code(code: str, start_date: str, end_date: str, t: StockHistoryType):
    handler = _create_history_handler(t)
    handler.refresh(
        code=code,
        start_date=start_date,
        end_date=end_date,
        t=t)

def reload_by_category(category: Category, start_date: str, end_date: str, t: StockHistoryType, is_all: bool):
    codes = get_codes(category)
    if not is_all:
        codes = get_followed_codes(category)
    handler = _create_history_handler(t)
    for code in codes:
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
        lg = bs.login()
        logging. info(f"登录结果为, code: {lg.error_code}, msg: {lg.error_msg}")

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
                    opening=row_data[2],
                    highest=row_data[3],
                    lowest=row_data[4],
                    closing=row_data[5],
                    turnover_count=row_data[6],
                    turnover_amount=row_data[7],
                    turnover_ratio=row_data[9],
                    change=row_data[10]
                )
            elif t == StockHistoryType.M:
                model_instance = StockHistoryM(
                    category=category,
                    code=code,
                    date=row_data[0],
                    opening=row_data[2],
                    highest=row_data[3],
                    lowest=row_data[4],
                    closing=row_data[5],
                    turnover_count=row_data[6],
                    turnover_amount=row_data[7],
                    turnover_ratio=row_data[9],
                    change=row_data[10]
                )
            elif t == StockHistoryType.THIRTY_M:
                model_instance = StockHistory30M(
                    category=category,
                    code=code,
                    date=row_data[0],
                    time=parse_baostock_datetime(row_data[1]),
                    opening=row_data[3],
                    highest=row_data[4],
                    lowest=row_data[5],
                    closing=row_data[6],
                    turnover_count=row_data[7],
                    turnover_amount=row_data[8],
                    #turnover_ratio=row_data[9],
                    #change=row_data[9]
                )
            else:
                model_instance = StockHistoryD(
                    category=category,
                    code=code,
                    date=row_data[0],
                    opening=row_data[2],
                    highest=row_data[3],
                    lowest=row_data[4],
                    closing=row_data[5],
                    turnover_count=row_data[6],
                    turnover_amount=row_data[7],
                    turnover_ratio=row_data[9],
                    change=row_data[10]

                )
            data_list.append(model_instance)
        logging.info( f"获取[{KEY_PREFIX}]数据成功..., 分类: {category.fullText}, 股票: {code}, 开始日期: {start_date}, 结束日期: {end_date}, 共{len(data_list)}条记录")
        bs.logout()
        return data_list
    except Exception as e:
        logging.error(f"获取[{KEY_PREFIX}]数据异常: {str(e)}")
        bs.logout()
        return data_list


def sync(t: StockHistoryType, is_all: bool, start_date=None, end_date=None) -> Dict[str, Any]:
    success_count = 0
    failed_count = 0
    # 如果没有提供时间范围，默认为近7天
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    # 转换为字符串格式
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    logging.info(f"开始同步[{KEY_PREFIX}]数据, 时间范围：{start_date_str} 至 {end_date_str}")
    categories = Category.get_all()
    for category in categories:
        logging.info(f"开始同步[{KEY_PREFIX}]数据，分类: {category.fullText}")
        codes = get_codes(category)
        if not is_all:
            codes = get_followed_codes(category)
        for code in codes:
            try:
                reload_by_code(code, start_date_str, end_date_str, t)
                success_count += 1
            except Exception as e:
                failed_count += 1
            logging.info(f"同步[{KEY_PREFIX}]的数据完成...，分类: {category.fullText}, 股票: {code}")
    logging.info(f"同步[{KEY_PREFIX}]数据完成，成功数: {success_count}, 失败数: {failed_count}")
    return {
        "success_count": success_count,
        "failed_count": failed_count
    }

