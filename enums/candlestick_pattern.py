from enum import Enum


class CandlestickPattern(Enum):
    """蜡烛图形态枚举"""

    # 单K线形态 - (code, text, icon, color, offset)
    # offset: 正数向上偏移，负数向下偏移
    HAMMER = ("hammer", "锤子线", "🪓", "#1E90FF", -0.1)  # 底部反转-看涨，亮蓝色，向下
    HANGING_MAN = ("hanging_man", "上吊线", "⚖️", "#FF4500", 0.1)  # 顶部反转-看跌，橙红色，向上
    INVERTED_HAMMER = ("inverted_hammer", "倒锤子线", "🔨", "#FFD700", 0.1)  # 底部反转-看涨，金色，向上
    SHOOTING_STAR = ("shooting_star", "流星线", "☄️", "#8B0000", 0.1)  # 顶部反转-看跌，深红色，向上

    # 十字线形态（细分类型）
    DOJI = ("doji", "标准十字线", "✝️", "#708090", 0)  # 中性/反转，石板灰，无偏移
    DRAGONFLY_DOJI_BULLISH = ("dragonfly_doji_bullish", "蜻蜓十字(涨)", "🦟", "#228B22", -0.1)  # 底部看涨，森林绿，向下
    DRAGONFLY_DOJI_BEARISH = ("dragonfly_doji_bearish", "蜻蜓十字(跌)", "🦟", "#B8860B", 0.1)  # 顶部看跌，深金黄，向上
    GRAVESTONE_DOJI_BULLISH = ("gravestone_doji_bullish", "墓碑十字(涨)", "🪦", "#DAA520", -0.1)  # 底部看涨，金黄，向下
    GRAVESTONE_DOJI_BEARISH = ("gravestone_doji_bearish", "墓碑十字(跌)", "🪦", "#8B0000", 0.1)  # 顶部看跌，深红，向上
    LONG_LEGGED_DOJI_BULLISH = ("long_legged_doji_bullish", "长腿十字(涨)", "🕷️", "#2E8B57", -0.1)  # 底部看涨，海绿，向下
    LONG_LEGGED_DOJI_BEARISH = ("long_legged_doji_bearish", "长腿十字(跌)", "🕷️", "#A0522D", 0.1)  # 顶部看跌，赭石棕，向上
    FOUR_PRICE_DOJI = ("four_price_doji", "四价十字", "➕", "#696969", 0)  # 极罕见，暗灰色，无偏移

    # 双K线形态
    BULLISH_ENGULFING = ("bullish_engulfing", "看涨吞没", "📈", "#32CD32", -0.1)  # 看涨，酸石灰绿，向下
    BEARISH_ENGULFING = ("bearish_engulfing", "看跌吞没", "📉", "#DC143C", 0.1)  # 看跌，深红色，向上
    DARK_CLOUD_COVER = ("dark_cloud_cover", "乌云盖顶", "⛈️️", "#4B0082", 0.1)  # 看跌，午夜蓝，向上
    PIERCING_PATTERN = ("piercing_pattern", "刺透形态", "💡", "#006400", -0.1)  # 看涨，深绿色，向下
    BULLISH_HARAMI = ("bullish_harami", "看涨孕线", "🤰", "#228B22", -0.1)  # 看涨，森林绿，向下
    BEARISH_HARAMI = ("bearish_harami", "看跌孕线", "🫄", "#B22222", 0.1)  # 看跌，火砖红，向上
    BULLISH_COUNTERATTACK = ("bullish_counterattack", "看涨反击", "⚔️", "#00FF00", -0.1)  # 看涨，亮绿色，向下
    BEARISH_COUNTERATTACK = ("bearish_counterattack", "看跌反击", "🗡️", "#FF0000", 0.1)  # 看跌，亮红色，向上

    # 三K线形态
    MORNING_STAR = ("morning_star", "启明星", "🌟", "#FFA500", -0.1)  # 看涨，橙色，向下
    EVENING_STAR = ("evening_star", "黄昏星", "🌆", "#800080", 0.1)  # 看跌，紫色，向上
    THREE_WHITE_SOLDIERS = ("three_white_soldiers", "三只白兵", "⚪", "#00CED1", -0.1)  # 看涨，深青色，向下
    THREE_BLACK_CROWS = ("three_black_crows", "三只乌鸦", "⚫", "#2F4F4F", 0.1)  # 看跌，深石板灰，向上

    # 多K线复杂形态
    ROUNDING_TOP = ("rounding_top", "圆形顶部", "🔴", "#8B0000", 0.1)  # 看跌，深红色，向上
    ROUNDING_BOTTOM = ("rounding_bottom", "平底锅底部", "🟢", "#006400", -0.1)  # 看涨，深绿色，向下
    TOWER_TOP = ("tower_top", "塔型顶部", "🏰", "#B22222", 0.1)  # 看跌，火砖红，向上
    TOWER_BOTTOM = ("tower_bottom", "塔型底部", "🏛️", "#228B22", -0.1)  # 看涨，森林绿，向下

    # 窗口形态（跳空缺口）
    RISING_WINDOW = ("rising_window", "上升窗口", "⬆️", "#FF6B6B", 0.1)  # 看涨延续，红色，向上
    FALLING_WINDOW = ("falling_window", "下降窗口", "⬇️", "#4ECDC4", -0.1)  # 看跌延续，青色，向下

    def __new__(cls, code, text, icon, color, offset):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.code = code
        obj.text = text
        obj.icon = icon
        obj.color = color  # 图表显示颜色
        obj.offset = offset  # Y轴偏移量
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
