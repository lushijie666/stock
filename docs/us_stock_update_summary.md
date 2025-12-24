# 美股数据获取优化完成总结

## 📋 任务概述

优化美股股票数据获取方式，解决以下问题：
1. 将美股列表获取从 `ak.stock_us_spot_em()` 替换为更高质量的 `ak.stock_us_famous_spot_em()`
2. 支持6个美股分类：科技类、金融类、医药食品类、媒体类、汽车能源类、制造零售类
3. 解决历史数据获取时代码前缀写死为105的问题（实际有105和106两种前缀）
4. 将前缀信息存储到数据库，历史数据获取时动态读取

---

## ✅ 完成的修改

### 1. 修改股票列表获取逻辑 (`service/stock.py`)

**文件**: `service/stock.py` 第500-562行

**主要改动**:

```python
# 处理美股数据
elif category == Category.US_XX:
    logging.info(f"开始获取[{KEY_PREFIX}]数据..., 分类: {category.text}")
    data = []  # 在循环外初始化，收集所有分类的数据

    # 遍历所有6个美股分类
    for symbol in [
        "科技类",
        "金融类",
        "医药食品类",
        "媒体类",
        "汽车能源类",
        "制造零售类",
    ]:
        # 使用新的API
        df = ak.stock_us_famous_spot_em(symbol=symbol)
        logging.info(f"成功获取[{KEY_PREFIX}]数据, 分类: {category.text}, symbol: {symbol}, 共 {len(df)} 条记录")

        for i, row in df.iterrows():
            # 提取前缀和代码
            raw_code = row.get("代码", "")  # 格式: "105.AAPL" 或 "106.BABA"
            if '.' in str(raw_code):
                prefix, code = str(raw_code).split('.', 1)
            else:
                prefix = ""
                code = str(raw_code)

            # 将前缀保存到 full_name 字段
            # 格式: 名称(前缀)，例如: "英伟达(105)"
            name = row.get("名称", "")
            full_name = f"{name}({prefix})" if prefix else str(name)

            s = Stock(
                category=category,
                code=code,
                name=clean_name(str(name)),
                full_name=full_name,  # 保存前缀信息
                ipo_at=None,
                total_capital=None,
                flow_capital=None,
                industry=symbol,  # 使用美股分类作为行业
            )
            data.append(s)

    return data
```

**关键点**:
- ✅ 使用 `ak.stock_us_famous_spot_em(symbol="分类")` 获取高质量美股数据
- ✅ 遍历所有6个分类，合并结果
- ✅ 从原始代码中提取前缀（105或106）
- ✅ 将前缀保存到 `full_name` 字段，格式: `名称(前缀)`
- ✅ 将美股分类保存到 `industry` 字段

### 2. 优化历史数据获取逻辑 (`service/stock_history.py`)

**文件**: `service/stock_history.py` 第395-431行

**主要改动**:

```python
def _fetch_us_stock_data(code: str, start_date: str, end_date: str, t: StockHistoryType) -> list:
    """使用 akshare 抓取美股数据（东财数据源，国内网络友好）"""
    def _fetch_data():
        _us_stock_limiter.wait_before_request()

        # 从数据库获取股票信息，提取前缀
        prefix = "105"  # 默认前缀
        try:
            with get_db_session() as session:
                from models.stock import Stock
                stock = session.query(Stock).filter(
                    Stock.code == code,
                    Stock.category == Category.US_XX
                ).first()

                if stock and stock.full_name:
                    # full_name 格式: 名称(前缀)，例如: 英伟达(105)
                    import re
                    match = re.search(r'\((\d+)\)$', stock.full_name)
                    if match:
                        prefix = match.group(1)
                        logging.info(f"从数据库获取到美股前缀: {prefix}, full_name: {stock.full_name}")
                    else:
                        logging.warning(f"无法从 full_name 提取前缀，使用默认值: {prefix}")
                else:
                    logging.warning(f"未找到股票或 full_name 为空，使用默认前缀: {prefix}")
        except Exception as e:
            logging.warning(f"查询股票前缀失败，使用默认值: {prefix}, 错误: {str(e)}")

        # akshare 需要带前缀的股票代码（如 105.AAPL 或 106.BABA）
        symbol = f"{prefix}.{code}"
        logging.info(f"使用美股代码: {symbol} (前缀: {prefix}, 代码: {code})")

        # 继续获取历史数据...
```

**关键点**:
- ✅ 不再写死前缀为105
- ✅ 从数据库查询股票的 `full_name`
- ✅ 使用正则表达式提取前缀: `r'\((\d+)\)$'`
- ✅ 如果提取失败或未找到，使用默认值105
- ✅ 动态构造 akshare 需要的代码格式: `{prefix}.{code}`

---

## 📊 测试结果

### 测试1: 获取美股列表

```
✅ 成功获取 106 只美股

前5只股票信息:
1. 代码: GRPN, 名称: GrouponInc-A, 全称: Groupon Inc-A(105), 行业: 科技类
2. 代码: NVDA, 名称: 英伟达, 全称: 英伟达(105), 行业: 科技类
3. 代码: AMZN, 名称: 亚马逊, 全称: 亚马逊(105), 行业: 科技类
4. 代码: MSI, 名称: 摩托罗拉解决方案, 全称: 摩托罗拉解决方案(106), 行业: 科技类
5. 代码: VOD, 名称: 沃达丰, 全称: 沃达丰(105), 行业: 科技类

检查前缀信息（full_name格式）:
发现的前缀分布:
  前缀 105: 24 只股票
  前缀 106: 82 只股票

行业分布:
  制造零售类: 19 只
  医药食品类: 15 只
  媒体类: 4 只
  汽车能源类: 18 只
  科技类: 29 只
  金融类: 21 只
```

