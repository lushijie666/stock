from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import func
import streamlit_echarts
from typing import List, Dict
from enums.candlestick_pattern import CandlestickPattern
from models.stock import Stock
from models.stock_history import get_history_model
from enums.history_type import StockHistoryType
from utils.chart import ChartBuilder
from utils.convert import format_dates, format_date_by_type
from utils.strategy import calculate_macd, calculate_multi_period_rsi
from utils.candlestick_pattern_detector import CandlestickPatternDetector


from utils.db import get_db_session
from utils.session import get_session_key, SessionKeys
from utils.trading_signal_analyzer import TradingSignalAnalyzer
from utils.trading_analysis_ui import render_trading_analysis_ui

KEY_PREFIX = "stock_chart"


@st.dialog("股票图表", width="large")
def show_detail_dialog(stock_code):
    with get_db_session() as session:
        stock = session.query(Stock).filter(Stock.code == stock_code).first()
        if stock:
            show_detail(stock)
        else:
            st.error(f"未找到股票代码为 {stock_code} 的股票信息")

def show_detail(stock):
    t = st.radio(
        "选择时间周期",
        ["天", "周", "月", "30分钟"],
        horizontal=True,
        key=f"{KEY_PREFIX}_{stock.code}_radio",
        label_visibility="collapsed"
    )
    handlers = {
        "天": lambda: show_page(stock, StockHistoryType.D),
        "周": lambda: show_page(stock, StockHistoryType.W),
        "月": lambda: show_page(stock, StockHistoryType.M),
        "30分钟": lambda: show_page(stock, StockHistoryType.THIRTY_M),
    }
    handlers.get(t, lambda: None)()

def show_page(stock, t: StockHistoryType):
    chart_type = st.radio(
        "选择功能",
        ["图表", "买卖点分析", "回测分析"],
        horizontal=True,
        key=f"{KEY_PREFIX}_{stock.code}_{t}_radio2",
        label_visibility="collapsed"
    )
    chart_handlers = {
        "图表": lambda: show_chart(stock, t),
        "买卖点分析": lambda: show_trading_analysis(stock, t),
        "回测分析": lambda: show_chart(stock, t)
    }
    chart_handlers.get(chart_type, lambda: None)()

