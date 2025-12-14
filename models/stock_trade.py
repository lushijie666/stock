from datetime import datetime as dt
from sqlalchemy import  Date

from config.database import Base


from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, UniqueConstraint, Index

from enums.history_type import StockHistoryType


def get_trade_model(history_type: StockHistoryType):
    model_mapping = {
        StockHistoryType.D: StockTradeD,
        StockHistoryType.W: StockTradeW,
        StockHistoryType.M: StockTradeM,
        StockHistoryType.THIRTY_M: StockTrade30M
    }
    return model_mapping.get(history_type, StockTradeD)

class StockTradeD(Base):
    __tablename__ = "stock_trade_d"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint('code', 'date', 'strategy_type', name='uix_stock_trade_d_code_date_strategy'),
        Index('idx_trade_d_code_date', 'code', 'date'),
    )
    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    date = Column(Date)  # 日期
    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号
    strategy_type = Column(String(32))   # 策略类型
    signal_type = Column(String(32)) # 信号类型
    signal_strength = Column(String(32)) # 信号强度

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class StockTradeW(Base):
    __tablename__ = "stock_trade_w"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint('code', 'date', 'strategy_type', name='uix_stock_trade_w_code_date_strategy'),
        Index('idx_trade_w_code_date', 'code', 'date'),
    )
    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    date = Column(Date)  # 日期
    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号
    strategy_type = Column(String(32))   # 策略类型
    signal_type = Column(String(32)) # 信号类型
    signal_strength = Column(String(32)) # 信号强度

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class StockTradeM(Base):
    __tablename__ = "stock_trade_m"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint('code', 'date', 'strategy_type', name='uix_stock_trade_m_code_date_strategy'),
        Index('idx_trade_m_code_date', 'code', 'date'),
    )
    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    date = Column(Date)  # 日期
    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号
    strategy_type = Column(String(32))   # 策略类型
    signal_type = Column(String(32)) # 信号类型
    signal_strength = Column(String(32)) # 信号强度

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class StockTrade30M(Base):
    __tablename__ = "stock_trade_30m"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint('code', 'date', 'strategy_type', name='uix_stock_trade_30m_code_date_strategy'),
        Index('idx_trade_30m_code_date', 'code', 'date'),
    )
    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    date = Column(Date)  # 日期
    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号
    strategy_type = Column(String(32))   # 策略类型
    signal_type = Column(String(32)) # 信号类型
    signal_strength = Column(String(32)) # 信号强度

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)