import streamlit as st

from enums import strategy
from enums.strategy import StrategyType


def show_page():
    if 'selected_strategy' in st.session_state:
        del st.session_state['selected_strategy']
    st.markdown(
        f"""
          <div class="table-header">
              <div class="table-title">策略概览</div>
          </div>
          """,
        unsafe_allow_html=True
    )


    # 定义策略分组
    trend_strategies = [StrategyType.MACD_STRATEGY,StrategyType.SMA_STRATEGY, StrategyType.TURTLE_STRATEGY]
    overbought_oversold_strategies = [StrategyType.RSI_STRATEGY,StrategyType.KDJ_STRATEGY]
    other_strategies = [StrategyType.BOLL_STRATEGY,StrategyType.CBR_STRATEGY]

    st.markdown(f"""
             <div class="chart-header">
                 <span class="chart-icon">🔍</span>
                 <span class="chart-title">趋势跟踪策略</span>
             </div>
    """, unsafe_allow_html=True)

    # 使用网格布局显示策略卡片
    for i in range(0, len(trend_strategies), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(trend_strategies):
                strategy = trend_strategies[i + j]
                with col:
                    st.markdown(
                        f"""
                          <div class="stock-card">
                              <div class="stock-card-header">
                                  <div class="stock-card-title">
                                      <span class="stock-name">{strategy.fullText}</span>
                                  </div>
                              </div>
                              <div class="stock-card-body">
                                  <div class="stock-info-row">
                                      <span class="info-label">描述</span>
                                      <span class="info-value">{strategy.desc}</span>
                                  </div>
                              </div>

                          </div>
                        """
                        , unsafe_allow_html=True)
                    if st.button(
                            "详情",
                            key=f"btn_{strategy.value}",
                            use_container_width=True
                    ):
                        # 将选中的策略存储到session state中
                        st.session_state['selected_strategy'] = strategy

    st.markdown(f"""
             <div class="chart-header">
                 <span class="chart-icon">🔍</span>
                 <span class="chart-title">超买超卖策略</span>
             </div>
    """, unsafe_allow_html=True)
    for i in range(0, len(overbought_oversold_strategies), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(overbought_oversold_strategies):
                strategy = overbought_oversold_strategies[i + j]
                with col:
                    st.markdown(
                        f"""
                          <div class="stock-card">
                              <div class="stock-card-header">
                                  <div class="stock-card-title">
                                      <span class="stock-name">{strategy.fullText}</span>
                                  </div>
                              </div>
                              <div class="stock-card-body">
                                  <div class="stock-info-row">
                                      <span class="info-label">描述</span>
                                      <span class="info-value">{strategy.desc}</span>
                                  </div>
                              </div>

                          </div>
                        """
                        , unsafe_allow_html=True)
                    if st.button(
                            "详情",
                            key=f"btn_{strategy.value}",
                            use_container_width=True
                    ):
                        # 将选中的策略存储到session state中
                        st.session_state['selected_strategy'] = strategy

    st.markdown(f"""
             <div class="chart-header">
                 <span class="chart-icon">🔍</span>
                 <span class="chart-title">其他策略</span>
             </div>
    """, unsafe_allow_html=True)

    # 使用网格布局显示其他策略卡片
    for i in range(0, len(other_strategies), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(other_strategies):
                strategy = other_strategies[i + j]
                with col:
                    st.markdown(
                        f"""
                          <div class="stock-card">
                              <div class="stock-card-header">
                                  <div class="stock-card-title">
                                      <span class="stock-name">{strategy.fullText}</span>
                                  </div>
                              </div>
                              <div class="stock-card-body">
                                  <div class="stock-info-row">
                                      <span class="info-label">描述</span>
                                      <span class="info-value">{strategy.desc}</span>
                                  </div>
                              </div>

                          </div>
                        """
                        , unsafe_allow_html=True)
                    if st.button(
                            "详情",
                            key=f"btn_{strategy.value}",
                            use_container_width=True
                    ):
                        # 将选中的策略存储到session state中
                        st.session_state['selected_strategy'] = strategy

    # 检查是否需要显示弹窗
    if 'selected_strategy' in st.session_state:
        selected_strategy = st.session_state['selected_strategy']
        show_detail_dialog(selected_strategy)

@st.dialog("策略详情", width="large")
def show_detail_dialog(strategy):
    # 显示策略标题
    st.markdown(
        f"""
             <div class="table-header">
                 <div class="table-title">{strategy.fullText} - {strategy.desc}</div>
             </div>
             """,
        unsafe_allow_html=True
    )
    # 根据策略类型调用对应的详情函数
    strategy_mapping = {
        StrategyType.MACD_STRATEGY: show_macd_strategy,
        StrategyType.SMA_STRATEGY: show_sma_strategy,
        StrategyType.TURTLE_STRATEGY: show_turtle_strategy,
        StrategyType.CBR_STRATEGY: show_cbr_strategy,
        StrategyType.RSI_STRATEGY: show_rsi_strategy,
        StrategyType.BOLL_STRATEGY: show_bollinger_strategy,
        StrategyType.KDJ_STRATEGY: show_kdj_strategy,
    }
    handler = strategy_mapping.get(strategy)
    if handler:
        handler()

def show_macd_strategy():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-1">
                   <div class="metric-label">策略类型</div>
                   <div class="metric-value">趋势跟踪</div>
               </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-2">
                  <div class="metric-label">适用周期</div>
                  <div class="metric-value">日/周/月线</div>
              </div>
       """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-3">
                  <div class="metric-label">难度等级</div>
                  <div class="metric-value">⭐⭐</div>
              </div>
       """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""
                   <div class="chart-header">
                       <span class="chart-icon">📖</span>
                       <span class="chart-title">策略原理</span>
                   </div>
          """, unsafe_allow_html=True)
    st.markdown("""
        MACD（Moving Average Convergence Divergence）由Gerald Appel在1970年代发明
        
        **最经典的技术指标之一**
    
        **核心思想**：通过快慢两条移动平均线的差值变化来判断趋势的强弱和转折点
    
        **计算公式**：
        - **DIFF（快线）** = 12日EMA - 26日EMA
        - **DEA（慢线）** = DIFF的9日EMA
        - **MACD柱** = (DIFF - DEA) × 2
    
        其中EMA是指数移动平均线（Exponential Moving Average）
        """)

    st.markdown(f"""
                       <div class="chart-header">
                           <span class="chart-icon">🎯</span>
                           <span class="chart-title">交易信号</span>
                       </div>
              """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🟢 买入信号（金叉）
        1. **DIFF上穿DEA**（金叉出现）
        2. **DIFF > 0**（零轴上方，趋势向上）
        3. **强买入**：DIFF上升角度>30°

        **示例**：
        - DIFF从-0.5上升到0.2并穿过DEA
        - 此时DIFF>0，为强买入信号
        """)

    with col2:
        st.markdown("""
        #### 🔴 卖出信号（死叉）
        1. **DIFF下穿DEA**（死叉出现）
        2. **强卖出**：DIFF<0且DEA<0（双双进入负值区）

        **示例**：
        - DIFF从0.3下降到-0.1并跌破DEA
        - DIFF和DEA都小于0，为强卖出信号
        """)

    # 优缺点
    st.markdown(f"""
                          <div class="chart-header">
                              <span class="chart-icon">⚖️</span>
                              <span class="chart-title">优缺点</span>
                          </div>
    """, unsafe_allow_html=True)


    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **✅ 优点**
        - 趋势跟踪能力强，适合捕捉中长期趋势
        - 信号明确，容易判断（金叉买入，死叉卖出）
        - 适合趋势明显的市场
        - 过滤了价格的短期波动
        - 应用广泛，被大量交易者认可
        """)

    with col2:
        st.markdown("""
        **❌ 缺点**
        - 震荡市场会产生虚假信号
        - 存在一定的滞后性（基于移动平均）
        - 横盘整理时表现不佳
        - 需要结合其他指标确认
        """)

    # 实战技巧
    st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">💡</span>
                      <span class="chart-title">实战技巧</span>
                  </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    1. **结合趋势使用**：在明确的上升或下降趋势中使用效果最好
    2. **零轴判断**：DIFF在零轴上方金叉更可靠，在零轴下方死叉更可靠
    3. **柱状图辅助**：MACD柱状图由负转正可提前预示金叉
    4. **背离信号**：价格创新高但MACD不创新高（顶背离），可能见顶
    5. **组合使用**：建议与成交量、趋势线等配合使用
    """)

    # 参数说明
    st.markdown(f"""
              <div class="chart-header">
                  <span class="chart-icon">⚙️</span>
                  <span class="chart-title">参数说明</span>
              </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    | 参数 | 默认值 | 说明 |
    |------|--------|------|
    | 快线周期 | 12 | 短期EMA的计算周期 |
    | 慢线周期 | 26 | 长期EMA的计算周期 |
    | 信号周期 | 9 | DEA线的平滑周期 |

    **调参建议**：
    - 短线交易：可使用(6, 13, 5)
    - 长线交易：可使用(19, 39, 9)
    - **不建议**频繁调整参数，容易过度优化
    """)

    # 示例
    st.markdown(f"""
              <div class="chart-header">
                  <span class="chart-icon">📈</span>
                  <span class="chart-title">信号示例</span>
              </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    ```
    日期       收盘价    DIFF    DEA     信号
    01-10     100.0    -0.3    -0.2     -
    01-11     102.0    -0.1    -0.15    -
    01-12     105.0     0.2     0.05    🟢 买入（金叉+零轴上方）
    01-13     108.0     0.4     0.2     持有
    01-14     106.0     0.3     0.25    持有
    01-15     103.0     0.1     0.2     🔴 卖出（死叉）
    ```
    """)


def show_sma_strategy():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
                  <div class="metric-sub-card metric-card-1">
                      <div class="metric-label">策略类型</div>
                      <div class="metric-value">趋势跟踪</div>
                  </div>
           """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
                 <div class="metric-sub-card metric-card-2">
                     <div class="metric-label">适用周期</div>
                     <div class="metric-value">日/周/月线</div>
                 </div>
          """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
                 <div class="metric-sub-card metric-card-3">
                     <div class="metric-label">难度等级</div>
                     <div class="metric-value">⭐</div>
                 </div>
          """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""
                      <div class="chart-header">
                          <span class="chart-icon">📖</span>
                          <span class="chart-title">策略原理</span>
                      </div>
             """, unsafe_allow_html=True)
    st.markdown("""
    SMA（Simple Moving Average）是**最简单也最经典**的技术分析工具

    **核心思想**：短期均线代表短期趋势，长期均线代表长期趋势。当短期均线上穿长期均线时，表示短期趋势转强，产生买入信号

    **本系统使用的均线**：
    - **MA5**：5日移动平均线（短期趋势）
    - **MA10**：10日移动平均线（中短期趋势）
    - **MA30**：30日移动平均线（中期趋势）
    - **MA250**：250日移动平均线（年线，长期趋势）
    """)

    st.markdown(f"""
                           <div class="chart-header">
                               <span class="chart-icon">🎯</span>
                               <span class="chart-title">交易信号</span>
                           </div>
                  """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🟢 买入信号（金叉）
        **条件**：
        1. **MA5上穿MA10**
        2. **MACD DIFF > 0** 且 **DEA > 0**（趋势确认）

        这种双重确认可以**降低虚假信号**
        """)

    with col2:
        st.markdown("""
        #### 🔴 卖出信号（死叉）
        **条件**：
        1. **MA10下破MA5**
        2. 为强卖出信号

        **特点**：简单直接，容易执行
        """)

    st.markdown(f"""
                              <div class="chart-header">
                                  <span class="chart-icon">⚖️</span>
                                  <span class="chart-title">优缺点</span>
                              </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **✅ 优点**
        - 非常简单，新手易于理解和使用
        - 信号明确，不需要复杂判断
        - 多时间框架验证（短中长期均线）
        - 适合趋势明显的市场
        """)

    with col2:
        st.markdown("""
        **❌ 缺点**
        - 滞后性较强（毕竟是移动平均）
        - 震荡市场频繁产生虚假信号
        - 可能错过趋势初期的最佳入场点
        """)

    st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">💡</span>
                      <span class="chart-title">实战技巧</span>
                  </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    1. **多头排列**：MA5 > MA10 > MA30 > MA250，强势上涨趋势
    2. **空头排列**：MA5 < MA10 < MA30 < MA250，强势下跌趋势
    3. **年线支撑**：MA250常作为重要的支撑/压力位
    4. **均线粘合**：多条均线靠得很近时，往往预示即将变盘
    5. **配合成交量**：金叉时放量更可靠
    """)


