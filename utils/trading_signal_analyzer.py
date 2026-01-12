"""
买卖点分析器 - 基于多层级指标体系的交易信号生成

层级结构：
① 市场状态判定（MACD + RSI）：能不能做多/做空/观望
② 关键区域识别（K线形态 + 结构位置）：在哪里做
③ 入场触发验证（K线形态 + 成交量）：现在是不是那个点
④ 风险过滤（RSI背离 + 成交量）：这个信号会不会是假突破

核心原则：在 MACD 与 RSI 同向的趋势中，只在关键结构位，出现放量的 K 线反转形态时入场；
         当 RSI 背离且量能衰减时退出。
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
from enums.signal import SignalType, SignalStrength
from enums.candlestick_pattern import CandlestickPattern
from utils.strategy import calculate_macd, calculate_rsi
from utils.candlestick_pattern_detector import CandlestickPatternDetector


class TradingSignalAnalyzer:
    """交易信号分析器"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化分析器

        Args:
            df: 包含股票历史数据的DataFrame，需要包含以下列：
                - date: 日期
                - opening, closing, highest, lowest: OHLC价格
                - turnover_count: 成交量
        """
        self.df = df.copy()
        self._prepare_data()

    def _prepare_data(self):
        """准备分析所需的所有指标数据"""
        # 计算MACD
        macd_df = calculate_macd(self.df)
        self.df['DIFF'] = macd_df['DIFF']
        self.df['DEA'] = macd_df['DEA']
        self.df['MACD'] = macd_df['MACD_hist']

        # 计算RSI（使用14周期）
        self.df['RSI'] = calculate_rsi(self.df, period=14)

        # 计算均线（用于结构位置判断）
        self.df['MA5'] = self.df['closing'].rolling(window=5).mean()
        self.df['MA10'] = self.df['closing'].rolling(window=10).mean()
        self.df['MA20'] = self.df['closing'].rolling(window=20).mean()
        self.df['MA60'] = self.df['closing'].rolling(window=60).mean()

        # 计算成交量均线（用于放量判断）
        self.df['VOL_MA5'] = self.df['turnover_count'].rolling(window=5).mean()
        self.df['VOL_MA10'] = self.df['turnover_count'].rolling(window=10).mean()

        # 检测所有K线形态
        self.patterns = CandlestickPatternDetector.detect_all_patterns(self.df)

    def analyze(self) -> List[Dict]:
        """
        执行完整的多层级分析，生成买卖信号

        Returns:
            信号列表，每个信号包含：
            - date: 日期
            - price: 价格
            - type: 信号类型（BUY/SELL）
            - strength: 信号强度
            - analysis: 详细分析结果
        """
        signals = []

        # 遍历每一天进行分析（从第60天开始，确保所有指标都有效）
        for i in range(60, len(self.df)):
            row = self.df.iloc[i]

            # 第一步：判断市场状态
            market_state = self._step1_market_state(i)

            # 如果是震荡期，跳过
            if market_state['direction'] == 'RANGING':
                continue

            # 第二步：检查是否在关键区域
            key_area = self._step2_key_area(i)

            # 第三步：检查入场触发条件
            entry_trigger = self._step3_entry_trigger(i, market_state['direction'])

            # 第四步：风险过滤
            risk_filter = self._step4_risk_filter(i)

            # 综合判断：生成信号
            signal = self._generate_signal(
                i, row, market_state, key_area, entry_trigger, risk_filter
            )

            if signal:
                signals.append(signal)

        return signals

    def _step1_market_state(self, idx: int) -> Dict:
        """
        第一步：市场状态判定（MACD + RSI）

        判断逻辑：
        - MACD在0轴上方 → 只考虑做多
        - MACD在0轴下方 → 只考虑做空
        - MACD贴着0轴来回 → 震荡，不交易

        - RSI > 55 → 多头趋势
        - RSI < 45 → 空头趋势
        - 45-55 → 震荡

        Returns:
            {
                'direction': 'LONG' | 'SHORT' | 'RANGING',
                'macd_position': 'ABOVE' | 'BELOW' | 'NEUTRAL',
                'rsi_state': 'BULL' | 'BEAR' | 'NEUTRAL',
                'confidence': float  # 0-1之间的置信度
            }
        """
        row = self.df.iloc[idx]
        diff = row['DIFF']
        rsi = row['RSI']

        # 判断MACD位置
        if pd.isna(diff):
            macd_position = 'NEUTRAL'
        elif diff > 0.5:  # MACD明显在0轴上方
            macd_position = 'ABOVE'
        elif diff < -0.5:  # MACD明显在0轴下方
            macd_position = 'BELOW'
        else:  # MACD在0轴附近震荡
            macd_position = 'NEUTRAL'

        # 判断RSI状态
        if pd.isna(rsi):
            rsi_state = 'NEUTRAL'
        elif rsi > 55:
            rsi_state = 'BULL'
        elif rsi < 45:
            rsi_state = 'BEAR'
        else:
            rsi_state = 'NEUTRAL'

        # 综合判断方向
        direction = 'RANGING'
        confidence = 0.0

        if macd_position == 'ABOVE' and rsi_state == 'BULL':
            direction = 'LONG'
            confidence = min((rsi - 55) / 20, 1.0)  # RSI越高，置信度越高
        elif macd_position == 'BELOW' and rsi_state == 'BEAR':
            direction = 'SHORT'
            confidence = min((45 - rsi) / 20, 1.0)  # RSI越低，置信度越高
        elif macd_position == 'ABOVE' and rsi_state == 'NEUTRAL':
            direction = 'LONG'
            confidence = 0.5
        elif macd_position == 'BELOW' and rsi_state == 'NEUTRAL':
            direction = 'SHORT'
            confidence = 0.5

        return {
            'direction': direction,
            'macd_position': macd_position,
            'rsi_state': rsi_state,
            'confidence': confidence,
            'macd_value': float(diff) if not pd.isna(diff) else None,
            'rsi_value': float(rsi) if not pd.isna(rsi) else None
        }

    def _step2_key_area(self, idx: int) -> Dict:
        """
        第二步：关键区域识别（K线形态 + 结构位置）

        关键区域包括：
        1. 均线支撑/阻力位（MA5, MA10, MA20, MA60）
        2. 前期高低点
        3. K线反转形态出现的位置

        Returns:
            {
                'is_key_area': bool,
                'area_type': 'SUPPORT' | 'RESISTANCE' | None,
                'reasons': List[str],  # 为什么是关键区域
                'patterns': List[Dict]  # 该位置的K线形态
            }
        """
        row = self.df.iloc[idx]
        current_price = row['closing']

        is_key_area = False
        area_type = None
        reasons = []

        # 检查是否在均线附近（±2%）
        tolerance = 0.02

        for ma_name in ['MA5', 'MA10', 'MA20', 'MA60']:
            ma_value = row[ma_name]
            if pd.isna(ma_value):
                continue

            deviation = abs(current_price - ma_value) / ma_value
            if deviation <= tolerance:
                is_key_area = True
                area_type = 'SUPPORT' if current_price >= ma_value else 'RESISTANCE'
                reasons.append(f"价格触及{ma_name}线({ma_value:.2f})")

        # 检查是否在前期高低点附近（回看20天）
        if idx >= 20:
            lookback_df = self.df.iloc[idx-20:idx]
            recent_high = lookback_df['highest'].max()
            recent_low = lookback_df['lowest'].min()

            # 检查是否接近前期高点
            if abs(current_price - recent_high) / recent_high <= tolerance:
                is_key_area = True
                area_type = 'RESISTANCE'
                reasons.append(f"接近前期高点({recent_high:.2f})")

            # 检查是否接近前期低点
            if abs(current_price - recent_low) / recent_low <= tolerance:
                is_key_area = True
                area_type = 'SUPPORT'
                reasons.append(f"接近前期低点({recent_low:.2f})")

        # 检查当前位置的K线形态
        current_date = row['date']
        current_patterns = [
            p for p in self.patterns
            if p['date'] == current_date
        ]

        # 如果有重要的反转形态，也认为是关键区域
        if current_patterns:
            important_patterns = [
                CandlestickPattern.BULLISH_ENGULFING,
                CandlestickPattern.BEARISH_ENGULFING,
                CandlestickPattern.MORNING_STAR,
                CandlestickPattern.EVENING_STAR,
                CandlestickPattern.HAMMER,
                CandlestickPattern.SHOOTING_STAR
            ]

            for pattern in current_patterns:
                if pattern['pattern_type'] in important_patterns:
                    is_key_area = True
                    reasons.append(f"出现{pattern['pattern_type'].text}形态")

        return {
            'is_key_area': is_key_area,
            'area_type': area_type,
            'reasons': reasons,
            'patterns': current_patterns
        }

    def _step3_entry_trigger(self, idx: int, direction: str) -> Dict:
        """
        第三步：入场触发验证（K线形态 + 成交量）

        验证逻辑：
        1. K线形态必须与方向一致（做多看涨形态，做空看跌形态）
        2. 成交量必须放大（相对5日均量）

        成交量有效的三种情况（做多）：
        - 吞没 + 放量
        - 回调缩量，反转放量
        - 突破关键位时明显放量

        Returns:
            {
                'is_triggered': bool,
                'pattern_matched': bool,
                'volume_confirmed': bool,
                'volume_ratio': float,  # 当前成交量 / 5日均量
                'pattern_info': Dict
            }
        """
        if direction == 'RANGING':
            return {
                'is_triggered': False,
                'pattern_matched': False,
                'volume_confirmed': False,
                'volume_ratio': 0,
                'pattern_info': None
            }

        row = self.df.iloc[idx]
        current_date = row['date']
        current_volume = row['turnover_count']
        vol_ma5 = row['VOL_MA5']

        # 计算成交量放大倍数
        volume_ratio = current_volume / vol_ma5 if not pd.isna(vol_ma5) and vol_ma5 > 0 else 0
        volume_confirmed = volume_ratio >= 1.3  # 成交量至少放大30%

        # 检查K线形态
        current_patterns = [p for p in self.patterns if p['date'] == current_date]

        # 做多的看涨形态
        bullish_patterns = [
            CandlestickPattern.BULLISH_ENGULFING,
            CandlestickPattern.MORNING_STAR,
            CandlestickPattern.HAMMER,
            CandlestickPattern.INVERTED_HAMMER,
            CandlestickPattern.PIERCING_PATTERN,
            CandlestickPattern.THREE_WHITE_SOLDIERS
        ]

        # 做空的看跌形态
        bearish_patterns = [
            CandlestickPattern.BEARISH_ENGULFING,
            CandlestickPattern.EVENING_STAR,
            CandlestickPattern.SHOOTING_STAR,
            CandlestickPattern.HANGING_MAN,
            CandlestickPattern.DARK_CLOUD_COVER,
            CandlestickPattern.THREE_BLACK_CROWS
        ]

        pattern_matched = False
        matched_pattern = None

        for pattern in current_patterns:
            pattern_type = pattern['pattern_type']

            if direction == 'LONG' and pattern_type in bullish_patterns:
                pattern_matched = True
                matched_pattern = pattern
                break
            elif direction == 'SHORT' and pattern_type in bearish_patterns:
                pattern_matched = True
                matched_pattern = pattern
                break

        is_triggered = pattern_matched and volume_confirmed

        return {
            'is_triggered': is_triggered,
            'pattern_matched': pattern_matched,
            'volume_confirmed': volume_confirmed,
            'volume_ratio': float(volume_ratio),
            'pattern_info': matched_pattern
        }

    def _step4_risk_filter(self, idx: int) -> Dict:
        """
        第四步：风险过滤（RSI背离 + 成交量衰减）

        RSI背离的用法：
        - 背离 ≠ 立刻反转
        - 背离 = 不要加仓 / 准备离场

        判断逻辑：
        - 价格创新高，RSI不创新高，同时成交量走弱 → 做多风险高
        - 价格创新低，RSI不创新低,同时成交量走弱 → 做空风险高

        Returns:
            {
                'has_risk': bool,
                'risk_type': 'BULLISH_DIVERGENCE' | 'BEARISH_DIVERGENCE' | None,
                'should_exit': bool,  # 是否应该退出
                'risk_level': 'LOW' | 'MEDIUM' | 'HIGH'
            }
        """
        if idx < 10:  # 需要足够的历史数据来判断背离
            return {
                'has_risk': False,
                'risk_type': None,
                'should_exit': False,
                'risk_level': 'LOW'
            }

        row = self.df.iloc[idx]
        current_price = row['closing']
        current_rsi = row['RSI']
        current_volume = row['turnover_count']
        vol_ma10 = row['VOL_MA10']

        # 回看最近10天
        lookback = 10
        recent_df = self.df.iloc[idx-lookback:idx+1]

        # 检查顶背离（做多风险）
        price_high = recent_df['closing'].max()
        price_high_idx = recent_df['closing'].idxmax()
        rsi_high = recent_df['RSI'].max()
        rsi_high_idx = recent_df['RSI'].idxmax()

        # 检查底背离（做空风险）
        price_low = recent_df['closing'].min()
        price_low_idx = recent_df['closing'].idxmin()
        rsi_low = recent_df['RSI'].min()
        rsi_low_idx = recent_df['RSI'].idxmin()

        # 成交量是否衰减
        volume_weakening = current_volume < vol_ma10 if not pd.isna(vol_ma10) else False

        has_risk = False
        risk_type = None
        should_exit = False
        risk_level = 'LOW'

        # 顶背离：价格创新高时，RSI未创新高
        if current_price >= price_high * 0.98:  # 当前价格接近或创新高
            if price_high_idx > rsi_high_idx:  # 价格高点在RSI高点之后
                if current_rsi < rsi_high * 0.95:  # RSI明显未创新高
                    has_risk = True
                    risk_type = 'BEARISH_DIVERGENCE'  # 顶背离
                    should_exit = volume_weakening
                    risk_level = 'HIGH' if volume_weakening else 'MEDIUM'

        # 底背离：价格创新低时，RSI未创新低
        if current_price <= price_low * 1.02:  # 当前价格接近或创新低
            if price_low_idx > rsi_low_idx:  # 价格低点在RSI低点之后
                if current_rsi > rsi_low * 1.05:  # RSI明显未创新低
                    has_risk = True
                    risk_type = 'BULLISH_DIVERGENCE'  # 底背离
                    should_exit = volume_weakening
                    risk_level = 'HIGH' if volume_weakening else 'MEDIUM'

        return {
            'has_risk': has_risk,
            'risk_type': risk_type,
            'should_exit': should_exit,
            'risk_level': risk_level,
            'volume_weakening': volume_weakening
        }

    def _generate_signal(
        self,
        idx: int,
        row: pd.Series,
        market_state: Dict,
        key_area: Dict,
        entry_trigger: Dict,
        risk_filter: Dict
    ) -> Optional[Dict]:
        """
        综合所有分析结果，生成最终的买卖信号

        信号生成规则：
        1. 做多信号：
           - 市场状态 = LONG
           - 在关键支撑区
           - 出现看涨形态 + 放量
           - 无顶背离风险

        2. 做空信号：
           - 市场状态 = SHORT
           - 在关键阻力区
           - 出现看跌形态 + 放量
           - 无底背离风险

        3. 退出信号：
           - RSI背离 + 成交量衰减
        """
        direction = market_state['direction']

        # 退出信号优先级最高
        if risk_filter['should_exit']:
            # 判断是平多还是平空
            if risk_filter['risk_type'] == 'BEARISH_DIVERGENCE':
                # 顶背离 → 平多头仓位
                return {
                    'date': row['date'],
                    'price': float(row['closing']),
                    'type': SignalType.SELL,
                    'strength': SignalStrength.STRONG,
                    'action': 'EXIT_LONG',
                    'analysis': {
                        'market_state': market_state,
                        'key_area': key_area,
                        'entry_trigger': entry_trigger,
                        'risk_filter': risk_filter,
                        'reason': 'RSI顶背离 + 成交量衰减，建议平多'
                    }
                }
            elif risk_filter['risk_type'] == 'BULLISH_DIVERGENCE':
                # 底背离 → 平空头仓位
                return {
                    'date': row['date'],
                    'price': float(row['closing']),
                    'type': SignalType.BUY,
                    'strength': SignalStrength.STRONG,
                    'action': 'EXIT_SHORT',
                    'analysis': {
                        'market_state': market_state,
                        'key_area': key_area,
                        'entry_trigger': entry_trigger,
                        'risk_filter': risk_filter,
                        'reason': 'RSI底背离 + 成交量衰减，建议平空'
                    }
                }

        # 如果有风险但不是必须退出，降低信号强度
        strength_penalty = 0
        if risk_filter['has_risk']:
            strength_penalty = 1

        # 生成做多信号
        if direction == 'LONG' and entry_trigger['is_triggered']:
            # 最好是在支撑区，但不是强制要求
            in_support = key_area['is_key_area'] and key_area['area_type'] == 'SUPPORT'

            # 计算信号强度
            strength_score = 0
            if market_state['confidence'] > 0.7:
                strength_score += 2
            elif market_state['confidence'] > 0.5:
                strength_score += 1

            if in_support:
                strength_score += 2
            elif key_area['is_key_area']:
                strength_score += 1

            if entry_trigger['volume_ratio'] >= 1.5:
                strength_score += 2
            elif entry_trigger['volume_ratio'] >= 1.3:
                strength_score += 1

            strength_score -= strength_penalty

            if strength_score >= 3:
                strength = SignalStrength.STRONG
            else:
                strength = SignalStrength.WEAK

            reasons = []
            reasons.append(f"MACD在0轴{'上方' if market_state['macd_position'] == 'ABOVE' else '附近'}")
            reasons.append(f"RSI={market_state['rsi_value']:.1f}（多头趋势）")
            if in_support:
                reasons.append(f"在关键支撑区：{', '.join(key_area['reasons'])}")
            if entry_trigger['pattern_info']:
                reasons.append(f"出现{entry_trigger['pattern_info']['pattern_type'].text}")
            reasons.append(f"成交量放大{entry_trigger['volume_ratio']:.1f}倍")
            if risk_filter['has_risk']:
                reasons.append(f"⚠️ 注意：存在{risk_filter['risk_type']}风险")

            return {
                'date': row['date'],
                'price': float(row['closing']),
                'type': SignalType.BUY,
                'strength': strength,
                'action': 'ENTER_LONG',
                'analysis': {
                    'market_state': market_state,
                    'key_area': key_area,
                    'entry_trigger': entry_trigger,
                    'risk_filter': risk_filter,
                    'reason': ' | '.join(reasons),
                    'strength_score': strength_score
                }
            }

        # 生成做空信号
        if direction == 'SHORT' and entry_trigger['is_triggered']:
            # 最好是在阻力区
            in_resistance = key_area['is_key_area'] and key_area['area_type'] == 'RESISTANCE'

            # 计算信号强度
            strength_score = 0
            if market_state['confidence'] > 0.7:
                strength_score += 2
            elif market_state['confidence'] > 0.5:
                strength_score += 1

            if in_resistance:
                strength_score += 2
            elif key_area['is_key_area']:
                strength_score += 1

            if entry_trigger['volume_ratio'] >= 1.5:
                strength_score += 2
            elif entry_trigger['volume_ratio'] >= 1.3:
                strength_score += 1

            strength_score -= strength_penalty

            if strength_score >= 3:
                strength = SignalStrength.STRONG
            else:
                strength = SignalStrength.WEAK

            reasons = []
            reasons.append(f"MACD在0轴{'下方' if market_state['macd_position'] == 'BELOW' else '附近'}")
            reasons.append(f"RSI={market_state['rsi_value']:.1f}（空头趋势）")
            if in_resistance:
                reasons.append(f"在关键阻力区：{', '.join(key_area['reasons'])}")
            if entry_trigger['pattern_info']:
                reasons.append(f"出现{entry_trigger['pattern_info']['pattern_type'].text}")
            reasons.append(f"成交量放大{entry_trigger['volume_ratio']:.1f}倍")
            if risk_filter['has_risk']:
                reasons.append(f"⚠️ 注意：存在{risk_filter['risk_type']}风险")

            return {
                'date': row['date'],
                'price': float(row['closing']),
                'type': SignalType.SELL,
                'strength': strength,
                'action': 'ENTER_SHORT',
                'analysis': {
                    'market_state': market_state,
                    'key_area': key_area,
                    'entry_trigger': entry_trigger,
                    'risk_filter': risk_filter,
                    'reason': ' | '.join(reasons),
                    'strength_score': strength_score
                }
            }

        return None

    def get_daily_analysis(self, date) -> Optional[Dict]:
        """
        获取指定日期的完整分析结果（用于UI展示）

        Args:
            date: 要查询的日期

        Returns:
            包含所有4个步骤分析结果的字典
        """
        # 找到对应日期的索引
        try:
            idx = self.df[self.df['date'] == date].index[0]
        except (IndexError, KeyError):
            return None

        if idx < 60:  # 数据不足
            return None

        row = self.df.iloc[idx]

        # 执行所有分析步骤
        market_state = self._step1_market_state(idx)
        key_area = self._step2_key_area(idx)
        entry_trigger = self._step3_entry_trigger(idx, market_state['direction'])
        risk_filter = self._step4_risk_filter(idx)

        return {
            'date': date,
            'price': float(row['closing']),
            'step1_market_state': market_state,
            'step2_key_area': key_area,
            'step3_entry_trigger': entry_trigger,
            'step4_risk_filter': risk_filter
        }
