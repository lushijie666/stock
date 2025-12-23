#!/usr/bin/env python3
"""测试30分钟美股数据获取"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from service.stock_history import _fetch_us_stock_data
from enums.history_type import StockHistoryType

def test_30min_data():
    """测试30分钟数据获取"""

    code = "AAPL"
    end_date = date.today()
    start_date = end_date - timedelta(days=1)  # 获取最近1天的30分钟数据

    print(f"{'='*70}")
    print(f"测试美股30分钟数据获取")
    print(f"股票: {code}")
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"{'='*70}\n")

    try:
        data_list = _fetch_us_stock_data(
            code=code,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            t=StockHistoryType.THIRTY_M
        )

        if data_list:
            print(f"✅ 成功获取 {len(data_list)} 条30分钟数据\n")

            # 显示前5条数据
            print("前5条数据:")
            print("-" * 70)
            for i, item in enumerate(data_list[:5], 1):
                print(f"{i}. 时间: {item.date}")
                print(f"   开盘: {item.opening}, 收盘: {item.closing}")
                print(f"   最高: {item.highest}, 最低: {item.lowest}")
                print(f"   成交量: {item.turnover_count}")
                print(f"   成交额: {item.turnover_amount}")
                print()

            # 显示最后3条数据
            if len(data_list) > 5:
                print("最后3条数据:")
                print("-" * 70)
                for i, item in enumerate(data_list[-3:], len(data_list)-2):
                    print(f"{i}. 时间: {item.date}")
                    print(f"   开盘: {item.opening}, 收盘: {item.closing}")
                    print(f"   最高: {item.highest}, 最低: {item.lowest}")
                    print(f"   成交量: {item.turnover_count}")
                    print(f"   成交额: {item.turnover_amount}")
                    print()
        else:
            print(f"⚠️ 未获取到数据（可能是非交易时段）")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print(f"{'='*70}")
    print("测试完成")
    print(f"{'='*70}")


if __name__ == "__main__":
    test_30min_data()
