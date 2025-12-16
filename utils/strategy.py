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
    计算策略指标
    """
    if not signals:
        return None

    # 按日期排序
    signals = sorted(signals, key=lambda x: x['date'])

    # 计算胜率
    buy_signals = [s for s in signals if s['type'] == SignalType.BUY]
    sell_signals = [s for s in signals if s['type'] == SignalType.SELL]

    # 计算平均持股天数
    holding_periods = []
    buy_dates = {}

    for signal in signals:
        if signal['type'] == SignalType.BUY:
            buy_dates[signal['date']] = signal['price']
        elif signal['type'] == SignalType.SELL and buy_dates:
            # 简单匹配最近的买入信号
            if buy_dates:
                last_buy_date = list(buy_dates.keys())[-1]
                holding_days = (signal['date'] - last_buy_date).days
                if holding_days > 0:
                    holding_periods.append(holding_days)
                del buy_dates[last_buy_date]

    avg_holding_period = sum(holding_periods) / len(holding_periods) if holding_periods else 0

    return {
        'total_signals': len(signals),
        'buy_signals': len(buy_signals),
        'sell_signals': len(sell_signals),
        'avg_holding_period': avg_holding_period
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