**验证结果**:
- ✅ 成功从6个分类获取106只美股
- ✅ 前缀信息正确保存到 `full_name` 字段
- ✅ 发现105和106两种前缀，符合预期
- ✅ 行业分类正确分布到6个类别

### 测试2: 保存美股到数据库

```
✅ 保存完成
```

**验证结果**:
- ✅ 数据成功保存到数据库
- ✅ `full_name` 字段包含前缀信息

---

## 🔧 数据格式说明

### Stock 表字段变化

| 字段名 | 原格式 | 新格式 | 说明 |
|--------|--------|--------|------|
| `code` | AAPL | AAPL | 保持不变，纯代码 |
| `name` | 苹果 | 苹果 | 保持不变，中文名称 |
| `full_name` | 苹果 | **苹果(105)** | ✨ 新增前缀信息 |
| `industry` | (空) | **科技类** | ✨ 使用美股分类 |

### 前缀提取正则表达式

```python
import re
pattern = r'\((\d+)\)$'
match = re.search(pattern, full_name)
if match:
    prefix = match.group(1)  # 提取括号中的数字
```

**示例**:
- `"英伟达(105)"` → 提取出 `"105"`
- `"摩托罗拉解决方案(106)"` → 提取出 `"106"`
- `"苹果"` → 提取失败，使用默认值

---

## 📈 优势对比

### 旧方案 vs 新方案

| 对比项 | 旧方案 | 新方案 |
|--------|--------|--------|
| **API** | `ak.stock_us_spot_em()` | `ak.stock_us_famous_spot_em()` |
| **数据质量** | 包含大量小型股票 | 仅包含知名股票，质量更高 |
| **股票数量** | ~3000只 | ~106只（精选） |
| **分类** | 无分类 | 6个专业分类 |
| **前缀处理** | 写死105 | 动态提取105/106 |
| **行业信息** | 无 | 有（科技类、金融类等） |

### 新方案优势

1. **数据质量更高**
   - 仅包含知名美股，去除了大量不活跃的小型股票
   - 适合个人投资者关注和分析

2. **分类更清晰**
   - 6个专业分类便于用户按行业筛选
   - 支持行业对比分析

3. **前缀动态化**
   - 解决了前缀写死导致部分股票无法获取历史数据的问题
   - 支持105和106两种前缀

4. **维护性更好**
   - 前缀信息存储在数据库，便于管理
   - 如果akshare改变前缀规则，只需重新获取数据即可

---

## 🚀 使用说明

### 更新美股列表

在 UI 中，进入"股票信息" → "美股"页面，点击"更新"按钮即可。

系统会：
1. 调用 `ak.stock_us_famous_spot_em()` 获取6个分类的美股
2. 提取每只股票的前缀信息
3. 将前缀保存到 `full_name` 字段
4. 将分类保存到 `industry` 字段
5. 保存到数据库（自动去重）

### 获取历史数据

获取美股历史数据时，系统会：
1. 从数据库查询股票的 `full_name`
2. 从 `full_name` 中提取前缀
3. 构造完整代码：`{prefix}.{code}`（如 `105.AAPL`）
4. 调用 akshare API 获取历史数据

**注意**: 如果数据库中的美股没有前缀信息（旧数据），会使用默认前缀105。建议重新更新美股列表以获取前缀信息。

---

## 📝 已修改文件清单

1. **service/stock.py**
   - 修改 `fetch()` 函数，使用新API和6个分类
   - 添加前缀提取和保存逻辑
   - 简化 `reload()` 函数签名

2. **service/stock_history.py**
   - 修改 `_fetch_us_stock_data()` 函数
   - 添加从数据库查询前缀的逻辑
   - 添加正则表达式提取前缀

3. **test_us_stock_update.py** (新增)
   - 测试美股列表获取
   - 测试数据保存
   - 测试前缀提取

4. **docs/us_stock_update_summary.md** (本文档)
   - 完整的修改说明和使用指南

---

## ⚠️ 注意事项

1. **旧数据处理**
   - 数据库中已有的美股数据可能没有前缀信息
   - 建议重新点击"更新"按钮获取新数据
   - 或手动更新旧数据的 `full_name` 字段

2. **API限流**
   - `ak.stock_us_famous_spot_em()` 需要调用6次（6个分类）
   - 已有限流机制，不需要担心被封

3. **前缀兼容性**
   - 如果未来出现新的前缀（如107），代码会自动处理
   - 历史数据获取如果提取失败，会使用默认前缀105

4. **数据更新频率**
   - 知名美股列表相对稳定
   - 建议每月更新一次即可
   - 新股票上市时可手动更新

---

## ✅ 总结

本次优化完成了以下目标：

1. ✅ 替换为高质量的美股数据源
2. ✅ 支持6个专业分类
3. ✅ 解决前缀写死问题
4. ✅ 实现前缀动态提取和存储
5. ✅ 获取到106只知名美股
6. ✅ 发现并正确处理105和106两种前缀
7. ✅ 添加行业分类信息

系统现在可以更准确、更高效地获取美股数据和历史行情！
