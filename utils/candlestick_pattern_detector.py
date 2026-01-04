"""蜡烛图形态识别器"""
from typing import List, Dict
import pandas as pd
from enums.candlestick_pattern import CandlestickPattern


class CandlestickPatternDetector:
    """蜡烛图形态检测器"""

    @staticmethod
    def detect_hammer(df: pd.DataFrame, threshold: float = 2.0, trend_period: int = 5) -> List[Dict]:
        """
        检测锤子线形态
        底部反转形态(看涨信号)
        🗳 之前存在下降趋势 - 前 5 天的前半段(5/2天的收盘价平均值) <  后半段(5 - 5/2天的收盘价平均值)
        🗳 可以是阳线或阴线, 实体较小 - 实体长度(收盘价 - 开盘价绝对值) > 0.01
        🗳 下影线长度至少是实体的2倍 - 下影线长度 >= 实体长度 * 2.0
        🗳 上影线很短或没有 - 上影线长度 <= 实体长度 * 0.3
        🗳 收盘价位于最高价或接近最高价 - (收盘价 - 最低价) / (最高价 - 最低价) >= 0.6
        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            threshold: 下影线与实体的比例阈值，默认2.0, 上隐线与实体的比例阈值默认 0.3
            trend_period: 判断趋势的周期，默认5天
        Returns:
            检测到的锤子线列表，每个元素包含日期、价格、形态类型等信息
        """
        patterns = []

        for i in range(trend_period, len(df)):  # 从trend_period开始，确保有足够的历史数据判断趋势
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
            # 1. 判断是否为锤子线形态特征
            # 下影线长度至少是实体的threshold倍
            # 上影线很短（小于实体的0.3倍）
            if not (lower_shadow >= body * threshold and upper_shadow <= body * 0.3):
                continue
            # 2. 判断收盘价位置：收盘价应该在K线的上半部分
            # 计算收盘价在整个K线范围内的位置比例
            k_line_range = highest - lowest
            if k_line_range == 0:
                continue
            close_position = (closing - lowest) / k_line_range
            # 收盘价应该在上半部分（大于0.6表示接近最高价）
            if close_position < 0.6:
                continue
            # 3. 判断之前是否存在下降趋势
            # 检查前trend_period天的趋势
            previous_closes = df.iloc[i-trend_period:i]['closing'].tolist()
            if len(previous_closes) < 2:
                continue
            # 计算趋势：比较前几天的平均收盘价
            early_avg = sum(previous_closes[:trend_period//2]) / (trend_period//2)
            recent_avg = sum(previous_closes[trend_period//2:]) / (trend_period - trend_period//2)
            # 如果recent_avg < early_avg，说明存在下降趋势
            is_downtrend = recent_avg < early_avg
            if not is_downtrend:
               continue
            # 满足所有条件，记录锤子线
            patterns.append({
                'date': row['date'] if 'date' in row else row.name,
                'index': i,
                'row': row.to_dict(),
                'pattern_type': CandlestickPattern.HAMMER,
                'price': lowest,
                'description': f'实体={body:.2f}, 'f'下影线/实体比={lower_shadow/body:.2f}, 收盘位置={close_position:.1%}, 下跌差价={abs(recent_avg-early_avg):.2f}'
            })
        return patterns

    @staticmethod
    def detect_hanging_man(df: pd.DataFrame, threshold: float = 2.0, trend_period: int = 5) -> List[Dict]:
        """
        检测上吊线形态
        顶部反转形态（看跌信号）
        🗳 之前存在上升趋势 - 前 5 天的前半段(5/2天的收盘价平均值) >  后半段(5 - 5/2天的收盘价平均值)
        🗳 当前价格处于高位 -> 当前收盘价 >= 前期 5 天收盘平均值 * 0.95
        🗳 可以是阳线或阴线, 实体较小 - 实体长度(收盘价 - 开盘价绝对值) > 0.01
        🗳 下影线长度至少是实体的2倍 - 下影线长度 >= 实体长度 * 2.0
        🗳 上影线很短或没有 - 上影线长度 <= 实体长度 * 0.3
        🗳 收盘价位于最高价或接近最高价 - (收盘价 - 最低价) / (最高价 - 最低价) >= 0.6
        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            threshold: 下影线与实体的比例阈值，默认2.0
            trend_period: 判断趋势的周期，默认5天

        Returns:
            检测到的上吊线列表，每个元素包含日期、价格、形态类型等信息
        """
        patterns = []

        for i in range(trend_period, len(df)):  # 从trend_period开始，确保有足够的历史数据判断趋势
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

            # 1. 判断是否为上吊线形态特征（与锤子线形态相同）
            # 下影线长度至少是实体的threshold倍
            # 上影线很短（小于实体的0.3倍）
            if not (lower_shadow >= body * threshold and upper_shadow <= body * 0.3):
                continue

            # 2. 判断收盘价位置：收盘价应该在K线的上半部分
            # 计算收盘价在整个K线范围内的位置比例
            k_line_range = highest - lowest
            if k_line_range == 0:
                continue
            close_position = (closing - lowest) / k_line_range
            # 收盘价应该在上半部分（大于0.6表示接近最高价）
            if close_position < 0.6:
                continue

            # 3. 判断之前是否存在上升趋势（与锤子线相反）
            # 检查前trend_period天的趋势
            previous_closes = df.iloc[i-trend_period:i]['closing'].tolist()
            if len(previous_closes) < 2:
                continue

            # 计算趋势：比较前几天的平均收盘价
            early_avg = sum(previous_closes[:trend_period//2]) / (trend_period//2)
            recent_avg = sum(previous_closes[trend_period//2:]) / (trend_period - trend_period//2)

            # 如果recent_avg > early_avg，说明存在上升趋势
            is_uptrend = recent_avg > early_avg

            if not is_uptrend:
                continue

            # 4. 判断是否在高位：当前收盘价应该高于前期平均价
            # 这是上吊线与锤子线的关键区别
            avg_price = (early_avg + recent_avg) / 2
            is_at_high = closing >= avg_price * 0.95  # 当前价格至少是平均价的95%

            if not is_at_high:
                continue

            # 满足所有条件，记录上吊线
            patterns.append({
                'date': row['date'] if 'date' in row else row.name,
                'index': i,
                'row': row.to_dict(),
                'pattern_type': CandlestickPattern.HANGING_MAN,
                'price': highest,  # 标记在最高点，因为是顶部反转信号
                'description': f'实体={body:.2f}, 'f'下影线/实体比={lower_shadow/body:.2f}, 收盘位置={close_position:.1%}, 上涨差价={abs(recent_avg-early_avg):.2f}'
            })

        return patterns

    @staticmethod
    def detect_inverted_hammer(df: pd.DataFrame, threshold: float = 2.0, trend_period: int = 5) -> List[Dict]:
        """
        检测倒锤子线形态（Inverted Hammer）
        底部反转形态（看涨信号）

        🗳 之前存在下降趋势 - 前 5 天的前半段(5/2天的收盘价平均值) < 后半段(5 - 5/2天的收盘价平均值)
        🗳 可以是阳线或阴线, 实体较小 - 实体长度(收盘价 - 开盘价绝对值) > 0.01
        🗳 上影线长度至少是实体的2倍 - 上影线长度 >= 实体长度 * 2.0
        🗳 下影线很短或没有 - 下影线长度 <= 实体长度 * 0.3
        🗳 收盘价位于最低价或接近最低价 - (最高价 - 收盘价) / (最高价 - 最低价) >= 0.6

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            threshold: 上影线与实体的比例阈值，默认2.0
            trend_period: 判断趋势的周期，默认5天

        Returns:
            检测到的倒锤子线列表，每个元素包含日期、价格、形态类型等信息
        """
        patterns = []

        for i in range(trend_period, len(df)):  # 从trend_period开始，确保有足够的历史数据判断趋势
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

            # 1. 判断是否为倒锤子线形态特征
            # 上影线长度至少是实体的threshold倍
            # 下影线很短（小于实体的0.3倍）
            if not (upper_shadow >= body * threshold and lower_shadow <= body * 0.3):
                continue

            # 2. 判断收盘价位置：收盘价应该在K线的下半部分
            # 计算收盘价在整个K线范围内的位置比例
            k_line_range = highest - lowest
            if k_line_range == 0:
                continue
            close_position = (highest - closing) / k_line_range
            # 收盘价应该在下半部分（大于0.6表示接近最低价）
            if close_position < 0.6:
                continue

            # 3. 判断之前是否存在下降趋势
            # 检查前trend_period天的趋势
            previous_closes = df.iloc[i-trend_period:i]['closing'].tolist()
            if len(previous_closes) < 2:
                continue

            # 计算趋势：比较前几天的平均收盘价
            early_avg = sum(previous_closes[:trend_period//2]) / (trend_period//2)
            recent_avg = sum(previous_closes[trend_period//2:]) / (trend_period - trend_period//2)

            # 如果recent_avg < early_avg，说明存在下降趋势
            is_downtrend = recent_avg < early_avg

            if not is_downtrend:
                continue

            # 满足所有条件，记录倒锤子线
            patterns.append({
                'date': row['date'] if 'date' in row else row.name,
                'index': i,
                'row': row.to_dict(),
                'pattern_type': CandlestickPattern.INVERTED_HAMMER,
                'price': highest,  # 标记在最高点（上影线顶部）
                'description': f'实体={body:.2f}, 'f'上影线/实体比={upper_shadow/body:.2f}, 收盘位置={close_position:.1%}, 下跌差价={abs(recent_avg-early_avg):.2f}'
            })

        return patterns

    @staticmethod
    def detect_shooting_star(df: pd.DataFrame, threshold: float = 2.0, trend_period: int = 5) -> List[Dict]:
        """
        检测流星线形态（Shooting Star）
        顶部反转形态（看跌信号）

        核心特征（参考《日本蜡烛图技术》）：
        🗳 之前存在上升趋势 - 前 5 天的前半段(5/2天的收盘价平均值) > 后半段(5 - 5/2天的收盘价平均值)
        🗳 当前价格处于高位 -> 当前收盘价 >= 前期 5 天收盘平均值 * 0.95
        🗳 可以是阳线或阴线, 实体较小 - 实体长度(收盘价 - 开盘价绝对值) > 0.01
        🗳 上影线长度至少是实体的2倍 - 上影线长度 >= 实体长度 * 2.0
        🗳 下影线很短或没有 - 下影线长度 <= 实体长度 * 0.3
        🗳 收盘价位于最低价或接近最低价 - (最高价 - 收盘价) / (最高价 - 最低价) >= 0.6

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            threshold: 上影线与实体的比例阈值，默认2.0
            trend_period: 判断趋势的周期，默认5天

        Returns:
            检测到的流星线列表，每个元素包含日期、价格、形态类型等信息
        """
        patterns = []

        for i in range(trend_period, len(df)):  # 从trend_period开始，确保有足够的历史数据判断趋势
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

            # 1. 判断是否为流星线形态特征（与倒锤子线形态相同）
            # 上影线长度至少是实体的threshold倍
            # 下影线很短（小于实体的0.3倍）
            if not (upper_shadow >= body * threshold and lower_shadow <= body * 0.3):
                continue

            # 2. 判断收盘价位置：收盘价应该在K线的下半部分
            # 计算收盘价在整个K线范围内的位置比例
            k_line_range = highest - lowest
            if k_line_range == 0:
                continue
            close_position = (highest - closing) / k_line_range
            # 收盘价应该在下半部分（大于0.6表示接近最低价）
            if close_position < 0.6:
                continue

            # 3. 判断之前是否存在上升趋势（与倒锤子线相反）
            # 检查前trend_period天的趋势
            previous_closes = df.iloc[i-trend_period:i]['closing'].tolist()
            if len(previous_closes) < 2:
                continue

            # 计算趋势：比较前几天的平均收盘价
            early_avg = sum(previous_closes[:trend_period//2]) / (trend_period//2)
            recent_avg = sum(previous_closes[trend_period//2:]) / (trend_period - trend_period//2)

            # 如果recent_avg > early_avg，说明存在上升趋势
            is_uptrend = recent_avg > early_avg

            if not is_uptrend:
                continue

            # 4. 判断是否在高位：当前收盘价应该高于前期平均价
            # 这是流星线与倒锤子线的关键区别
            avg_price = (early_avg + recent_avg) / 2
            is_at_high = closing >= avg_price * 0.95  # 当前价格至少是平均价的95%

            if not is_at_high:
                continue

            # 满足所有条件，记录流星线
            patterns.append({
                'date': row['date'] if 'date' in row else row.name,
                'index': i,
                'row': row.to_dict(),
                'pattern_type': CandlestickPattern.SHOOTING_STAR,
                'price': highest,  # 标记在最高点（顶部反转信号）
                'description': f'实体={body:.2f}, 'f'上影线/实体比={upper_shadow/body:.2f}, 收盘位置={close_position:.1%}, 上涨差价={abs(recent_avg-early_avg):.2f}'
            })

        return patterns

    @staticmethod
    def detect_bullish_engulfing(df: pd.DataFrame, trend_period: int = 5, min_body_ratio: float = 1.0) -> List[Dict]:
        """
        检测看涨吞没形态（Bullish Engulfing）
        底部反转形态 - 双K线形态

        🗳 之前存在下降趋势 - 前 5 天的前半段收盘价平均值 < 后半段收盘价平均值
        🗳 第一根K线是阴线 - 开盘价 > 收盘价
        🗳 第二根K线是阳线 - 收盘价 > 开盘价
        🗳 第二根K线的实体完全吞没第一根K线的实体
        🗳 第二根阳线的开盘价低于前一日阴线的收盘价 - 形成向下跳空
        🗳 第二根阳线的收盘价高于前一日阴线的开盘价
        🗳 第二根K线实体明显大于第一根 - 第二根实体 >= 第一根实体 * min_body_ratio

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            trend_period: 判断趋势的周期，默认5天
            min_body_ratio: 第二根K线实体与第一根的最小比例，默认1.0（完全吞没）

        Returns:
            检测到的看涨吞没形态列表
        """
        patterns = []

        # 从trend_period+1开始，需要前一天数据和足够的历史数据判断趋势
        for i in range(trend_period + 1, len(df)):
            prev_row = df.iloc[i - 1]  # 第一根K线
            curr_row = df.iloc[i]       # 第二根K线

            prev_opening = prev_row['opening']
            prev_closing = prev_row['closing']
            curr_opening = curr_row['opening']
            curr_closing = curr_row['closing']

            # 1. 判断第一根是阴线，第二根是阳线
            if not (prev_closing < prev_opening and curr_closing > curr_opening):
                continue

            # 2. 计算实体长度
            prev_body = abs(prev_closing - prev_opening)
            curr_body = abs(curr_closing - curr_opening)

            # 实体太小的跳过
            if prev_body < 0.01 or curr_body < 0.01:
                continue

            # 3. 判断吞没关系
            # 第二根阳线的开盘价 <= 前一日阴线的收盘价（下方）
            # 第二根阳线的收盘价 >= 前一日阴线的开盘价（上方）
            if not (curr_opening <= prev_closing and curr_closing >= prev_opening):
                continue

            # 4. 第二根K线实体应该明显大于第一根
            if curr_body < prev_body * min_body_ratio:
                continue

            # 5. 判断之前存在下降趋势
            if i >= trend_period:
                half = trend_period // 2
                early_avg = df.iloc[i - trend_period:i - trend_period + half]['closing'].mean()
                recent_avg = df.iloc[i - half:i]['closing'].mean()

                # 下降趋势：早期平均 > 近期平均
                if early_avg <= recent_avg:
                    continue

            # 计算吞没幅度和趋势强度
            engulfing_ratio = curr_body / prev_body


            patterns.append({
                'date': curr_row['date'] if 'date' in curr_row else curr_row.name,
                'index': i,
                'row': curr_row,
                'pattern_type': CandlestickPattern.BULLISH_ENGULFING,
                'price': curr_row['lowest'],  # 标记在最低点（底部反转）
                'start_index': i - 1,  # 双K线形态开始位置（第一根K线）
                'end_index': i,        # 双K线形态结束位置（第二根K线）
                'description': f'实体=1:{prev_body:.2f} → 2:{curr_body:.2f}, 'f'吞没比(2-1)={abs(engulfing_ratio):.2f}, 下跌差价={abs(recent_avg - early_avg):.2f}'
            })

        return patterns

    @staticmethod
    def detect_bearish_engulfing(df: pd.DataFrame, trend_period: int = 5, min_body_ratio: float = 1.0) -> List[Dict]:
        """
        检测看跌吞没形态（Bearish Engulfing）
        顶部反转形态 - 双K线形态

        🗳 之前存在上升趋势 - 前 5 天的前半段收盘价平均值 > 后半段收盘价平均值
        🗳 第一根K线是阳线 - 收盘价 > 开盘价
        🗳 第二根K线是阴线 - 开盘价 > 收盘价
        🗳 第二根K线的实体完全吞没第一根K线的实体
        🗳 第二根阴线的开盘价高于前一日阳线的收盘价 - 形成向上跳空
        🗳 第二根阴线的收盘价低于前一日阳线的开盘价
        🗳 第二根K线实体明显大于第一根 - 第二根实体 >= 第一根实体 * min_body_ratio

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            trend_period: 判断趋势的周期，默认5天
            min_body_ratio: 第二根K线实体与第一根的最小比例，默认1.0（完全吞没）

        Returns:
            检测到的看跌吞没形态列表
        """
        patterns = []

        # 从trend_period+1开始，需要前一天数据和足够的历史数据判断趋势
        for i in range(trend_period + 1, len(df)):
            prev_row = df.iloc[i - 1]  # 第一根K线
            curr_row = df.iloc[i]       # 第二根K线

            prev_opening = prev_row['opening']
            prev_closing = prev_row['closing']
            curr_opening = curr_row['opening']
            curr_closing = curr_row['closing']

            # 1. 判断第一根是阳线，第二根是阴线
            if not (prev_closing > prev_opening and curr_closing < curr_opening):
                continue

            # 2. 计算实体长度
            prev_body = abs(prev_closing - prev_opening)
            curr_body = abs(curr_closing - curr_opening)

            # 实体太小的跳过
            if prev_body < 0.01 or curr_body < 0.01:
                continue

            # 3. 判断吞没关系
            # 第二根阴线的开盘价 >= 前一日阳线的收盘价（上方）
            # 第二根阴线的收盘价 <= 前一日阳线的开盘价（下方）
            if not (curr_opening >= prev_closing and curr_closing <= prev_opening):
                continue

            # 4. 第二根K线实体应该明显大于第一根
            if curr_body < prev_body * min_body_ratio:
                continue

            # 5. 判断之前存在上升趋势
            if i >= trend_period:
                half = trend_period // 2
                early_avg = df.iloc[i - trend_period:i - trend_period + half]['closing'].mean()
                recent_avg = df.iloc[i - half:i]['closing'].mean()

                # 上升趋势：早期平均 < 近期平均
                if early_avg >= recent_avg:
                    continue

            # 计算吞没幅度和趋势强度
            engulfing_ratio = curr_body / prev_body

            patterns.append({
                'date': curr_row['date'] if 'date' in curr_row else curr_row.name,
                'index': i,
                'row': curr_row,
                'pattern_type': CandlestickPattern.BEARISH_ENGULFING,
                'price': curr_row['highest'],  # 标记在最高点（顶部反转）
                'start_index': i - 1,  # 双K线形态开始位置（第一根K线）
                'end_index': i,        # 双K线形态结束位置（第二根K线）
                'description': f'实体=1:{prev_body:.2f} → 2:{curr_body:.2f}, 'f'吞没比(2-1)={abs(engulfing_ratio):.2f}, 上涨差价={abs(recent_avg - early_avg):.2f}'
            })

        return patterns

    @staticmethod
    def detect_dark_cloud_cover(df: pd.DataFrame, trend_period: int = 5, min_penetration: float = 0.5) -> List[Dict]:
        """
        检测乌云盖顶形态（Dark Cloud Cover）
        顶部反转形态 - 双K线形态

        🗳 之前存在上升趋势 - 前 5 天的前半段收盘价平均值 < 后半段收盘价平均值
        🗳 第一根K线是阳线（最好是大阳线） - 收盘价 > 开盘价
        🗳 第二根K线是阴线 - 开盘价 > 收盘价
        🗳 第二根K线的开盘价高于第一根K线的最高价 - 形成向上跳空
        🗳 第二根K线的收盘价深入到第一根K线实体内部 - 穿透比例 >= 50%
        🗳 第二根阴线的收盘价应该低于第一根阳线实体的中点
        🗳 第二根阴线的收盘价应该高于第一根阳线的开盘价（未完全吞没）

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            trend_period: 判断趋势的周期，默认5天
            min_penetration: 最小穿透比例，默认0.5（50%）

        Returns:
            检测到的乌云盖顶形态列表
        """
        patterns = []

        # 从trend_period+1开始，需要前一天数据和足够的历史数据判断趋势
        for i in range(trend_period + 1, len(df)):
            prev_row = df.iloc[i - 1]  # 第一根K线（阳线）
            curr_row = df.iloc[i]       # 第二根K线（阴线）

            prev_opening = prev_row['opening']
            prev_closing = prev_row['closing']
            prev_highest = prev_row['highest']
            curr_opening = curr_row['opening']
            curr_closing = curr_row['closing']

            # 1. 判断第一根是阳线，第二根是阴线
            if not (prev_closing > prev_opening and curr_closing < curr_opening):
                continue

            # 2. 计算实体长度
            prev_body = abs(prev_closing - prev_opening)
            curr_body = abs(curr_closing - curr_opening)

            # 实体太小的跳过
            if prev_body < 0.01:
                continue

            # 3. 第二根K线开盘价应该高于第一根K线的最高价（向上跳空）
            if curr_opening <= prev_highest:
                continue

            # 4. 第二根阴线的收盘价应该深入第一根阳线实体内部
            # 收盘价必须低于第一根阳线的收盘价
            if curr_closing >= prev_closing:
                continue

            # 5. 计算穿透深度（第二根阴线收盘价穿透第一根阳线实体的比例）
            penetration = (prev_closing - curr_closing) / prev_body

            # 穿透深度应该至少达到50%（最好是50%-100%之间）
            if penetration < min_penetration:
                continue

            # 6. 第二根阴线的收盘价应该高于第一根阳线的开盘价（未完全吞没）
            if curr_closing <= prev_opening:
                continue

            # 7. 判断之前存在上升趋势
            if i >= trend_period:
                half = trend_period // 2
                early_avg = df.iloc[i - trend_period:i - trend_period + half]['closing'].mean()
                recent_avg = df.iloc[i - half:i]['closing'].mean()

                # 上升趋势：早期平均 < 近期平均
                if early_avg >= recent_avg:
                    continue

            # 计算穿透比例和趋势强度
            gap = curr_opening - prev_highest  # 跳空缺口大小

            patterns.append({
                'date': curr_row['date'] if 'date' in curr_row else curr_row.name,
                'index': i,
                'row': curr_row,
                'pattern_type': CandlestickPattern.DARK_CLOUD_COVER,
                'price': curr_row['highest'],  # 标记在最高点（顶部反转）
                'start_index': i - 1,  # 双K线形态开始位置（第一根K线）
                'end_index': i,        # 双K线形态结束位置（第二根K线）
                'description': f'实体=1:{prev_body:.2f} → 2: {curr_body:.2f}, 'f'穿透比(2-1)={abs(penetration):.1%}, 跳空(1-2)={abs(gap):.2f}, 上涨差价={abs(recent_avg - early_avg):.2f}'

            })

        return patterns

    @staticmethod
    def detect_piercing_pattern(df: pd.DataFrame, trend_period: int = 5, min_penetration: float = 0.5) -> List[Dict]:
        """
        检测刺透形态（Piercing Pattern）
        底部反转形态 - 双K线形态

        🗳 之前存在下降趋势 - 前 5 天的前半段收盘价平均值 > 后半段收盘价平均值
        🗳 第一根K线是阴线（最好是大阴线） - 开盘价 > 收盘价
        🗳 第二根K线是阳线 - 收盘价 > 开盘价
        🗳 第二根K线的开盘价低于第一根K线的最低价 - 形成向下跳空
        🗳 第二根K线的收盘价深入到第一根K线实体内部 - 穿透比例 >= 50%
        🗳 第二根阳线的收盘价应该高于第一根阴线实体的中点
        🗳 第二根阳线的收盘价应该低于第一根阴线的开盘价（未完全吞没）

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            trend_period: 判断趋势的周期，默认5天
            min_penetration: 最小穿透比例，默认0.5（50%）

        Returns:
            检测到的刺透形态列表
        """
        patterns = []

        # 从trend_period+1开始，需要前一天数据和足够的历史数据判断趋势
        for i in range(trend_period + 1, len(df)):
            prev_row = df.iloc[i - 1]  # 第一根K线（阴线）
            curr_row = df.iloc[i]       # 第二根K线（阳线）

            prev_opening = prev_row['opening']
            prev_closing = prev_row['closing']
            prev_lowest = prev_row['lowest']
            curr_opening = curr_row['opening']
            curr_closing = curr_row['closing']

            # 1. 判断第一根是阴线，第二根是阳线
            if not (prev_closing < prev_opening and curr_closing > curr_opening):
                continue

            # 2. 计算实体长度
            prev_body = abs(prev_closing - prev_opening)
            curr_body = abs(curr_closing - curr_opening)

            # 实体太小的跳过
            if prev_body < 0.01:
                continue

            # 3. 第二根K线开盘价应该低于第一根K线的最低价
            if curr_opening >= prev_lowest:
                continue

            # 4. 第二根阳线的收盘价应该深入第一根阴线实体内部
            # 收盘价必须高于第一根阴线的收盘价
            if curr_closing <= prev_closing:
                continue

            # 5. 计算穿透深度（第二根阳线收盘价穿透第一根阴线实体的比例）
            penetration = (curr_closing - prev_closing) / prev_body

            # 穿透深度应该至少达到50%（最好是50%-100%之间）
            if penetration < min_penetration:
                continue

            # 6. 第二根阳线的收盘价应该低于第一根阴线的开盘价（未完全吞没）
            if curr_closing >= prev_opening:
                continue

            # 7. 判断之前存在下降趋势
            if i >= trend_period:
                half = trend_period // 2
                early_avg = df.iloc[i - trend_period:i - trend_period + half]['closing'].mean()
                recent_avg = df.iloc[i - half:i]['closing'].mean()

                # 下降趋势：早期平均 > 近期平均
                if early_avg <= recent_avg:
                    continue

            gap = prev_lowest - curr_opening  # 跳空缺口大小

            patterns.append({
                'date': curr_row['date'] if 'date' in curr_row else curr_row.name,
                'index': i,
                'row': curr_row,
                'pattern_type': CandlestickPattern.PIERCING_PATTERN,
                'price': curr_row['lowest'],  # 标记在最低点（底部反转）
                'start_index': i - 1,  # 双K线形态开始位置（第一根K线）
                'end_index': i,        # 双K线形态结束位置（第二根K线）
                'description': f'实体=1:{prev_body:.2f} → 2:{curr_body:.2f}, 'f'穿透比(2-1)={abs(penetration):.1%}, 跳空(1-2)={abs(gap):.2f}, 下跌差价={abs(recent_avg - early_avg):.2f}'
            })

        return patterns

    @staticmethod
    def detect_morning_star(df: pd.DataFrame, trend_period: int = 5, star_body_ratio: float = 0.3, min_gap: float = 0.01) -> List[Dict]:
        """
        检测启明星形态（Morning Star）
        底部反转形态 - 三K线形态

        🗳 之前存在下降趋势 - 前 5 天的前半段收盘价平均值 > 后半段收盘价平均值
        🗳 第一根K线是大阴线 - 开盘价 > 收盘价，实体较大
        🗳 第二根K线是小实体星线（可阴可阳） - 实体很小，低于第一根K线
        🗳 第二根星线与第一根阴线之间有向下跳空 - 形成缺口
        🗳 第三根K线是阳线 - 收盘价 > 开盘价
        🗳 第三根阳线与第二根星线之间有向上跳空 - 形成缺口
        🗳 第三根阳线的收盘价深入第一根阴线实体内部 - 最好超过50%

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            trend_period: 判断趋势的周期，默认5天
            star_body_ratio: 星线实体占第一根K线实体的最大比例，默认0.3（30%）
            min_gap: 最小跳空缺口，默认0.01

        Returns:
            检测到的启明星形态列表
        """
        patterns = []

        # 从trend_period+2开始，需要前两天数据和足够的历史数据判断趋势
        for i in range(trend_period + 2, len(df)):
            first_row = df.iloc[i - 2]   # 第一根K线（大阴线）
            second_row = df.iloc[i - 1]  # 第二根K线（星线）
            third_row = df.iloc[i]       # 第三根K线（阳线）

            first_opening = first_row['opening']
            first_closing = first_row['closing']
            first_lowest = first_row['lowest']

            second_opening = second_row['opening']
            second_closing = second_row['closing']
            second_highest = second_row['highest']
            second_lowest = second_row['lowest']

            third_opening = third_row['opening']
            third_closing = third_row['closing']

            # 1. 第一根必须是阴线
            if first_closing >= first_opening:
                continue

            # 2. 计算第一根阴线的实体长度
            first_body = first_opening - first_closing

            # 第一根实体应该较大
            if first_body < 0.01:
                continue

            # 3. 第二根是小实体星线（可阴可阳）
            second_body = abs(second_closing - second_opening)

            # 星线实体应该很小，小于第一根实体的30%
            if second_body > first_body * star_body_ratio:
                continue

            # 4. 第二根星线与第一根阴线之间有向下跳空
            # 星线的最高价应该低于第一根阴线的最低价
            gap_down = first_lowest - second_highest
            if gap_down < min_gap:
                continue

            # 5. 第三根必须是阳线
            if third_closing <= third_opening:
                continue
            third_body = abs(third_closing - third_opening)

            # 6. 第三根阳线与第二根星线之间有向上跳空
            # 第三根的开盘价应该高于星线的最高价
            gap_up = third_opening - second_highest
            if gap_up < min_gap:
                continue

            # 7. 第三根阳线的收盘价应该深入第一根阴线实体内部
            # 收盘价应该高于第一根阴线的收盘价
            if third_closing <= first_closing:
                continue

            # 8. 判断之前存在下降趋势
            if i >= trend_period + 2:
                half = trend_period // 2
                early_avg = df.iloc[i - trend_period - 2:i - trend_period - 2 + half]['closing'].mean()
                recent_avg = df.iloc[i - half - 2:i - 2]['closing'].mean()

                # 下降趋势：早期平均 > 近期平均
                if early_avg <= recent_avg:
                    continue

            # 计算穿透深度
            penetration = (third_closing - first_closing) / first_body if first_body > 0 else 0

            patterns.append({
                'date': third_row['date'] if 'date' in third_row else third_row.name,
                'index': i,
                'row': third_row,
                'pattern_type': CandlestickPattern.MORNING_STAR,
                'price': third_row['lowest'],  # 标记在最低点（底部反转）
                'start_index': i - 2,  # 形态开始位置
                'end_index': i,        # 形态结束位置
                'description': f'实体=1:{first_body:.2f} → 2:{second_body:.2f} → 3:{third_body:.2f}, 'f'穿透比(3-1)={abs(penetration):.1%}, 下跳空(1-2)={abs(gap_down):.2f}, 上跳空(2-3)={abs(gap_up):.2f}, 'f'下跌差价={abs(recent_avg - early_avg):.2f}'
            })

        return patterns

    @staticmethod
    def detect_evening_star(df: pd.DataFrame, trend_period: int = 5, star_body_ratio: float = 0.3,
                           min_gap: float = 0.01) -> List[Dict]:
        """
        检测黄昏星形态（Evening Star）
        顶部反转形态 - 三K线形态

        核心特征（参考《日本蜡烛图技术》）：
        🗳 之前存在上升趋势 - 前 5 天的前半段收盘价平均值 < 后半段收盘价平均值
        🗳 第一根K线是大阳线 - 收盘价 > 开盘价，实体较大
        🗳 第二根K线是小实体星线（可阴可阳） - 实体很小，高于第一根K线
        🗳 第二根星线与第一根阳线之间有向上跳空 - 形成缺口
        🗳 第三根K线是阴线 - 开盘价 > 收盘价
        🗳 第三根阴线与第二根星线之间有向下跳空 - 形成缺口
        🗳 第三根阴线的收盘价深入第一根阳线实体内部 - 最好超过50%

        Args:
            df: 包含开盘价、收盘价、最高价、最低价的DataFrame
            trend_period: 判断趋势的周期，默认5天
            star_body_ratio: 星线实体占第一根K线实体的最大比例，默认0.3（30%）
            min_gap: 最小跳空缺口，默认0.01

        Returns:
            检测到的黄昏星形态列表
        """
        patterns = []

        # 从trend_period+2开始，需要前两天数据和足够的历史数据判断趋势
        for i in range(trend_period + 2, len(df)):
            first_row = df.iloc[i - 2]   # 第一根K线（大阳线）
            second_row = df.iloc[i - 1]  # 第二根K线（星线）
            third_row = df.iloc[i]       # 第三根K线（阴线）

            first_opening = first_row['opening']
            first_closing = first_row['closing']
            first_highest = first_row['highest']

            second_opening = second_row['opening']
            second_closing = second_row['closing']
            second_highest = second_row['highest']
            second_lowest = second_row['lowest']

            third_opening = third_row['opening']
            third_closing = third_row['closing']

            # 1. 第一根必须是阳线
            if first_closing <= first_opening:
                continue

            # 2. 计算第一根阳线的实体长度
            first_body = first_closing - first_opening

            # 第一根实体应该较大
            if first_body < 0.01:
                continue

            # 3. 第二根是小实体星线（可阴可阳）
            second_body = abs(second_closing - second_opening)

            # 星线实体应该很小，小于第一根实体的30%
            if second_body > first_body * star_body_ratio:
                continue

            # 4. 第二根星线与第一根阳线之间有向上跳空
            # 星线的最低价应该高于第一根阳线的最高价
            gap_up = second_lowest - first_highest
            if gap_up < min_gap:
                continue

            # 5. 第三根必须是阴线
            if third_closing >= third_opening:
                continue
            third_body = abs(third_closing - third_opening)

            # 6. 第三根阴线与第二根星线之间有向下跳空
            # 第三根的开盘价应该低于星线的最低价
            gap_down = second_lowest - third_opening
            if gap_down < min_gap:
                continue

            # 7. 第三根阴线的收盘价应该深入第一根阳线实体内部
            # 收盘价应该低于第一根阳线的收盘价
            if third_closing >= first_closing:
                continue

            # 8. 判断之前存在上升趋势
            if i >= trend_period + 2:
                half = trend_period // 2
                early_avg = df.iloc[i - trend_period - 2:i - trend_period - 2 + half]['closing'].mean()
                recent_avg = df.iloc[i - half - 2:i - 2]['closing'].mean()

                # 上升趋势：早期平均 < 近期平均
                if early_avg >= recent_avg:
                    continue

            # 计算穿透深度
            penetration = (first_closing - third_closing) / first_body if first_body > 0 else 0

            patterns.append({
                'date': third_row['date'] if 'date' in third_row else third_row.name,
                'index': i,
                'row': third_row,
                'pattern_type': CandlestickPattern.EVENING_STAR,
                'price': third_row['highest'],  # 标记在最高点（顶部反转）
                'start_index': i - 2,  # 形态开始位置
                'end_index': i,        # 形态结束位置
                'description': f'实体=1:{first_body:.2f} → 2:{second_body:.2f} → 3:{third_body:.2f}, 'f'穿透比(3-1)={abs(penetration):.1%}, 上跳空(1-2)={abs(gap_up):.2f}, 下跳空(2-3)={abs(gap_down):.2f}, 'f'下跌差价={abs(recent_avg - early_avg):.2f}'

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

        # 单K线形态
        # 检测锤子线（底部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_hammer(df))

        # 检测上吊线（顶部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_hanging_man(df))

        # 检测倒锤子线（底部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_inverted_hammer(df))

        # 检测流星线（顶部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_shooting_star(df))

        # 双K线形态
        # 检测看涨吞没（底部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_bullish_engulfing(df))

        # 检测看跌吞没（顶部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_bearish_engulfing(df))

        # 检测刺透形态（底部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_piercing_pattern(df))

        # 检测乌云盖顶（顶部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_dark_cloud_cover(df))

        # 三K线形态
        # 检测启明星（底部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_morning_star(df))

        # 检测黄昏星（顶部反转）
        all_patterns.extend(CandlestickPatternDetector.detect_evening_star(df))

        # 按日期排序
        all_patterns.sort(key=lambda x: x['index'])

        return all_patterns

    @staticmethod
    def get_pattern_algorithm_info() -> List[Dict]:
        """
        获取所有已实现的形态算法描述信息

        Returns:
            形态算法信息列表，每个元素包含：
            - pattern_type: 形态类型枚举
            - category: 形态类别（底部反转/顶部反转/中性等）
            - criteria: 算法判定标准列表
            - color_class: CSS颜色类名
        """
        return [
            {
                'pattern_type': CandlestickPattern.HAMMER,
                'category': '单K线 - 底部反转',
                'signal': "看涨",
                'criteria': [
                    "之前存在下降趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &lt;  后半段(5 - 5/2天的收盘价平均值)",
                    "可以是阳线或阴线, 实体较小 -> 实体长度(收盘价 - 开盘价绝对值) &gt; 0.01",
                    "下影线长度至少是实体的2倍 -> 下影线长度 &gt;= 实体长度 * 2.0",
                    "上影线很短或没有 -> 上影线长度 &lt;= 实体长度 * 0.3",
                    "收盘价位于最高价或接近最高价 -> (收盘价 - 最低价) / (最高价 - 最低价) &gt;= 0.6"
                ],
                'color_class': 'sync-card-blue'
            },
            {
                'pattern_type': CandlestickPattern.HANGING_MAN,
                'category': '单K线 - 顶部反转',
                'signal': "看跌",
                'criteria': [
                    "之前存在上升趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &gt;  后半段(5 - 5/2天的收盘价平均值)",
                    "当前价格处于高位 -> 当前收盘价 &gt;= 前期 5 天收盘平均值 * 0.95",
                    "可以是阳线或阴线, 实体较小 -> 实体长度(收盘价 - 开盘价绝对值) &gt; 0.01",
                    "下影线长度至少是实体的2倍 -> 下影线长度 &gt;= 实体长度 * 2.0",
                    "上影线很短或没有 -> 上影线长度 &lt;= 实体长度 * 0.3",
                    "收盘价位于最高价或接近最高价 -> (收盘价 - 最低价) / (最高价 - 最低价) &gt;= 0.6"
                ],
                'color_class': 'sync-card-orange'
            },
            {
                'pattern_type': CandlestickPattern.INVERTED_HAMMER,
                'category': '单K线 - 底部反转',
                'signal': "看涨",
                'criteria': [
                    "之前存在下降趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &lt;  后半段(5 - 5/2天的收盘价平均值)",
                    "可以是阳线或阴线, 实体较小 -> 实体长度(收盘价 - 开盘价绝对值) &gt; 0.01",
                    "上影线长度至少是实体的2倍 -> 上影线长度 &gt;= 实体长度 * 2.0",
                    "下影线很短或没有 -> 下影线长度 &lt;= 实体长度 * 0.3",
                    "收盘价位于最低价或接近最低价 -> (最高价 - 收盘价) / (最高价 - 最低价) &gt;= 0.6"
                ],
                'color_class': 'sync-card-pink'
            },
            {
                'pattern_type': CandlestickPattern.SHOOTING_STAR,
                'category': '单K线 - 顶部反转',
                'signal': "看跌",
                'criteria': [
                    "之前存在上升趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &gt;  后半段(5 - 5/2天的收盘价平均值)",
                    "当前价格处于高位 -> 当前收盘价 &gt;= 前期 5 天收盘平均值 * 0.95",
                    "可以是阳线或阴线, 实体较小 -> 实体长度(收盘价 - 开盘价绝对值) &gt; 0.01",
                    "上影线长度至少是实体的2倍 -> 上影线长度 &gt;= 实体长度 * 2.0",
                    "下影线很短或没有 -> 下影线长度 &lt;= 实体长度 * 0.3",
                    "收盘价位于最低价或接近最低价 -> (最高价 - 收盘价) / (最高价 - 最低价) &gt;= 0.6"
                ],
                'color_class': 'sync-card-cyan'
            },
            {
                'pattern_type': CandlestickPattern.BULLISH_ENGULFING,
                'category': '双K线 - 底部反转',
                'signal': "看涨",
                'criteria': [
                    "之前存在下降趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &lt;  后半段(5 - 5/2天的收盘价平均值)",
                    "第 1 根是阴线 -> 开盘价 &gt; 收盘价",
                    "第 2 根是阳线 -> 收盘价 &gt; 开盘价",
                    "第 2 根实体完全吞没第 1 根实体",
                    "第 2 根阳线开盘价低于第 1 根阴线收盘价 -> 第 2 根开盘价 &lt;= 第 1 根收盘价",
                    "第 2 根阳线收盘价高于第 1 根阴线开盘价 -> 第 2 根收盘价 &gt;= 第 1 根开盘价",
                    "第 2 根实体明显大于第 1 根 -> 第 2 根实体 &gt;= 第 1 根实体 * 1.0"
                ],
                'color_class': 'sync-card-green'
            },
            {
                'pattern_type': CandlestickPattern.BEARISH_ENGULFING,
                'category': '双K线 - 顶部反转',
                'signal': "看跌",
                'criteria': [
                    "之前存在上升趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &gt;  后半段(5 - 5/2天的收盘价平均值)",
                    "第 1 根是阳线 -> 收盘价 &gt; 开盘价",
                    "第 2 根是阴线 -> 开盘价 &gt; 收盘价",
                    "第 2 根阴线实体完全吞没第 1 根阳线实体",
                    "第 2 根阴线开盘价高于第 1 根阳线收盘价 -> 第 2 根开盘价 &gt;= 第 1 根收盘价",
                    "第 2 根阴线收盘价低于第 1 根阳线开盘价 -> 第 2 根收盘价 &lt;= 第 1 根开盘价",
                    "第 2 根阴线实体明显大于第 1 根阳线实体 -> 第 2 根实体 &gt;= 第 1 根实体 * 1.0"
                ],
                'color_class': 'sync-card-purple'
            },
            {
                'pattern_type': CandlestickPattern.PIERCING_PATTERN,
                'category': '双K线 - 底部反转',
                'signal': "看涨",
                'criteria': [
                    "之前存在下降趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &lt;  后半段(5 - 5/2天的收盘价平均值)",
                    "第 1 根是阴线 -> 开盘价 &gt; 收盘价",
                    "第 2 根是阳线 -> 收盘价 &gt; 开盘价",
                    "第 2 根阳线开盘价低于第 1 根阴线最低价, 形成向下跳空 ",
                    "第 2 根阳线收盘价深入第 1 根阴线实体, 高于第 1 根阴线实体中点 -> (第 2 根收盘价 - 第 1 根收盘价) / 第 1 根实体 &gt;= 50%",
                    "第 2 根阳线收盘价低于第 1 根阴线开盘价,未完全吞没 -> 第 2 根阳线收盘价 < 第 1 根阴线开盘价"
                ],
                'color_class': 'sync-card-blue'
            },
            {
                'pattern_type': CandlestickPattern.DARK_CLOUD_COVER,
                'category': '双K线 - 顶部反转',
                'signal': "看跌",
                'criteria': [
                    "之前存在上升趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &gt;  后半段(5 - 5/2天的收盘价平均值)",
                    "第 1 根是阳线 -> 收盘价 &gt; 开盘价",
                    "第 2 根是阴线 -> 开盘价 &gt; 收盘价",
                    "第 2 根阴线开盘价高于第 1 根阳线最高价, 形成向上跳空 ",
                    "第 2 根阴线收盘价深入第 1 根阳线实体, 低于第 1 根阳线实体中点 -> (第 1 根收盘价 - 第 2 根收盘价) / 第 1 根实体 &gt;= 50%",
                    "第 2 根阴线收盘价高于第 1 根阳线开盘价,未完全吞没 -> 第 2 根阳线收盘价 > 第 1 根阴线开盘价"
                ],
                'color_class': 'sync-card-orange'
            },
            {
                'pattern_type': CandlestickPattern.MORNING_STAR,
                'category': '三K线 - 底部反转',
                'signal': "看涨",
                'criteria': [
                    "之前存在下降趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &lt;  后半段(5 - 5/2天的收盘价平均值)",
                    "第 1 根是大阴线, 实体较大 -> 开盘价 &gt; 收盘价",
                    "第 1 根是小实体星线(可阴可阳), 实体很小 -> &lt; 第 1 根实体 * 30%",
                    "第 3 根是阳线 -> 收盘价 &gt; 开盘价",
                    "第 2 根星线与第 1 根阴线之间有向下跳空 -> 第 2 根星线最高价 &lt; 第 1 根阴线最低价",
                    "第 3 根阳线与第 2 根星线之间有向上跳空 -> 第 3 根阳线开盘价 &gt; 第 2 根星线最高价",
                    "第 3 根阳线收盘价深入第 1 根阴线实体 -> 第 3 根阳线收盘价 &gt; 第 1 根阴线收盘价"
                ],
                'color_class': 'sync-card-green'
            },
            {
                'pattern_type': CandlestickPattern.EVENING_STAR,
                'category': '三K线 - 顶部反转',
                'signal': "看跌",
                'criteria': [
                    "之前存在上升趋势 -> 前 5 天的前半段(5/2天的收盘价平均值) &gt;  后半段(5 - 5/2天的收盘价平均值)",
                    "第 1 根是大阳线, 实体较大 -> 收盘价 &gt; 开盘价",
                    "第 2 根是小实体星线(可阴可阳), 实体很小 -> &lt; 第 1 根实体 * 30%",
                    "第 3 根是阴线 -> 开盘价 &gt; 收盘价",
                    "第 2 根星线与第 1 根阳线之间有向上跳空 -> 第 2 根星线最低价 &gt; 第 1 根阳线最高价",
                    "第 3 根阴线与第 2 根星线之间有向下跳空 -> 第 3 根阴线开盘价 &lt;  第 2 根星线最低价",
                    "第 3 根阴线收盘价深入第 1 根阳线实体 -> 第 3 根阴线收盘价 &lt; 第 1 根阳线收盘价"
                ],
                'color_class': 'sync-card-purple'
            }

        ]
