"""
测试30分钟数据的开盘价修复逻辑

验证：当开盘价为0时，使用前一条记录的收盘价
"""
import logging
from datetime import date, timedelta
from service.stock_history import _fetch_us_stock_data
from enums.history_type import StockHistoryType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_open_price_fix():
    """测试开盘价修复"""
    print("=" * 60)
    print("测试30分钟数据 - 开盘价修复逻辑")
    print("=" * 60)

    # 测试参数
    code = "105.AAPL"
    end_date = date(2025, 12, 23)
    start_date = end_date - timedelta(days=5)

    print(f"\n股票代码: {code}")
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"数据类型: 30分钟")

    # 获取数据
    try:
        data_list = _fetch_us_stock_data(
            code=code,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            t=StockHistoryType.THIRTY_M
        )

        print(f"\n成功获取 {len(data_list)} 条30分钟数据")

        # 检查开盘价
        zero_open_count = sum(1 for item in data_list if item.opening == 0)
        print(f"\n开盘价为0的记录数: {zero_open_count}")

        if zero_open_count > 0:
            print("\n⚠️  警告：仍有开盘价为0的记录！")
            # 显示前几条开盘价为0的记录
            count = 0
            for item in data_list:
                if item.opening == 0 and count < 5:
                    print(f"  时间: {item.date}, 开盘: {item.opening}, 收盘: {item.closing}")
                    count += 1
        else:
            print("\n✅ 所有开盘价都已正确填充！")

        # 显示前10条数据以供验证
        print(f"\n前10条30分钟数据:")
        print("-" * 100)
        for i, item in enumerate(data_list[:10]):
            print(f"{i+1:2d}. 时间: {item.date:<20} "
                  f"开盘: {item.opening:>8.2f}  "
                  f"收盘: {item.closing:>8.2f}  "
                  f"最高: {item.highest:>8.2f}  "
                  f"最低: {item.lowest:>8.2f}  "
                  f"成交量: {item.volume:>12,}")

        # 验证逻辑：检查相邻记录的开盘价和前一条收盘价的关系
        print(f"\n验证修复逻辑（检查前5对相邻记录）:")
        print("-" * 100)
        for i in range(min(5, len(data_list) - 1)):
            curr = data_list[i + 1]
            prev = data_list[i]
            print(f"记录 {i+1}->{i+2}:")
            print(f"  前一条收盘: {prev.closing:>8.2f}")
            print(f"  当前开盘:   {curr.opening:>8.2f}")

            # 如果当前开盘价等于前一条收盘价，说明可能是修复后的结果
            if abs(curr.opening - prev.closing) < 0.01:
                print(f"  ✓ 当前开盘价可能使用了前一条收盘价")
            else:
                print(f"  ℹ 当前开盘价是原始值")

    except Exception as e:
        print(f"\n❌ 获取数据失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_open_price_fix()
