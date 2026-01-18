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

def safe_string_assign(value):
    if value is None:
        return ""
    try:
        # 更严格的检查
        value_str = str(value)
        if value_str.strip().lower() in ["nan", "<na>", "none", "null", "", "nat"]:
            return ""
        return value_str
    except:
        return ""

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

def format_date(date_value):
   return format_date_by_type(date_value, StockHistoryType.D)

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


def format_pattern_text(signal):
    """
    格式化形态文本，按照不同策略分别展示详细信息

    展示规则：
    - 融合策略（投票模式）：显示参与的各个策略及其强度，如 [CBR策略(强)、KDJ策略(弱) | 3策略]
    - 融合策略（加权/自适应模式）：显示权重、强度、得分，如 [MACD策略(权重1.0×强=2.0) | 总分:7.5]
    - 蜡烛图策略：显示识别的形态名称，如 [看涨吞没、晨星]
    - 其他策略：显示 [-]
    - 多个策略：用空格分隔每个策略的信息
    """
    from enums.strategy import StrategyType

    strategy_code = signal.get('strategy_code', '')
    if not strategy_code:
        return '-'

    # 检查是否有多个策略（合并后的信号）
    strategies = signal.get('strategies', [])

    if strategies:
        # 多个策略的情况
        return _format_multiple_strategies(signal, strategies)
    else:
        # 单个策略的情况
        return _format_single_strategy(signal, strategy_code)


def _format_multiple_strategies(signal, strategies):
    """格式化多个策略的模式信息"""
    from enums.strategy import StrategyType

    pattern_parts = []

    # 获取每个策略的详细信息字典
    strategy_details_map = signal.get('strategy_details', {})

    for strategy in strategies:
        # 如果有保存的策略详细信息，使用它
        if strategy in strategy_details_map:
            strategy_info = strategy_details_map[strategy]
            # 创建临时signal对象，包含该策略的详细信息
            temp_signal = {
                'details': strategy_info.get('details'),
                'pattern_name': strategy_info.get('pattern_name'),
                'score': strategy_info.get('score'),
                'type': signal.get('type')  # 保留原始信号类型
            }

            if strategy == StrategyType.FUSION_STRATEGY:
                pattern_parts.append(_format_fusion_strategy(temp_signal))
            elif strategy == StrategyType.CANDLESTICK_STRATEGY:
                pattern_parts.append(_format_candlestick_strategy(temp_signal))
            else:
                pattern_parts.append('[-]')
        else:
            # 没有保存的详细信息，使用原始signal（兼容旧数据）
            if strategy == StrategyType.FUSION_STRATEGY:
                pattern_parts.append(_format_fusion_strategy(signal))
            elif strategy == StrategyType.CANDLESTICK_STRATEGY:
                pattern_parts.append(_format_candlestick_strategy(signal))
            else:
                pattern_parts.append('[-]')

    return ' '.join(pattern_parts) if pattern_parts else '-'


def _format_single_strategy(signal, strategy_code):
    """格式化单个策略的模式信息"""
    if strategy_code == 'FS':
        return _format_fusion_strategy(signal)
    elif strategy_code == 'CS':
        return _format_candlestick_strategy(signal)
    else:
        return '[-]'


def _format_fusion_strategy(signal):
    """
    格式化融合策略的详细信息

    根据 details 结构自动判断是投票模式还是加权/自适应模式
    """
    from enums.signal import SignalType

    details = signal.get('details')

    if isinstance(details, dict):
        # 投票模式：details 是字典 {SignalType.BUY: [...], SignalType.SELL: [...]}
        return _format_voting_fusion(signal, details)
    elif isinstance(details, list):
        # 加权/自适应模式：details 是列表
        return _format_weighted_fusion(signal, details)
    else:
        return '[-]'


def _format_voting_fusion(signal, details):
    """格式化投票模式融合策略"""
    from enums.signal import SignalType

    signal_type = signal.get('type')
    if signal_type not in details:
        return '[-]'

    strategy_list = details[signal_type]
    if not strategy_list:
        return '[-]'

    # 格式化每个参与的策略
    formatted_strategies = []
    for s in strategy_list:
        strategy_type_obj = s.get('strategy')
        strength = s.get('strength')
        if strategy_type_obj and strength:
            formatted_strategies.append(
                f"{strategy_type_obj.text}({strength.display_name})"
            )

    if not formatted_strategies:
        return '[-]'

    # 获取参与策略数
    participated_count = len(strategy_list)

    # 格式：[策略1、策略2 | X策略]
    detail_str = '、'.join(formatted_strategies)
    return f"[{detail_str} | {participated_count}策略]"


def _format_weighted_fusion(signal, details):
    """格式化加权/自适应模式融合策略"""
    if not details:
        return '[-]'

    formatted_strategies = []
    total_score = signal.get('score', 0)

    for s in details:
        strategy_type_obj = s.get('strategy')
        strength = s.get('strength')
        weight = s.get('weight', 1.0)
        score = s.get('score', 0)

        if strategy_type_obj and strength:
            # 格式：策略名(权重×强度=得分)
            formatted_strategies.append(
                f"{strategy_type_obj.text}(权重{weight:.1f}×{strength.display_name}={score:.1f})"
            )

    if not formatted_strategies:
        return '[-]'

    # 格式：[策略1、策略2 | 总分:X.X]
    detail_str = '、'.join(formatted_strategies)
    return f"[{detail_str} | 总分:{total_score:.1f}]"


def _format_candlestick_strategy(signal):
    """格式化蜡烛图策略的形态信息"""
    pattern_name = signal.get('pattern_name', '')
    if pattern_name:
        return f"[{pattern_name}]"
    else:
        return '[-]'