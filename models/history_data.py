from datetime import datetime as dt

from config.database import Base
from sqlalchemy import Column, BigInteger, String, Numeric, Date, DateTime, Boolean, UniqueConstraint, Index


class HistoryDateData(Base):
    __tablename__ = "history_date_data"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', 'date', name='uix_history_date_data_code_date'),
        Index('idx_history_date_data_code_date', 'code', 'date'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号

    date = Column(Date) # 日期
    opening = Column(Numeric(10, 3))  # 开盘
    closing = Column(Numeric(10, 3))  # 收盘
    highest = Column(Numeric(10, 3))  # 最高
    lowest = Column(Numeric(10, 3))  # 最低
    turnover_count = Column(Numeric(20, 3))  # 成交量
    turnover_amount = Column(Numeric(20, 3))  # 成交额
    swing = Column(Numeric(10, 3))  # 振幅
    change = Column(Numeric(10, 3))  # 涨跌幅
    change_amount = Column(Numeric(10, 3))  # 涨跌额
    turnover_ratio = Column(Numeric(10, 3))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