def show_chart(stock, t: StockHistoryType):
    st.markdown(
        f"""
               <div class="table-header">
                   <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - 图表</div>
               </div>
               """,
        unsafe_allow_html=True
    )
    df, dates, k_line_data, volumes, extra_lines, ma_lines = _build_stock_chart_data(stock, t)


    st.markdown("""
          <div class="chart-header">
              <span class="chart-icon">🔍</span>
              <span class="chart-title">图表</span>
          </div>
      """, unsafe_allow_html=True)

    # 创建各个独立的图表
    # 1. 原始K线图
    kline_original = ChartBuilder.create_kline_chart(dates, k_line_data, df, ma_lines=ma_lines, extra_lines=extra_lines)

    # 2. 带形态的K线图
    candlestick_patterns = CandlestickPatternDetector.detect_all_patterns(df)
    # 转换形态数据用于图表显示
    pattern_markers = []
    for pattern in candlestick_patterns:
        pattern_type = pattern['pattern_type']
        marker_data = {
            'date': format_date_by_type(pattern['date'], t),
            'value': pattern['price'],
            'type': pattern_type.code,
            'name': pattern_type.text,
            'icon': pattern_type.icon,
            'color': pattern_type.color,
            'offset': pattern_type.offset,
            'description': pattern['description']
        }
        if 'start_index' in pattern and 'end_index' in pattern:
            marker_data['start_index'] = pattern['start_index']
            marker_data['end_index'] = pattern['end_index']
        if 'window_top' in pattern:
            marker_data['window_top'] = pattern['window_top']
        if 'window_bottom' in pattern:
            marker_data['window_bottom'] = pattern['window_bottom']
        pattern_markers.append(marker_data)
    kline_pattern = ChartBuilder.create_kline_chart(dates, k_line_data, df, ma_lines=ma_lines, extra_lines=extra_lines, candlestick_patterns=pattern_markers)

    # 3. 成交量图
    volume_bar = ChartBuilder.create_volume_bar(dates, volumes, df)

    # 4. MACD图表
    # 计算MACD指标
    macd_data = {}
    if len(df) > 0:
        macd_df = calculate_macd(df)
        macd_data = {
            'dif': macd_df['DIFF'].tolist(),
            'dea': macd_df['DEA'].tolist(),
            'macd': macd_df['MACD_hist'].tolist()
        }
    macd_chart = None
    if macd_data and 'dif' in macd_data:
        macd_chart = ChartBuilder.create_macd_chart(
            dates,
            macd_data['dif'],
            macd_data['dea'],
            macd_data['macd']
        )

    # 5. RSI图表
    # 计算RSI指标
    rsi_data = {}
    if len(df) > 0:
        rsi_df = calculate_multi_period_rsi(df, periods=[6, 12, 24])
        for col in rsi_df.columns:
            rsi_data[col] = rsi_df[col].tolist()

    rsi_chart = None
    if rsi_data:
        rsi_chart = ChartBuilder.create_rsi_chart(dates, rsi_data)

    # 配置图表联动 - 使用具体像素值布局（总高度2000px）
    charts_config = [
        {
            "chart": kline_original,
            "grid_pos": {"pos_top": "60px", "height": "350px"},
            "title": "原始K线图",
            "show_tooltip": False,
            "legend_height": "310px"  # 图例区域高度，防止溢出到下一个图表
        },
        {
            "chart": kline_pattern,
            "grid_pos": {"pos_top": "450px", "height": "350px"},
            "title": "K线图（含形态）",
            "show_tooltip": True,
            "legend_height": "310px"
        },
        {
            "chart": volume_bar,
            "grid_pos": {"pos_top": "840px", "height": "240px"},
            "title": "成交量",
            "show_tooltip": True,
            "legend_height": "200px"
        }
    ]

    # 添加MACD图表（如果有数据）
    if macd_chart:
        charts_config.append({
            "chart": macd_chart,
            "grid_pos": {"pos_top": "1120px", "height": "240px"},
            "title": "MACD",
            "show_tooltip": True,
            "legend_height": "200px"
        })

    # 添加RSI图表（如果有数据）
    if rsi_chart:
        charts_config.append({
            "chart": rsi_chart,
            "grid_pos": {"pos_top": "1400px", "height": "240px"},
            "title": "RSI",
            "show_tooltip": True,
            "legend_height": "200px"
        })

    # 创建联动图表
    total_height = "1400px" if len(charts_config) <= 3 else "1700px"
    linked_chart = ChartBuilder.create_linked_charts(charts_config, total_height=total_height)

    # 显示联动图表
    streamlit_echarts.st_pyecharts(linked_chart, theme="white", height=total_height, key=f"{KEY_PREFIX}_{stock.code}_{t}_linked_chart")

    # 显示形态表格
    _build_stock_patterns_tables(t, df, candlestick_patterns)


