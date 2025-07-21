import logging
from datetime import datetime as dt
from typing import List

from config.database import Base
from pypinyin import lazy_pinyin, Style

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, UniqueConstraint, Index

from enums.category import Category


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
    pinyin = Column(String(128))  # 拼音
    full_name = Column(String(256), index=True) # 全称
    ipo_at = Column(DateTime, default=dt.now)
    total_capital = Column(BigInteger, default=0) # 总股本
    flow_capital = Column(BigInteger, default=0) # 流通股本
    industry = Column(String(256), default=0) # 行业
    is_followed = Column(Boolean, default=False) # 是否关注

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def generate_pinyin(self):
        """生成拼音"""
        # 完整拼音
        full_pinyin = ''.join(lazy_pinyin(self.name))
        # 拼音首字母
        first_letters = ''.join(lazy_pinyin(self.name, style=Style.FIRST_LETTER))
        return f"{full_pinyin},{first_letters}"

    @classmethod
    def get_codes_by_category(cls, session, category: Category) -> List[str]:
        try:
            codes = (
                session.query(cls.code)
                .filter(
                    cls.category == category,
                    cls.removed == False
                )
                .order_by(cls.code.asc())  # 按代码排序
                .all()
            )
            # 将结果转换为简单的列表
            return [code[0] for code in codes]
        except Exception as e:
            logging.error(f"获取{category.text}股票代码列表失败: {str(e)}")
            return []