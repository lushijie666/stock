from enum import Enum


class SignalType(Enum):
    BUY = ("buy", "MB(买入)", "🔴")
    SELL = ("sell", "MS(卖出)", "🟢")

    def __init__(self, value, display_name, icon):
        self._value_ = value
        self.display_name = display_name
        self.icon = icon

    @property
    def fullText(self):
        """返回完整显示文本：图标 + 显示名称"""
        return f"{self.icon} {self.display_name}"

    @classmethod
    def lookup(cls, value):
        if not value:
            return None
        for v in cls:
            if v.value == value:
                return v
        return None

class SignalStrength(Enum):
    STRONG = ("strong", "强", "🔥")
    WEAK = ("weak", "弱", "🥀")

    def __init__(self, value, display_name, icon):
        self._value_ = value
        self.display_name = display_name
        self.icon = icon

    @property
    def fullText(self):
        """返回完整显示文本：图标 + 显示名称"""
        return f"{self.icon} {self.display_name}"

    @classmethod
    def lookup(cls, value):
        if not value:
            return None
        for v in cls:
            if v.value == value:
                return v
        return None