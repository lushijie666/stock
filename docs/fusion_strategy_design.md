# 策略融合功能设计方案

## 1. 背景与目标

### 1.1 背景
当前系统已集成8种交易策略：
1. **MACD策略** - 趋势跟随，适合中长期
2. **SMA策略** - 均线交叉，适合趋势明确时
3. **海龟策略** - 突破型策略，适合波动市场
4. **CBR策略** - 成本均线，适合长期价值投资
5. **RSI策略** - 超买超卖，适合震荡市场
6. **布林带策略** - 波动性策略，适合区间震荡
7. **KDJ策略** - 随机指标，适合短期交易
8. **蜡烛图策略** - 形态识别，适合关键转折点

每种策略都有其适用场景和局限性，单一策略容易产生假信号。

### 1.2 目标
设计一个**策略融合系统**，能够：
- 综合多个策略的信号，提高准确性
- 根据市场环境动态调整策略权重
- 提供信号强度评分机制
- 支持用户自定义融合规则

---

## 2. 融合策略设计

### 2.1 融合方法

#### 方法一：投票机制（Voting）
- **原理**：多数策略发出相同信号时触发
- **优点**：简单直观，降低假信号
- **适用**：适合追求稳定性的投资者

```
买入信号 = 至少N个策略同时发出买入信号
卖出信号 = 至少M个策略同时发出卖出信号
```

#### 方法二：加权评分（Weighted Scoring）
- **原理**：不同策略赋予不同权重，计算综合得分
- **优点**：灵活性高，可根据市场调整权重
- **适用**：适合有经验的投资者

```
综合得分 = Σ(策略i的信号 × 权重i × 强度系数i)
```

#### 方法三：市场环境自适应（Adaptive）
- **原理**：根据市场状态（趋势/震荡）动态选择策略组合
- **优点**：适应性强，提高准确率
- **适用**：适合全天候交易

```
if 趋势市场:
    侧重 MACD + SMA + 海龟策略
elif 震荡市场:
    侧重 RSI + 布林带 + KDJ策略
elif 转折点:
    侧重 蜡烛图策略
```

---

## 3. 技术实现方案

### 3.1 数据结构

#### 融合策略枚举
```python
# enums/strategy.py
FUSION_STRATEGY = ("fusion", "FS", "融合策略", "多策略综合信号")
```

#### 融合配置
```python
class FusionConfig:
    """融合策略配置"""
    method: str  # 'voting', 'weighted', 'adaptive'
    min_consensus: int  # 投票模式：最小一致策略数
    weights: Dict[str, float]  # 加权模式：策略权重
    market_detection: bool  # 是否启用市场环境检测
```

### 3.2 核心算法

#### 投票机制实现
```python
def voting_fusion(signals_list, min_consensus=3):
    """
    投票融合：多个策略达成一致才发出信号

    Args:
        signals_list: 各策略的信号列表
        min_consensus: 最小一致策略数（默认3个）

    Returns:
        融合后的信号列表
    """
    # 按日期分组统计
    date_signals = {}
    for strategy_signals in signals_list:
        for signal in strategy_signals:
            date = signal['date']
            if date not in date_signals:
                date_signals[date] = {'BUY': [], 'SELL': []}

            signal_type = signal['type']
            date_signals[date][signal_type].append({
                'strategy': signal['strategy_code'],
                'strength': signal['strength'],
                'pattern': signal.get('pattern_name', '')
            })

    # 生成融合信号
    fusion_signals = []
    for date, signals in date_signals.items():
        # 买入信号投票
        if len(signals['BUY']) >= min_consensus:
            strength = calculate_consensus_strength(signals['BUY'])
            fusion_signals.append({
                'date': date,
                'type': SignalType.BUY,
                'strength': strength,
                'consensus_count': len(signals['BUY']),
                'strategies': [s['strategy'] for s in signals['BUY']],
                'details': signals['BUY']
            })

        # 卖出信号投票
        if len(signals['SELL']) >= min_consensus:
            strength = calculate_consensus_strength(signals['SELL'])
            fusion_signals.append({
                'date': date,
                'type': SignalType.SELL,
                'strength': strength,
                'consensus_count': len(signals['SELL']),
                'strategies': [s['strategy'] for s in signals['SELL']],
                'details': signals['SELL']
            })

    return fusion_signals
```

#### 加权评分实现
```python
def weighted_fusion(signals_list, weights):
    """
    加权融合：根据策略权重计算综合得分

    Args:
        signals_list: 各策略的信号列表
        weights: 策略权重字典 {strategy_code: weight}

    Returns:
        融合后的信号列表
    """
    date_scores = {}

    for strategy_signals in signals_list:
        for signal in strategy_signals:
            date = signal['date']
            strategy = signal['strategy_code']
            strength = signal['strength']

            if date not in date_scores:
                date_scores[date] = {'BUY': 0, 'SELL': 0, 'details': {'BUY': [], 'SELL': []}}

            # 信号强度转换为数值
            strength_value = {
                SignalStrength.STRONG: 2.0,
                SignalStrength.WEAK: 1.0
            }[strength]

            # 计算加权得分
            weight = weights.get(strategy, 1.0)
            score = strength_value * weight

            signal_type = 'BUY' if signal['type'] == SignalType.BUY else 'SELL'
            date_scores[date][signal_type] += score
            date_scores[date]['details'][signal_type].append({
                'strategy': strategy,
                'strength': strength,
                'weight': weight,
                'score': score
            })

    # 生成融合信号
    fusion_signals = []
    threshold = 3.0  # 阈值：总分超过3才发出信号

    for date, scores in date_scores.items():
        if scores['BUY'] >= threshold:
            strength = SignalStrength.STRONG if scores['BUY'] >= 5.0 else SignalStrength.WEAK
            fusion_signals.append({
                'date': date,
                'type': SignalType.BUY,
                'strength': strength,
                'score': scores['BUY'],
                'details': scores['details']['BUY']
            })

        if scores['SELL'] >= threshold:
            strength = SignalStrength.STRONG if scores['SELL'] >= 5.0 else SignalStrength.WEAK
            fusion_signals.append({
                'date': date,
                'type': SignalType.SELL,
                'strength': strength,
                'score': scores['SELL'],
                'details': scores['details']['SELL']
            })

    return fusion_signals
```

