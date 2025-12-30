import json
from datetime import datetime as dt

from config.database import Base
from sqlalchemy import Column, BigInteger, String, Numeric, Date, DateTime, Boolean, UniqueConstraint, Index

from enums.history_type import StockHistoryType


class BaseStockHistory(Base):
    """股票历史数据基类"""
    __abstract__ = True  # 抽象基类

    def __str__(self):
        return self.to_json()

    def to_json(self):
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))  # 移除缩进，紧凑格式

    def to_dict(self):
        """转换为字典，子类可重写此方法以自定义输出"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, dt):
                value = value.isoformat()
            elif hasattr(value, 'to_eng_float'):  # 处理 Numeric 类型
                value = float(value) if value is not None else None
            elif isinstance(value, int) and value is not None:
                value = int(value)
            elif isinstance(value, float) and value is not None:
                value = float(value)
            result[column.name] = value
        return result

def get_history_model(history_type: StockHistoryType):
    model_mapping = {
        StockHistoryType.D: StockHistoryD,
        StockHistoryType.W: StockHistoryW,
        StockHistoryType.M: StockHistoryM,
        StockHistoryType.THIRTY_M: StockHistory30M
    }
    return model_mapping.get(history_type, StockHistoryD)

class StockHistoryD(BaseStockHistory):
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

    date = Column(DateTime) # 日期
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change_amount = Column(Numeric(100, 4))  # 涨跌额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class StockHistoryW(BaseStockHistory):
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

    date = Column(DateTime) # 日期
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change_amount = Column(Numeric(100, 4))  # 涨跌额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class StockHistoryM(BaseStockHistory):
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

    date = Column(DateTime) # 日期
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change_amount = Column(Numeric(100, 4))  # 涨跌额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class StockHistory30M(BaseStockHistory):
    __tablename__ = "stock_history_30m"

    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint( 'code', 'date', name='uix_stock_history_30m_code_date'),
        Index('idx_history_30m_code_date', 'code', 'date'),
    )

    # 基础信息
    id = Column(BigInteger, primary_key=True, index=True)
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, default=dt.now, onupdate=dt.now)

    category = Column(String(32), index=True)
    code = Column(String(32), index=True) # 代号

    date = Column(DateTime) # 日期
    opening = Column(Numeric(100, 4))  # 开盘
    closing = Column(Numeric(100, 4))  # 收盘
    highest = Column(Numeric(100, 4))  # 最高
    lowest = Column(Numeric(100, 4))  # 最低
    turnover_count = Column(Numeric(100, 0))  # 成交量
    turnover_amount = Column(Numeric(100, 4))  # 成交额
    change_amount = Column(Numeric(100, 4))  # 涨跌额
    change = Column(Numeric(100, 6))  # 涨跌幅
    turnover_ratio = Column(Numeric(100, 6))  # 换手率

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)