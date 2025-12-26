from enum import Enum


class StrategyType(Enum):
    """策略类型枚举"""
    MACD_STRATEGY = ("macd", "M", "MACD策略", "动量指标之王")
    SMA_STRATEGY = ("sma", "S", "SMA策略", "移动平均线交叉")
    TURTLE_STRATEGY = ("turtle", "T", "海龟策略", "突破系统经典")
    CBR_STRATEGY = ("cbr", "C", "CBR策略", "反转确认")
    RSI_STRATEGY = ("rsi", "R", "RSI策略", "相对强弱指标")
    BOLL_STRATEGY = ("boll", "B", "布林带策略", "波动性通道")
    KDJ_STRATEGY = ("kdj", "K", "KDJ策略", "随机指标")
    CANDLESTICK_STRATEGY = ("candle", "CS", "蜡烛图策略", "K线形态识别")
    FUSION_STRATEGY = ("fusion", "FS", "融合策略", "多策略综合信号")

    def __new__(cls, value, code, text, desc):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.code = code
        obj.text = text
        obj.desc = desc
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
    def all_base_strategies(cls):
        """返回所有可用的策略类型(去掉融合的)"""
        return [
            cls.MACD_STRATEGY,
            cls.SMA_STRATEGY,
            cls.TURTLE_STRATEGY,
            cls.CBR_STRATEGY,
            cls.RSI_STRATEGY,
            cls.BOLL_STRATEGY,
            cls.KDJ_STRATEGY,
            cls.CANDLESTICK_STRATEGY,
        ]

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
            cls.KDJ_STRATEGY,
            cls.CANDLESTICK_STRATEGY,
            cls.FUSION_STRATEGY,
        ]

    @classmethod
    def get_default_strategies_by_type(cls, t):
        """根据时间周期类型获取默认策略配置"""
        from enums.history_type import StockHistoryType  # 延迟导入避免循环依赖

        strategy_mapping = {
            StockHistoryType.D: [  # 日线
                cls.MACD_STRATEGY,
                cls.SMA_STRATEGY,
                cls.RSI_STRATEGY,
                cls.KDJ_STRATEGY,
                cls.BOLL_STRATEGY,
                cls.CANDLESTICK_STRATEGY,  # 蜡烛图适合日线
            ],
            StockHistoryType.W: [  # 周线
                cls.MACD_STRATEGY,
                cls.SMA_STRATEGY,
                cls.TURTLE_STRATEGY,
                cls.RSI_STRATEGY,
                cls.KDJ_STRATEGY,
                cls.BOLL_STRATEGY,
                cls.CBR_STRATEGY,
                cls.CANDLESTICK_STRATEGY,  # 蜡烛图适合周线
            ],
            StockHistoryType.M: [  # 月线
                cls.MACD_STRATEGY,
                cls.SMA_STRATEGY,
                cls.TURTLE_STRATEGY,
                cls.CBR_STRATEGY,
                cls.CANDLESTICK_STRATEGY,  # 蜡烛图适合月线
            ],

            StockHistoryType.THIRTY_M: [  # 30分钟线
                cls.MACD_STRATEGY,
                cls.SMA_STRATEGY,
                cls.RSI_STRATEGY,
                cls.KDJ_STRATEGY,
            ]
        }
        return strategy_mapping.get(t, [
            cls.MACD_STRATEGY,
            cls.SMA_STRATEGY,
            cls.RSI_STRATEGY,
            cls.KDJ_STRATEGY,
            cls.BOLL_STRATEGY,
        ])

class FusionStrategyModel(Enum):
    """策略类型枚举"""
    VOTING_MODEL = ("voting", "投票模式", "🗳", "稳健")
    WEIGHTED_MODEL = ("weighted", "加权模式",  "⚖️", "灵活")
    ADAPTIVE_MODEL = ("adaptive", "自适应模式", "🤖", "智能")

    def __new__(cls, code, text, icon, desc):
        obj = object.__new__(cls)
        obj.code = code
        obj.text = text
        obj.icon = icon
        obj.desc = desc
        return obj

    @property
    def fullText(self) -> str:
        return f"{self.icon} {self.text} ({self.desc})"