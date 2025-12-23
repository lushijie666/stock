# 定义字段映射
import datetime
from datetime import datetime, time

import logging
from datetime import date
from typing import Optional, List, Dict
from sqlalchemy.orm import Query
import pandas as pd

from enums.history_type import StockHistoryType

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

def clean_numeric_value(value: str) -> Optional[float]:
    """清理数值字符串，将无效值转换为None
    
    Args:
        value: 要清理的数值字符串
        
    Returns:
        float或None: 清理后的数值，如果无效则返回None
    """
    try:
        if value is None or value == "":
            return None
        if pd.isna(value):
            return None
        # 移除逗号和空格
        cleaned = str(value).replace(',', '').replace(' ', '')
        if not cleaned:
            return None
        # 转换为float
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def clean_name(name: str) -> str:
    replacements = {
        'Ａ': '',
        'ａ': '',
        '*': '',
        '　': '',  # 全角空格
        ' ': '',  # 半角空格
        '\t': '',  # 制表符
        '\n': '',  # 换行符
        '\r': '',  # 回车符
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name.strip()

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
        start_datetime = datetime.combine(value, time.min)
        return query.filter(column >= start_datetime)
    elif field == 'end_date':
        end_datetime = datetime.combine(value, time.max)
        return query.filter(column <= end_datetime)
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


def parse_baostock_datetime(datetime_str: str) -> datetime:
    """
    解析 baostock 返回的时间字符串格式 YYYYMMDDHHMMSSsss
    :param datetime_str: baostock 时间字符串 (YYYYMMDDHHMMSSsss)
    :return: datetime 对象
    """
    try:
        if not datetime_str or len(datetime_str) < 14:
            return None
        # 提取各个时间组件
        year = datetime_str[0:4]
        month = datetime_str[4:6]
        day = datetime_str[6:8]
        hour = datetime_str[8:10]
        minute = datetime_str[10:12]
        second = datetime_str[12:14]
        # 构造标准时间字符串并解析
        formatted_datetime_str = f"{year}-{month}-{day} {hour}:{minute}:{second}"
        return datetime.strptime(formatted_datetime_str, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"Error parsing baostock datetime: {datetime_str}, error: {str(e)}")
        return None


def format_dates(df, t: StockHistoryType):
    """
    根据时间类型格式化日期

    Args:
        df: 包含'date'列的DataFrame
        t: 时间类型枚举

    Returns:
        格式化后的日期字符串列表
    """
    df['date'] = pd.to_datetime(df['date'])
    if t == StockHistoryType.THIRTY_M:
        return df['date'].dt.strftime('%Y-%m-%d %H:%M').tolist()
    else:
        return df['date'].dt.strftime('%Y-%m-%d').tolist()


def format_dates_series(date_series, t: StockHistoryType):
    """
    根据时间类型格式化日期序列

    Args:
        date_series: 日期序列
        t: 时间类型枚举

    Returns:
        格式化后的日期字符串列表
    """
    if t == StockHistoryType.THIRTY_M:
        return date_series.dt.strftime('%Y-%m-%d %H:%M').tolist()
    else:
        return date_series.dt.strftime('%Y-%m-%d').tolist()


def format_dates_signals(signals: List[Dict], t: StockHistoryType) -> List[Dict]:
    formatted_signals = []

    for signal in signals:
        formatted_signal = signal.copy()
        # 根据历史数据类型格式化日期，直接替换 date 字段
        formatted_signal['date'] = format_date_by_type(signal['date'], t)
        formatted_signals.append(formatted_signal)

    return formatted_signals

def format_date_by_type(date_value, t: StockHistoryType):
    """
    根据时间类型格式化日期

    Args:
        date_value: 日期值
        t: 时间类型枚举

    Returns:
        格式化后的日期字符串
    """
    # 如果是字符串，先解析为datetime对象
    if isinstance(date_value, str):
        try:
            # 尝试解析常见的日期格式
            if ' ' in date_value and ':' in date_value:
                # 包含时间信息的格式
                date_obj = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
            else:
                # 只有日期信息的格式
                date_obj = datetime.strptime(date_value, '%Y-%m-%d')
        except ValueError:
            # 如果解析失败，直接返回原字符串
            return date_value
    else:
        # 假设是datetime对象
        date_obj = date_value

    # 使用解析后的date_obj进行格式化
    if t == StockHistoryType.THIRTY_M:
        return date_obj.strftime('%Y-%m-%d %H:%M')
    else:
        return date_obj.strftime('%Y-%m-%d')

def extend_end_date(end_date):
    """
    将结束日期扩展到当天的最后一刻
    - 对于字符串日期(YYYY-MM-DD)，扩展为 YYYY-MM-DD 23:59:59
    - 对于date对象，扩展为datetime对象的23:59:59
    - 对于datetime对象，保持不变
    """
    if isinstance(end_date, str) and len(end_date) == 10:  # YYYY-MM-DD
        return f"{end_date} 23:59:59"
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        return datetime.combine(end_date, time.max)
    else:
        return end_date