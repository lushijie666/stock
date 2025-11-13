from enum import Enum, StrEnum
from typing import Tuple


class Category(StrEnum):
    A_SH = "A_SH"
    A_SZ = "A_SZ"
    A_BJ = "A_BJ"
    X_XX = "X_XX"

    @property
    def text(self) -> str:
        """返回中文描述"""
        return {
            Category.A_SH: "「A股-上证」",
            Category.A_SZ: "「A股-深证」",
            Category.A_BJ: "「A股-北证」",
            Category.X_XX: "「其他」"
        }.get(self, "未知")

    @property
    def fullText(self) -> str:
        return {
            Category.A_SH: f"{Category.A_SH.text} {Category.A_SH}",
            Category.A_SZ: f"{Category.A_SZ.text} {Category.A_SZ}",
            Category.A_BJ: f"{Category.A_BJ.text} {Category.A_BJ}",
            Category.X_XX: f"{Category.X_XX.text} {Category.X_XX}",
        }.get(self, "未知")

    def get_full_code(self, code: str) -> str:
        """
        根据分类和股票代码生成完整代码
        例如：传入 000001 返回 sz000001
        """
        if not code:
            return ""
        prefix_map = {
            Category.A_SH: "sh",
            Category.A_SZ: "sz",
            Category.A_BJ: "bj",
        }
        prefix = prefix_map.get(self, "")
        if not prefix:
            return code
        return f"{prefix}{code}"

    @classmethod
    def values(cls) -> list[str]:
        return [category.value for category in cls]

    @classmethod
    def fullTexts(cls) -> list[str]:
        return [category.fullText for category in cls]

    @classmethod
    def from_stock_code(cls, code: str) -> 'Category':
        """根据股票代码返回对应的 Category"""
        """
        上海证券交易所（沪市）包括：
            主板（600、601、603、605开头）
            科创板（688、689开头）
        深圳证券交易所（深市）包括：
            主板（000开头）
            原中小板（002开头，现已并入主板）
            创业板（300开头）
        """
        if not code:
            return cls.X_XX
            # 上海证券交易所
        if code.startswith(('600', '601', '603', '605', '688', '689')):  # 主板 + 科创板
            return cls.A_SH
        elif code.startswith(('900')):  # 沪市B股
            return cls.A_SH
        elif code.startswith(('500', '550')):  # 沪市基金
            return cls.A_SH
        # 深圳证券交易所（包括主板、中小板和创业板）
        elif code.startswith(('000', '001', '002', '003')):  # 主板（含原中小板）
            return cls.A_SZ
        elif code.startswith(('300')):  # 创业板
            return cls.A_SZ  # 创业板属于深市
        elif code.startswith(('200')):  # 深市B股
            return cls.A_SZ
        elif code.startswith(('150', '160', '161', '162', '163')):  # 深市基金
            return cls.A_SZ
        # 北京证券交易所
        elif code.startswith(('8', '43', '83', '87', '88', '920')):  # 北交所股票 + 新三板做市
            return cls.A_BJ
        # 其他特殊情况（如债券、REITs等）
        elif code.startswith(('10', '11', '12', '13')):  # 沪/深债券（需进一步细分）
            return cls.X_XX
        elif code.startswith(('18')):  # REITs（基础设施基金）
            return cls.X_XX
        return cls.X_XX

    @classmethod
    def parse_full_code(cls, full_code: str) -> Tuple['Category', str]:
        if not full_code or len(full_code) < 3:
            return cls.A_XX, ""
        code = full_code[2:]
        category = cls.from_stock_code(code)
        return category, code
