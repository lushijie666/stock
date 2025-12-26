
from typing import List, Dict

import pandas as pd


from enums.signal import SignalStrength
from enums.strategy import StrategyType, FusionStrategyModel

from utils.strategy import StrategyResult, MACDStrategy, SMAStrategy, TurtleStrategy, CBRStrategy, RSIStrategy, \
    BollingerStrategy, KDJStrategy, CandlestickStrategy, FusionStrategy


def calculate_all_signals(
    df: pd.DataFrame,
    strategies: List[StrategyType] = None,
    merge_and_filter: bool = True,
    fusion_config: Dict = None
) -> List[Dict]:
    """
    计算所有策略的信号并合并为一个信号列表

    Args:
        df: 股票数据DataFrame
        strategies: 要计算的策略列表，如果为None则计算所有策略
        merge_and_filter: 是否对信号进行合并和过滤处理
        fusion_config: 融合策略配置字典，包含mode、min_consensus、weights、threshold等

    Returns:
        List[Dict]: 合并后的信号列表
    """
    # 获取各策略的信号结果
    strategy_results = calculate_all_signals_by_strategy(df, strategies, False, fusion_config)
    # 收集所有信号
    all_signals = []
    for strategy_type, result in strategy_results.items():
        if result.signals:
            # 为每个信号添加策略来源信息
            for signal in result.signals:
                signal_copy = signal.copy()
                signal_copy['strategy'] = strategy_type
                all_signals.append(signal_copy)
    # 如果需要，对所有信号进行合并和过滤处理
    if merge_and_filter and all_signals:
        # 合并同一天的信号
        merged_signals = merge_signals_by_date(all_signals)
        # 按日期排序
        merged_signals.sort(key=lambda x: x['date'])
        # 过滤连续信号
        filtered_signals = filter_consecutive_signals(merged_signals)

        # 为每个信号添加策略显示文本
        for signal in filtered_signals:
            if 'strategies' in signal:
                strategy_codes = [s.code for s in signal['strategies']]
                signal['strategy_code'] = f"{','.join(strategy_codes)}"
            elif 'strategy' in signal:
                signal['strategy_code'] = f"{signal['strategy'].code}"

        return filtered_signals

    # 为未合并的信号也添加策略显示文本
    for signal in all_signals:
        signal['strategy_code'] = f"{signal['strategy'].code}"

    # 按日期排序后返回
    all_signals.sort(key=lambda x: x['date'])
    return all_signals


def calculate_all_signals_by_strategy(
    df: pd.DataFrame,
    strategies: List[StrategyType] = None,
    merge_and_filter: bool = True,
    fusion_config: Dict = None
) -> Dict[StrategyType, StrategyResult]:
    """
    根据指定策略计算信号

    Args:
        df: 股票数据DataFrame
        strategies: 要计算的策略列表，如果为None则计算所有策略
        merge_and_filter: 是否对信号进行合并和过滤处理
        fusion_config: 融合策略配置字典

    Returns:
        Dict[StrategyType, StrategyResult]: 各策略的计算结果
    """
    if 'date' in df.columns:
        df = df.sort_values('date').reset_index(drop=True) # 按日期从小到大排序

    if strategies is None:
        strategies = StrategyType.all_strategies()

    # 根据 fusion_config 创建融合策略实例
    if fusion_config:
        mode = fusion_config.get('mode', FusionStrategyModel.VOTING_MODEL)
        min_consensus = fusion_config.get('min_consensus')
        weights = fusion_config.get('weights')
        threshold = fusion_config.get('threshold')
        fusion_strategy = FusionStrategy(
            mode=mode,
            min_consensus=min_consensus,
            weights=weights,
            threshold=threshold
        )
    else:
        fusion_strategy = FusionStrategy(mode=FusionStrategyModel.VOTING_MODEL, min_consensus=2)

    strategy_map = {
        StrategyType.MACD_STRATEGY: MACDStrategy(),
        StrategyType.SMA_STRATEGY: SMAStrategy(),
        StrategyType.TURTLE_STRATEGY: TurtleStrategy(),
        StrategyType.CBR_STRATEGY: CBRStrategy(),
        StrategyType.RSI_STRATEGY: RSIStrategy(),
        StrategyType.BOLL_STRATEGY: BollingerStrategy(),
        StrategyType.KDJ_STRATEGY: KDJStrategy(),
        StrategyType.CANDLESTICK_STRATEGY: CandlestickStrategy(),
        StrategyType.FUSION_STRATEGY: fusion_strategy,
    }

    results = {}
    for strategy_type in strategies:
        if strategy_type in strategy_map:
            strategy = strategy_map[strategy_type]
            result = strategy.generate_signals(df)

            # 如果需要，对信号进行合并和过滤处理
            if merge_and_filter and result.signals:
                # 合并同一天的信号
                merged_signals = merge_signals_by_date(result.signals)
                # 按日期排序
                merged_signals.sort(key=lambda x: x['date'])
                # 过滤连续信号
                filtered_signals = filter_consecutive_signals(merged_signals)
                # 更新结果
                result.signals = filtered_signals

            results[strategy_type] = result
    return results