def show_rsi_strategy():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-1">
                   <div class="metric-label">策略类型</div>
                   <div class="metric-value">超买超卖</div>
               </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-2">
                  <div class="metric-label">适用周期</div>
                  <div class="metric-value">日/周线</div>
              </div>
       """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-3">
                  <div class="metric-label">难度等级</div>
                  <div class="metric-value">⭐⭐</div>
              </div>
       """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""
                   <div class="chart-header">
                       <span class="chart-icon">📖</span>
                       <span class="chart-title">策略原理</span>
                   </div>
          """, unsafe_allow_html=True)
    st.markdown("""
    RSI（Relative Strength Index）由Welles Wilder在**1978年**发明
    
    是衡量价格变动速度和幅度的**动量震荡指标**

    **核心思想**：通过比较一段时期内价格上涨幅度和下跌幅度的平均值来衡量买卖力量的强弱

    **计算公式**：
    ```
    RS = 平均涨幅 / 平均跌幅
    RSI = 100 - (100 / (1 + RS))
    ```

    **取值范围**：0-100
    - **>70**：超买区（Overbought），可能回调
    - **<30**：超卖区（Oversold），可能反弹
    - **50**：中性区
    """)

    st.markdown(f"""
                       <div class="chart-header">
                           <span class="chart-icon">🎯</span>
                           <span class="chart-title">交易信号</span>
                       </div>
              """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🟢 买入信号
        **条件**：
        1. RSI **从超卖区（<30）向上穿越**
        2. **强买入**：RSI急速上升（单日变化>5）

        **原理**：超卖后反弹，抄底机会
        """)

    with col2:
        st.markdown("""
        #### 🔴 卖出信号
        **条件**：
        1. RSI **从超买区（>70）向下穿越**
        2. **强卖出**：RSI急速下降（单日变化>5）

        **原理**：超买后回调，获利了结
        """)

    st.markdown(f"""
                          <div class="chart-header">
                              <span class="chart-icon">⚖️</span>
                              <span class="chart-title">优缺点</span>
                          </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **✅ 优点**
        - 反应灵敏，适合短线交易
        - 超买超卖判断准确
        - 特别适合震荡市场
        - 可以提前预警价格反转
        - 应用广泛，成熟可靠
        """)

    with col2:
        st.markdown("""
        **❌ 缺点**
        - 强趋势中会过早退出
        - 可能长时间处于超买/超卖区
        - 需要结合趋势判断
        - 参数敏感，需要调优
        """)

    st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">💡</span>
                      <span class="chart-title">实战技巧</span>
                  </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    1. **趋势配合**：在上升趋势中，RSI常在40-90区间波动；下降趋势中在10-60区间
    2. **背离信号**：
       - 价格创新高但RSI不创新高 → 顶背离，警惕下跌
       - 价格创新低但RSI不创新低 → 底背离，可能反弹
    3. **区间修正**：
       - 强势股：超买线70→80，超卖线30→40
       - 弱势股：超买线70→60，超卖线30→20
    4. **中线穿越**：RSI上穿50线确认上升趋势，下穿50线确认下降趋势
    5. **钝化现象**：强趋势中RSI可能持续在超买/超卖区，不要盲目反向操作
    """)

    st.markdown(f"""
              <div class="chart-header">
                  <span class="chart-icon">⚙️</span>
                  <span class="chart-title">参数说明</span>
              </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    | 参数 | 默认值 | 说明 |
    |------|--------|------|
    | period | 14 | 计算周期 |
    | oversold | 30 | 超卖线 |
    | overbought | 70 | 超买线 |

    **常用设置**：
    - 短线：(6, 20, 80) - 更灵敏
    - 中线：(14, 30, 70) - 标准设置
    - 长线：(21, 35, 65) - 更平滑
    """)


def show_bollinger_strategy():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-1">
                   <div class="metric-label">策略类型</div>
                   <div class="metric-value">波动性</div>
               </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-2">
                  <div class="metric-label">适用周期</div>
                  <div class="metric-value">日/周线</div>
              </div>
       """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-3">
                  <div class="metric-label">难度等级</div>
                  <div class="metric-value">⭐⭐⭐</div>
              </div>
       """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""
                   <div class="chart-header">
                       <span class="chart-icon">📖</span>
                       <span class="chart-title">策略原理</span>
                   </div>
          """, unsafe_allow_html=True)
    st.markdown("""
    布林带（Bollinger Bands）由John Bollinger在**1980年代**发明，是基于**统计学标准差**的动态通道指标

    **核心思想**：价格围绕均值波动，当偏离过大时会回归。通道宽度随波动性自动调整

    **计算公式**：
    - **中轨** = N日简单移动平均线（SMA）
    - **上轨** = 中轨 + K × N日标准差
    - **下轨** = 中轨 - K × N日标准差
    
    **默认参数**：N=20，K=2
    

    **统计意义**：价格有95%的概率在上下轨之间波动（假设正态分布）
    """)

    st.markdown(f"""
                       <div class="chart-header">
                           <span class="chart-icon">🎯</span>
                           <span class="chart-title">交易信号</span>
                       </div>
              """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🟢 买入信号
        **条件**：
        1. 价格**跌破下轨**后**反弹**
        2. **强买入**：反弹幅度 > 2%

        **原理**：价格超跌，均值回归
        """)

    with col2:
        st.markdown("""
        #### 🔴 卖出信号
        **条件**：
        1. 价格**突破上轨**后**回落**
        2. **强卖出**：回落幅度 > 2%

        **原理**：价格超涨，均值回归
        """)

    st.markdown(f"""
                          <div class="chart-header">
                              <span class="chart-icon">⚖️</span>
                              <span class="chart-title">优缺点</span>
                          </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **✅ 优点**
        - 动态调整，适应市场波动变化
        - 结合了价格和波动性两个维度
        - 特别适合波段交易
        - 可以识别超买超卖和趋势
        - 直观易懂，视觉化好
        """)

    with col2:
        st.markdown("""
        **❌ 缺点**
        - 强趋势中通道会持续扩张
        - 触及轨道不一定反转
        - 需要结合其他指标确认
        - 横盘时信号较少
        """)

    st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">💡</span>
                      <span class="chart-title">实战技巧</span>
                  </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    1. **通道收窄**：布林带变窄（Squeeze）预示即将出现大行情
    2. **通道扩张**：布林带变宽预示波动加剧
    3. **中轨作用**：
       - 上升趋势：价格常在中轨上方运行
       - 下降趋势：价格常在中轨下方运行
       - 中轨可作为支撑/压力位
    4. **骑墙走**：价格沿着上轨或下轨运行，说明趋势很强
    5. **W底和M顶**：
       - 价格两次触及下轨形成W底 → 买入
       - 价格两次触及上轨形成M顶 → 卖出
    6. **配合RSI**：触及下轨且RSI<30，买入信号更可靠
    """)

    st.markdown(f"""
              <div class="chart-header">
                  <span class="chart-icon">⚙️</span>
                  <span class="chart-title">参数说明</span>
              </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    | 参数 | 默认值 | 说明 |
    |------|--------|------|
    | period | 20 | 中轨周期 |
    | std_dev | 2.0 | 标准差倍数 |

    **参数调整**：
    - 通道太窄：增大std_dev（如2.5）
    - 通道太宽：减小std_dev（如1.5）
    - 更灵敏：减小period（如10）
    - 更平滑：增大period（如30）
    """)