def show_trading_analysis(stock, t: StockHistoryType):
    """
    显示买卖点分析页面
    """
    st.markdown(
        f"""
               <div class="table-header">
                   <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - 买卖点分析</div>
               </div>
               """,
        unsafe_allow_html=True
    )

    # 获取股票数据
    df = _get_stock_history_data(stock, t)

    # 检查数据是否充足
    min_required = 120  # 预热天数
    if len(df) < min_required:
        st.warning(f"""
        数据不足，无法进行买卖点分析

        - 当前数据：{len(df)} 个周期
        - 最少需要：{min_required} 个周期
        - 还需要：{min_required - len(df)} 个周期

        **原因说明：**
        - MA60均线需要60天数据
        - 前期高低点分析需要回看20天
        - RSI背离检测需要回看10天
        - 额外缓冲确保指标稳定：30天

        **建议：**
        - 等待更多交易日数据积累
        - 或切换到周线/月线周期（需要数据量更少）
        """)
        return

    # 如果数据充足但不够多，给出提示
    if len(df) < 200:
        st.info(f"""
        ℹ️ 当前数据量：{len(df)} 个周期

        建议数据量：200个周期以上（约9个月）可以获得更准确的分析结果。
        当前可以分析，但历史数据越多，趋势判断越准确。
        """)

    # 创建分析器
    try:
        with st.spinner("正在分析买卖点..."):
            analyzer = TradingSignalAnalyzer(df)
            signals, stats = analyzer.analyze()

        st.markdown("""
            <div class="chart-header">
                <span class="chart-icon">🎯</span>
                <span class="chart-title">买卖点分析</span>
            </div>
        """, unsafe_allow_html=True)

        # 显示策略说明
        with st.expander("📖 分析策略说明", expanded=False):
            st.markdown("""
            ### 四层级买卖点分析体系

            本分析系统采用多层级指标体系，严格筛选高质量交易信号：

            #### ① 市场状态判定（MACD + RSI）
            - **MACD在0轴上方** → 只考虑做多
            - **MACD在0轴下方** → 只考虑做空
            - **MACD贴着0轴来回** → 震荡，不交易
            - **RSI > 55** → 多头趋势
            - **RSI < 45** → 空头趋势
            - **45-55** → 震荡

            #### ② 关键区域识别（K线形态 + 结构位置）
            寻找关键的支撑/阻力位：
            - 均线支撑/阻力（MA5/10/20/60）
            - 前期高低点
            - 重要K线形态出现的位置

            #### ③ 入场触发验证（K线形态 + 成交量）
            验证信号的有效性：
            - K线形态必须与方向一致
            - 成交量必须放大（≥1.3倍5日均量）
            - 重要形态：吞没、启明星/黄昏星、锤子线、流星线等

            #### ④ 风险过滤（RSI背离 + 成交量）
            识别潜在风险：
            - **顶背离**：价格创新高，RSI不创新高 → 做多风险
            - **底背离**：价格创新低，RSI不创新低 → 做空风险
            - 成交量衰减 → 警惕反转

            ### 核心原则
            > 在 MACD 与 RSI 同向的趋势中，只在关键结构位，出现放量的 K 线反转形态时入场；
            > 当 RSI 背离且量能衰减时退出。
            """)

        # 渲染分析结果UI
        render_trading_analysis_ui(signals, df, analyzer, stats)

    except Exception as e:
        st.error(f"分析过程中出现错误: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


def _build_stock_chart_data(stock, t: StockHistoryType):
    df = _get_stock_history_data(stock, t)
    dates = format_dates(df, t)
    k_line_data = df[['opening', 'closing', 'lowest', 'highest']].values.tolist()
    volumes = df['turnover_count'].tolist()
    max_highest, min_lowest = _get_stock_history_lately_max_min(stock, t, 180)
    extra_lines = {}
    if max_highest is not None:
        extra_lines['阻力线(半年)'] = {
            'values': [max_highest] * len(dates),  # 阻力线
            'color': '#ef232a'  # 红色
        }
    if min_lowest is not None:
        extra_lines['支撑线(半年)'] = {
            'values': [min_lowest] * len(dates),  # 支撑线
            'color': '#14b143'  # 绿色
        }
    ma_lines = {}
    if len(df) > 0:
        # 短期均线
        if len(df) >= 5:
            ma_lines['MA5'] = df['closing'].rolling(window=5, min_periods=1).mean().round(2).tolist()
        if len(df) >= 10:
            ma_lines['MA10'] = df['closing'].rolling(window=10, min_periods=1).mean().round(2).tolist()
        # 中期均线
        if len(df) >= 20:
            ma_lines['MA20'] = df['closing'].rolling(window=20, min_periods=1).mean().round(2).tolist()
        if len(df) >= 30:
            ma_lines['MA30'] = df['closing'].rolling(window=30, min_periods=1).mean().round(2).tolist()
        # 长期均线
        if len(df) >= 60:
            ma_lines['MA60'] = df['closing'].rolling(window=60, min_periods=1).mean().round(2).tolist()

    return df, dates, k_line_data, volumes, extra_lines, ma_lines


def _build_stock_patterns_tables(t: StockHistoryType, df, candlestick_patterns: List[Dict]):
    # 显示形态信息表格
    if candlestick_patterns:
        st.markdown("""
                      <div class="chart-header">
                          <span class="chart-icon">🔍</span>
                          <span class="chart-title">形态信息</span>
                      </div>
                  """, unsafe_allow_html=True)

        # 构建表格数据
        pattern_table_data = []
        pattern_counts = {}
        for pattern in candlestick_patterns:
            # 构建日期字符串（包含所有涉及的K线日期）
            if 'start_index' in pattern and 'end_index' in pattern:
                start_idx = pattern['start_index']
                end_idx = pattern['end_index']
                pattern_dates = []
                pattern_opens = []
                pattern_closes = []
                pattern_lows = []
                pattern_highs = []
                pattern_changes = []
                # 获取形态涉及的所有日期
                pattern_dates = []
                for idx in range(start_idx, end_idx + 1):
                    if idx < len(df):
                        date_str = format_date_by_type(df.iloc[idx]['date'], t)
                        pattern_dates.append(date_str)
                        pattern_opens.append(f"{df.iloc[idx]['opening']:.2f}")
                        pattern_closes.append(f"{df.iloc[idx]['closing']:.2f}")
                        pattern_lows.append(f"{df.iloc[idx]['lowest']:.2f}")
                        pattern_highs.append(f"{df.iloc[idx]['highest']:.2f}")
                        pattern_changes.append(f"{df.iloc[idx]['change_amount']:.2f}")
                date_display = ' → '.join(pattern_dates)
                open_display = ' → '.join(pattern_opens)
                close_display = ' → '.join(pattern_closes)
                low_display = ' → '.join(pattern_lows)
                high_display = ' → '.join(pattern_highs)
                change_display = ' → '.join(pattern_changes)
            else:
                # 单K线形态，只显示一个日期
                date_display = format_date_by_type(pattern['date'], t)
                open_display = f"{pattern['row']['opening']:.2f}"
                close_display = f"{pattern['row']['closing']:.2f}"
                low_display = f"{pattern['row']['lowest']:.2f}"
                high_display = f"{pattern['row']['highest']:.2f}"
                change_display = f"{pattern['row']['change_amount']:.2f}"
            pattern_table_data.append({
                '日期': date_display,
                '形态': f"{pattern['pattern_type'].icon} {pattern['pattern_type'].text}",
                '开盘价': open_display,
                '收盘价': close_display,
                '最低价': low_display,
                '最高价': high_display,
                '涨跌额': change_display,
                '说明': pattern['description']
            })
            pattern_type = pattern['pattern_type']
            pattern_type_text = pattern_type.text
            if pattern_type_text in pattern_counts:
                pattern_counts[pattern_type_text] += 1
            else:
                pattern_counts[pattern_type_text] = 1

        # 创建枚举顺序映射
        enum_order = {enum.text: i for i, enum in enumerate(CandlestickPattern)}
        # 按照枚举顺序对形态计数进行排序
        sorted_patterns = sorted(pattern_counts.items(), key=lambda x: enum_order.get(x[0], float('inf')))
        # 计算需要的行数
        items_per_row = 4
        rows = (len(sorted_patterns) + items_per_row - 1) // items_per_row
        for row_idx in range(rows):
            start_idx = row_idx * items_per_row
            end_idx = min(start_idx + items_per_row, len(sorted_patterns))
            current_row = sorted_patterns[start_idx:end_idx]
            # 创建每行的4列布局
            cols = st.columns(items_per_row)
            for col_idx, (pattern_name, count) in enumerate(current_row):
                with cols[col_idx]:
                    st.markdown(f"""
                                    <div class="metric-sub-card metric-card-{row_idx * items_per_row + col_idx + 1}">
                                        <div class="metric-label">{pattern_name}</div>
                                        <div class="metric-value">{count}</div>
                                    </div>
                            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        # 显示表格
        pattern_df = pd.DataFrame(pattern_table_data)
        st.dataframe(
            pattern_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(pattern_df) * 35 + 38)
        )

    # 形态算法说明
    st.markdown(f"""
                    <div class="chart-header">
                        <span class="chart-icon">🔮</span>
                        <span class="chart-title">形态算法</span>
                    </div>
            """, unsafe_allow_html=True)

    # 从检测器获取算法信息
    pattern_algorithm_infos = CandlestickPatternDetector.get_pattern_algorithm_info()

    # 每行显示2个形态卡片
    items_per_row = 2
    rows = (len(pattern_algorithm_infos) + items_per_row - 1) // items_per_row

    for row_idx in range(rows):
        start_idx = row_idx * items_per_row
        end_idx = min(start_idx + items_per_row, len(pattern_algorithm_infos))
        current_row = pattern_algorithm_infos[start_idx:end_idx]

        current_row_max_criteria = max(len(pattern['criteria']) for pattern in current_row) if current_row else 0
        # 创建列布局
        info_cols = st.columns(items_per_row)
        for col_idx, pattern_info in enumerate(current_row):
            with info_cols[col_idx]:
                pattern_type = pattern_info['pattern_type']
                category = pattern_info['category']
                signal = pattern_info['signal']
                criteria = pattern_info['criteria']
                color_class = pattern_info['color_class']

                padded_criteria = criteria + [''] * (current_row_max_criteria - len(criteria))
                criteria_html = '<br>'.join(
                    [f"🗳 {criterion}" if criterion else "&nbsp;" for criterion in padded_criteria])
                st.markdown(f"""
                        <div class="sync-button-card {color_class}">
                            <div class="sync-card-icon {color_class}">
                                <span class="sync-icon-large">{pattern_type.icon}</span>
                            </div>
                            <div class="sync-card-content">
                                <div class="sync-card-title">{pattern_type.text}  -  {category}  -  {signal}</div>
                                <div class="sync-card-desc">{criteria_html}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

def _get_stock_history_data(stock, t: StockHistoryType) -> pd.DataFrame:
    model = get_history_model(t)
    try:
        with get_db_session() as session:
            # 获取该股票的最早和最晚日期
            date_range = session.query(
                func.min(model.date),
                func.max(model.date)
            ).filter(
                model.code == stock.code,
                model.removed == False
            ).first()
            if not date_range or None in date_range:
                st.warning("没有找到数据")
                return pd.DataFrame()
            min_date, max_date = date_range
            default_start_date = t.get_default_start_date(max_date, min_date)
            key_prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_{t}',category=stock.category)
            start_date_key = f"{key_prefix}_start_date"
            end_date_key = f"{key_prefix}_end_date"

            if start_date_key not in st.session_state:
                st.session_state[start_date_key] = default_start_date
            if end_date_key not in st.session_state:
                st.session_state[end_date_key] = max_date
            # 添加日期选择器
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "开始日期",
                    min_value=min_date,
                    max_value=max_date,
                    key=start_date_key
                )
                if start_date != st.session_state[start_date_key]:
                    st.session_state[start_date_key] = start_date
            with col2:
                end_date = st.date_input(
                    "结束日期",
                    min_value=min_date,
                    max_value=max_date,
                    key=end_date_key
                )
                if end_date != st.session_state[end_date_key]:
                    st.session_state[end_date_key] = end_date
            # 从数据库获取数据
            query = session.query(
                model.date,
                model.opening,
                model.highest,
                model.lowest,
                model.closing,
                model.turnover_count,
                model.turnover_amount,
                model.change,
                model.change_amount,
                model.turnover_ratio
            ).filter(
                model.code == stock.code,
                model.removed == False,
                model.date >= start_date,
                model.date <= datetime.combine(end_date, time.max)  # 结束日期包含 23:59:59
            ).order_by(model.date)
            # 读取数据到DataFrame
            return pd.read_sql(query.statement, session.bind)
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")
    return pd.DataFrame()

def _get_stock_history_lately_max_min(stock, t: StockHistoryType, days: int):
    model = get_history_model(t)
    with get_db_session() as session:
        latest_date = session.query(func.max(model.date)).filter(
            model.code == stock.code,
            model.removed == False
        ).scalar()
        if latest_date:
            days_ago = latest_date - timedelta(days=days)
            result = session.query(
                func.max(model.highest).label('max_high'),
                func.min(model.lowest).label('min_low')
            ).filter(
                model.code == stock.code,
                model.date >= days_ago,
                model.date <= latest_date,
                model.removed == False
            ).first()
            if result:
                return result.max_high, result.min_low
            else:
                return None, None
    return None, None
