"""
买卖点分析UI - 详细展示分析过程和结果
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from datetime import datetime


def render_trading_analysis_ui(signals: List[Dict], df: pd.DataFrame, analyzer):
    """
    渲染买卖点分析的完整UI界面

    Args:
        signals: 生成的交易信号列表
        df: 股票数据DataFrame
        analyzer: TradingSignalAnalyzer实例
    """
    st.markdown("""
        <style>
        .analysis-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            color: white;
        }
        .analysis-card-green {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            color: white;
        }
        .analysis-card-red {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            color: white;
        }
        .step-header {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            border-bottom: 2px solid white;
            padding-bottom: 5px;
        }
        .metric-box {
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
        }
        .signal-badge-buy {
            background: #10b981;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
        }
        .signal-badge-sell {
            background: #ef4444;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
        }
        .signal-badge-strong {
            background: #f59e0b;
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
            margin-left: 10px;
        }
        .signal-badge-weak {
            background: #6b7280;
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
            margin-left: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # 顶部统计
    st.markdown("### 📊 信号统计")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("总信号数", len(signals))

    with col2:
        buy_signals = [s for s in signals if s['type'].code == 'BUY']
        st.metric("买入信号", len(buy_signals))

    with col3:
        sell_signals = [s for s in signals if s['type'].code == 'SELL']
        st.metric("卖出信号", len(sell_signals))

    with col4:
        strong_signals = [s for s in signals if s['strength'].code == 'STRONG']
        st.metric("强信号数", len(strong_signals))

    st.markdown("---")

    # 信号列表展示
    st.markdown("### 🎯 交易信号详情")

    if not signals:
        st.info("当前时间范围内没有生成交易信号")
        return

    # 按日期倒序排列，最新的在最前面
    signals_sorted = sorted(signals, key=lambda x: x['date'], reverse=True)

    for signal in signals_sorted:
        render_signal_detail(signal)

    st.markdown("---")

    # 逐日分析查询器
    st.markdown("### 🔍 逐日分析查询")
    st.markdown("选择日期查看该日的完整4步分析过程（即使没有生成信号）")

    # 日期选择器
    min_date = df['date'].min()
    max_date = df['date'].max()

    selected_date = st.date_input(
        "选择日期",
        value=max_date.date() if hasattr(max_date, 'date') else max_date,
        min_value=min_date.date() if hasattr(min_date, 'date') else min_date,
        max_value=max_date.date() if hasattr(max_date, 'date') else max_date
    )

    # 转换为pandas Timestamp
    selected_datetime = pd.Timestamp(selected_date)

    if st.button("查看该日分析", key="view_daily_analysis"):
        daily_analysis = analyzer.get_daily_analysis(selected_datetime)

        if daily_analysis:
            render_daily_analysis(daily_analysis)
        else:
            st.warning("该日期数据不足或不存在")


def render_signal_detail(signal: Dict):
    """渲染单个交易信号的详细信息"""

    signal_type = signal['type']
    strength = signal['strength']
    analysis = signal['analysis']
    date_str = signal['date'].strftime('%Y-%m-%d')
    action = signal.get('action', 'UNKNOWN')

    # 根据信号类型选择样式
    if signal_type.code == 'BUY':
        card_class = "analysis-card-green"
        badge_html = f'<span class="signal-badge-buy">🔴 买入信号</span>'
    else:
        card_class = "analysis-card-red"
        badge_html = f'<span class="signal-badge-sell">🟢 卖出信号</span>'

    strength_badge = f'<span class="signal-badge-strong">💪 强信号</span>' if strength.code == 'STRONG' else f'<span class="signal-badge-weak">弱信号</span>'

    # 动作标签
    action_text_map = {
        'ENTER_LONG': '【开多】',
        'EXIT_LONG': '【平多】',
        'ENTER_SHORT': '【开空】',
        'EXIT_SHORT': '【平空】'
    }
    action_text = action_text_map.get(action, '')

    with st.expander(f"📅 {date_str} - {action_text} 价格: ¥{signal['price']:.2f}", expanded=False):
        st.markdown(f"""
            <div class="{card_class}">
                <div style="margin-bottom: 15px;">
                    {badge_html}
                    {strength_badge}
                </div>
                <div class="metric-box">
                    <strong>📝 综合判断：</strong><br/>
                    {analysis['reason']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 四个步骤的详细展示
        st.markdown("#### 📊 四步分析详情")

        col1, col2 = st.columns(2)

        with col1:
            # 第一步：市场状态
            market_state = analysis['market_state']
            st.markdown("**① 市场状态判定（MACD + RSI）**")
            st.markdown(f"""
            - 方向：**{market_state['direction']}**
            - MACD位置：{market_state['macd_position']} ({market_state.get('macd_value', 'N/A')})
            - RSI状态：{market_state['rsi_state']} ({market_state.get('rsi_value', 'N/A'):.1f})
            - 置信度：{market_state['confidence']:.1%}
            """)

            # 第二步：关键区域
            key_area = analysis['key_area']
            st.markdown("**② 关键区域识别**")
            if key_area['is_key_area']:
                st.markdown(f"- 类型：**{key_area['area_type']}**")
                for reason in key_area['reasons']:
                    st.markdown(f"- {reason}")
            else:
                st.markdown("- 非关键区域")

        with col2:
            # 第三步：入场触发
            entry_trigger = analysis['entry_trigger']
            st.markdown("**③ 入场触发验证（K线+成交量）**")
            st.markdown(f"""
            - 触发状态：{'✅ 已触发' if entry_trigger['is_triggered'] else '❌ 未触发'}
            - 形态匹配：{'✅' if entry_trigger['pattern_matched'] else '❌'}
            - 成交量确认：{'✅' if entry_trigger['volume_confirmed'] else '❌'}
            - 成交量比：{entry_trigger['volume_ratio']:.2f}x
            """)
            if entry_trigger['pattern_info']:
                pattern = entry_trigger['pattern_info']
                st.markdown(f"- 形态：**{pattern['pattern_type'].text}**")

            # 第四步：风险过滤
            risk_filter = analysis['risk_filter']
            st.markdown("**④ 风险过滤（RSI背离）**")
            if risk_filter['has_risk']:
                st.markdown(f"""
                - ⚠️ 风险类型：**{risk_filter['risk_type']}**
                - 风险等级：{risk_filter['risk_level']}
                - 建议退出：{'是' if risk_filter['should_exit'] else '否'}
                - 成交量衰减：{'是' if risk_filter.get('volume_weakening') else '否'}
                """)
            else:
                st.markdown("- ✅ 无明显风险")


def render_daily_analysis(daily_analysis: Dict):
    """渲染指定日期的完整分析"""

    date_str = daily_analysis['date'].strftime('%Y-%m-%d')
    price = daily_analysis['price']

    st.markdown(f"### 📅 {date_str} 完整分析")
    st.markdown(f"**收盘价：¥{price:.2f}**")

    # 创建四个列来展示四个步骤
    st.markdown("---")

    # 第一步
    st.markdown("#### ① 市场状态判定（MACD + RSI）")
    market_state = daily_analysis['step1_market_state']

    col1, col2, col3 = st.columns(3)
    with col1:
        direction_emoji = {
            'LONG': '📈',
            'SHORT': '📉',
            'RANGING': '↔️'
        }
        st.metric(
            "市场方向",
            f"{direction_emoji.get(market_state['direction'], '')} {market_state['direction']}"
        )

    with col2:
        st.metric(
            "MACD位置",
            market_state['macd_position'],
            delta=f"{market_state.get('macd_value', 0):.3f}"
        )

    with col3:
        st.metric(
            "RSI状态",
            market_state['rsi_state'],
            delta=f"{market_state.get('rsi_value', 0):.1f}"
        )

    # 置信度进度条
    confidence = market_state['confidence']
    st.progress(confidence, text=f"置信度: {confidence:.1%}")

    st.markdown("**结论：**")
    if market_state['direction'] == 'LONG':
        st.success("✅ 可以考虑做多")
    elif market_state['direction'] == 'SHORT':
        st.error("✅ 可以考虑做空")
    else:
        st.warning("⚠️ 震荡期，建议观望")

    st.markdown("---")

    # 第二步
    st.markdown("#### ② 关键区域识别（K线形态 + 结构位置）")
    key_area = daily_analysis['step2_key_area']

    if key_area['is_key_area']:
        area_type_emoji = '🔺' if key_area['area_type'] == 'RESISTANCE' else '🔻'
        st.info(f"{area_type_emoji} **{key_area['area_type']}区域**")

        st.markdown("**原因：**")
        for reason in key_area['reasons']:
            st.markdown(f"- {reason}")

        if key_area['patterns']:
            st.markdown("**K线形态：**")
            for pattern in key_area['patterns']:
                st.markdown(f"- {pattern['pattern_type'].icon} {pattern['pattern_type'].text}")
    else:
        st.info("非关键区域")

    st.markdown("---")

    # 第三步
    st.markdown("#### ③ 入场触发验证（K线形态 + 成交量）")
    entry_trigger = daily_analysis['step3_entry_trigger']

    col1, col2, col3 = st.columns(3)
    with col1:
        status = "✅ 触发" if entry_trigger['is_triggered'] else "❌ 未触发"
        st.metric("触发状态", status)

    with col2:
        pattern_status = "✅ 匹配" if entry_trigger['pattern_matched'] else "❌ 未匹配"
        st.metric("形态匹配", pattern_status)

    with col3:
        volume_status = "✅ 确认" if entry_trigger['volume_confirmed'] else "❌ 未确认"
        st.metric("成交量", f"{entry_trigger['volume_ratio']:.2f}x")

    if entry_trigger['pattern_info']:
        pattern = entry_trigger['pattern_info']
        st.success(f"检测到形态：{pattern['pattern_type'].icon} **{pattern['pattern_type'].text}**")

    st.markdown("---")

    # 第四步
    st.markdown("#### ④ 风险过滤（RSI背离 + 成交量）")
    risk_filter = daily_analysis['step4_risk_filter']

    if risk_filter['has_risk']:
        risk_emoji = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🔴'
        }
        level_emoji = risk_emoji.get(risk_filter['risk_level'], '⚪')

        st.warning(f"{level_emoji} **风险等级：{risk_filter['risk_level']}**")
        st.markdown(f"- 风险类型：{risk_filter['risk_type']}")
        st.markdown(f"- 建议退出：{'是' if risk_filter['should_exit'] else '否'}")
        st.markdown(f"- 成交量衰减：{'是' if risk_filter.get('volume_weakening') else '否'}")
    else:
        st.success("✅ 无明显风险")

    st.markdown("---")

    # 最终建议
    st.markdown("#### 💡 最终建议")

    direction = market_state['direction']
    is_triggered = entry_trigger['is_triggered']
    has_high_risk = risk_filter['has_risk'] and risk_filter['risk_level'] == 'HIGH'

    if direction == 'RANGING':
        st.info("🤷 市场震荡，建议观望")
    elif direction == 'LONG' and is_triggered and not has_high_risk:
        st.success("🎯 建议做多入场")
    elif direction == 'SHORT' and is_triggered and not has_high_risk:
        st.error("🎯 建议做空入场")
    elif has_high_risk and risk_filter['should_exit']:
        st.warning("⚠️ 建议退出仓位")
    else:
        st.info("等待更好的入场机会")


def render_signal_summary_table(signals: List[Dict]):
    """渲染信号汇总表格"""

    if not signals:
        return

    # 准备表格数据
    table_data = []
    for signal in signals:
        analysis = signal['analysis']
        market_state = analysis['market_state']

        table_data.append({
            '日期': signal['date'].strftime('%Y-%m-%d'),
            '价格': f"¥{signal['price']:.2f}",
            '信号': '🔴 买入' if signal['type'].code == 'BUY' else '🟢 卖出',
            '强度': '💪 强' if signal['strength'].code == 'STRONG' else '弱',
            '动作': signal.get('action', 'N/A'),
            'MACD': f"{market_state.get('macd_value', 0):.3f}",
            'RSI': f"{market_state.get('rsi_value', 0):.1f}",
            '成交量比': f"{analysis['entry_trigger']['volume_ratio']:.2f}x" if 'entry_trigger' in analysis else 'N/A'
        })

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True)