def show_kdj_strategy():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-1">
                   <div class="metric-label">策略类型</div>
                   <div class="metric-value">超买超卖</div>
               </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-2">
                  <div class="metric-label">适用周期</div>
                  <div class="metric-value">日/周线</div>
              </div>
       """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-3">
                  <div class="metric-label">难度等级</div>
                  <div class="metric-value">⭐⭐</div>
              </div>
       """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""
                   <div class="chart-header">
                       <span class="chart-icon">📖</span>
                       <span class="chart-title">策略原理</span>
                   </div>
          """, unsafe_allow_html=True)
    st.markdown("""
    KDJ指标由George Lane在**1950年代**发明，又称**随机指标**（Stochastic Oscillator）

    **核心思想**：比较收盘价在最近一段时间内最高最低价区间的相对位置。上涨时收盘价趋向最高价，下跌时趋向最低价

    **计算公式**：
    ```
    RSV = (收盘价 - N日内最低价) / (N日内最高价 - N日内最低价) × 100
    K值 = RSV的M1日移动平均
    D值 = K值的M2日移动平均
    J值 = 3K - 2D
    ```

    **默认参数**：N=9, M1=3, M2=3

    **取值范围**：0-100（J值可能超出）
    """)

    st.markdown(f"""
                       <div class="chart-header">
                           <span class="chart-icon">🎯</span>
                           <span class="chart-title">交易信号</span>
                       </div>
              """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🟢 买入信号（金叉）
        **条件**：
        1. **K线上穿D线**（金叉）
        2. **强买入**：K和D都在20以下（深度超卖区）

        **原理**：超卖反弹，做多信号
        """)

    with col2:
        st.markdown("""
        #### 🔴 卖出信号（死叉）
        **条件**：
        1. **K线下穿D线**（死叉）
        2. **强卖出**：K和D都在80以上（深度超买区）

        **原理**：超买回落，做空信号
        """)

    st.markdown(f"""
                          <div class="chart-header">
                              <span class="chart-icon">⚖️</span>
                              <span class="chart-title">优缺点</span>
                          </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **✅ 优点**
        - 灵敏度高，反应迅速
        - 适合短线和波段交易
        - J值领先指标，提前预警
        - 超买超卖判断准确
        - 中国股市使用广泛
        """)

    with col2:
        st.markdown("""
        **❌ 缺点**
        - 震荡市场信号过多
        - 强趋势中会产生虚假信号
        - 需要频繁交易
        - 参数敏感
        """)

    st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">💡</span>
                      <span class="chart-title">实战技巧</span>
                  </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    1. **KDJ金叉死叉**：
       - 20以下金叉 → 强买入（超卖反弹）
       - 80以上死叉 → 强卖出（超买回落）
       - 50附近交叉 → 信号较弱，谨慎对待

    2. **J值应用**：
       - J值>100：严重超买，警惕回调
       - J值<0：严重超卖，可能反弹
       - J值领先K值和D值，可提前预警

    3. **钝化现象**：
       - 强势股：KDJ可能长期在高位钝化（>80）
       - 弱势股：KDJ可能长期在低位钝化（<20）
       - 钝化时不要盲目反向操作

    4. **背离信号**：
       - 价格创新高，KDJ不创新高 → 顶背离
       - 价格创新低，KDJ不创新低 → 底背离

    5. **配合趋势**：
       - 上升趋势：关注低位金叉
       - 下降趋势：关注高位死叉
    """)

    st.markdown(f"""
              <div class="chart-header">
                  <span class="chart-icon">⚙️</span>
                  <span class="chart-title">参数说明</span>
              </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    | 参数 | 默认值 | 说明 |
    |------|--------|------|
    | n | 9 | RSV计算周期 |
    | m1 | 3 | K值平滑参数 |
    | m2 | 3 | D值平滑参数 |
    | oversold | 20 | 超卖线 |
    | overbought | 80 | 超买线 |

    **参数调整**：
    - 短线：(5, 3, 3) - 更灵敏
    - 中线：(9, 3, 3) - 标准设置
    - 长线：(14, 5, 5) - 更平滑
    """)


def show_turtle_strategy():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-1">
                   <div class="metric-label">策略类型</div>
                   <div class="metric-value">突破系统</div>
               </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-2">
                  <div class="metric-label">适用周期</div>
                  <div class="metric-value">周/月线</div>
              </div>
       """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
              <div class="metric-sub-card metric-card-3">
                  <div class="metric-label">难度等级</div>
                  <div class="metric-value">⭐⭐⭐</div>
              </div>
       """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""
                   <div class="chart-header">
                       <span class="chart-icon">📖</span>
                       <span class="chart-title">策略原理</span>
                   </div>
          """, unsafe_allow_html=True)
    st.markdown("""
    海龟交易法则源自**1980年代**著名的"海龟交易实验", Richard Dennis和William Eckhardt通过训练新手证明交易可以被教授

    **核心思想**：基于唐奇安通道（Donchian Channels）的突破系统。当价格突破近期最高/最低价时，说明趋势可能形成

    **通道计算**：
    - **上轨** = 过去N天的最高价
    - **下轨** = 过去N天的最低价

    **ATR（平均真实波幅）**：
    ```
    TR = max(最高价-最低价, |最高价-昨收|, |最低价-昨收|)
    ATR = TR的N日移动平均
    ```

    ATR用于衡量市场波动性和信号强度。
    """)

    st.markdown(f"""
                       <div class="chart-header">
                           <span class="chart-icon">🎯</span>
                           <span class="chart-title">交易信号</span>
                       </div>
              """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🟢 买入信号（突破）
        **入场条件**：
        1. 收盘价**突破20日上轨**
        2. **强买入**：突破幅度 ≥ 0.5倍ATR

        **原理**：突破新高，趋势形成
        """)

    with col2:
        st.markdown("""
        #### 🔴 卖出信号（回落）
        **出场条件**：
        1. 多头**回落至10日下轨**
        2. 止损退出

        **原理**：跌破近期低点，趋势结束
        """)

    st.markdown(f"""
                          <div class="chart-header">
                              <span class="chart-icon">⚖️</span>
                              <span class="chart-title">优缺点</span>
                          </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **✅ 优点**
        - 经过实战验证的经典策略
        - 趋势跟踪能力极强
        - 风险控制明确（ATR止损）
        - 适合长线交易
        - 可应用于多个市场
        """)

    with col2:
        st.markdown("""
        **❌ 缺点**
        - 震荡市场频繁止损
        - 需要较长的观察周期
        - 入场较晚（确认突破后）
        - 胜率相对较低（约40-50%）
        - 需要严格纪律执行
        """)

    st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">💡</span>
                      <span class="chart-title">实战技巧</span>
                  </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    1. **原版海龟法则**：
       - 入场：突破20日最高价
       - 加仓：每上涨0.5ATR加仓一次（最多4次）
       - 止损：跌破2ATR止损
       - 出场：跌破10日最低价

    2. **通道选择**：
       - 系统1：20日通道入场，10日通道出场（激进）
       - 系统2：55日通道入场，20日通道出场（保守）

    3. **资金管理**：
       - 每次交易风险不超过账户的1-2%
       - 使用ATR计算仓位大小

    4. **市场选择**：
       - 最适合趋势明显的商品期货市场
       - 股票市场中选择强势股
       - 避免长期横盘的标的

    5. **心理准备**：
       - 接受连续止损（可能5-8次）
       - 耐心等待大趋势
       - 一次大趋势的盈利可以覆盖多次小亏损
    """)

    st.markdown(f"""
              <div class="chart-header">
                  <span class="chart-icon">⚙️</span>
                  <span class="chart-title">参数说明</span>
              </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    | 参数 | 默认值 | 说明 |
    |------|--------|------|
    | entry_window | 20 | 入场通道周期 |
    | exit_window | 10 | 出场通道周期 |
    | atr_period | 20 | ATR计算周期 |

    **经典组合**：
    - 激进：(20, 10, 20)
    - 保守：(55, 20, 20)
    - 超短：(10, 5, 14)
    """)


