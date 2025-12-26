from datetime import date

from enums.history_type import StockHistoryType
from enums.strategy import StrategyType
from typing import List, Dict, Any
import pandas as pd
from enums.signal import SignalType, SignalStrength
from models.stock_history import get_history_model
from utils.db import get_db_session


class StrategyResult:
    """策略结果类"""
    def __init__(self, strategy_type: StrategyType, signals: List[Dict], metadata: Dict = None):
        self.strategy_type = strategy_type
        self.signals = signals
        self.metadata = metadata or {}


class BaseStrategy:
    """策略基类"""
    def __init__(self, name: str):
        self.name = name

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        raise NotImplementedError("子类必须实现 generate_signals 方法")


class MACDStrategy(BaseStrategy):
    """MACD策略"""
    def __init__(self):
        super().__init__("MACD策略")

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        # 计算信号标记
        signals = calculate_macd_signals(df)
        return StrategyResult(
            strategy_type=StrategyType.MACD_STRATEGY,
            signals=signals,
            metadata={
                "description": "基于MACD指标的交易信号",
                "indicators_used": ["MACD", "DIFF", "DEA"]
            }
        )


class SMAStrategy(BaseStrategy):
    """SMA策略"""
    def __init__(self):
        super().__init__("SMA策略")

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        # 计算SMA信号
        signals = calculate_sma_signals(df)
        return StrategyResult(
            strategy_type=StrategyType.SMA_STRATEGY,
            signals=signals,
            metadata={
                "description": "基于简单移动平均线的交易信号",
                "indicators_used": ["MA5", "MA10", "MA30", "MA250"]
            }
        )

class TurtleStrategy(BaseStrategy):
    """海龟策略"""
    def __init__(self, entry_window: int = 20, exit_window: int = 10, atr_period: int = 20):
        super().__init__("海龟策略")
        self.entry_window = entry_window
        self.exit_window = exit_window
        self.atr_period = atr_period

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = calculate_turtle_signals(
            df,
            entry_window=self.entry_window,
            exit_window=self.exit_window,
            atr_period=self.atr_period
        )

        return StrategyResult(
            strategy_type=StrategyType.TURTLE_STRATEGY,
            signals=signals,
            metadata={
                "description": "基于唐奇安通道的交易信号",
                "entry_window": self.entry_window,
                "exit_window": self.exit_window,
                "atr_period": self.atr_period
            }
        )

class CBRStrategy(BaseStrategy):
    """CBR (Confirmation-Based Reversal) 策略"""
    def __init__(self):
        super().__init__("CBR策略")

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        # 计算CBR信号
        signals = calculate_cbr_signals(df)
        return StrategyResult(
            strategy_type=StrategyType.CBR_STRATEGY,
            signals=signals,
            metadata={
                "description": "基于价格形态和MACD确认的反转策略",
                "indicators_used": ["Price Pattern", "MACD"]
            }
        )


class RSIStrategy(BaseStrategy):
    """RSI策略 - 相对强弱指标"""
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("RSI策略")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = calculate_rsi_signals(
            df,
            period=self.period,
            oversold=self.oversold,
            overbought=self.overbought
        )
        return StrategyResult(
            strategy_type=StrategyType.RSI_STRATEGY,
            signals=signals,
            metadata={
                "description": f"基于RSI指标的超买超卖策略",
                "period": self.period,
                "oversold": self.oversold,
                "overbought": self.overbought
            }
        )


class BollingerStrategy(BaseStrategy):
    """布林带策略"""
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("布林带策略")
        self.period = period
        self.std_dev = std_dev

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = calculate_bollinger_signals(
            df,
            period=self.period,
            std_dev=self.std_dev
        )
        return StrategyResult(
            strategy_type=StrategyType.BOLL_STRATEGY,
            signals=signals,
            metadata={
                "description": "基于布林带通道的突破策略",
                "period": self.period,
                "std_dev": self.std_dev
            }
        )


class KDJStrategy(BaseStrategy):
    """KDJ策略 - 随机指标"""
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        super().__init__("KDJ策略")
        self.n = n
        self.m1 = m1
        self.m2 = m2

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = calculate_kdj_signals(
            df,
            n=self.n,
            m1=self.m1,
            m2=self.m2
        )
        return StrategyResult(
            strategy_type=StrategyType.KDJ_STRATEGY,
            signals=signals,
            metadata={
                "description": "基于KDJ指标的超买超卖策略",
                "n": self.n,
                "m1": self.m1,
                "m2": self.m2
            }
        )


class CandlestickStrategy(BaseStrategy):
    """蜡烛图形态策略 - K线形态识别"""
    def __init__(self,
                 body_min_ratio: float = 0.6,
                 shadow_ratio: float = 2.0,
                 trend_ma_period: int = 20):
        super().__init__("蜡烛图策略")
        self.body_min_ratio = body_min_ratio
        self.shadow_ratio = shadow_ratio
        self.trend_ma_period = trend_ma_period

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = calculate_candlestick_signals(
            df,
            body_min_ratio=self.body_min_ratio,
            shadow_ratio=self.shadow_ratio,
            trend_ma_period=self.trend_ma_period
        )
        return StrategyResult(
            strategy_type=StrategyType.CANDLESTICK_STRATEGY,
            signals=signals,
            metadata={
                "description": "基于经典K线形态的交易信号识别",
                "patterns": [
                    "锤子线/上吊线",
                    "倒锤子线/流星线",
                    "十字星",
                    "看涨吞没/看跌吞没",
                    "乌云盖顶/刺透形态",
                    "晨星/黄昏星",
                    "三只白兵/三只乌鸦"
                ],
                "body_min_ratio": self.body_min_ratio,
                "shadow_ratio": self.shadow_ratio,
                "trend_ma_period": self.trend_ma_period
            }
        )


def calculate_macd(df: pd.DataFrame, fast_period=12, slow_period=26, signal_period=9):
    df = df.copy()
    df['EMA12'] = df['closing'].ewm(span=fast_period, adjust=False).mean()
    df['EMA26'] = df['closing'].ewm(span=slow_period, adjust=False).mean()
    df['DIFF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIFF'].ewm(span=signal_period, adjust=False).mean()
    df['MACD_hist'] = df['DIFF'] - df['DEA']
    return df[['DIFF', 'DEA', 'MACD_hist']]

def calculate_macd_signals(df):
    # 计算 MACD
    macd_df = calculate_macd(df)
    """
    根据MACD指标计算买卖信号
    """
    signals = []

    # 确保两个DataFrame长度一致
    min_len = min(len(df), len(macd_df))
    df = df.iloc[:min_len]
    macd_df = macd_df.iloc[:min_len]

    try:
        for i in range(1, len(macd_df)):
            # 获取当前和前一日的数据
            prev_diff = macd_df.iloc[i - 1]['DIFF']
            prev_dea = macd_df.iloc[i - 1]['DEA']
            curr_diff = macd_df.iloc[i]['DIFF']
            curr_dea = macd_df.iloc[i]['DEA']

            # 从原始df中获取日期和价格
            date = df.iloc[i]['date']
            price = df.iloc[i]['closing']

            # 计算DIFF的角度（使用前后两天的差值）
            if i >= 2:
                prev2_diff = macd_df.iloc[i - 2]['DIFF']
                # 避免除零错误
                if abs(curr_diff - prev2_diff) > 1e-10:
                    diff_angle = abs((curr_diff - prev2_diff) / 2 * 45)
                else:
                    diff_angle = 0
            else:
                diff_angle = 0

            # 买入信号：DIFF上穿DEA且DIFF>0
            if prev_diff <= prev_dea and curr_diff > curr_dea and curr_diff > 0:
                strength = SignalStrength.STRONG if diff_angle > 30 else SignalStrength.WEAK
                signals.append({
                    'date': date,
                    'price': float(price),
                    'type': SignalType.BUY,
                    'strength': strength
                })

            # 卖出信号：DIFF下穿DEA
            elif prev_diff >= prev_dea and curr_diff < curr_dea:
                # 如果DIFF<0且DEA<0，为强卖出信号
                if curr_diff < 0 and curr_dea < 0:
                    strength = SignalStrength.STRONG
                else:
                    strength = SignalStrength.WEAK

                signals.append({
                    'date': date,
                    'price': float(price),
                    'type': SignalType.SELL,
                    'strength': strength
                })
    except Exception as e:
        pass

    return signals

