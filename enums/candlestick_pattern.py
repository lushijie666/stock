from enum import Enum


class CandlestickPattern(Enum):
    """蜡烛图形态枚举"""

    # 单K线形态
    HAMMER = ("hammer", "锤子线", "🔨", )
    HANGING_MAN = ("hanging_man", "上吊线", "🪢")
    INVERTED_HAMMER = ("inverted_hammer", "倒锤子线", "🔨")
    SHOOTING_STAR = ("shooting_star", "流星线", "⭐")
    DOJI = ("doji", "十字星", "✝️")

    # 双K线形态
    BULLISH_ENGULFING = ("bullish_engulfing", "看涨吞没", "📈")
    BEARISH_ENGULFING = ("bearish_engulfing", "看跌吞没", "📉")
    DARK_CLOUD_COVER = ("dark_cloud_cover", "乌云盖顶", "☁️")
    PIERCING_PATTERN = ("piercing_pattern", "刺透形态", "🔆")

    # 三K线形态
    MORNING_STAR = ("morning_star", "晨星", "🌟")
    EVENING_STAR = ("evening_star", "黄昏星", "🌆")
    THREE_WHITE_SOLDIERS = ("three_white_soldiers", "三只白兵", "⚪⚪⚪")
    THREE_BLACK_CROWS = ("three_black_crows", "三只乌鸦", "⚫⚫⚫")

    def __new__(cls, code, text, icon):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.code = code
        obj.text = text
        obj.icon = icon
        return obj

    @property
    def fullText(self) -> str:
        """返回完整显示文本：图标 + 文本"""
        return f"{self.icon} {self.text}"

    @classmethod
    def lookup(cls, value):
        """根据code或text查找枚举值"""
        if not value:
            return None
        for v in cls:
            if v.code == value or v.text == value:
                return v
        return None

    @classmethod
    def get_text(cls, value):
        """获取显示文本，如果找不到则返回原值"""
        pattern = cls.lookup(value)
        return pattern.text if pattern else value
