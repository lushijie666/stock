"""蜡烛图形态识别器"""
from typing import List, Dict
import pandas as pd
from enums.candlestick_pattern import CandlestickPattern


class CandlestickPatternDetector:
    """蜡烛图形态检测器"""

    @staticmethod
    def detect_hammer(df: pd.DataFrame, threshold: float = 2.0) -> List[Dict]:
        """
        检测锤子线形态

        锤子线特征：
        1. 实体较小
        2. 下影线长度至少是实体的2倍
        3. 上影线很短或没有
        4. 通常出现在下跌趋势中，是看涨信号

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            threshold: 下影线与实体的比例阈值，默认2.0

        Returns:
            检测到的锤子线列表，每个元素包含日期、价格、形态类型等信息
        """
        patterns = []

        for i in range(len(df)):
            row = df.iloc[i]
            opening = row['opening']
            closing = row['closing']
            highest = row['highest']
            lowest = row['lowest']

            # 计算实体长度
            body = abs(closing - opening)

            # 避免除零错误，实体太小的跳过
            if body < 0.01:
                continue

            # 计算上下影线长度
            if closing > opening:  # 阳线
                upper_shadow = highest - closing
                lower_shadow = opening - lowest
            else:  # 阴线
                upper_shadow = highest - opening
                lower_shadow = closing - lowest

            # 判断是否为锤子线
            # 1. 下影线长度至少是实体的threshold倍
            # 2. 上影线很短（小于实体的0.3倍）
            if lower_shadow >= body * threshold and upper_shadow <= body * 0.3:
                patterns.append({
                    'date': row['date'] if 'date' in row else row.name,
                    'index': i,
                    'opening': opening,
                    'closing': closing,
                    'highest': highest,
                    'lowest': lowest,
                    'pattern_type': CandlestickPattern.HAMMER,
                    'pattern_name': CandlestickPattern.HAMMER.text,
                    'pattern_icon': CandlestickPattern.HAMMER.icon,
                    'price': lowest,  # 标记在最低点
                    'description': f'下影线/实体比={lower_shadow/body:.2f}'
                })

        return patterns

    @staticmethod
    def detect_inverted_hammer(df: pd.DataFrame, threshold: float = 2.0) -> List[Dict]:
        """
        检测倒锤子线形态

        倒锤子线特征：
        1. 实体较小
        2. 上影线长度至少是实体的2倍
        3. 下影线很短或没有
        4. 通常出现在下跌趋势末期，是潜在看涨信号

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            threshold: 上影线与实体的比例阈值，默认2.0

        Returns:
            检测到的倒锤子线列表
        """
        patterns = []

        for i in range(len(df)):
            row = df.iloc[i]
            opening = row['opening']
            closing = row['closing']
            highest = row['highest']
            lowest = row['lowest']

            # 计算实体长度
            body = abs(closing - opening)

            # 避免除零错误，实体太小的跳过
            if body < 0.01:
                continue

            # 计算上下影线长度
            if closing > opening:  # 阳线
                upper_shadow = highest - closing
                lower_shadow = opening - lowest
            else:  # 阴线
                upper_shadow = highest - opening
                lower_shadow = closing - lowest

            # 判断是否为倒锤子线
            # 1. 上影线长度至少是实体的threshold倍
            # 2. 下影线很短（小于实体的0.3倍）
            if upper_shadow >= body * threshold and lower_shadow <= body * 0.3:
                patterns.append({
                    'date': row['date'] if 'date' in row else row.name,
                    'index': i,
                    'opening': opening,
                    'closing': closing,
                    'highest': highest,
                    'lowest': lowest,
                    'pattern_type': CandlestickPattern.INVERTED_HAMMER,
                    'pattern_name': CandlestickPattern.INVERTED_HAMMER.text,
                    'pattern_icon': CandlestickPattern.INVERTED_HAMMER.icon,
                    'price': highest,  # 标记在最高点
                    'description': f'上影线/实体比={upper_shadow/body:.2f}'
                })

        return patterns

    @staticmethod
    def detect_all_patterns(df: pd.DataFrame) -> List[Dict]:
        """
        检测所有支持的蜡烛图形态

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame

        Returns:
            所有检测到的形态列表
        """
        all_patterns = []

        # 检测锤子线
        all_patterns.extend(CandlestickPatternDetector.detect_hammer(df))

        # 检测倒锤子线
        all_patterns.extend(CandlestickPatternDetector.detect_inverted_hammer(df))

        # 按日期排序
        all_patterns.sort(key=lambda x: x['index'])

        return all_patterns
