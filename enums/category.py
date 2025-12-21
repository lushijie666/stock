from enum import StrEnum
from typing import Tuple, List


class Category(StrEnum):
    """股票分类枚举"""
    A_SH = ("A_SH", "沪A", "「A股-上证」")
    A_SZ = ("A_SZ", "深A", "「A股-深证」")
    A_BJ = ("A_BJ", "京A", "「A股-北证」")
    US_XX = ("US_XX", "美股", "「美股」")
    X_XX = ("X_XX", "其他", "「其他」")

    def __new__(cls, value, code, text):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.code = code
        obj.text = text
        return obj

    @property
    def fullText(self) -> str:
        return f"{self.text} {self.value}"

    def get_full_code(self, code: str, separator: str) -> str:
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
            Category.US_XX: "",
        }
        prefix = prefix_map.get(self, "")
        if not prefix:
            return code
        return f"{prefix}{separator}{code}"

    @classmethod
    def values(cls) -> list[str]:
        return [category.value for category in cls]

    @classmethod
    def fullTexts(cls) -> list[str]:
        return [category.fullText for category in cls]

    @classmethod
    def from_stock_code(cls, code: str) -> 'Category':
        """根据股票代码返回对应的 Category"""
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
        # 美股代码特征（可根据实际情况调整）
        elif any(code.endswith(suffix) for suffix in ['W', 'R', 'Z', 'Q']) or \
             (len(code) >= 1 and code[0].isalpha()) or \
             ('.' in code and any(x.isalpha() for x in code.split('.')[0])):
            return cls.US_XX
        # 其他特殊情况（如债券、REITs等）
        elif code.startswith(('10', '11', '12', '13')):  # 沪/深债券（需进一步细分）
            return cls.X_XX
        elif code.startswith(('18')):  # REITs（基础设施基金）
            return cls.X_XX
        return cls.X_XX

    @classmethod
    def parse_full_code(cls, full_code: str) -> Tuple['Category', str]:
        if not full_code or len(full_code) < 3:
            return cls.X_XX, ""
        # 处理美股代码（通常没有前缀）
        if not full_code.startswith(('sh', 'sz', 'bj')):
            code = full_code
            category = cls.from_stock_code(code)
            return category, code

        # 处理A股代码
        if len(full_code) < 3:
            return cls.X_XX, ""
        code = full_code[2:]
        category = cls.from_stock_code(code)
        return category, code

    @classmethod
    def get_all(cls) -> List['Category']:
        return [cls.A_SH, cls.A_SZ, cls.A_BJ, cls.US_XX, cls.X_XX]
