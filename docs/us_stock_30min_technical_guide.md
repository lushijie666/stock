# 美股30分钟数据获取 - 技术说明

## 问题背景

之前的实现错误地使用了 `stock_us_hist(period="30")` 来获取30分钟数据，但该接口不支持30分钟周期。

## 解决方案

### 技术路线

1. **使用正确的接口**: `stock_us_hist_min_em` - 获取1分钟级别的分时数据
2. **数据聚合**: 将1分钟数据按30分钟重采样聚合
3. **字段映射**: 处理不同接口返回字段名的差异

### 实现细节

#### 1. 数据获取

```python
# 30分钟数据使用分时接口
if t == StockHistoryType.THIRTY_M:
    start_datetime = f"{start_date} 00:00:00"
    end_datetime = f"{end_date} 23:59:59"

    df = ak.stock_us_hist_min_em(
        symbol=symbol,
        start_date=start_datetime,
        end_date=end_datetime
    )

    # 聚合为30分钟
    df = _aggregate_minute_to_30min(df)
```

#### 2. 聚合函数

```python
def _aggregate_minute_to_30min(df: pd.DataFrame) -> pd.DataFrame:
    """将1分钟数据聚合为30分钟"""

    # 设置时间为索引
    df['时间'] = pd.to_datetime(df['时间'])
    df.set_index('时间', inplace=True)

    # 定义聚合规则
    agg_rules = {
        '开盘': 'first',   # 第一个值
        '最高': 'max',     # 最大值
        '最低': 'min',     # 最小值
        '收盘': 'last',    # 最后一个值
        '成交量': 'sum',   # 求和
        '成交额': 'sum',   # 求和
    }

    # 重采样为30分钟
    df_30min = df.resample('30min').agg(agg_rules)

    return df_30min
```

#### 3. 字段映射

不同接口返回的字段名不同：

| 接口 | 时间字段 | 其他字段 |
|-----|---------|---------|
| `stock_us_hist` | 日期 | 开盘、收盘、最高、最低、成交量、成交额、换手率、涨跌幅 |
| `stock_us_hist_min_em` | 时间 | 开盘、收盘、最高、最低、成交量、成交额 |

代码中的处理：

```python
# 30分钟数据的字段名不同
if t == StockHistoryType.THIRTY_M:
    if '时间' in row:
        date_str = str(row['时间'])
    else:
        date_str = str(index)

    model_instance = StockHistory30M(
        date=date_str,
        opening=clean_numeric_value(row['开盘']),
        # ... 其他字段
    )
else:
    # 日/周/月使用'日期'字段
    date_str = str(row['日期'])
```

## 接口对比

### stock_us_hist

- **用途**: 获取历史K线数据
- **支持周期**: daily(日), weekly(周), monthly(月)
- **返回字段**: 日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率

### stock_us_hist_min_em

- **用途**: 获取分时数据
- **周期**: 固定1分钟
- **返回字段**: 时间、开盘、收盘、最高、最低、成交量、成交额、最新价
- **注意**:
  - 时间格式为 `YYYY-MM-DD HH:MM:SS`
  - 不包含换手率、涨跌幅等衍生字段

## 聚合规则说明

### OHLC 聚合

按照金融行业标准的K线聚合规则：

| 字段 | 聚合方法 | 说明 |
|-----|---------|------|
| 开盘价 | `first` | 取时间段内第一个值 |
| 最高价 | `max` | 取时间段内最大值 |
| 最低价 | `min` | 取时间段内最小值 |
| 收盘价 | `last` | 取时间段内最后一个值 |
| 成交量 | `sum` | 累加 |
| 成交额 | `sum` | 累加 |

### 时间对齐

使用 pandas 的 `resample('30min')` 方法：

- **左闭右开**: `[22:30:00, 23:00:00)`
- **对齐方式**: 以整点为准（如 22:30, 23:00, 23:30）

示例：
```
22:30 - 22:59 的1分钟数据 → 聚合为 22:30 的30分钟数据
23:00 - 23:29 的1分钟数据 → 聚合为 23:00 的30分钟数据
```

