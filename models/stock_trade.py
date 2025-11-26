from datetime import datetime as dt
from sqlalchemy import  Date

from config.database import Base


from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, UniqueConstraint, Index



class StockTrade(Base):
    __tablename__ = "stock_trade"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', name='uix_stock_trade_code_date'),
        Index('idx_trade_code_date', 'code', 'date'),
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
