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
    """格式化成交量"""
    if value is None:
        return ""
    if value >= 100000000:  # 大于1亿手
        return f"{value / 100000000:.2f}亿手"
    elif value >= 10000:  # 大于1万手
        return f"{value / 10000:.2f}万手"
    return f"{value:.0f}手"


def format_pinyin_short(value):
    if not value:
        return value
    parts = value.split(',')
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    return value
