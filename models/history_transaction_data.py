from datetime import datetime as dt

from config.database import Base
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Boolean, UniqueConstraint, Index


class HistoryTransactionData(Base):
    __tablename__ = "history_transaction_data"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', 'turnover_time', name='uix_history_transaction_data_code_turnover_time'),
        Index('idx_history_transaction_data_code_turnover_time', 'code', 'turnover_time'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True)

    turnover_time = Column(DateTime) # 成交时间
    turnover_price = Column(Numeric(10, 3))  # 成交价
    price_change = Column(Numeric(10, 3))  # 价格变动
    turnover_count = Column(Numeric(20, 3))  # 成交量
    turnover_amount = Column(Numeric(20, 3))  # 成交额
    turnover_type = Column(String(10), index=True)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
