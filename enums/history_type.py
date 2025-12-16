from enum import StrEnum
from enums.sync_type import SyncHistoryType
from datetime import timedelta


class StockHistoryType(StrEnum):
    """股票历史数据类型枚举"""
    D = ("D", "天", "d", SyncHistoryType.STOCK_HISTORY_D, SyncHistoryType.STOCK_TRADE_D, 90)
    W = ("W", "周", "w", SyncHistoryType.STOCK_HISTORY_W, SyncHistoryType.STOCK_TRADE_W, 365)
    M = ("M", "月", "m", SyncHistoryType.STOCK_HISTORY_M, SyncHistoryType.STOCK_TRADE_M, 730)
    THIRTY_M = ("30m", "30分钟", "30", SyncHistoryType.STOCK_HISTORY_THIRTY_M, SyncHistoryType.STOCK_HISTORY_THIRTY_M, 15)

    def __new__(cls, value, text, bs_frequency, sync_history_type, sync_trade_type, default_days):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.text = text
        obj.bs_frequency = bs_frequency
        obj.sync_history_type = sync_history_type
        obj.sync_trade_type = sync_trade_type
        obj.default_days = default_days
        return obj

    def get_default_start_date(self, max_date, min_date):
        """根据历史数据类型计算默认开始日期"""
        return max(max_date - timedelta(days=self.default_days), min_date)

    @property
    def ma_periods(self):
        """返回该周期对应的默认均线周期列表"""
        mapping = {
            self.D: [5, 10, 30, 250],
            self.W: [5, 10, 20, 60],
            self.M: [5, 10, 20, 60],
            self.THIRTY_M: [5, 10, 20, 60]  # 30分钟图使用较短周期
        }
        return mapping[self]