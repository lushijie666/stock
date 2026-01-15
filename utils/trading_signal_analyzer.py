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
from enums.market_state import (
    MarketDirection, MacdPosition, RsiState,
    AreaType, RiskType, RiskLevel
)
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

    def analyze(self, min_warmup_days: int = None) -> Tuple[List[Dict], Dict]:
        """
        执行完整的多层级分析，生成买卖信号

        Args:
            min_warmup_days: 最小预热天数。如果为None，自动计算最优值。
                           建议值：120天（确保所有指标稳定且有足够历史数据）

        Returns:
            字典包含3部分：
            {
                'signals': [  # 1. 触发准确买卖信号的列表
                    {
                        'date': 日期,
                        'price': 价格,
                        'type': 信号类型（SignalType.BUY/SELL）,
                        'strength': 信号强度（SignalStrength）,
                        'analysis': {
                            'market_state': 市场状态,
                            'key_area': 关键区域,
                            'entry_trigger': 入场触发,
                            'risk_filter': 风险过滤
                        },
                        'reason': 触发原因描述
                    }
                ],
                'statistics': {  # 2. 总的统计信息
                    'total_days': 总分析天数,
                    'ranging_days': 震荡期天数,
                    'trend_days': 趋势期天数,
                    'long_days': 多头天数,
                    'short_days': 空头天数,
                    'no_pattern_days': 有趋势但无形态的天数,
                    'no_volume_days': 有形态但成交量不足的天数,
                    'filtered_by_risk': 被风险过滤掉的天数,
                    'signal_days': 最终生成信号的天数,
                    'ranging_reasons': 震荡期详细原因列表,
                    'warmup_days': 预热天数
                },
                'daily_analysis': [  # 3. 每天的详细分析信息
                    {
                        'date': 日期,
                        'price': 价格,
                        'step1_market_state': 第一步分析结果,
                        'step2_key_area': 第二步分析结果,
                        'step3_entry_trigger': 第三步分析结果,
                        'step4_risk_filter': 第四步分析结果,
                        'has_signal': 是否生成信号,
                        'reason': 当天的分析原因
                    }
                ]
            }
        """
        signals = []
        daily_analysis = []

        # 计算最优预热天数
        if min_warmup_days is None:
            # 自动计算：确保所有指标都有足够的数据
            # MA60(60) + 前期高低点分析(20) + RSI背离检测(10) + 额外缓冲(30) = 120
            min_warmup_days = 120

        # 初始化统计计数器
        stats = {
            'total_days': 0,
            'ranging_days': 0,
            'trend_days': 0,
            'long_days': 0,
            'short_days': 0,
            'filtered_by_risk': 0,
            'signal_days': 0,
            'ranging_reasons': [],  # 震荡期的详细原因
            'long_reasons': [],
            'short_reasons': [],
            'key_area_ma_days': 0,
            'key_area_past_high_days': 0,
            'key_area_past_low_days': 0,
            'key_area_candlestick_pattern_days': 0,
            'key_area_reasons': [],
            'triggered_days': 0,
            'pattern_matched_days': 0,
            'only_pattern_matched_days': 0,
            'volume_confirmed_days': 0,
            'only_volume_confirmed_days': 0,
            'triggered_reasons': [],
            'not_triggered_reasons': [],
            'has_risk_days': 0,
            'bearish_divergence_days':0,
            'bullish_divergence_days':0,
            'volume_weakening_days': 0,
            'risk_reasons': [],

            'warmup_days': min_warmup_days,  # 记录使用的预热天数
        }

        # 遍历每一天进行分析（从预热天数后开始，确保所有指标都有效）
        for i in range(min_warmup_days, len(self.df)):
            row = self.df.iloc[i]
            stats['total_days'] += 1

            # 第一步：判断市场状态
            market_state = self._step1_market_state(i)

            # 初始化当天的分析记录
            day_analysis = {
                'date': row['date'],
                'price': row['closing'],
                'step1_market_state': market_state,
                'step2_key_area': None,
                'step3_entry_trigger': None,
                'step4_risk_filter': None,
                'has_signal': False,
                'reason': ''
            }

            # 如果是震荡期，记录原因
            if market_state['direction'] == MarketDirection.RANGING:
                stats['ranging_days'] += 1
                reason = self._get_ranging_reason(market_state)
                stats['ranging_reasons'].append({
                    'date': row['date'],
                    'row': row,
                    'reason': reason,
                    'macd': market_state.get('macd_value'),
                    'rsi': market_state.get('rsi_value')
                })
                day_analysis['reason'] = f"震荡期：{reason}"
                daily_analysis.append(day_analysis)
                continue

            # 记录趋势天数
            stats['trend_days'] += 1
            if market_state['direction'] == MarketDirection.LONG:
                stats['long_days'] += 1
                stats['long_reasons'].append({
                    'date': row['date'],
                    'row': row,
                    'macd': market_state.get('macd_value'),
                    'rsi': market_state.get('rsi_value')
                })
            else:
                stats['short_days'] += 1
                stats['short_reasons'].append({
                    'date': row['date'],
                    'row': row,
                    'macd': market_state.get('macd_value'),
                    'rsi': market_state.get('rsi_value')
                })

            # 第二步：检查是否在关键区域
            key_area = self._step2_key_area(i)
            day_analysis['step2_key_area'] = key_area

            # 记录各个区域
            if key_area['is_key_area']:
                # 统计各种类型的关键区域天数
                area_types = key_area.get('all_area_types', [])
                # 统计各类型，避免重复计算
                has_ma_type = False
                has_past_high = False
                has_past_low = False
                has_candlestick_pattern = False

                for area_type in area_types:
                    if area_type in ['MA5', 'MA10', 'MA20', 'MA60'] and not has_ma_type:
                        stats['key_area_ma_days'] += 1
                        has_ma_type = True
                    elif area_type == 'PAST_HIGH' and not has_past_high:
                        stats['key_area_past_high_days'] += 1
                        has_past_high = True
                    elif area_type == 'PAST_LOW' and not has_past_low:
                        stats['key_area_past_low_days'] += 1
                        has_past_low = True
                    elif area_type == 'CANDLESTICK_PATTERN' and not has_candlestick_pattern:
                        stats['key_area_candlestick_pattern_days'] += 1
                        has_candlestick_pattern = True
                reasons = key_area.get('reasons', [])
                stats['key_area_reasons'].append({
                    'date': row['date'],
                    'row': row,
                    'all_types': area_types,
                    'reason':   " | ".join(reasons) if reasons else "-"
                })

            # 第三步：检查入场触发条件
            entry_trigger = self._step3_entry_trigger(i, market_state['direction'])
            day_analysis['step3_entry_trigger'] = entry_trigger

            # 记录入场触发天数
            entry_trigger_reasons = entry_trigger.get('reasons', [])
            if entry_trigger['is_triggered']:
                stats['triggered_days'] += 1
                stats['triggered_reasons'].append({
                    'date': row['date'],
                    'row': row,
                    'reason': " | ".join(entry_trigger_reasons) if entry_trigger_reasons else "-"
                })

            else:
                if entry_trigger['pattern_matched']:
                    stats['only_pattern_matched_days'] += 1
                if entry_trigger['volume_confirmed']:
                    stats['only_volume_confirmed_days'] += 1
                stats['not_triggered_reasons'].append({
                    'date': row['date'],
                    'row': row,
                    'reason': " | ".join(entry_trigger_reasons) if entry_trigger_reasons else "-"
                })
            if entry_trigger['pattern_matched']:
                stats['pattern_matched_days'] += 1
            if entry_trigger['volume_confirmed']:
                stats['volume_confirmed_days'] += 1


            # 第四步：风险过滤
            risk_filter = self._step4_risk_filter(i)
            day_analysis['step4_risk_filter'] = risk_filter

            # 记录风险天数
            if risk_filter['has_risk']:
                stats['has_risk_days'] += 1
                risk_type = risk_filter.get('risk_type')
                if risk_type:
                    if risk_type == RiskType.BEARISH_DIVERGENCE:  # 顶背离
                        stats['bearish_divergence_days'] +=  1
                    elif risk_type == RiskType.BULLISH_DIVERGENCE:  # 底背离
                        stats['bullish_divergence_days'] += 1
                risk_reasons = risk_filter.get('reasons', [])
                stats['risk_reasons'].append({
                    'date': row['date'],
                    'row': row,
                    'risk_type': risk_type,
                    'risk_level': risk_filter.get('risk_level'),
                    'volume_weakening': risk_filter.get('volume_weakening'),
                    'reason': " | ".join(risk_reasons) if risk_reasons else "-"
                })

            if risk_filter['volume_weakening']:
                stats['volume_weakening_days'] += 1

            # 综合判断：生成信号
            signal = self._generate_signal(
                i, row, market_state, key_area, entry_trigger, risk_filter
            )
            if signal:
                signals.append(signal)
                stats['signal_days'] += 1
                day_analysis['has_signal'] = True
            elif entry_trigger['is_triggered'] and risk_filter['has_risk'] and risk_filter['risk_level'] == RiskLevel.HIGH:
                # 本来会触发但被风险过滤
                stats['filtered_by_risk'] += 1
                risk_type = risk_filter['risk_type']
                day_analysis['reason'] = f"{market_state['direction'].text}趋势，触发入场但存在{risk_type.text}风险"

            # 如果reason还是空的，给个默认值
            if not day_analysis['reason']:
                if entry_trigger['is_triggered']:
                    day_analysis['reason'] = f"{market_state['direction'].text}趋势，触发入场但风险等级{risk_filter['risk_level'].text if risk_filter['has_risk'] else '可接受'}"
                else:
                    day_analysis['reason'] = f"{market_state['direction'].text}趋势，等待入场触发"

            daily_analysis.append(day_analysis)

        return {
            'signals': signals,
            'statistics': stats,
            'daily_analysis': daily_analysis
        }

    def _get_ranging_reason(self, market_state: Dict) -> str:
        """获取震荡期的详细原因"""
        macd_pos = market_state['macd_position']
        rsi_state = market_state['rsi_state']
        macd_val = market_state.get('macd_value', 0)
        rsi_val = market_state.get('rsi_value', 0)

        reasons = []

        if macd_pos == MacdPosition.NEUTRAL:
            reasons.append(f"MACD在{macd_pos.text} → ({macd_val:.2f})")

        if rsi_state == RsiState.NEUTRAL:
            reasons.append(f"RSI在{rsi_state.text} → ({rsi_val:.2f})")

        if macd_pos == MacdPosition.ABOVE and rsi_state == RsiState.BEAR:
            reasons.append(f"MACD在{macd_pos.text} → ({macd_val:.2f})但RSI在{rsi_state.text} → ({rsi_val:.2f})，方向不一致")

        if macd_pos == MacdPosition.BELOW and rsi_state == RsiState.BULL:
            reasons.append(f"MACD在{macd_pos.text} → ({macd_val:.2f})但RSI在{rsi_state.text} → ({rsi_val:.2f})，方向不一致")

        return " | ".join(reasons) if reasons else "市场方向不明确"

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
                'direction': MarketDirection,
                'macd_position': MacdPosition,
                'rsi_state': RsiState,
                'confidence': float  # 0-1之间的置信度
            }
        """
        row = self.df.iloc[idx]
        diff = row['DIFF']
        rsi = row['RSI']

        # 判断MACD位置
        if pd.isna(diff):
            macd_position = MacdPosition.NEUTRAL
        elif diff > 0.5:  # MACD明显在0轴上方
            macd_position = MacdPosition.ABOVE
        elif diff < -0.5:  # MACD明显在0轴下方
            macd_position = MacdPosition.BELOW
        else:  # MACD在0轴附近震荡
            macd_position = MacdPosition.NEUTRAL

        # 判断RSI状态
        if pd.isna(rsi):
            rsi_state = RsiState.NEUTRAL
        elif rsi > 55:
            rsi_state = RsiState.BULL
        elif rsi < 45:
            rsi_state = RsiState.BEAR
        else:
            rsi_state = RsiState.NEUTRAL

        # 综合判断方向
        direction = MarketDirection.RANGING
        confidence = 0.0

        if macd_position == MacdPosition.ABOVE and rsi_state == RsiState.BULL:
            direction = MarketDirection.LONG
            confidence = min((rsi - 55) / 20, 1.0)  # RSI越高，置信度越高
        elif macd_position == MacdPosition.BELOW and rsi_state == RsiState.BEAR:
            direction = MarketDirection.SHORT
            confidence = min((45 - rsi) / 20, 1.0)  # RSI越低，置信度越高
        elif macd_position == MacdPosition.ABOVE and rsi_state == RsiState.NEUTRAL:
            direction = MarketDirection.LONG
            confidence = 0.5
        elif macd_position == MacdPosition.BELOW and rsi_state == RsiState.NEUTRAL:
            direction = MarketDirection.SHORT
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
                'all_area_types': List[str],  # ['MA_LINE', 'PAST_HIGH_LOW', 'CANDLESTICK_PATTERN']
                'reasons': List[str],  # 为什么是关键区域
                'patterns': List[Dict]  # 该位置的K线形态
            }
        """
        row = self.df.iloc[idx]
        current_price = row['closing']

        is_key_area = False
        area_type = None
        all_area_types = []
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
                area_type = AreaType.SUPPORT if current_price >= ma_value else AreaType.RESISTANCE
                reasons.append(f"价格触及{ma_name}线[{ma_value:.2f}] → ({current_price:.2f}, 比例：{deviation:.2f})")
                all_area_types.append(ma_name)

        # 检查是否在前期高低点附近（回看20天）
        if idx >= 20:
            lookback_df = self.df.iloc[idx-20:idx]
            recent_high = lookback_df['highest'].max()
            recent_low = lookback_df['lowest'].min()

            # 计算价格与前期高点的距离比率
            distance_to_high_ratio = abs(current_price - recent_high) / recent_high
            # 计算价格与前期低点的距离比率
            distance_to_low_ratio = abs(current_price - recent_low) / recent_low

            # 检查是否接近前期高点
            if distance_to_high_ratio <= tolerance:
                is_key_area = True
                area_type = AreaType.RESISTANCE
                reasons.append(f"接近前期[前20天]高点[{recent_high:.2f}] → ({current_price:.2f}, 比例: {distance_to_high_ratio:.2f})")
                all_area_types.append('PAST_HIGH')

            # 检查是否接近前期低点
            if distance_to_low_ratio <= tolerance:
                is_key_area = True
                area_type = AreaType.SUPPORT
                reasons.append(f"接近前期[前20天]低点[{recent_low:.2f}] → ({current_price:.2f}, 比例: {distance_to_low_ratio:.2f})")
                all_area_types.append('PAST_LOW')

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
                    reasons.append(f"出现形态 → ({pattern['pattern_type'].fullText})")
                    all_area_types.append('CANDLESTICK_PATTERN')

        return {
            'is_key_area': is_key_area,
            'area_type': area_type,
            'all_area_types': all_area_types,
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
        if direction == MarketDirection.RANGING:
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
        reasons = []

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

            if direction == MarketDirection.LONG and pattern_type in bullish_patterns:
                pattern_matched = True
                matched_pattern = pattern
                reasons.append(f"匹配形态 → ({pattern_type.fullText})")
                break
            elif direction == MarketDirection.SHORT and pattern_type in bearish_patterns:
                pattern_matched = True
                matched_pattern = pattern
                reasons.append(f"匹配形态 → ({pattern_type.fullText})")
                break

        is_triggered = pattern_matched and volume_confirmed
        if volume_confirmed:
            reasons.append(f"匹配5日均成交量[{vol_ma5}*1.3={vol_ma5*1.3}] → ({current_volume}, 倍数: {volume_ratio:.2f})")

        return {
            'is_triggered': is_triggered,
            'pattern_matched': pattern_matched,
            'volume_confirmed': volume_confirmed,
            'volume_ratio': float(volume_ratio),
            'pattern_info': matched_pattern,
            'reasons': reasons
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
                'risk_level': 'LOW',
                'reasons': []
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
        risk_level = RiskLevel.LOW
        reasons = []

        # 顶背离：价格创新高时，RSI未创新高
        if current_price >= price_high * 0.98:  # 当前价格接近或创新高
            if price_high_idx > rsi_high_idx:  # 价格高点在RSI高点之后
                if current_rsi < rsi_high * 0.95:  # RSI明显未创新高
                    has_risk = True
                    risk_type = RiskType.BEARISH_DIVERGENCE  # 顶背离
                    should_exit = volume_weakening
                    risk_level = RiskLevel.HIGH if volume_weakening else RiskLevel.MEDIUM
                    reasons.append(f"当前价格创新高[{price_high:.2f}*0.98={price_high*0.98:.2f}], RSI未创新高[{rsi_high:.2f}*0.95={rsi_high*0.95:.2f}] → (价格: {current_price:.2f}, RSI: {current_rsi}, 类型: {risk_type.text}, 成交量是否衰减: {volume_weakening}, 级别: {risk_level.text})")

        # 底背离：价格创新低时，RSI未创新低
        if current_price <= price_low * 1.02:  # 当前价格接近或创新低
            if price_low_idx > rsi_low_idx:  # 价格低点在RSI低点之后
                if current_rsi > rsi_low * 1.05:  # RSI明显未创新低
                    has_risk = True
                    risk_type = RiskType.BULLISH_DIVERGENCE  # 底背离
                    should_exit = volume_weakening
                    risk_level = RiskLevel.HIGH if volume_weakening else RiskLevel.MEDIUM
                    reasons.append(f"当前价格创新低[{price_low:.2f}*1.02={price_low*1.02:.2f}], RSI未创新低[{rsi_low:.2f}*1.05={rsi_low*1.05:.2f}] → (价格: {current_price:.2f}, RSI: {current_rsi:.2f}, 类型: {risk_type.text}, 成交量是否衰减: {volume_weakening}, 级别: {risk_level.text})")


        return {
            'has_risk': has_risk,
            'risk_type': risk_type,
            'should_exit': should_exit,
            'risk_level': risk_level,
            'volume_weakening': volume_weakening,
            'reasons': reasons
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
            if risk_filter['risk_type'] == RiskType.BEARISH_DIVERGENCE:
                # 顶背离 → 平多头仓位
                reason = 'RSI顶背离 + 成交量衰减, 建议卖出'
                return {
                    'date': row['date'],
                    'type': SignalType.SELL,
                    'strength': SignalStrength.STRONG,
                    'reason': reason,
                    'analysis': {
                        'market_state': market_state,
                        'key_area': key_area,
                        'entry_trigger': entry_trigger,
                        'risk_filter': risk_filter
                    }
                }
            elif risk_filter['risk_type'] == RiskType.BULLISH_DIVERGENCE:
                # 底背离 → 平空头仓位
                reason = 'RSI底背离 + 成交量衰减, 建议买入'
                return {
                    'date': row['date'],
                    'price': float(row['closing']),
                    'type': SignalType.BUY,
                    'strength': SignalStrength.STRONG,
                    'reason': reason,
                    'analysis': {
                        'market_state': market_state,
                        'key_area': key_area,
                        'entry_trigger': entry_trigger,
                        'risk_filter': risk_filter
                    }
                }

        # 如果有风险但不是必须退出，降低信号强度
        strength_penalty = 0
        if risk_filter['has_risk']:
            strength_penalty = 1

        # 生成做多信号
        if direction == MarketDirection.LONG and entry_trigger['is_triggered']:
            # 最好是在支撑区，但不是强制要求
            in_support = key_area['is_key_area'] and key_area['area_type'] == AreaType.SUPPORT

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
            reasons.append(f"MACD在0轴{'上方' if market_state['macd_position'] == MacdPosition.ABOVE else '附近'}")
            reasons.append(f"RSI={market_state['rsi_value']:.1f}（多头趋势）")
            if in_support:
                reasons.append(f"在关键支撑区：{', '.join(key_area['reasons'])}")
            if entry_trigger['pattern_info']:
                reasons.append(f"出现{entry_trigger['pattern_info']['pattern_type'].text}")
            reasons.append(f"成交量放大{entry_trigger['volume_ratio']:.1f}倍")
            if risk_filter['has_risk']:
                reasons.append(f"⚠️ 注意：存在{risk_filter['risk_type'].text if risk_filter['risk_type'] else None}风险")

            reason_text = ' | '.join(reasons)

            return {
                'date': row['date'],
                'price': float(row['closing']),
                'type': SignalType.BUY,
                'strength': strength,
                'action': 'ENTER_LONG',
                'reason': reason_text,
                'analysis': {
                    'market_state': market_state,
                    'key_area': key_area,
                    'entry_trigger': entry_trigger,
                    'risk_filter': risk_filter
                }
            }

        # 生成做空信号
        if direction == MarketDirection.SHORT and entry_trigger['is_triggered']:
            # 最好是在阻力区
            in_resistance = key_area['is_key_area'] and key_area['area_type'] == AreaType.RESISTANCE

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
            reasons.append(f"MACD在0轴{'下方' if market_state['macd_position'] == MacdPosition.BELOW else '附近'}")
            reasons.append(f"RSI={market_state['rsi_value']:.1f}（空头趋势）")
            if in_resistance:
                reasons.append(f"在关键阻力区：{', '.join(key_area['reasons'])}")
            if entry_trigger['pattern_info']:
                reasons.append(f"出现{entry_trigger['pattern_info']['pattern_type'].text}")
            reasons.append(f"成交量放大{entry_trigger['volume_ratio']:.1f}倍")
            if risk_filter['has_risk']:
                reasons.append(f"⚠️ 注意：存在{risk_filter['risk_type'].text if risk_filter['risk_type'] else None}风险")

            reason_text = ' | '.join(reasons)

            return {
                'date': row['date'],
                'price': float(row['closing']),
                'type': SignalType.SELL,
                'strength': strength,
                'action': 'ENTER_SHORT',
                'reason': reason_text,
                'analysis': {
                    'market_state': market_state,
                    'key_area': key_area,
                    'entry_trigger': entry_trigger,
                    'risk_filter': risk_filter
                }
            }
        return None


    @staticmethod
    def get_algorithm_info() -> List[Dict]:
        return [
            {
                'step': "市场状态判定",
                'why': "能不能做多/做空/观望",
                'icon': "⓵",
                'strategy': 'MACD + RSI',
                'criteria': [
                    "MACD判断趋方向",
                    "MACD在0轴上方, 只考虑做多 -> MACD的DIFF值 > 0.5",
                    "MACD在0轴下方, 只考虑做空 -> MACD的DIFF值 < -0.5",
                    "MACD贴着0轴来回, 震荡, 不交易 -> MACD的DIFF值在-0.5 ~ 0.5之间",
                    "RSI判断趋势强度",
                    "RSI(14) > 55, 多头趋势",
                    "RSI(14) < 45, 空头趋势",
                    "RSI(14)45 ~ 55, 中性, 震荡",
                    "MACD上方 + RSI多头 -> 考虑做多",
                    "MACD上方 + RSI中性 -> 考虑做多",
                    "MACD下方 + RSI空头 -> 考虑做空",
                    "MACD下方 + RSI中性 -> 考虑做空",
                    "其他组合 -> 震荡",
                    "做多置信度 -> min((RSI - 55) / 20, 1.0)",
                    "做空置信度 -> min((45 - RSI) / 20, 1.0)",
                ],
                'color_class': 'sync-card-blue'
            },
            {
                'step': "关键区域识别",
                'why': "在哪里做",
                'icon': "⓶",
                'strategy': 'K线形态 + 结构位置',
                'criteria': [
                    "均线(MA5、MA10、MA20、MA60)支持/阻力区域 -> 价格触及均线 ±2% 范围内",
                    "前期高低点区域 -> 价格触及前20天内的最高点/最低点±2%范围内",
                    "K线重要反转形态区域 -> 看涨吞没、看跌吞没、启明星、黄昏星、锤子线、流星线",
                ],
                'color_class': 'sync-card-green'
            },
            {
                'step': "入场触发验证",
                'why': "现在是不是那个点",
                'icon': "⓷",
                'strategy': 'K线形态 + 成交量',
                'criteria': [
                   "K线形态匹配方向",
                    "做多时,看涨形态 -> 看涨吞没、启明星、锤子线、倒锤子线、刺透形态、三只白兵",
                    "做空时,看跌形态 -> 看跌吞没、黄昏星、流星线、上吊线、乌云盖顶、三只乌鸦",
                    "成交量放大确认 -> 当前成交量 >= 5日均成交量 * 1.3(放大 30% 以上)",
                ],
                'color_class': 'sync-card-orange'
            },
            {
                'step': "风险过滤",
                'why': "这个信号会不会是假突破",
                'icon': "⓸",
                'strategy': 'RSI背离 + 成交量衰减',
                'criteria': [
                    "顶背离,做多风险 -> 当前价格接近或创新高, 价格高点在RSI高点之后, RSI未创新高",
                    "底背离,做空风险 -> 当前价格接近或创新低, 价格低点在RSI低点之后, RSI未创新低",
                    "风险等级 -> low(有背离+成交量正常)、medium(背离+成交量走弱)、high(背离+成交量明显衰减)",
                ],
                'color_class': 'sync-card-purple'
            }
        ]