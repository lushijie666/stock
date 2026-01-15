"""
市场状态相关枚举
"""
from enum import Enum


class MarketDirection(Enum):
    """市场方向"""
    LONG = ('LONG', '做多', '📈', '#10b981')      # 多头趋势
    SHORT = ('SHORT', '做空', '📉', '#ef4444')    # 空头趋势
    RANGING = ('RANGING', '震荡', '↔️', '#f59e0b')  # 震荡区间

    def __init__(self, code, text, icon, color):
        self.code = code
        self.text = text
        self.icon = icon
        self.color = color

    def __str__(self):
        return self.text

    @classmethod
    def from_code(cls, code: str):
        """根据代码获取枚举"""
        for item in cls:
            if item.code == code:
                return item
        return None


class MacdPosition(Enum):
    """MACD位置"""
    ABOVE = ('ABOVE', '0轴上方', '⬆️', '#10b981')     # 在0轴上方
    BELOW = ('BELOW', '0轴下方', '⬇️', '#ef4444')     # 在0轴下方
    NEUTRAL = ('NEUTRAL', '0轴[-0.5~0.5]附近', '➡️', '#6b7280')  # 在0轴附近震荡

    def __init__(self, code, text, icon, color):
        self.code = code
        self.text = text
        self.icon = icon
        self.color = color

    def __str__(self):
        return self.text

    @classmethod
    def from_code(cls, code: str):
        """根据代码获取枚举"""
        for item in cls:
            if item.code == code:
                return item
        return None


class RsiState(Enum):
    """RSI状态"""
    BULL = ('BULL', '多头趋势', '🐂', '#10b981')      # 多头（>55）
    BEAR = ('BEAR', '空头趋势', '🐻', '#ef4444')      # 空头（<45）
    NEUTRAL = ('NEUTRAL', '震荡区间[45~55]', '🦘', '#f59e0b')  # 震荡（45-55）

    def __init__(self, code, text, icon, color):
        self.code = code
        self.text = text
        self.icon = icon
        self.color = color

    def __str__(self):
        return self.text

    @classmethod
    def from_code(cls, code: str):
        """根据代码获取枚举"""
        for item in cls:
            if item.code == code:
                return item
        return None


class AreaType(Enum):
    """关键区域类型"""
    SUPPORT = ('SUPPORT', '支撑区', '🔻', '#10b981')      # 支撑位
    RESISTANCE = ('RESISTANCE', '阻力区', '🔺', '#ef4444')  # 阻力位

    def __init__(self, code, text, icon, color):
        self.code = code
        self.text = text
        self.icon = icon
        self.color = color

    def __str__(self):
        return self.text

    @classmethod
    def from_code(cls, code: str):
        """根据代码获取枚举"""
        for item in cls:
            if item.code == code:
                return item
        return None


class RiskType(Enum):
    """风险类型"""
    BEARISH_DIVERGENCE = ('BEARISH_DIVERGENCE', '顶背离', '⚠️', '#ef4444')  # 顶背离（做多风险）
    BULLISH_DIVERGENCE = ('BULLISH_DIVERGENCE', '底背离', '⚠️', '#10b981')  # 底背离（做空风险）

    def __init__(self, code, text, icon, color):
        self.code = code
        self.text = text
        self.icon = icon
        self.color = color

    def __str__(self):
        return self.text

    @classmethod
    def from_code(cls, code: str):
        """根据代码获取枚举"""
        for item in cls:
            if item.code == code:
                return item
        return None


class RiskLevel(Enum):
    """风险等级"""
    LOW = ('LOW', '低风险', '🟢', '#10b981')
    MEDIUM = ('MEDIUM', '中等风险', '🟡', '#f59e0b')
    HIGH = ('HIGH', '高风险', '🔴', '#ef4444')

    def __init__(self, code, text, icon, color):
        self.code = code
        self.text = text
        self.icon = icon
        self.color = color

    def __str__(self):
        return self.text

    @classmethod
    def from_code(cls, code: str):
        """根据代码获取枚举"""
        for item in cls:
            if item.code == code:
                return item
        return None
