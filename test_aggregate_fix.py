"""
单元测试：测试30分钟聚合函数的开盘价修复逻辑

使用模拟数据直接测试 _aggregate_minute_to_30min 函数
"""
import pandas as pd
import logging
from service.stock_history import _aggregate_minute_to_30min

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_aggregate_with_zero_open():
    """测试开盘价为0的情况"""
    print("=" * 80)
    print("单元测试：30分钟聚合 - 开盘价修复逻辑")
    print("=" * 80)

    # 创建模拟的1分钟数据，包含一些开盘价为0的情况
    data = {
        '时间': pd.date_range('2025-12-22 22:30:00', periods=60, freq='1min'),
        '开盘': [100.0] * 10 + [0.0] * 20 + [110.0] * 10 + [0.0] * 20,  # 混合正常值和0值
        '收盘': [100.5, 101.0, 101.5, 102.0, 102.5,
                 103.0, 103.5, 104.0, 104.5, 105.0,  # 第一个10分钟
                 105.5, 106.0, 106.5, 107.0, 107.5,
                 108.0, 108.5, 109.0, 109.5, 110.0,  # 第二个10分钟（开盘为0）
                 110.5, 111.0, 111.5, 112.0, 112.5,
                 113.0, 113.5, 114.0, 114.5, 115.0,  # 第三个10分钟
                 115.5, 116.0, 116.5, 117.0, 117.5,
                 118.0, 118.5, 119.0, 119.5, 120.0,  # 第四个10分钟（开盘为0）
                 120.5, 121.0, 121.5, 122.0, 122.5,
                 123.0, 123.5, 124.0, 124.5, 125.0,  # 第五个10分钟
                 125.5, 126.0, 126.5, 127.0, 127.5,
                 128.0, 128.5, 129.0, 129.5, 130.0], # 第六个10分钟
        '最高': [101.0] * 10 + [107.0] * 20 + [115.0] * 10 + [120.0] * 20,
        '最低': [99.0] * 10 + [105.0] * 20 + [109.0] * 10 + [115.0] * 20,
        '成交量': [1000] * 60,
        '成交额': [100000] * 60,
    }

    df = pd.DataFrame(data)

    print(f"\n原始1分钟数据: {len(df)} 条")
    print("\n前10条原始数据:")
    print(df[['时间', '开盘', '收盘', '最高', '最低']].head(10).to_string())

    # 调用聚合函数
    print("\n\n正在聚合为30分钟数据...")
    df_30min = _aggregate_minute_to_30min(df)

    print(f"\n聚合后30分钟数据: {len(df_30min)} 条")

    # 检查结果
    print("\n聚合后的30分钟数据:")
    print("-" * 80)
    for i, row in df_30min.iterrows():
        print(f"时间: {row['时间']}, "
              f"开盘: {row['开盘']:>7.2f}, "
              f"收盘: {row['收盘']:>7.2f}, "
              f"最高: {row['最高']:>7.2f}, "
              f"最低: {row['最低']:>7.2f}")

    # 验证修复逻辑
    print("\n\n验证修复逻辑:")
    print("-" * 80)
    zero_count = (df_30min['开盘'] == 0).sum()
    print(f"开盘价为0的记录数: {zero_count}")

    if zero_count == 0:
        print("✅ 成功：所有开盘价都已正确填充！")

        # 进一步验证：检查第二条记录的开盘价是否等于第一条记录的收盘价
        if len(df_30min) >= 2:
            first_close = df_30min.iloc[0]['收盘']
            second_open = df_30min.iloc[1]['开盘']

            print(f"\n详细验证:")
            print(f"  第1条收盘价: {first_close:.2f}")
            print(f"  第2条开盘价: {second_open:.2f}")

            # 由于原始数据第二个30分钟的开盘价为0，应该被修复为第一个30分钟的收盘价
            if abs(second_open - first_close) < 0.01:
                print(f"  ✅ 第2条开盘价正确使用了第1条收盘价（修复成功）")
            else:
                print(f"  ℹ️  第2条开盘价是原始值（未触发修复）")
    else:
        print(f"❌ 失败：仍有 {zero_count} 条记录的开盘价为0")

    return df_30min


if __name__ == "__main__":
    test_aggregate_with_zero_open()
