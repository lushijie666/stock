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
    followed_at = Column(DateTime) # 关注时间

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return (f"Stock(code='{self.code}', name='{self.name}', category={self.category}, "
                f"full_name='{self.full_name}', ipo_at={self.ipo_at}, "
                f"total_capital={self.total_capital}, flow_capital={self.flow_capital}, "
                f"industry='{self.industry}', pinyin='{self.pinyin}')")

    def generate_pinyin(self):
        if self.category == Category.US_XX:
            return self.code
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

    @classmethod
    def get_followed_codes_by_category(cls, session, category: Category) -> List[str]:
        try:
            codes = (
                session.query(cls.code)
                .filter(
                    cls.category == category,
                    cls.is_followed == True,
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

    def get_us_stock_prefix(self) -> str:
        """
        获取美股股票的前缀
        从 full_name 字段中提取前缀，格式如: "英伟达(105)" -> "105"
        如果无法提取，则返回默认前缀 "105"
        """
        if not self.full_name:
            return "105"

        import re
        match = re.search(r'\((\d+)\)$', self.full_name)
        if match:
            return match.group(1)
        else:
            logging.warning(f"无法从 full_name 提取前缀，使用默认值: 105, full_name: {self.full_name}")
            return "105"

    def get_us_stock_symbol(self) -> str:
        """
        获取美股股票的完整symbol，格式如: "105.AAPL"
        """
        if self.category != Category.US_XX:
            raise ValueError(f"股票 {self.code} 不是美股分类")
        prefix = self.get_us_stock_prefix()
        return f"{prefix}.{self.code}"