#### 市场环境检测
```python
def detect_market_state(df, window=20):
    """
    检测市场状态：趋势 or 震荡

    Args:
        df: 股票数据
        window: 检测窗口期

    Returns:
        'trending' 或 'ranging'
    """
    # 计算ADX（平均趋向指数）来判断趋势强度
    # ADX > 25：趋势市场
    # ADX < 20：震荡市场

    high = df['highest']
    low = df['lowest']
    close = df['closing']

    # 计算+DI和-DI
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)

    atr = tr.rolling(window).mean()
    plus_di = 100 * (plus_dm.rolling(window).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window).mean() / atr)

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window).mean().iloc[-1]

    if adx > 25:
        return 'trending'
    else:
        return 'ranging'
```

#### 自适应融合
```python
def adaptive_fusion(df, signals_list):
    """
    自适应融合：根据市场环境选择策略组合
    """
    market_state = detect_market_state(df)

    if market_state == 'trending':
        # 趋势市场：侧重趋势跟随策略
        weights = {
            'macd': 2.0,
            'sma': 2.0,
            'turtle': 1.5,
            'cbr': 1.0,
            'rsi': 0.5,
            'boll': 0.5,
            'kdj': 0.5,
            'candle': 1.0
        }
    else:
        # 震荡市场：侧重反转策略
        weights = {
            'macd': 0.5,
            'sma': 0.5,
            'turtle': 0.5,
            'cbr': 0.5,
            'rsi': 2.0,
            'boll': 2.0,
            'kdj': 2.0,
            'candle': 1.5
        }

    return weighted_fusion(signals_list, weights)
```

---

## 4. UI设计

### 4.1 融合策略配置界面
```python
# 融合模式选择
mode = st.selectbox(
    "融合模式",
    ["投票机制", "加权评分", "市场自适应"]
)

if mode == "投票机制":
    min_consensus = st.slider(
        "最小一致策略数",
        min_value=2,
        max_value=8,
        value=3,
        help="至少几个策略发出相同信号才触发"
    )

elif mode == "加权评分":
    st.write("### 策略权重配置")
    weights = {}
    for strategy in StrategyType:
        weights[strategy.code] = st.slider(
            strategy.fullText,
            min_value=0.0,
            max_value=3.0,
            value=1.0,
            step=0.1
        )
```

### 4.2 融合信号展示
```python
# 显示融合信号详情
for signal in fusion_signals:
    with st.expander(f"{signal['date']} - {signal['type'].fullText}"):
        st.write(f"**综合强度**: {signal['strength'].fullText}")
        st.write(f"**一致策略数**: {signal['consensus_count']}")
        st.write("**参与策略**:")
        for detail in signal['details']:
            st.write(f"  - {detail['strategy']}: {detail['strength'].fullText}")
```

---

## 5. 实施计划

### 阶段一：基础融合（投票机制）
- [x] 添加融合策略枚举
- [ ] 实现投票融合算法
- [ ] UI集成：融合模式选择
- [ ] 测试验证

### 阶段二：高级融合（加权评分）
- [ ] 实现加权评分算法
- [ ] 权重配置UI
- [ ] 预设权重模板（保守/激进/平衡）
- [ ] 测试验证

### 阶段三：智能融合（自适应）
- [ ] 市场环境检测算法
- [ ] 自适应权重调整
- [ ] 回测验证准确率
- [ ] 性能优化

---

## 6. 预期效果

### 6.1 准确性提升
- 减少单一策略假信号：预计降低30-50%
- 提高关键买卖点捕捉率：预计提升20-40%

### 6.2 适用场景
- **投票模式**：适合保守型投资者，追求稳定性
- **加权模式**：适合有经验投资者，灵活调整
- **自适应模式**：适合全天候交易，智能决策

### 6.3 风险控制
- 多策略验证降低误判风险
- 信号强度评分辅助仓位管理
- 历史回测验证策略有效性

---

## 7. 注意事项

1. **过度拟合风险**：避免权重过度优化历史数据
2. **计算性能**：融合策略会增加计算量，需要优化
3. **用户教育**：需要提供融合策略使用指南
4. **参数调优**：不同股票可能需要不同的融合参数

---

## 8. 后续优化方向

1. **机器学习优化**：使用ML自动学习最优权重
2. **实时自适应**：根据实时市场数据动态调整
3. **策略组合推荐**：根据历史回测推荐最佳组合
4. **风险评估**：融合信号的可信度评估