def show_cbr_strategy():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
                   <div class="metric-sub-card metric-card-1">
                       <div class="metric-label">策略类型</div>
                       <div class="metric-value">反转策略</div>
                   </div>
            """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
                  <div class="metric-sub-card metric-card-2">
                      <div class="metric-label">适用周期</div>
                      <div class="metric-value">周/月线</div>
                  </div>
           """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
                  <div class="metric-sub-card metric-card-3">
                      <div class="metric-label">难度等级</div>
                      <div class="metric-value">⭐⭐⭐⭐</div>
                  </div>
           """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""
                       <div class="chart-header">
                           <span class="chart-icon">📖</span>
                           <span class="chart-title">策略原理</span>
                       </div>
              """, unsafe_allow_html=True)
    st.markdown("""
    CBR（Confirmation-Based Reversal）是一种**基于价格形态和MACD确认的反转策略**

    **核心思想**：通过观察连续3天的K线形态变化，结合MACD指标确认，捕捉趋势反转的机会

    **时间窗口**：
    - **T-2**：前天
    - **T-1**：昨天
    - **T**：今天

    **双重确认机制**：
    1. 价格形态确认（K线相对位置变化）
    2. MACD指标确认（金叉/死叉）
    """)

    st.markdown(f"""
                   <div class="chart-header">
                       <span class="chart-icon">🎯</span>
                       <span class="chart-title">交易信号</span>
                   </div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🟢 买入信号（反转向上）
        **条件1（价格回落）**：
        - T-2的最高价 > T-1的最高价
        - T-2的最低价 > T-1的最低价

        **条件2（突破确认）**：
        - T的收盘价 > T-1的最高价
        **或** MACD金叉

        **原理**：价格先回落再突破，反转信号
        """)

    with col2:
        st.markdown("""
        #### 🔴 卖出信号（反转向下）
        **条件1（价格上涨）**：
        - T-2的最高价 < T-1的最高价
        - T-2的最低价 < T-1的最低价

        **条件2（跌破确认）**：
        - T的收盘价 < T-1的最低价
        **或** MACD死叉

        **原理**：价格先上涨再跌破，反转信号
        """)

    st.markdown(f"""
                          <div class="chart-header">
                              <span class="chart-icon">⚖️</span>
                              <span class="chart-title">优缺点</span>
                          </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **✅ 优点**
        - 捕捉反转机会，买在相对低点
        - 双重确认降低虚假信号
        - 适合震荡市和反转行情
        - 结合形态和指标，更可靠
        """)

    with col2:
        st.markdown("""
        **❌ 缺点**
        - 需要更长时间框架（至少3天）
        - 信号较少，等待时间长
        - 趋势市场中表现不佳
        - 判断较复杂，需要经验
        """)

    st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">💡</span>
                      <span class="chart-title">实战技巧</span>
                  </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    1. **最佳时机**：
       - 下跌趋势末期的反转向上
       - 上涨趋势末期的反转向下

    2. **结合趋势**：
       - 在长期上升趋势中，只做买入信号
       - 在长期下降趋势中，只做卖出信号

    3. **止损设置**：
       - 买入后：跌破T-1的最低价止损
       - 卖出后：突破T-1的最高价止损

    4. **周期选择**：
       - 日线：信号多但准确度较低
       - 周线：信号少但质量高（推荐）
       - 月线：信号非常少，适合长线

    5. **配合成交量**：
       - 反转信号伴随放量更可靠
       - 缩量反转需谨慎对待
    """)

    st.markdown(f"""
              <div class="chart-header">
                  <span class="chart-icon">📈</span>
                  <span class="chart-title">信号示例</span>
              </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    ```
    买入示例：
    T-2: 最高102, 最低98  (前天，较高位置)
    T-1: 最高100, 最低96  (昨天，回落)
    T:   收盘101          (今天，收盘突破昨日最高100)

    → 满足条件：回落后突破，买入信号！

    卖出示例：
    T-2: 最高98,  最低94  (前天，较低位置)
    T-1: 最高102, 最低98  (昨天，上涨)
    T:   收盘97           (今天，收盘跌破昨日最低98)

    → 满足条件：上涨后跌破，卖出信号！
    ```
    """)