def calculate_sma_signals(df):
    ma_lines = {}
    default_ma_periods = [5, 10, 30, 250]
    for period in default_ma_periods:
        ma_lines[f'MA{period}'] = df['closing'].rolling(window=period).mean().tolist()
    """
    根据简单移动平均线计算买卖信号
    1. 5日线上穿10日线时为买入信号（删除DIF和DEA大于0的条件）
    2. 10日均线下破5日均线 && MACD DIF下破DEA 时为强卖出信号
    3. 收盘价<10日线时为弱卖出信号
    """
    signals = []

    # 确保有足够数据
    if len(df) < 11 or 'MA5' not in ma_lines or 'MA10' not in ma_lines:
        return signals

    # 计算MACD的DIFF值用于判断
    macd_df = calculate_macd(df)

    # 获取数据
    dates = df['date']
    closing_prices = df['closing']
    ma5_values = ma_lines['MA5']
    ma10_values = ma_lines['MA10']
    diff_values = macd_df['DIFF']
    dea_values = macd_df['DEA']

    # 遍历数据计算信号
    for i in range(1, len(df)):
        # 检查是否有足够的数据点
        if i < 1:
            continue

        try:
            # 获取当前和前一日的数据
            prev_ma5 = ma5_values[i - 1] if not pd.isna(ma5_values[i - 1]) else None
            curr_ma5 = ma5_values[i] if not pd.isna(ma5_values[i]) else None
            prev_ma10 = ma10_values[i - 1] if not pd.isna(ma10_values[i - 1]) else None
            curr_ma10 = ma10_values[i] if not pd.isna(ma10_values[i]) else None
            prev_diff = diff_values[i - 1] if not pd.isna(diff_values[i - 1]) else None
            curr_diff = diff_values[i] if not pd.isna(diff_values[i]) else None
            prev_dea = dea_values[i - 1] if not pd.isna(dea_values[i - 1]) else None
            curr_dea = dea_values[i] if not pd.isna(dea_values[i]) else None
            curr_closing = closing_prices.iloc[i]
            curr_date = dates.iloc[i]

            # 确保所有必要数据都存在
            if (prev_ma5 is None or curr_ma5 is None or
                    prev_ma10 is None or curr_ma10 is None or
                    prev_diff is None or curr_diff is None or
                    prev_dea is None or curr_dea is None):
                continue

            # 买入信号：5日线上穿10日线
            if (prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10 and prev_diff > 0 and prev_dea > 0):
                signals.append({
                    'date': curr_date,
                    'price': float(curr_closing),
                    'type': SignalType.BUY,
                    'strength': SignalStrength.STRONG
                })
            # 强卖出信号：10日均线下破5日均线 && MACD DIF下破DEA
            # and curr_dea<curr_ma5 and prev_diff >= prev_dea and curr_diff < curr_dea
            if (prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10):
                signals.append({
                    'date': curr_date,
                    'price': float(curr_closing),
                    'type': SignalType.SELL,
                    'strength': SignalStrength.STRONG
                })

            # 弱卖出信号：收盘价 < 10日线
            """elif curr_ma10 is not None and curr_closing < curr_ma10:
                signals.append({
                    'date': curr_date,
                    'price': float(curr_closing),
                    'type': SignalType.SELL,
                    'strength': SignalStrength.Week
                })"""

        except Exception as e:
            continue
    return signals


