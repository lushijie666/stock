# 实时行情数据
import time
from datetime import datetime as dt
from functools import partial
from typing import Callable, Dict, Any, List

import akshare as ak
import pandas as pd
import logging
import streamlit as st
from requests import Session

from enums.category import Category
from utils.db import get_db_session, upsert_objects
from utils.fetch_handler import create_reload_handler
from utils.session import get_session_key, SessionKeys
from utils.table import format_percent, format_volume, format_amount
from utils.message import show_message
from models.real_time_data import RealTimeData
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionConfig, ActionButton

KEY_PREFIX = "real_time_data"

def show_page(category: Category):
    try:
        with get_db_session() as session:
            # 构建查询
            query = session.query(RealTimeData).filter(
                RealTimeData.category == category,
                RealTimeData.removed == False
            ).order_by(RealTimeData.code.asc())
            # 使用通用分页显示
            paginate_dataframe(
                query,
                10,
                columns_config={
                    # 基础信息
                   # 'category': st.column_config.TextColumn('分类', help="股票分类"),
                    'code': st.column_config.TextColumn('股票代码', help="股票代码"),
                    'name': st.column_config.TextColumn('股票名称', help="股票名称"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                    # 价格相关
                    'current_price': st.column_config.NumberColumn('最新价', help="当前交易价格", format="%.3f"),
                    'change_percent': st.column_config.NumberColumn('涨跌幅', help="价格变动百分比", format="%.2f%%"),
                    'change_amount': st.column_config.NumberColumn('涨跌额', help="价格变动额", format="%.3f"),
                    'turnover_count': st.column_config.TextColumn('成交量(手)', help="成交股数"),
                    'turnover_amount': st.column_config.TextColumn('成交额(万/亿)', help="成交金额"),
                    # 交易指标
                    'swing': st.column_config.NumberColumn('振幅', help="当日最高最低价格变动幅度", format="%.2f%%"),
                    'highest': st.column_config.NumberColumn('最高', help="当日最高价", format="%.3f"),
                    'lowest': st.column_config.NumberColumn('最低', help="当日最低价", format="%.3f"),
                    'today_open': st.column_config.NumberColumn('今开', help="今日开盘价", format="%.3f"),
                    'yesterday_close': st.column_config.NumberColumn('昨收', help="昨日收盘价", format="%.3f"),
                    # 交易比率
                    'quantity_ratio': st.column_config.NumberColumn('量比', help="当日成交量与过去5日平均成交量之比", format="%.2f"),
                    'turnover_ratio': st.column_config.NumberColumn('换手率', help="成交股数与流通股数之比", format="%.2f%%"),
                    'pe_ratio': st.column_config.NumberColumn('市盈率', help="股价与每股收益之比", format="%.2f"),
                    'pb_ratio': st.column_config.NumberColumn('市净率', help="股价与每股净资产之比", format="%.2f%%"),
                    # 市值
                    'total_value': st.column_config.TextColumn('总市值(亿)', help="公司总市值"),
                    'traded_value': st.column_config.TextColumn('流通市值(亿)', help="流通股市值"),
                    # 涨跌指标
                    'teeming_ratio': st.column_config.NumberColumn('涨速', help="最近一笔成交相对于上一笔成交的涨跌幅", format="%.2f%%"),
                    'minute_5_change': st.column_config.NumberColumn('5分钟涨跌', help="5分钟价格涨跌幅",format="%.2f%%"),
                    'day_60_change': st.column_config.NumberColumn('60日涨跌幅', help="60个交易日价格涨跌幅", format="%.2f%%"),
                    'ytd_change': st.column_config.NumberColumn('年初至今涨跌幅', help="从年初至今的价格涨跌幅", format="%.2f%%"),
                },
                # 格式化函数
                format_funcs={
                    'turnover_amount': format_amount,
                    'total_value': format_amount,
                    'traded_value': format_amount,
                    'turnover_count': format_volume,
                    'change_percent': format_percent,
                    'swing': format_percent,
                    'turnover_ratio': format_percent,
                    'teeming_ratio': format_percent,
                    'minute_5_change': format_percent,
                    'day_60_change': format_percent,
                    'ytd_change': format_percent,
                },
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="code",
                            label="股票代码",
                            type="text",
                            placeholder="输入股票代码"
                        ),
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
                    layout=[1, 0.1]  # 每个按钮占一列
                ),
                title=category.fullText,
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}', category=category),
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")

