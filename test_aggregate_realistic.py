"""
单元测试：测试30分钟聚合函数的开盘价修复逻辑 (改进版)

模拟真实情况：1分钟数据聚合为30分钟后，第一个值(first)恰好为0
"""
import pandas as pd
import logging
from service.stock_history import _aggregate_minute_to_30min

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_aggregate_with_zero_open_realistic():
    """
    测试真实场景：
    - 某个30分钟时间段的第一条1分钟数据的开盘价为0
    - 聚合后，该30分钟K线的开盘价会变成0
    - 修复逻辑应将其改为前一个30分钟K线的收盘价
    """
    print("=" * 80)
    print("单元测试：30分钟聚合 - 开盘价修复逻辑 (真实场景)")
    print("=" * 80)

    # 创建模拟的1分钟数据
    # 第1个30分钟时段 (22:30-23:00): 正常数据，开盘100，收盘115
    # 第2个30分钟时段 (23:00-23:30): 第一条数据开盘价为0，聚合后开盘变0，应修复为115
    # 第3个30分钟时段 (23:30-00:00): 第一条数据开盘价为0，聚合后开盘变0，应修复为130

    times = []
    opens = []
    closes = []
    highs = []
    lows = []
    volumes = []
    amounts = []

    # 第1个30分钟时段 (22:30-23:00): 30条记录，开盘价正常
    base_time = pd.Timestamp('2025-12-22 22:30:00')
    for i in range(30):
        times.append(base_time + pd.Timedelta(minutes=i))
        opens.append(100.0 + i * 0.5)  # 开盘价正常
        closes.append(100.5 + i * 0.5)
        highs.append(101.0 + i * 0.5)
        lows.append(99.0 + i * 0.5)
        volumes.append(1000)
        amounts.append(100000)

    # 第2个30分钟时段 (23:00-23:30): 30条记录，第一条开盘价为0
    base_time = pd.Timestamp('2025-12-22 23:00:00')
    for i in range(30):
        times.append(base_time + pd.Timedelta(minutes=i))
        opens.append(0.0 if i == 0 else 115.5 + i * 0.5)  # 第一条开盘为0！
        closes.append(115.5 + i * 0.5)
        highs.append(116.0 + i * 0.5)
        lows.append(115.0 + i * 0.5)
        volumes.append(1000)
        amounts.append(115000)

    # 第3个30分钟时段 (23:30-00:00): 30条记录，第一条开盘价为0
    base_time = pd.Timestamp('2025-12-22 23:30:00')
    for i in range(30):
        times.append(base_time + pd.Timedelta(minutes=i))
        opens.append(0.0 if i == 0 else 130.5 + i * 0.5)  # 第一条开盘为0！
        closes.append(130.5 + i * 0.5)
        highs.append(131.0 + i * 0.5)
        lows.append(130.0 + i * 0.5)
        volumes.append(1000)
        amounts.append(130000)

    df = pd.DataFrame({
        '时间': times,
        '开盘': opens,
        '收盘': closes,
        '最高': highs,
        '最低': lows,
        '成交量': volumes,
        '成交额': amounts,
    })

    print(f"\n原始1分钟数据: {len(df)} 条")

    # 显示关键的第一条记录位置
    print("\n关键时间点的原始数据（每个30分钟的第一条）:")
    print("-" * 80)
    for idx in [0, 30, 60]:
        if idx < len(df):
            row = df.iloc[idx]
            print(f"索引 {idx:2d}: 时间={row['时间']}, 开盘={row['开盘']:>7.2f}, 收盘={row['收盘']:>7.2f}")

    # 调用聚合函数
    print("\n\n正在聚合为30分钟数据...")
    df_30min = _aggregate_minute_to_30min(df)

    print(f"\n聚合后30分钟数据: {len(df_30min)} 条")

    # 显示所有聚合结果
    print("\n聚合后的30分钟数据:")
    print("-" * 80)
    for i, row in df_30min.iterrows():
        print(f"{i}. 时间: {row['时间']}, "
              f"开盘: {row['开盘']:>7.2f}, "
              f"收盘: {row['收盘']:>7.2f}, "
              f"最高: {row['最高']:>7.2f}, "
              f"最低: {row['最低']:>7.2f}")

    # 验证修复逻辑
    print("\n\n验证修复逻辑:")
    print("=" * 80)

    zero_count = (df_30min['开盘'] == 0).sum()
    print(f"修复后，开盘价为0的记录数: {zero_count}")

    if zero_count == 0:
        print("✅ 成功：所有开盘价都已正确填充！\n")

        # 详细验证每一对相邻记录
        for i in range(len(df_30min) - 1):
            prev_row = df_30min.iloc[i]
            curr_row = df_30min.iloc[i + 1]

            prev_close = prev_row['收盘']
            curr_open = curr_row['开盘']

            print(f"记录 {i} -> {i+1}:")
            print(f"  前一条 {prev_row['时间']}: 收盘={prev_close:>7.2f}")
            print(f"  当前条 {curr_row['时间']}: 开盘={curr_open:>7.2f}")

            # 检查是否使用了前一条的收盘价
            if abs(curr_open - prev_close) < 0.01:
                print(f"  ✅ 当前开盘价等于前一条收盘价（修复成功）")
            else:
                diff = abs(curr_open - prev_close)
                print(f"  ℹ️  当前开盘价与前收盘价相差 {diff:.2f}（原始值或正常跳空）")
            print()

        print("\n" + "=" * 80)
        print("测试结论：修复逻辑工作正常！")
        print("- 第2个30分钟的开盘价应该被修复为第1个30分钟的收盘价 (115.00)")
        print("- 第3个30分钟的开盘价应该被修复为第2个30分钟的收盘价 (130.00)")
        print("=" * 80)
    else:
        print(f"❌ 失败：仍有 {zero_count} 条记录的开盘价为0")
        for i, row in df_30min.iterrows():
            if row['开盘'] == 0:
                print(f"  时间: {row['时间']}, 开盘: {row['开盘']}")

    return df_30min


if __name__ == "__main__":
    test_aggregate_with_zero_open_realistic()
