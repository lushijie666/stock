import time
from typing import Callable
import streamlit as st

from enums.signal import SignalType, SignalStrength
from utils.message import show_message

def format_percent(value: float) -> str:
    """格式化百分比，添加正负号和百分号"""
    if value is None:
        return ""
    if value > 0:
        return f"+{value:.2f}"  # 正值添加加号
    return f"{value:.2f}"  # 负值保持原样


def format_price(value: float) -> str:
    """格式化价格"""
    if value is None:
        return ""
    return f"{value:.3f}"


def format_amount(value: float) -> str:
    """格式化金额（万元）"""
    if value is None:
        return ""
    if value >= 100000000:  # 大于1亿
        return f"{value / 100000000:.2f}亿"
    return f"{value / 10000:.2f}万"


def format_volume(value: float) -> str:
    """格式化成交量，输入单位为股，输出格式化为股"""
    if value is None:
        return ""
    if value >= 10000000000:  # 大于100亿股
        return f"{value / 10000000000:.2f}亿股"
    elif value >= 100000000:  # 大于1亿股
        return f"{value / 100000000:.2f}亿股"
    elif value >= 1000000:  # 大于100万股
        return f"{value / 1000000:.2f}万股"
    elif value >= 1000:  # 大于1千股
        return f"{value / 1000:.2f}千股"
    return f"{value:.0f}股"


def format_pinyin_short(value):
    if not value:
        return value
    parts = value.split(',')
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    return value