def merge_signals_by_date(signals: List[Dict]) -> List[Dict]:
    """
    合并同一天的信号，优先选择强信号

    Args:
        signals: 信号列表

    Returns:
        List[Dict]: 合并后的信号列表
    """
    if not signals:
        return signals

    # 按日期分组信号
    signals_by_time = {}
    for signal in signals:
        # 使用完整的时间戳作为键，确保30分钟数据能被正确区分
        if hasattr(signal['date'], 'strftime'):
            time_key = signal['date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_key = str(signal['date'])
        if time_key not in signals_by_time:
            signals_by_time[time_key] = []
        signals_by_time[time_key].append(signal)

    # 对每天的信号进行合并
    merged_signals = []
    for date_key, date_signals in signals_by_time.items():
        if len(date_signals) == 1:
            merged_signals.append(date_signals[0])
        else:
            # 多个信号的处理策略：
            # 1. 优先选择强信号
            strong_signals = [s for s in date_signals if s['strength'] == SignalStrength.STRONG]
            if strong_signals:
                merged_signal = strong_signals[0].copy()
                if len(strong_signals) > 1:
                    # 如果有多个强信号，收集所有策略
                    strategies = [s['strategy'] for s in strong_signals]
                    merged_signal['strategies'] = strategies
                merged_signals.append(merged_signal)
            else:
                # 2. 如果都是弱信号，选择第一个，并保留策略信息
                weak_signal = date_signals[0].copy()
                if len(date_signals) > 1:
                    # 如果有多个弱信号，收集所有策略
                    strategies = [s['strategy'] for s in date_signals]
                    weak_signal['strategies'] = strategies
                merged_signals.append(weak_signal)
    return merged_signals


def filter_consecutive_signals(signals: List[Dict]) -> List[Dict]:
    """
    过滤连续信号的策略

    Args:
        signals: 已按日期排序的信号列表

    Returns:
        List[Dict]: 过滤后的信号列表
    """
    if len(signals) <= 1:
        return signals

    filtered_signals = [signals[0]]

    for i in range(1, len(signals)):
        current_signal = signals[i]
        previous_signal = filtered_signals[-1]

        # 信号过滤规则：
        # 1. 信号类型改变时保留
        # 2. 强信号总是保留
        # 3. 相同类型信号间隔超过3天时保留

        should_keep = False

        # 规则1：信号类型不同则保留
        if current_signal['type'] != previous_signal['type']:
            should_keep = True
        # 规则2：强信号总是保留
        elif current_signal['strength'] == SignalStrength.STRONG:
            should_keep = True
        # 规则3：相同类型信号间隔超过3天则保留
        else:
            # 使用精确的时间差计算
            if hasattr(current_signal['date'], 'timestamp') and hasattr(previous_signal['date'], 'timestamp'):
                # 计算秒级时间差
                time_diff_seconds = current_signal['date'].timestamp() - previous_signal['date'].timestamp()
                # 对于30分钟数据，如果间隔超过2小时(7200秒)则保留
                if time_diff_seconds > 7200:
                    should_keep = True
            else:
                # 兜底方案：按天计算
                try:
                    date_diff = (current_signal['date'] - previous_signal['date']).days
                    if date_diff > 1:
                        should_keep = True
                except:
                    pass
        if should_keep:
            filtered_signals.append(current_signal)

    return filtered_signals
