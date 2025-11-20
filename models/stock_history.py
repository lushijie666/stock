from datetime import datetime as dt

from config.database import Base
from sqlalchemy import Column, BigInteger, String, Numeric, Date, DateTime, Boolean, UniqueConstraint, Index

from enums.history_type import StockHistoryType


def get_history_model(history_type: StockHistoryType):
    model_mapping = {
        StockHistoryType.D: StockHistoryD,
        StockHistoryType.W: StockHistoryW,
        StockHistoryType.M: StockHistoryM,
        StockHistoryType.THIRTY_M: StockHistory30M
    }
    return model_mapping.get(history_type, StockHistoryD)

class StockHistoryD(Base):
    __tablename__ = "stock_history_d"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', 'date', name='uix_stock_history_d_code_date'),
        Index('idx_history_d_code_date', 'code', 'date'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号

    date = Column(Date) # 日期
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class StockHistoryW(Base):
    __tablename__ = "stock_history_w"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', 'date', name='uix_stock_history_w_code_date'),
        Index('idx_history_w_code_date', 'code', 'date'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号

    date = Column(Date) # 日期
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class StockHistoryM(Base):
    __tablename__ = "stock_history_m"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', 'date', name='uix_stock_history_m_code_date'),
        Index('idx_history_m_code_date', 'code', 'date'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号

    date = Column(Date) # 日期
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class StockHistory30M(Base):
    __tablename__ = "stock_history_30m"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', 'time', name='uix_stock_history_30m_code_time'),
        Index('idx_history_30m_code_time', 'code', 'time'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号

    date = Column(Date) # 日期
    time = Column(DateTime) # 时间
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)