from enum import  StrEnum

from enums.sync_type import SyncHistoryType
from datetime import timedelta

class StockHistoryType(StrEnum):
    D = "D"
    W = "W"
    M = "M"
    THIRTY_M = "30m"

    @property
    def text(self) -> str:
        return {
            StockHistoryType.D: "天",
            StockHistoryType.W: "周",
            StockHistoryType.M: "月",
            StockHistoryType.THIRTY_M: "30分钟",
        }.get(self, "未知")

    @property
    def bs_frequency(self) -> str:
        return {
            StockHistoryType.D: "d",
            StockHistoryType.W: "w",
            StockHistoryType.M: "m",
            StockHistoryType.THIRTY_M: "30",
        }.get(self, "d")
    @property
    def sync_history_type(self) -> str:
        return {
            StockHistoryType.D: SyncHistoryType.STOCK_HISTORY_D,
            StockHistoryType.W: SyncHistoryType.STOCK_HISTORY_W,
            StockHistoryType.M: SyncHistoryType.STOCK_HISTORY_M,
            StockHistoryType.THIRTY_M: SyncHistoryType.STOCK_HISTORY_THIRTY_M,
        }.get(self, SyncHistoryType.STOCK_HISTORY_D)

    @property
    def default_days(self) -> int:
        """获取不同类型历史数据的默认显示天数"""
        return {
            StockHistoryType.THIRTY_M: 15,  # 30分钟数据默认显示15天
            StockHistoryType.W: 365,  # 周数据默认显示1年(365天)
            StockHistoryType.M: 730,  # 月数据默认显示2年(730天)
            StockHistoryType.D: 90,  # 天数据默认显示90天
        }.get(self, 90)

    def get_default_start_date(self, max_date, min_date):
        """根据历史数据类型计算默认开始日期"""
        return max(max_date - timedelta(days=self.default_days), min_date)