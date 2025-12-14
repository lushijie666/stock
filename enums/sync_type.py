from enum import  StrEnum

class SyncHistoryType(StrEnum):
    STOCK = "stock"
    STOCK_HISTORY_D = "stock_history_d"
    STOCK_HISTORY_W = "stock_history_w"
    STOCK_HISTORY_M = "stock_history_m"
    STOCK_HISTORY_THIRTY_M = "stock_history_30m"
    STOCK_TRADE_D = "stock_trade_d"
    STOCK_TRADE_W = "stock_trade_w"
    STOCK_TRADE_M = "stock_trade_M"
    STOCK_TRADE_THIRTY_M = "stock_trade_30m"

    @property
    def display_name(self):
        """获取显示名称"""
        type_map = {
            SyncHistoryType.STOCK: "股票信息",
            SyncHistoryType.STOCK_HISTORY_D: "历史数据-天",
            SyncHistoryType.STOCK_HISTORY_W: "历史数据-周",
            SyncHistoryType.STOCK_HISTORY_M: "历史数据-月",
            SyncHistoryType.STOCK_HISTORY_THIRTY_M: "历史数据-30分钟",
            SyncHistoryType.STOCK_TRADE_D: "买卖记录-天",
            SyncHistoryType.STOCK_TRADE_W: "买卖记录-周",
            SyncHistoryType.STOCK_TRADE_M: "买卖记录-月",
            SyncHistoryType.STOCK_TRADE_THIRTY_M: "买卖记录-30分支",
        }
        return type_map.get(self, "未知")