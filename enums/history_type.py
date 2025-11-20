from enum import  StrEnum

from enums.sync_type import SyncHistoryType


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