def compute_donchian_channels(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    计算唐奇安通道（海龟通道）：
    - 上轨：过去 window 天（不含当日）的最高价滚动最大值
    - 下轨：过去 window 天（不含当日）的最低价滚动最小值
    """
    channels = pd.DataFrame(index=df.index)
    channels["upper"] = df["highest"].shift(1).rolling(window).max()
    channels["lower"] = df["lowest"].shift(1).rolling(window).min()
    return channels


def compute_atr(df: pd.DataFrame, period: int = 20, method: str = "ema") -> pd.Series:
    """
    计算 ATR（Average True Range）用于估计波动和强弱：
    TR = max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    )
    ATR 为 TR 的均线（默认 EMA）。
    """
    highest = df["highest"]
    lowest = df["lowest"]
    closing = df["closing"]
    prev_close = closing.shift(1)

    tr = pd.concat([
        (highest - lowest),
        (highest - prev_close).abs(),
        (lowest - prev_close).abs(),
    ], axis=1).max(axis=1)

    if method == "ema":
        return tr.ewm(span=period, adjust=False).mean()
    else:
        return tr.rolling(period).mean()

def calculate_turtle_signals(
    df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    atr_period: int = 20,
    allow_short: bool = False,
) -> List[Dict]:
    """
    基于海龟策略（唐奇安通道）生成交易信号：
    - 入场：收盘价突破 entry_window 通道上轨（做多），或跌破下轨（做空，可选）
    - 出场：做多回落至 exit_window 下轨；做空反弹至 exit_window 上轨
    - 强弱：用突破幅度相对 ATR 估计（>=0.5 记为 strong，否则 weak）

    输入 df 至少包含列：date, high, low, closing
    返回信号列表：{date, price, signal_type: 'buy'|'sell', strength: 'strong'|'weak'}
    """
    signals: List[Dict] = []

    channels_entry = compute_donchian_channels(df, entry_window)
    channels_exit = compute_donchian_channels(df, exit_window)
    atr = compute_atr(df, atr_period)
    position = 0  # 0: 空仓；1: 多头；-1: 空头

    for i in range(len(df)):
        date = df.iloc[i]["date"]
        price = float(df.iloc[i]["closing"])

        upper = channels_entry.iloc[i]["upper"]
        lower = channels_entry.iloc[i]["lower"]
        exit_low = channels_exit.iloc[i]["lower"]
        exit_upper = channels_exit.iloc[i]["upper"]
        curr_atr = atr.iloc[i]

        # 入场：做多突破上轨
        if position <= 0 and pd.notna(upper) and df.iloc[i]["closing"] >= upper:
            strength = SignalStrength.STRONG if pd.notna(curr_atr) and (df.iloc[i]["closing"] - upper) / (curr_atr + 1e-9) >= 0.5 else SignalStrength.WEAK
            signals.append({
                "date": date,
                "price": price,
                "type": SignalType.BUY,
                "strength": strength,
            })
            position = 1
            continue

        # 出场：多头跌破 exit_window 下轨
        if position == 1 and pd.notna(exit_low) and df.iloc[i]["closing"] <= exit_low:
            signals.append({
                "date": date,
                "price": price,
                "type": SignalType.SELL,
                "strength": SignalStrength.WEAK,
            })
            position = 0
            continue

        if allow_short:
            # 入场：做空跌破下轨
            if position >= 0 and pd.notna(lower) and df.iloc[i]["closing"] <= lower:
                strength = SignalStrength.STRONG if pd.notna(curr_atr) and (lower - df.iloc[i]["closing"]) / (curr_atr + 1e-9) >= 0.5 else SignalStrength.WEAK
                signals.append({
                    "date": date,
                    "price": price,
                    "type": SignalType.SELL,
                    "strength": strength,
                })
                position = -1
                continue

            # 出场：空头反弹至 exit_window 上轨
            if position == -1 and pd.notna(exit_upper) and df.iloc[i]["closing"] >= exit_upper:
                signals.append({
                    "date": date,
                    "price": price,
                    "type": SignalType.BUY,
                    "strength": SignalStrength.WEAK,
                })
                position = 0
                continue

    return signals


def calculate_cbr_signals(df):
    """
    根据CBR策略计算买卖信号
    买点: T-2的最高和最低 > T-1的最高和最低，T的收盘价 > T-1的最高 或者 MACD金叉
    卖点: T-2的最高和最低 < T-1的最高和最低，T的收盘价 < T-1的最低 或者 MACD死叉
    """
    signals = []

    # 确保有足够数据(T-2, T-1, T需要至少3天数据)
    if len(df) < 3:
        return signals

    # 确保必要的列存在
    required_columns = ['highest', 'lowest', 'closing']
    if not all(col in df.columns for col in required_columns):
        return signals

    # 计算MACD指标（如果不存在）
    if 'DIFF' not in df.columns or 'DEA' not in df.columns:
        macd_df = calculate_macd(df)
        df = df.copy()
        df['DIFF'] = macd_df['DIFF']
        df['DEA'] = macd_df['DEA']

    # 遍历数据生成信号(从第3天开始，因为需要T-2的数据)
    for i in range(2, len(df)):
        # 获取T-2, T-1, T三个时间点的数据
        t_minus_2_highest = df.iloc[i - 2]['highest']
        t_minus_2_lowest = df.iloc[i - 2]['lowest']
        t_minus_1_highest = df.iloc[i - 1]['highest']
        t_minus_1_lowest = df.iloc[i - 1]['lowest']
        t_closing = df.iloc[i]['closing']
        t_date = df.iloc[i]['date']

        # 获取MACD值
        t_diff = df.iloc[i]['DIFF'] if 'DIFF' in df.columns else None
        t_dea = df.iloc[i]['DEA'] if 'DEA' in df.columns else None
        t_minus_1_diff = df.iloc[i - 1]['DIFF'] if 'DIFF' in df.columns else None
        t_minus_1_dea = df.iloc[i - 1]['DEA'] if 'DEA' in df.columns else None

        # 判断买点条件
        # 条件1: T-2的最高和最低 > T-1的最高和最低
        condition1_buy = (t_minus_2_highest > t_minus_1_highest) and (t_minus_2_lowest > t_minus_1_lowest)
        # 条件2: T的收盘价 > T-1的最高 或者 MACD金叉
        condition2_buy = False
        if t_diff is not None and t_dea is not None and t_minus_1_diff is not None and t_minus_1_dea is not None:
            condition2_buy = (t_closing > t_minus_1_highest) or (t_diff > t_dea and t_minus_1_diff <= t_minus_1_dea)
        else:
            condition2_buy = (t_closing > t_minus_1_highest)

        # 判断卖点条件
        # 条件1: T-2的最高和最低 < T-1的最高和最低
        condition1_sell = (t_minus_2_highest < t_minus_1_highest) and (t_minus_2_lowest < t_minus_1_lowest)
        # 条件2: T的收盘价 < T-1的最低 或者 MACD死叉
        condition2_sell = False
        if t_diff is not None and t_dea is not None and t_minus_1_diff is not None and t_minus_1_dea is not None:
            condition2_sell = (t_closing < t_minus_1_lowest) or (t_diff < t_dea and t_minus_1_diff >= t_minus_1_dea)
        else:
            condition2_sell = (t_closing < t_minus_1_lowest)

        # 生成买入信号
        if condition1_buy and condition2_buy:
            signals.append({
                'date': t_date,
                'price': float(t_closing),
                'type': SignalType.BUY,
                'strength': SignalStrength.STRONG
            })

        # 生成卖出信号
        elif condition1_sell and condition2_sell:
            signals.append({
                'date': t_date,
                'price': float(t_closing),
                'type': SignalType.SELL,
                'strength': SignalStrength.STRONG
            })

    return signals

def backtest_strategy(df, signals, initial_capital=100000.0, buy_ratios=None, sell_ratios=None):
    """
    基于生成的信号进行回测
    """
    if not signals:
        return None

    if buy_ratios is None:
        buy_ratios = {SignalStrength.STRONG: 0.8, SignalStrength.WEAK: 0.5}
    if sell_ratios is None:
        sell_ratios = {SignalStrength.STRONG: 0.8, SignalStrength.WEAK: 0.5}

    # 初始化回测参数
    capital = initial_capital
    position = 0  # 持仓数量
    trades = []  # 交易记录

    # 处理交易信号
    for signal in signals:
        signal_date = signal['date']
        signal_price = signal['price']
        signal_type = signal['type']
        strength = signal['strength']

        # 获取信号日期对应的数据行
        if signal_date in df['date'].values:
            row = df[df['date'] == signal_date].iloc[0]
            current_price = row['closing']
        else:
            current_price = signal_price

        # 买入信号
        if signal_type == SignalType.BUY and position == 0:
            # 根据信号强度决定买入比例
            buy_ratio = buy_ratios.get(strength, 0.5)  # 默认使用弱信号比例
            amount_to_invest = capital * buy_ratio
            shares_to_buy = int(amount_to_invest / current_price)

            if shares_to_buy > 0:
                cost = shares_to_buy * current_price
                capital -= cost
                position += shares_to_buy

                trades.append({
                    'date': signal_date,
                    'type': SignalType.BUY,
                    'price': current_price,
                    'shares': shares_to_buy,
                    'amount': cost,
                    'strength': strength,
                    'capital': capital,
                    'position': position
                })

        # 卖出信号
        elif signal_type == SignalType.SELL and position > 0:
            # 根据信号强度决定卖出比例
            sell_ratio = sell_ratios.get(strength, 0.5)  # 默认使用弱信号比例
            shares_to_sell = int(position * sell_ratio)

            if shares_to_sell > 0:
                revenue = shares_to_sell * current_price
                capital += revenue
                position -= shares_to_sell
                trades.append({
                    'date': signal_date,
                    'type': SignalType.SELL,
                    'price': current_price,
                    'shares': shares_to_sell,
                    'amount': revenue,
                    'strength': strength,
                    'capital': capital,
                    'position': position
                })

    # 计算最终价值（包括持仓）
    final_date = df['date'].max()
    final_price = df[df['date'] == final_date]['closing'].iloc[0]
    final_value = capital + position * final_price
    total_return = (final_value - initial_capital) / initial_capital * 100

    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'trades': trades,
        'capital': capital,
        'position': position,
        'final_price': final_price
    }


def calculate_strategy_metrics(df, signals):
    """
    计算策略指标（增强版）

    返回：
    - 总信号数
    - 买入/卖出信号数
    - 平均持股天数
    - 胜率（盈利交易 / 总交易）
    - 盈亏比（平均盈利 / 平均亏损）
    - 最大连续盈利/亏损次数
    """
    if not signals:
        return {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'avg_holding_period': 0,
            'win_rate': 0,
            'profit_loss_ratio': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

    # 按日期排序
    signals = sorted(signals, key=lambda x: x['date'])

    # 计算胜率
    buy_signals = [s for s in signals if s['type'] == SignalType.BUY]
    sell_signals = [s for s in signals if s['type'] == SignalType.SELL]

    # 计算平均持股天数和盈亏情况
    holding_periods = []
    buy_dates = {}
    profits = []  # 每次交易的盈亏
    consecutive_wins = 0
    consecutive_losses = 0
    max_consecutive_wins = 0
    max_consecutive_losses = 0

    for signal in signals:
        if signal['type'] == SignalType.BUY:
            buy_dates[signal['date']] = signal['price']
        elif signal['type'] == SignalType.SELL and buy_dates:
            # 简单匹配最近的买入信号
            if buy_dates:
                last_buy_date = list(buy_dates.keys())[-1]
                last_buy_price = buy_dates[last_buy_date]

                # 计算持股天数
                holding_days = (signal['date'] - last_buy_date).days
                if holding_days > 0:
                    holding_periods.append(holding_days)

                # 计算盈亏
                profit_pct = (signal['price'] - last_buy_price) / last_buy_price
                profits.append(profit_pct)

                # 计算连续盈亏
                if profit_pct > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

                del buy_dates[last_buy_date]

    # 计算指标
    avg_holding_period = sum(holding_periods) / len(holding_periods) if holding_periods else 0

    # 胜率和盈亏比
    winning_trades = len([p for p in profits if p > 0])
    losing_trades = len([p for p in profits if p <= 0])
    total_trades = len(profits)

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    avg_profit = sum([p for p in profits if p > 0]) / winning_trades if winning_trades > 0 else 0
    avg_loss = abs(sum([p for p in profits if p <= 0]) / losing_trades) if losing_trades > 0 else 0
    profit_loss_ratio = (avg_profit / avg_loss) if avg_loss > 0 else 0

    return {
        'total_signals': len(signals),
        'buy_signals': len(buy_signals),
        'sell_signals': len(sell_signals),
        'avg_holding_period': avg_holding_period,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades
    }


def generate_trading_advice(df, signals, current_date=None):
    """
    生成交易建议
    """
    if not signals:
        return "当前无明确交易信号"
    if current_date is None:
        current_date = df['date'].max()
    # 获取最近的信号
    recent_signals = [s for s in signals if s['date'] <= current_date]
    if not recent_signals:
        return "当前无历史交易信号"
    # 按日期排序，获取最新的信号
    recent_signals.sort(key=lambda x: x['date'], reverse=True)
    latest_signal = recent_signals[0]
    # 获取当前价格
    current_price = df[df['date'] == current_date]['closing'].iloc[0] if current_date in df['date'].values else \
        latest_signal['price']
    advice = ""
    if latest_signal['type'] == SignalType.BUY:
        if latest_signal['strength'] == SignalStrength.STRONG:
            advice = f"🔴 🔥 MB（强烈买入），当前价格：¥{current_price:.2f}"
        else:
            advice = f"🔴 🥀 MB（建议买入），当前价格：¥{current_price:.2f}"
    else:  # sell signal
        if latest_signal['strength'] == SignalStrength.STRONG:
            advice = f"🟢 🔥 MS（强烈买入），当前价格：¥{current_price:.2f}"
        else:
            advice = f"🟢 🥀 MS（建议买入），当前价格：¥{current_price:.2f}"
    return advice


def calculate_risk_metrics(df, signals):
    """
    计算风险指标
    """
    if len(df) < 2 or not signals:
        return None
    # 计算股票收益率波动率
    df = df.copy()
    df['returns'] = df['closing'].pct_change()
    volatility = df['returns'].std() * (252 ** 0.5)  # 年化波动率

    # 计算最大回撤
    df['cummax'] = df['closing'].cummax()
    df['drawdown'] = (df['closing'] - df['cummax']) / df['cummax']
    max_drawdown = df['drawdown'].min()

    # 计算夏普比率(假设无风险利率为3%)
    risk_free_rate = 0.03
    sharpe_ratio = (df['returns'].mean() * 252 - risk_free_rate) / (df['returns'].std() * (252 ** 0.5)) if df['returns'].std() > 0 else 0

    return {
        'volatility': volatility,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio
    }


def calculate_strategy_performance(df, all_signals, backtest_result):
    """
    基于实际交易记录计算策略收益和基准收益
    """
    df_sorted = df.sort_values('date')
    dates = df_sorted['date'].tolist()
    prices = df_sorted['closing'].tolist()

    # 初始化策略收益序列
    strategy_values = []
    current_capital = backtest_result['initial_capital']
    current_position = 0

    # 按日期排序交易记录
    trades = sorted(backtest_result['trades'], key=lambda x: x['date'])
    trade_index = 0

    # 计算策略每日价值
    for i, (date, price) in enumerate(zip(dates, prices)):
        # 检查是否有在该日期的交易
        while trade_index < len(trades) and trades[trade_index]['date'] == date:
            trade = trades[trade_index]
            current_capital = trade['capital']
            current_position = trade['position']
            trade_index += 1

        # 计算当前总价值（现金 + 持仓价值）
        current_value = current_capital + current_position * price
        strategy_values.append(current_value)

    # 转换策略收益为百分比收益
    strategy_cumulative = [(value / backtest_result['initial_capital'] - 1) * 100
                           for value in strategy_values]
    # 计算基准收益（买入持有）
    initial_price = prices[0]
    benchmark_cumulative = [(price / initial_price - 1) * 100 for price in prices]
    return strategy_cumulative, benchmark_cumulative


def calculate_position_and_cash_values(df, backtest_result):
    """
    计算回测过程中的持仓价值和现金价值数据，用于展示资金分布变化图表

    Args:
        df: 包含股票价格数据的DataFrame
        backtest_result: 回测结果字典，包含交易记录等信息

    Returns:
        tuple: (position_values, cash_values)
    """
    # 准备持仓价值和现金价值数据
    position_values = []
    cash_values = []

    # 初始化资金和持仓
    daily_capital = backtest_result['initial_capital']
    daily_position = 0

    # 按日期排序的交易记录
    sorted_trades = sorted(backtest_result['trades'], key=lambda x: x['date'])
    trade_idx = 0

    # 遍历每天的数据
    for i, (date, price) in enumerate(zip(df['date'], df['closing'])):
        # 更新当天的资金和持仓情况
        while trade_idx < len(sorted_trades) and sorted_trades[trade_idx]['date'] == date:
            daily_capital = sorted_trades[trade_idx]['capital']
            daily_position = sorted_trades[trade_idx]['position']
            trade_idx += 1

        # 计算持仓价值和现金价值
        position_value = daily_position * price
        cash_value = daily_capital

        position_values.append(position_value)
        cash_values.append(cash_value)

    return position_values, cash_values


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    计算RSI（相对强弱指标）

    RSI = 100 - (100 / (1 + RS))
    其中 RS = 平均涨幅 / 平均跌幅
    """
    delta = df['closing'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_rsi_signals(
    df: pd.DataFrame,
    period: int = 14,
    oversold: int = 30,
    overbought: int = 70
) -> List[Dict]:
    """
    基于RSI指标生成交易信号

    买入信号：RSI < 30（超卖）且开始上升
    卖出信号：RSI > 70（超买）且开始下降
    """
    signals = []

    if len(df) < period + 1:
        return signals

    rsi = calculate_rsi(df, period)

    for i in range(1, len(df)):
        if pd.isna(rsi.iloc[i]) or pd.isna(rsi.iloc[i-1]):
            continue

        date = df.iloc[i]['date']
        price = float(df.iloc[i]['closing'])
        curr_rsi = rsi.iloc[i]
        prev_rsi = rsi.iloc[i-1]

        # 买入信号：RSI从超卖区域向上穿越
        if prev_rsi < oversold and curr_rsi >= oversold:
            # 强买入：RSI急速上升（变化>5）
            strength = SignalStrength.STRONG if (curr_rsi - prev_rsi) > 5 else SignalStrength.WEAK
            signals.append({
                'date': date,
                'price': price,
                'type': SignalType.BUY,
                'strength': strength
            })

        # 卖出信号：RSI从超买区域向下穿越
        elif prev_rsi > overbought and curr_rsi <= overbought:
            # 强卖出：RSI急速下降
            strength = SignalStrength.STRONG if (prev_rsi - curr_rsi) > 5 else SignalStrength.WEAK
            signals.append({
                'date': date,
                'price': price,
                'type': SignalType.SELL,
                'strength': strength
            })

    return signals


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    计算布林带指标

    中轨 = N日移动平均线
    上轨 = 中轨 + K × N日标准差
    下轨 = 中轨 - K × N日标准差
    """
    bands = pd.DataFrame(index=df.index)
    bands['middle'] = df['closing'].rolling(window=period).mean()
    std = df['closing'].rolling(window=period).std()
    bands['upper'] = bands['middle'] + (std_dev * std)
    bands['lower'] = bands['middle'] - (std_dev * std)
    return bands


def calculate_bollinger_signals(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0
) -> List[Dict]:
    """
    基于布林带策略生成交易信号

    买入信号：价格触及或跌破下轨后反弹
    卖出信号：价格触及或突破上轨后回落
    """
    signals = []

    if len(df) < period + 1:
        return signals

    bands = calculate_bollinger_bands(df, period, std_dev)

    for i in range(1, len(df)):
        if pd.isna(bands.iloc[i]['lower']) or pd.isna(bands.iloc[i]['upper']):
            continue

        date = df.iloc[i]['date']
        price = float(df.iloc[i]['closing'])
        curr_close = df.iloc[i]['closing']
        prev_close = df.iloc[i-1]['closing']
        lower = bands.iloc[i]['lower']
        upper = bands.iloc[i]['upper']
        prev_lower = bands.iloc[i-1]['lower']
        prev_upper = bands.iloc[i-1]['upper']

        # 买入信号：价格从下轨下方反弹
        if prev_close <= prev_lower and curr_close > lower:
            # 强买入：价格大幅反弹
            strength = SignalStrength.STRONG if (curr_close - lower) / lower > 0.02 else SignalStrength.WEAK
            signals.append({
                'date': date,
                'price': price,
                'type': SignalType.BUY,
                'strength': strength
            })

        # 卖出信号：价格从上轨上方回落
        elif prev_close >= prev_upper and curr_close < upper:
            # 强卖出：价格大幅回落
            strength = SignalStrength.STRONG if (upper - curr_close) / upper > 0.02 else SignalStrength.WEAK
            signals.append({
                'date': date,
                'price': price,
                'type': SignalType.SELL,
                'strength': strength
            })

    return signals


def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """
    计算KDJ指标（随机指标）

    RSV = (收盘价 - N日内最低价) / (N日内最高价 - N日内最低价) × 100
    K = RSV的M1日移动平均
    D = K的M2日移动平均
    J = 3K - 2D
    """
    kdj = pd.DataFrame(index=df.index)

    # 计算RSV
    low_n = df['lowest'].rolling(window=n).min()
    high_n = df['highest'].rolling(window=n).max()
    rsv = (df['closing'] - low_n) / (high_n - low_n) * 100

    # 计算K、D、J
    kdj['K'] = rsv.ewm(alpha=1/m1, adjust=False).mean()
    kdj['D'] = kdj['K'].ewm(alpha=1/m2, adjust=False).mean()
    kdj['J'] = 3 * kdj['K'] - 2 * kdj['D']

    return kdj


def calculate_kdj_signals(
    df: pd.DataFrame,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
    oversold: int = 20,
    overbought: int = 80
) -> List[Dict]:
    """
    基于KDJ指标生成交易信号

    买入信号：
    1. K线和D线都在20以下（超卖区）
    2. K线上穿D线（金叉）

    卖出信号：
    1. K线和D线都在80以上（超买区）
    2. K线下穿D线（死叉）
    """
    signals = []

    if len(df) < n + m1 + m2:
        return signals

    kdj = calculate_kdj(df, n, m1, m2)

    for i in range(1, len(df)):
        if pd.isna(kdj.iloc[i]['K']) or pd.isna(kdj.iloc[i]['D']):
            continue

        date = df.iloc[i]['date']
        price = float(df.iloc[i]['closing'])
        curr_k = kdj.iloc[i]['K']
        curr_d = kdj.iloc[i]['D']
        prev_k = kdj.iloc[i-1]['K']
        prev_d = kdj.iloc[i-1]['D']

        # 买入信号：金叉且在超卖区
        if prev_k <= prev_d and curr_k > curr_d:
            # 强买入：在深度超卖区（K和D都小于20）
            if curr_k < oversold and curr_d < oversold:
                strength = SignalStrength.STRONG
            else:
                strength = SignalStrength.WEAK

            signals.append({
                'date': date,
                'price': price,
                'type': SignalType.BUY,
                'strength': strength
            })

        # 卖出信号：死叉且在超买区
        elif prev_k >= prev_d and curr_k < curr_d:
            # 强卖出：在深度超买区（K和D都大于80）
            if curr_k > overbought and curr_d > overbought:
                strength = SignalStrength.STRONG
            else:
                strength = SignalStrength.WEAK

            signals.append({
                'date': date,
                'price': price,
                'type': SignalType.SELL,
                'strength': strength
            })

    return signals

def calculate_candlestick_signals(
    df: pd.DataFrame,
    body_min_ratio: float = 0.6,
    shadow_ratio: float = 2.0,
    trend_ma_period: int = 20
) -> List[Dict]:
    """
    蜡烛图形态识别策略
    
    识别15+种经典K线形态：
    - 单K线：锤子线、倒锤子线、上吊线、流星线、十字星
    - 双K线：看涨吞没、看跌吞没、乌云盖顶、刺透形态
    - 三K线：晨星、黄昏星、三只白兵、三只乌鸦
    
    参数：
        df: 股票数据DataFrame
        body_min_ratio: 实体最小比例（相对总长度）
        shadow_ratio: 影线比例阈值（相对实体）
        trend_ma_period: 趋势判断MA周期
    """
    signals = []
    
    if len(df) < max(trend_ma_period, 3):
        return signals
    
    # 计算趋势MA
    df = df.copy()
    df['MA'] = df['closing'].rolling(window=trend_ma_period).mean()
    
    for i in range(2, len(df)):  # 从第3根K线开始，确保有足够的历史数据
        # 获取当前和前两根K线数据
        curr = df.iloc[i]
        prev1 = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        
        # 分析K线特征
        curr_info = _analyze_candle(curr)
        prev1_info = _analyze_candle(prev1)
        prev2_info = _analyze_candle(prev2)
        
        # 判断趋势
        trend = _get_trend(curr, df, trend_ma_period)
        
        # 检测单K线形态
        single_pattern = _detect_single_candle_pattern(
            curr_info, trend, body_min_ratio, shadow_ratio
        )
        if single_pattern:
            signals.append({
                'date': curr['date'],
                'price': float(curr['closing']),
                'type': single_pattern['type'],
                'strength': single_pattern['strength'],
                'pattern_name': single_pattern['name']
            })
        
        # 检测双K线形态
        double_pattern = _detect_double_candle_pattern(
            prev1_info, curr_info, trend
        )
        if double_pattern:
            signals.append({
                'date': curr['date'],
                'price': float(curr['closing']),
                'type': double_pattern['type'],
                'strength': double_pattern['strength'],
                'pattern_name': double_pattern['name']
            })
        
        # 检测三K线形态
        triple_pattern = _detect_triple_candle_pattern(
            prev2_info, prev1_info, curr_info, trend
        )
        if triple_pattern:
            signals.append({
                'date': curr['date'],
                'price': float(curr['closing']),
                'type': triple_pattern['type'],
                'strength': triple_pattern['strength'],
                'pattern_name': triple_pattern['name']
            })
    
    return signals


def _analyze_candle(row) -> Dict:
    """分析单根K线的特征"""
    open_price = float(row['opening'])
    close_price = float(row['closing'])
    high_price = float(row['highest'])
    low_price = float(row['lowest'])
    
    # 实体
    body = abs(close_price - open_price)
    
    # 影线
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    
    # 总长度
    total_range = high_price - low_price
    
    # 颜色（阳线 or 阴线）
    is_bullish = close_price > open_price
    
    # 实体在总长度中的比例
    body_ratio = body / total_range if total_range > 0 else 0
    
    return {
        'open': open_price,
        'close': close_price,
        'high': high_price,
        'low': low_price,
        'body': body,
        'upper_shadow': upper_shadow,
        'lower_shadow': lower_shadow,
        'total_range': total_range,
        'is_bullish': is_bullish,
        'body_ratio': body_ratio
    }


def _get_trend(curr, df, ma_period: int) -> str:
    """判断当前趋势"""
    if pd.isna(curr['MA']):
        return 'neutral'
    
    price = float(curr['closing'])
    ma = float(curr['MA'])
    
    # 价格相对MA的偏离
    deviation = (price - ma) / ma if ma > 0 else 0
    
    if deviation > 0.02:  # 超过MA 2%
        return 'uptrend'
    elif deviation < -0.02:  # 低于MA 2%
        return 'downtrend'
    else:
        return 'neutral'


def _detect_single_candle_pattern(
    candle: Dict,
    trend: str,
    body_min_ratio: float,
    shadow_ratio: float
) -> Dict or None:
    """检测单K线形态"""
    
    # 1. 锤子线（Hammer）- 下跌趋势中出现
    if trend == 'downtrend':
        # 特征：下影线很长，上影线很短，实体小
        if (candle['lower_shadow'] >= candle['body'] * shadow_ratio and
            candle['upper_shadow'] <= candle['body'] * 0.1 and
            candle['body'] > 0):
            return {
                'name': '锤子线',
                'type': SignalType.BUY,
                'strength': SignalStrength.STRONG
            }
    
    # 2. 上吊线（Hanging Man）- 上涨趋势中出现
    if trend == 'uptrend':
        if (candle['lower_shadow'] >= candle['body'] * shadow_ratio and
            candle['upper_shadow'] <= candle['body'] * 0.1 and
            candle['body'] > 0):
            return {
                'name': '上吊线',
                'type': SignalType.SELL,
                'strength': SignalStrength.WEAK  # 需要确认
            }
    
    # 3. 倒锤子线（Inverted Hammer）- 下跌趋势中出现
    if trend == 'downtrend':
        if (candle['upper_shadow'] >= candle['body'] * shadow_ratio and
            candle['lower_shadow'] <= candle['body'] * 0.1 and
            candle['body'] > 0):
            return {
                'name': '倒锤子线',
                'type': SignalType.BUY,
                'strength': SignalStrength.WEAK  # 需要确认
            }
    
    # 4. 流星线（Shooting Star）- 上涨趋势中出现
    if trend == 'uptrend':
        if (candle['upper_shadow'] >= candle['body'] * shadow_ratio and
            candle['lower_shadow'] <= candle['body'] * 0.1 and
            candle['body'] > 0):
            return {
                'name': '流星线',
                'type': SignalType.SELL,
                'strength': SignalStrength.STRONG
            }
    
    # 5. 十字星（Doji）- 趋势转折信号
    if candle['body_ratio'] < 0.1:  # 实体很小
        if trend == 'uptrend':
            return {
                'name': '十字星',
                'type': SignalType.SELL,
                'strength': SignalStrength.WEAK
            }
        elif trend == 'downtrend':
            return {
                'name': '十字星',
                'type': SignalType.BUY,
                'strength': SignalStrength.WEAK
            }
    
    return None


def _detect_double_candle_pattern(
    prev: Dict,
    curr: Dict,
    trend: str
) -> Dict or None:
    """检测双K线组合形态"""
    
    # 1. 看涨吞没（Bullish Engulfing）
    if (trend == 'downtrend' and
        not prev['is_bullish'] and  # 前一根是阴线
        curr['is_bullish'] and      # 当前是阳线
        curr['open'] < prev['close'] and  # 当前开盘低于前一根收盘
        curr['close'] > prev['open']):    # 当前收盘高于前一根开盘
        return {
            'name': '看涨吞没',
            'type': SignalType.BUY,
            'strength': SignalStrength.STRONG
        }
    
    # 2. 看跌吞没（Bearish Engulfing）
    if (trend == 'uptrend' and
        prev['is_bullish'] and      # 前一根是阳线
        not curr['is_bullish'] and  # 当前是阴线
        curr['open'] > prev['close'] and  # 当前开盘高于前一根收盘
        curr['close'] < prev['open']):    # 当前收盘低于前一根开盘
        return {
            'name': '看跌吞没',
            'type': SignalType.SELL,
            'strength': SignalStrength.STRONG
        }
    
    # 3. 乌云盖顶（Dark Cloud Cover）
    if (trend == 'uptrend' and
        prev['is_bullish'] and      # 前一根是大阳线
        not curr['is_bullish'] and  # 当前是阴线
        prev['body'] > prev['total_range'] * 0.6 and  # 前一根实体够大
        curr['open'] > prev['high'] and  # 当前开盘高于前一根最高
        curr['close'] < (prev['open'] + prev['close']) / 2):  # 收盘在前一根实体中部以下
        return {
            'name': '乌云盖顶',
            'type': SignalType.SELL,
            'strength': SignalStrength.STRONG
        }
    
    # 4. 刺透形态（Piercing Pattern）
    if (trend == 'downtrend' and
        not prev['is_bullish'] and  # 前一根是大阴线
        curr['is_bullish'] and      # 当前是阳线
        prev['body'] > prev['total_range'] * 0.6 and  # 前一根实体够大
        curr['open'] < prev['low'] and  # 当前开盘低于前一根最低
        curr['close'] > (prev['open'] + prev['close']) / 2):  # 收盘在前一根实体中部以上
        return {
            'name': '刺透形态',
            'type': SignalType.BUY,
            'strength': SignalStrength.STRONG
        }
    
    return None


def _detect_triple_candle_pattern(
    candle1: Dict,
    candle2: Dict,
    candle3: Dict,
    trend: str
) -> Dict or None:
    """检测三K线组合形态"""
    
    # 1. 晨星（Morning Star）
    if (trend == 'downtrend' and
        not candle1['is_bullish'] and  # 第一根是大阴线
        candle1['body'] > candle1['total_range'] * 0.6 and
        candle2['body'] < candle2['total_range'] * 0.3 and  # 第二根实体小
        candle3['is_bullish'] and      # 第三根是大阳线
        candle3['body'] > candle3['total_range'] * 0.6 and
        candle3['close'] > (candle1['open'] + candle1['close']) / 2):  # 第三根收盘进入第一根实体
        return {
            'name': '晨星',
            'type': SignalType.BUY,
            'strength': SignalStrength.STRONG
        }
    
    # 2. 黄昏星（Evening Star）
    if (trend == 'uptrend' and
        candle1['is_bullish'] and      # 第一根是大阳线
        candle1['body'] > candle1['total_range'] * 0.6 and
        candle2['body'] < candle2['total_range'] * 0.3 and  # 第二根实体小
        not candle3['is_bullish'] and  # 第三根是大阴线
        candle3['body'] > candle3['total_range'] * 0.6 and
        candle3['close'] < (candle1['open'] + candle1['close']) / 2):  # 第三根收盘进入第一根实体
        return {
            'name': '黄昏星',
            'type': SignalType.SELL,
            'strength': SignalStrength.STRONG
        }
    
    # 3. 三只白兵（Three White Soldiers）
    if (candle1['is_bullish'] and candle2['is_bullish'] and candle3['is_bullish'] and
        candle2['close'] > candle1['close'] and  # 收盘价递增
        candle3['close'] > candle2['close'] and
        candle2['open'] > candle1['open'] and candle2['open'] < candle1['close'] and  # 开盘在前一根实体内
        candle3['open'] > candle2['open'] and candle3['open'] < candle2['close'] and
        candle1['upper_shadow'] < candle1['body'] * 0.3 and  # 上影线较短
        candle2['upper_shadow'] < candle2['body'] * 0.3 and
        candle3['upper_shadow'] < candle3['body'] * 0.3):
        return {
            'name': '三只白兵',
            'type': SignalType.BUY,
            'strength': SignalStrength.STRONG
        }
    
    # 4. 三只乌鸦（Three Black Crows）
    if (not candle1['is_bullish'] and not candle2['is_bullish'] and not candle3['is_bullish'] and
        candle2['close'] < candle1['close'] and  # 收盘价递减
        candle3['close'] < candle2['close'] and
        candle2['open'] < candle1['open'] and candle2['open'] > candle1['close'] and  # 开盘在前一根实体内
        candle3['open'] < candle2['open'] and candle3['open'] > candle2['close'] and
        candle1['lower_shadow'] < candle1['body'] * 0.3 and  # 下影线较短
        candle2['lower_shadow'] < candle2['body'] * 0.3 and
        candle3['lower_shadow'] < candle3['body'] * 0.3):
        return {
            'name': '三只乌鸦',
            'type': SignalType.SELL,
            'strength': SignalStrength.STRONG
        }
    
    return None


# ================== 融合策略 ==================

class FusionStrategy(BaseStrategy):
    """
    融合策略 - 综合多个策略的信号

    支持三种融合模式：
    1. 投票模式（voting）：多数策略达成一致才触发
    2. 加权模式（weighted）：根据策略权重计算综合得分
    3. 自适应模式（adaptive）：根据市场环境动态选择策略组合
    """

    def __init__(
        self,
        mode: str = 'voting',
        min_consensus: int = 3,
        weights: Dict[str, float] = None,
        threshold: float = 3.0,
        enable_market_detection: bool = False
    ):
        super().__init__("融合策略")
        self.mode = mode  # 'voting', 'weighted', 'adaptive'
        self.min_consensus = min_consensus  # 投票模式：最小一致策略数
        self.weights = weights or self._get_default_weights()  # 加权模式：策略权重
        self.threshold = threshold  # 加权模式：触发阈值
        self.enable_market_detection = enable_market_detection  # 是否启用市场检测

    def _get_default_weights(self) -> Dict[str, float]:
        """获取默认权重配置（平衡型）"""
        return {
            'macd': 1.0,
            'sma': 1.0,
            'turtle': 1.0,
            'cbr': 1.0,
            'rsi': 1.0,
            'boll': 1.0,
            'kdj': 1.0,
            'candle': 1.0
        }

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成融合信号

        Args:
            df: 股票历史数据

        Returns:
            融合后的信号结果
        """
        # 获取所有基础策略的信号
        all_strategy_signals = self._collect_all_strategy_signals(df)

        # 根据模式选择融合方法
        if self.mode == 'voting':
            fusion_signals = self._voting_fusion(all_strategy_signals)
        elif self.mode == 'weighted':
            fusion_signals = self._weighted_fusion(all_strategy_signals)
        elif self.mode == 'adaptive':
            fusion_signals = self._adaptive_fusion(df, all_strategy_signals)
        else:
            raise ValueError(f"未知的融合模式: {self.mode}")

        return StrategyResult(
            strategy_type=StrategyType.FUSION_STRATEGY,
            signals=fusion_signals,
            metadata={
                "description": f"融合策略 - {self.mode}模式",
                "mode": self.mode,
                "min_consensus": self.min_consensus if self.mode == 'voting' else None,
                "weights": self.weights if self.mode in ['weighted', 'adaptive'] else None,
                "threshold": self.threshold if self.mode == 'weighted' else None
            }
        )

    def _collect_all_strategy_signals(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """收集所有策略的信号"""
        strategies = {
            'M': MACDStrategy(),
            'S': SMAStrategy(),
            'T': TurtleStrategy(),
            'C': CBRStrategy(),
            'R': RSIStrategy(),
            'B': BollingerStrategy(),
            'K': KDJStrategy(),
            'CS': CandlestickStrategy()
        }

        all_signals = {}
        for code, strategy in strategies.items():
            try:
                result = strategy.generate_signals(df)
                all_signals[code] = result.signals
            except Exception as e:
                # 如果某个策略失败，记录但继续
                all_signals[code] = []

        return all_signals

    def _voting_fusion(self, all_strategy_signals: Dict[str, List[Dict]]) -> List[Dict]:
        """
        投票融合：多个策略达成一致才发出信号

        Args:
            all_strategy_signals: 所有策略的信号字典 {strategy_code: signals}

        Returns:
            融合后的信号列表
        """
        # 按日期分组统计
        date_signals = {}

        for strategy_code, signals in all_strategy_signals.items():
            for signal in signals:
                date = signal['date']
                if date not in date_signals:
                    date_signals[date] = {'BUY': [], 'SELL': []}

                signal_type = 'BUY' if signal['type'] == SignalType.BUY else 'SELL'
                date_signals[date][signal_type].append({
                    'strategy': strategy_code,
                    'strength': signal['strength'],
                    'pattern': signal.get('pattern_name', ''),
                    'price': signal.get('price', 0)
                })

        # 生成融合信号
        fusion_signals = []

        for date, signals in date_signals.items():
            # 买入信号投票
            if len(signals['BUY']) >= self.min_consensus:
                strength = self._calculate_consensus_strength(signals['BUY'])
                avg_price = sum(s['price'] for s in signals['BUY']) / len(signals['BUY'])

                fusion_signals.append({
                    'date': date,
                    'price': avg_price,
                    'type': SignalType.BUY,
                    'strength': strength,
                    'consensus_count': len(signals['BUY']),
                    'details': '、'.join([
                        f"{StrategyType.lookup(s['strategy']).text}({s['strength'].display_name})"
                        for s in signals['BUY']
                        if StrategyType.lookup(s['strategy'])
                    ])
                })

            # 卖出信号投票
            if len(signals['SELL']) >= self.min_consensus:
                strength = self._calculate_consensus_strength(signals['SELL'])
                avg_price = sum(s['price'] for s in signals['SELL']) / len(signals['SELL'])

                fusion_signals.append({
                    'date': date,
                    'price': avg_price,
                    'type': SignalType.SELL,
                    'strength': strength,
                    'consensus_count': len(signals['SELL']),
                    'details': '、'.join([
                        f"{StrategyType.lookup(s['strategy']).text}({s['strength'].display_name})"
                        for s in signals['SELL']
                        if StrategyType.lookup(s['strategy'])
                    ])
                })

        return fusion_signals

    def _weighted_fusion(self, all_strategy_signals: Dict[str, List[Dict]]) -> List[Dict]:
        """
        加权融合：根据策略权重计算综合得分

        Args:
            all_strategy_signals: 所有策略的信号字典

        Returns:
            融合后的信号列表
        """
        date_scores = {}

        for strategy_code, signals in all_strategy_signals.items():
            weight = self.weights.get(strategy_code, 1.0)

            for signal in signals:
                date = signal['date']
                if date not in date_scores:
                    date_scores[date] = {
                        'BUY': {'score': 0, 'details': [], 'prices': []},
                        'SELL': {'score': 0, 'details': [], 'prices': []}
                    }

                # 信号强度转换为数值
                strength_value = 2.0 if signal['strength'] == SignalStrength.STRONG else 1.0

                # 计算加权得分
                score = strength_value * weight

                signal_type = 'BUY' if signal['type'] == SignalType.BUY else 'SELL'
                date_scores[date][signal_type]['score'] += score
                date_scores[date][signal_type]['details'].append({
                    'strategy': strategy_code,
                    'strength': signal['strength'],
                    'weight': weight,
                    'score': score
                })
                date_scores[date][signal_type]['prices'].append(signal.get('price', 0))

        # 生成融合信号
        fusion_signals = []

        for date, scores in date_scores.items():
            # 买入信号
            if scores['BUY']['score'] >= self.threshold:
                strength = SignalStrength.STRONG if scores['BUY']['score'] >= 5.0 else SignalStrength.WEAK
                avg_price = sum(scores['BUY']['prices']) / len(scores['BUY']['prices']) if scores['BUY']['prices'] else 0

                fusion_signals.append({
                    'date': date,
                    'price': avg_price,
                    'type': SignalType.BUY,
                    'strength': strength,
                    'score': scores['BUY']['score'],
                    'details': '、'.join([
                        f"{StrategyType.lookup(d['strategy']).text}(权重{d['weight']:.1f}×{d['strength'].display_name}={d['score']:.1f})"
                        for d in scores['BUY']['details']
                        if StrategyType.lookup(d['strategy'])
                    ])
                })

            # 卖出信号
            if scores['SELL']['score'] >= self.threshold:
                strength = SignalStrength.STRONG if scores['SELL']['score'] >= 5.0 else SignalStrength.WEAK
                avg_price = sum(scores['SELL']['prices']) / len(scores['SELL']['prices']) if scores['SELL']['prices'] else 0

                fusion_signals.append({
                    'date': date,
                    'price': avg_price,
                    'type': SignalType.SELL,
                    'strength': strength,
                    'score': scores['SELL']['score'],
                    'details': '、'.join([
                        f"{StrategyType.lookup(d['strategy']).text}(权重{d['weight']:.1f}×{d['strength'].display_name}={d['score']:.1f})"
                        for d in scores['SELL']['details']
                        if StrategyType.lookup(d['strategy'])
                    ])
                })

        return fusion_signals

    def _adaptive_fusion(self, df: pd.DataFrame, all_strategy_signals: Dict[str, List[Dict]]) -> List[Dict]:
        """
        自适应融合：根据市场环境动态调整策略权重

        Args:
            df: 股票数据
            all_strategy_signals: 所有策略的信号字典

        Returns:
            融合后的信号列表
        """
        # 检测市场状态
        market_state = detect_market_state(df)

        # 根据市场状态调整权重
        if market_state == 'trending':
            # 趋势市场：侧重趋势跟随策略
            adaptive_weights = {
                'macd': 2.0,
                'sma': 2.0,
                'turtle': 1.5,
                'cbr': 1.0,
                'rsi': 0.5,
                'boll': 0.5,
                'kdj': 0.5,
                'candle': 1.0
            }
        else:
            # 震荡市场：侧重反转策略
            adaptive_weights = {
                'macd': 0.5,
                'sma': 0.5,
                'turtle': 0.5,
                'cbr': 0.5,
                'rsi': 2.0,
                'boll': 2.0,
                'kdj': 2.0,
                'candle': 1.5
            }

        # 使用自适应权重进行加权融合
        original_weights = self.weights
        self.weights = adaptive_weights
        result = self._weighted_fusion(all_strategy_signals)
        self.weights = original_weights  # 恢复原始权重

        # 在信号详情中添加市场状态信息
        for signal in result:
            signal['market_state'] = '趋势市场' if market_state == 'trending' else '震荡市场'

        return result

    def _calculate_consensus_strength(self, signals: List[Dict]) -> SignalStrength:
        """
        计算一致信号的强度

        Args:
            signals: 同一日期的信号列表

        Returns:
            综合强度
        """
        strong_count = sum(1 for s in signals if s['strength'] == SignalStrength.STRONG)
        total_count = len(signals)

        # 如果超过一半是强信号，则判定为强
        if strong_count / total_count >= 0.5:
            return SignalStrength.STRONG
        else:
            return SignalStrength.WEAK


def detect_market_state(df: pd.DataFrame, window: int = 20) -> str:
    """
    检测市场状态：趋势 or 震荡

    使用ADX（平均趋向指数）判断：
    - ADX > 25：趋势市场
    - ADX <= 25：震荡市场

    Args:
        df: 股票数据
        window: 检测窗口期

    Returns:
        'trending' 或 'ranging'
    """
    if len(df) < window + 1:
        return 'ranging'  # 数据不足，默认震荡

    try:
        high = df['highest']
        low = df['lowest']
        close = df['closing']

        # 计算+DM和-DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        # 计算TR（真实波幅）
        tr_list = []
        for i in range(len(df)):
            if i == 0:
                tr_list.append(high.iloc[i] - low.iloc[i])
            else:
                tr = max(
                    high.iloc[i] - low.iloc[i],
                    abs(high.iloc[i] - close.iloc[i-1]),
                    abs(low.iloc[i] - close.iloc[i-1])
                )
                tr_list.append(tr)

        tr = pd.Series(tr_list, index=df.index)

        # 计算ATR
        atr = tr.rolling(window).mean()

        # 计算+DI和-DI
        plus_di = 100 * (plus_dm.rolling(window).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window).mean() / atr)

        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)  # 避免除零
        adx = dx.rolling(window).mean()

        # 获取最新的ADX值
        latest_adx = adx.iloc[-1]

        if pd.isna(latest_adx):
            return 'ranging'

        # ADX > 25 为趋势市场
        if latest_adx > 25:
            return 'trending'
        else:
            return 'ranging'

    except Exception as e:
        # 如果计算失败，默认返回震荡市场
        return 'ranging'
