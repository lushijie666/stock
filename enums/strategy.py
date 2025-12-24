from enum import Enum


class StrategyType(Enum):
    """策略类型枚举"""
    MACD_STRATEGY = ("macd", "M", "MACD策略")
    SMA_STRATEGY = ("sma", "S", "SMA策略")
    TURTLE_STRATEGY = ("turtle", "T", "海龟策略")
    CBR_STRATEGY = ("cbr", "C", "CBR策略")
    RSI_STRATEGY = ("rsi", "R", "RSI策略")
    BOLL_STRATEGY = ("boll", "B", "布林带策略")
    KDJ_STRATEGY = ("kdj", "K", "KDJ策略")

    def __new__(cls, value, code, text):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.code = code
        obj.text = text
        return obj

    @property
    def fullText(self) -> str:
        return f"{self.text} ({self.code})"

    @classmethod
    def lookup(cls, value):
        if not value:
            return None
        for v in cls:
            if v.code == value:
                return v
        return None

    @classmethod
    def all_strategies(cls):
        """返回所有可用的策略类型"""
        return [
            cls.MACD_STRATEGY,
            cls.SMA_STRATEGY,
            cls.TURTLE_STRATEGY,
            cls.CBR_STRATEGY,
            cls.RSI_STRATEGY,
            cls.BOLL_STRATEGY,
            cls.KDJ_STRATEGY
        ]