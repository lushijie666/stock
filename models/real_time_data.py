from datetime import datetime as dt

from config.database import Base
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Boolean, UniqueConstraint, Index, Date


class RealTimeData(Base):
    __tablename__ = "real_time_data"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', name='uix_real_time_data_code'),
        Index('idx_real_time_data_code', 'code'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号

    date = Column(Date)  # 日期

    # 价格相关
    current_price = Column(Numeric(10, 3))  # 最新价
    change_percent = Column(Numeric(10, 3))  # 涨跌幅
    change_amount = Column(Numeric(10, 3))  # 涨跌额
    turnover_count = Column(Numeric(20, 3))  # 成交量
    turnover_amount = Column(Numeric(20, 3))  # 成交额

    # 交易指标
    swing = Column(Numeric(10, 3))  # 振幅
    highest = Column(Numeric(10, 3))  # 最高
    lowest = Column(Numeric(10, 3))  # 最低
    today_open = Column(Numeric(10, 3))  # 今开
    yesterday_close = Column(Numeric(10, 3))  # 昨收

    # 交易比率
    quantity_ratio = Column(Numeric(10, 3))  # 量比
    turnover_ratio = Column(Numeric(10, 3))  # 换手率
    pe_ratio = Column(Numeric(10, 3))  # 市盈率
    pb_ratio = Column(Numeric(10, 3))  # 市净率

    # 市值
    total_value = Column(Numeric(20, 3))  # 总市值
    traded_value = Column(Numeric(20, 3))  # 流通市值

    # 涨跌指标
    teeming_ratio = Column(Numeric(10, 3))  # 涨速
    minute_5_change = Column(Numeric(10, 3))  # 5分钟涨跌
    day_60_change = Column(Numeric(10, 3))  # 60日涨跌幅
    ytd_change = Column(Numeric(10, 3))  # 年初至今涨跌幅

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
