#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试美股数据获取功能更新

主要测试：
1. 使用 ak.stock_us_famous_spot_em 获取美股数据
2. 验证前缀存储到 full_name 字段
3. 验证历史数据获取时从 full_name 提取前缀
"""

import sys
import logging
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_fetch_us_stocks():
    """测试美股列表获取"""
    print("\n" + "="*80)
    print("测试1: 获取美股列表")
    print("="*80)

    from enums.category import Category
    from service.stock import fetch

    try:
        data = fetch(Category.US_XX)
        if data:
            print(f"\n✅ 成功获取 {len(data)} 只美股")
            print(f"\n前5只股票信息:")
            for i, stock in enumerate(data[:5], 1):
                print(f"{i}. 代码: {stock.code}, 名称: {stock.name}, 全称: {stock.full_name}, 行业: {stock.industry}")

            # 检查前缀信息
            print(f"\n检查前缀信息（full_name格式）:")
            prefixes = {}
            for stock in data:
                if stock.full_name and '(' in stock.full_name:
                    import re
                    match = re.search(r'\((\d+)\)$', stock.full_name)
                    if match:
                        prefix = match.group(1)
                        prefixes[prefix] = prefixes.get(prefix, 0) + 1

            if prefixes:
                print(f"发现的前缀分布:")
                for prefix, count in sorted(prefixes.items()):
                    print(f"  前缀 {prefix}: {count} 只股票")
            else:
                print("⚠️  未发现任何前缀信息")

            # 检查行业分布
            print(f"\n行业分布:")
            industries = {}
            for stock in data:
                ind = stock.industry or "未分类"
                industries[ind] = industries.get(ind, 0) + 1

            for industry, count in sorted(industries.items()):
                print(f"  {industry}: {count} 只")

            return True
        else:
            print("❌ 未获取到任何数据")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_save_us_stocks():
    """测试保存美股到数据库"""
    print("\n" + "="*80)
    print("测试2: 保存美股到数据库")
    print("="*80)

    from enums.category import Category
    from service.stock import reload

    try:
        result = reload(Category.US_XX)
        print(f"✅ 保存完成")
        return True
    except Exception as e:
        print(f"❌ 保存失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_query_us_stock_prefix():
    """测试从数据库查询美股前缀"""
    print("\n" + "="*80)
    print("测试3: 从数据库查询美股前缀信息")
    print("="*80)

    from utils.db import get_db_session
    from models.stock import Stock
    from enums.category import Category

    try:
        with get_db_session() as session:
            stocks = session.query(Stock).filter(
                Stock.category == Category.US_XX,
                Stock.removed == False
            ).limit(10).all()

            if stocks:
                print(f"\n查询到 {len(stocks)} 只美股（显示前10只）:")
                import re
                for i, stock in enumerate(stocks, 1):
                    prefix = "未找到"
                    if stock.full_name:
                        match = re.search(r'\((\d+)\)$', stock.full_name)
                        if match:
                            prefix = match.group(1)

                    print(f"{i}. {stock.code:8s} | {stock.name:15s} | 前缀: {prefix} | "
                          f"full_name: {stock.full_name} | 行业: {stock.industry}")

                return True
            else:
                print("⚠️  数据库中没有美股数据")
                return False

    except Exception as e:
        print(f"❌ 查询失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fetch_history_with_prefix():
    """测试使用前缀获取历史数据"""
    print("\n" + "="*80)
    print("测试4: 使用动态前缀获取历史数据")
    print("="*80)

    from utils.db import get_db_session
    from models.stock import Stock
    from enums.category import Category
    from enums.stock_history import StockHistoryType
    from service.stock_history import fetch

    try:
        # 从数据库获取一只美股
        with get_db_session() as session:
            stock = session.query(Stock).filter(
                Stock.category == Category.US_XX,
                Stock.removed == False
            ).first()

            if not stock:
                print("⚠️  数据库中没有美股数据，请先运行测试2")
                return False

            print(f"\n测试股票: {stock.name} ({stock.code})")
            print(f"full_name: {stock.full_name}")

            # 提取前缀
            import re
            prefix = "105"  # 默认
            if stock.full_name:
                match = re.search(r'\((\d+)\)$', stock.full_name)
                if match:
                    prefix = match.group(1)

            print(f"提取的前缀: {prefix}")

        # 获取最近7天的日线数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        print(f"\n尝试获取历史数据...")
        print(f"日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")

        data = fetch(
            code=stock.code,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            t=StockHistoryType.D
        )

        if data:
            print(f"✅ 成功获取 {len(data)} 条历史数据")
            if len(data) > 0:
                print(f"\n最近一条数据:")
                d = data[-1]
                print(f"  日期: {d.date}")
                print(f"  开盘: {d.opening}, 收盘: {d.closing}")
                print(f"  最高: {d.highest}, 最低: {d.lowest}")
            return True
        else:
            print("⚠️  未获取到历史数据（可能是时间范围内无交易数据）")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("美股数据获取功能测试")
    print("="*80)

    results = []

    # 测试1: 获取美股列表
    results.append(("获取美股列表", test_fetch_us_stocks()))

    # 测试2: 保存到数据库
    if results[-1][1]:  # 如果测试1成功
        results.append(("保存美股到数据库", test_save_us_stocks()))
    else:
        print("\n⚠️  跳过测试2（测试1失败）")
        results.append(("保存美股到数据库", False))

    # 测试3: 查询前缀信息
    if results[-1][1]:  # 如果测试2成功
        results.append(("查询美股前缀", test_query_us_stock_prefix()))
    else:
        print("\n⚠️  跳过测试3（测试2失败）")
        results.append(("查询美股前缀", False))

    # 测试4: 使用前缀获取历史数据
    if results[-1][1]:  # 如果测试3成功
        results.append(("获取历史数据", test_fetch_history_with_prefix()))
    else:
        print("\n⚠️  跳过测试4（测试3失败）")
        results.append(("获取历史数据", False))

    # 输出测试总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:20s}: {status}")

    success_count = sum(1 for _, r in results if r)
    total_count = len(results)
    print(f"\n总计: {success_count}/{total_count} 通过")

    return success_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