def reload(category: Category):
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        return [
            RealTimeData.category == category,
        ]
    history_handler = create_reload_handler(
        model=RealTimeData,
        fetch_func=fetch,
        unique_fields=['code'],
        build_filter=build_filter,
        mark_existing=True,
    )
    return history_handler.refresh(
        category=category)

def fetch(category: Category) -> list:
    # 拉取 https://akshare.akfamily.xyz/data/stock/stock.html#id14
    fetch_functions = {
        Category.A_SH: ak.stock_zh_a_spot_em,
        Category.A_SZ: ak.stock_zh_a_spot_em,
        Category.A_BJ: ak.stock_zh_a_spot_em,
    }
    try:
        if fetch_func := fetch_functions.get(category):
            logging.info(f"开始获取[real_time_data]数据..., 分类: {category.text}")
            df = fetch_func()
            logging.info(f"成功获取[real_time_data]数据，分类: {category.text}, 共 {len(df)} 条记录")
            # 数据类型转换
            numeric_columns = [
                "最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅",
                "最高", "最低", "今开", "昨收", "量比",
                "换手率", "市盈率-动态", "市净率", "总市值",
                "流通市值", "涨速", "5分钟涨跌", "60日涨跌幅",
                "年初至今涨跌幅"
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            data = []
            for _, row in df.iterrows():
                try:
                    code=row.get("代码")
                    cls=Category.from_stock_code(code)
                    if cls != category:
                        continue
                    current_price=row.get("最新价")
                    if pd.isna(current_price) or current_price == "":
                        continue

                    data.append(RealTimeData(
                        category=category,
                        code=code,
                        #name=row.get("名称"),
                        current_price=current_price,
                        change_percent=row.get("涨跌幅"),
                        change_amount=row.get("涨跌额"),
                        turnover_count=row.get("成交量"),
                        turnover_amount=row.get("成交额"),
                        swing=row.get("振幅"),
                        highest=row.get("最高"),
                        lowest=row.get("最低"),
                        today_open=row.get("今开"),
                        yesterday_close=row.get("昨收"),
                        quantity_ratio=row.get("量比"),
                        turnover_ratio=row.get("换手率"),
                        pe_ratio=row.get("市盈率-动态"),
                        pb_ratio=row.get("市净率"),
                        total_value=row.get("总市值"),
                        traded_value=row.get("流通市值"),
                        teeming_ratio=row.get("涨速"),
                        minute_5_change=row.get("5分钟涨跌"),
                        day_60_change=row.get("60日涨跌幅"),
                        ytd_change=row.get("年初至今涨跌幅"),
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


def sync_real_time_data() -> Dict[str, Any]:
    success_count = 0
    failed_count = 0
    logging.info(f"开始同步实时数据")
    try:
        categories = Category.get_all()
        for category in categories:
            try:
                logging.info(f"处理分类 {category.fullText}")
                reload(category)
                success_count += 1
                logging.info(f"成功同步分类 {category.fullText} 的实时数据")
            except Exception as e:
                failed_count += 1
                logging.error(f"同步分类 {category.fullText} 的实时数据失败: {str(e)}")

        logging.info(f"实时数据同步完成，成功: {success_count}, 失败: {failed_count}")
        return {
            "success_count": success_count,
            "failed_count": failed_count
        }

    except Exception as e:
        logging.error(f"实时数据同步过程中发生错误: {str(e)}")
        return {
            "success_count": success_count,
            "failed_count": failed_count
        }