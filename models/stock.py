from datetime import datetime as dt

from config.database import Base
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Boolean, UniqueConstraint, Index


class Stock(Base):
    __tablename__ = "stock"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', name='uix_stock_code'),
        Index('idx_stock_code', 'code'),
    )
    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号
    name = Column(String(128), index=True) # 名称
    full_name = Column(String(256), index=True) # 全称
    ipo_at = Column(DateTime, default=dt.now)
    total_capital = Column(BigInteger, default=0) # 总股本
    flow_capital = Column(BigInteger, default=0) # 流通股本
    industry = Column(String(256), default=0) # 行业

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
