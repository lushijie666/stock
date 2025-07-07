# 定义字段映射
import datetime
from datetime import datetime

import logging
from datetime import date
from typing import Optional
from sqlalchemy.orm import Query
import pandas as pd

COLUMN_MAPPINGS = {
    'code': ['证券代码', 'A股代码', '代码', 'code', 'CODE'],
    'name': ['证券简称', 'A股简称', '名称', 'name', 'NAME'],
    'ipo_at': ['上市日期', 'A股上市日期'],
    'total_capital': ['总股本', 'A股总股本'],
    'flow_capital': ['流通股本', 'A股流通股本'],
}

def clean_number_value(value: str) -> Optional[int]:
    """清理数字字符串，移除逗号并转换为整数"""
    try:
        if pd.isna(value):
            return None
        # 移除逗号和空格，然后转换为整数
        cleaned = str(value).replace(',', '').replace(' ', '')
        return int(float(cleaned)) if cleaned else None
    except (ValueError, TypeError):
        return None

def get_column_value(row: pd.Series, field: str, default: str = "") -> str:
    try:
        # 获取可能的列名列表
        possible_columns = COLUMN_MAPPINGS.get(field, [])
        # 遍历可能的列名
        for col in possible_columns:
            if col in row.index:
                value = row[col]
                return str(value) if pd.notna(value) else default

        return default
    except Exception as e:
        logging.error(f"Error getting column value for {field}: {str(e)}")
        return default

def date_range_filter(query: Query, field: str, value: date, date_field: str = 'date') -> Query:
    """日期范围过滤函数"""
    column = getattr(query.column_descriptions[0]['type'], date_field)  # 使用实际的日期字段名
    if field == 'start_date':
        return query.filter(column >= value)
    elif field == 'end_date':
        return query.filter(column <= value)
    return query


def date_str_to_datetime(date_str: str) -> tuple[datetime, datetime]:
    """
    将 YYYYMMDD 格式的字符串转换为当天的开始和结束时间
    例如: "20210101" -> (2021-01-01 00:00:00, 2021-01-01 23:59:59)
    """
    try:
        # 将字符串转换为 datetime
        d = datetime.strptime(date_str, '%Y%m%d')
        # 获取当天开始和结束时间
        start_time = datetime.combine(d.date(), datetime.min.time())
        end_time = datetime.combine(d.date(), datetime.max.time())
        return start_time, end_time
    except Exception as e:
        logging.error(f"日期转换错误: {str(e)}")
        return None, None

def parse_datetime(date_str: str, time_str: str) -> datetime:
    """
    解析日期和时间字符串为 DateTime 对象
    :param date_str: 日期字符串 (YYYY-MM-DD)
    :param time_str: 时间字符串 (HH:MM:SS)
    :return: DateTime 对象
    """
    try:
        datetime_str = f"{date_str} {time_str}"
        return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"Error parsing datetime: {date_str} {time_str}, error: {str(e)}")
        return None

def convert_date_format(date_str: str) -> str:
    """
    将 YYYY-MM-DD 格式转换为 YYYYMMDD 格式
    """
    try:
        # 先将字符串转换为 datetime 对象
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        # 再将 datetime 对象转换为目标格式字符串
        return date_obj.strftime('%Y%m%d')
    except Exception as e:
        logging.error(f"Error converting date format: {date_str}, error: {str(e)}")
        return None