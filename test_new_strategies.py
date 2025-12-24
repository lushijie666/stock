"""
测试新增的交易策略

验证RSI、布林带、KDJ策略是否正常工作
"""
import pandas as pd
from datetime import datetime, timedelta
from utils.strategy import (
    RSIStrategy,
    BollingerStrategy,
    KDJStrategy,
    calculate_strategy_metrics
)

def create_test_data():
    """创建测试数据"""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
    # 模拟股票数据：先涨后跌
    prices = [100 + i * 0.5 for i in range(50)] + [125 - i * 0.5 for i in range(50)]

    df = pd.DataFrame({
        'date': dates,
        'opening': prices,
        'highest': [p * 1.02 for p in prices],
        'lowest': [p * 0.98 for p in prices],
        'closing': prices
    })
    return df

def test_rsi_strategy():
    """测试RSI策略"""
    print("=" * 80)
    print("测试RSI策略（相对强弱指标）")
    print("=" * 80)

    df = create_test_data()
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    result = strategy.generate_signals(df)

    print(f"\n策略名称: {strategy.name}")
    print(f"策略类型: {result.strategy_type.fullText}")
    print(f"生成信号数: {len(result.signals)}")
    print(f"元数据: {result.metadata}")

    if result.signals:
        print(f"\n前5个信号:")
        for i, signal in enumerate(result.signals[:5]):
            print(f"  {i+1}. 日期: {signal['date']}, "
                  f"类型: {signal['type'].display_name}, "
                  f"强度: {'🔥强' if signal['strength'].value == 'strong' else '🥀弱'}, "
                  f"价格: {signal['price']:.2f}")

    # 计算策略指标
    if result.signals:
        metrics = calculate_strategy_metrics(df, result.signals)
        print(f"\n策略指标:")
        print(f"  胜率: {metrics['win_rate']:.1f}%")
        print(f"  盈亏比: {metrics['profit_loss_ratio']:.2f}")
        print(f"  总交易: {metrics['total_trades']}次")
        print(f"  盈利交易: {metrics['winning_trades']}次")
        print(f"  亏损交易: {metrics['losing_trades']}次")

    print(f"\n✅ RSI策略测试完成\n")

def test_bollinger_strategy():
    """测试布林带策略"""
    print("=" * 80)
    print("测试布林带策略（Bollinger Bands）")
    print("=" * 80)

    df = create_test_data()
    strategy = BollingerStrategy(period=20, std_dev=2.0)
    result = strategy.generate_signals(df)

    print(f"\n策略名称: {strategy.name}")
    print(f"策略类型: {result.strategy_type.fullText}")
    print(f"生成信号数: {len(result.signals)}")
    print(f"元数据: {result.metadata}")

    if result.signals:
        print(f"\n前5个信号:")
        for i, signal in enumerate(result.signals[:5]):
            print(f"  {i+1}. 日期: {signal['date']}, "
                  f"类型: {signal['type'].display_name}, "
                  f"强度: {'🔥强' if signal['strength'].value == 'strong' else '🥀弱'}, "
                  f"价格: {signal['price']:.2f}")

    print(f"\n✅ 布林带策略测试完成\n")

def test_kdj_strategy():
    """测试KDJ策略"""
    print("=" * 80)
    print("测试KDJ策略（随机指标）")
    print("=" * 80)

    df = create_test_data()
    strategy = KDJStrategy(n=9, m1=3, m2=3)
    result = strategy.generate_signals(df)

    print(f"\n策略名称: {strategy.name}")
    print(f"策略类型: {result.strategy_type.fullText}")
    print(f"生成信号数: {len(result.signals)}")
    print(f"元数据: {result.metadata}")

    if result.signals:
        print(f"\n前5个信号:")
        for i, signal in enumerate(result.signals[:5]):
            print(f"  {i+1}. 日期: {signal['date']}, "
                  f"类型: {signal['type'].display_name}, "
                  f"强度: {'🔥强' if signal['strength'].value == 'strong' else '🥀弱'}, "
                  f"价格: {signal['price']:.2f}")

    print(f"\n✅ KDJ策略测试完成\n")

def test_all_strategies():
    """测试所有新策略"""
    print("\n" + "=" * 80)
    print(" 新增交易策略测试")
    print("=" * 80 + "\n")

    test_rsi_strategy()
    test_bollinger_strategy()
    test_kdj_strategy()

    print("=" * 80)
    print("所有策略测试完成！")
    print("=" * 80)
    print("\n总结:")
    print("✅ RSI策略（相对强弱指标）- 超买超卖判断")
    print("✅ 布林带策略（Bollinger Bands）- 价格偏离通道")
    print("✅ KDJ策略（随机指标）- 灵敏的买卖点")
    print("\n现在可以在回测分析中使用这些策略！")

if __name__ == "__main__":
    test_all_strategies()