## 测试结果

### 测试数据

- **股票**: AAPL
- **时间范围**: 2025-12-22 至 2025-12-23
- **原始数据**: 391条1分钟数据
- **聚合后**: 14条30分钟数据

### 数据示例

```
时间: 2025-12-22 22:30:00
开盘: 272.86
收盘: 272.70
最高: 273.88
最低: 272.07
成交量: 5,256,164
成交额: 1,434,908,166
```

### 验证

✅ 数据完整性: 所有必需字段都有值
✅ 时间对齐: 30分钟边界正确
✅ 数值准确性: OHLC聚合规则正确
✅ 成交量/额: 累加正确

## 性能考虑

### 数据量

- 1天交易 ≈ 390条1分钟数据
- 聚合后 ≈ 13条30分钟数据
- 压缩比: ~30:1

### 处理时间

- 网络请求: ~0.3-0.5秒
- 数据聚合: ~0.01秒
- 总耗时: ~0.5-1秒

### 建议

- 如果需要大量历史数据（如1年），建议分批获取
- 使用通用限流器控制请求频率
- 考虑缓存已聚合的数据

## 使用示例

```python
from service.stock_history import _fetch_us_stock_data
from enums.history_type import StockHistoryType
from datetime import date, timedelta

# 获取最近3天的30分钟数据
end_date = date.today()
start_date = end_date - timedelta(days=3)

data_list = _fetch_us_stock_data(
    code="AAPL",
    start_date=start_date.strftime('%Y-%m-%d'),
    end_date=end_date.strftime('%Y-%m-%d'),
    t=StockHistoryType.THIRTY_M
)

# 遍历数据
for item in data_list:
    print(f"{item.date}: O={item.opening} H={item.highest} L={item.lowest} C={item.closing}")
```

## 注意事项

1. **交易时间**: 美股交易时间为北京时间 22:30 - 05:00（夏令时）或 23:30 - 06:00（冬令时）
2. **盘前盘后**: 分时接口可能包含盘前盘后交易数据
3. **节假日**: 非交易日返回空数据
4. **数据延迟**: 实时数据可能有几秒到几分钟的延迟

## 故障排查

### 问题1: 获取数据为空

**可能原因**:
- 查询时间段内无交易（周末、节假日）
- 股票代码错误
- 时间范围超出数据可用范围

**解决**:
- 检查是否为交易日
- 验证股票代码格式（应为 `105.AAPL` 形式）
- 缩小时间范围重试

### 问题2: 聚合数据异常

**可能原因**:
- 原始数据质量问题（缺失值）
- 时间格式解析错误

**解决**:
- 检查日志中的聚合比例
- 验证原始数据的时间格式

### 问题3: 性能慢

**可能原因**:
- 请求时间范围过大
- 网络延迟

**解决**:
- 缩小时间范围
- 使用防封策略控制请求频率

## 开盘价修复

### 问题

akshare 的 `stock_us_hist_min_em` 接口返回的1分钟数据中，部分记录的开盘价为0。聚合为30分钟数据后，如果某个30分钟时段的第一条1分钟数据开盘价为0，聚合后的开盘价也会是0。

### 解决方案

当聚合后的开盘价为0时，使用前一条30分钟记录的收盘价代替：

```python
# 使用 shift() 获取前一行的收盘价
df_30min['前收盘'] = df_30min['收盘'].shift(1)

# 当开盘价为0时，使用前一条的收盘价
df_30min['开盘'] = df_30min.apply(
    lambda row: row['前收盘'] if row['开盘'] == 0 and pd.notna(row['前收盘'])
                else (row['收盘'] if row['开盘'] == 0 else row['开盘']),
    axis=1
)
```

**详细说明**: 参见 [开盘价修复方案文档](./us_stock_30min_open_price_fix.md)

## 未来优化

1. **增量更新**: 支持仅获取新增数据
2. **缓存机制**: 缓存已聚合的30分钟数据
3. **多周期支持**: 支持5分钟、15分钟等其他周期
4. **并行聚合**: 大数据量时使用并行计算
