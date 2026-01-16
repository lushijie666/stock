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
from utils.pagination import paginate_dataframe

from utils.db import get_db_session
from utils.session import get_session_key, SessionKeys
from utils.trading_signal_analyzer import TradingSignalAnalyzer

KEY_PREFIX = "stock_chart"


@st.dialog("股票图表详情", width="large")
def show_detail_dialog(stock_code):
    with get_db_session() as session:
        stock = session.query(Stock).filter(Stock.code == stock_code).first()
        if stock:
            show_detail(stock)
        else:
            st.error(f"未找到股票代码为 {stock_code} 的股票信息")

@st.dialog("股票图表", width="large")
def show_chart_dialog(stock_code):
    with get_db_session() as session:
        stock = session.query(Stock).filter(Stock.code == stock_code).first()
        if stock:
            show_chart(stock, StockHistoryType.D, key_suffix="dialog")
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
        ["图表", "买卖点", "回测"],
        horizontal=True,
        key=f"{KEY_PREFIX}_{stock.code}_{t}_radio2",
        label_visibility="collapsed"
    )
    chart_handlers = {
        "图表": lambda: show_chart(stock, t),
        "买卖点": lambda: show_trading_analysis(stock, t),
        "回测": lambda: show_chart(stock, t)
    }
    chart_handlers.get(chart_type, lambda: None)()

def show_chart(stock, t: StockHistoryType, key_suffix: str = ""):
    st.markdown(
        f"""
               <div class="table-header">
                   <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - 图表</div>
               </div>
               """,
        unsafe_allow_html=True
    )
    # 获取数据
    df, dates, k_line_data, volumes, extra_lines, ma_lines, macd_data, rsi_data = _build_stock_chart_data(stock, t, key_suffix)
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
    macd_chart = None
    if macd_data and 'dif' in macd_data:
        macd_chart = ChartBuilder.create_macd_chart(
            dates,
            macd_data['dif'],
            macd_data['dea'],
            macd_data['hist']
        )

    # 5. RSI图表
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
    chart_key = f"{KEY_PREFIX}_{stock.code}_{t}_linked_chart"
    if key_suffix:
        chart_key = f"{KEY_PREFIX}_{key_suffix}_{stock.code}_{t}_linked_chart"
    streamlit_echarts.st_pyecharts(linked_chart, theme="white", height=total_height, key=chart_key)

    # 显示形态信息
    _build_stock_patterns_info(t, df, candlestick_patterns)


def show_trading_analysis(stock, t: StockHistoryType):
    st.markdown(
        f"""
               <div class="table-header">
                   <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - 买卖点分析</div>
               </div>
               """,
        unsafe_allow_html=True
    )
    df = _get_stock_history_data(stock, t)
    is_analyze = True
    # 检查数据是否充足
    min_required = 120  # 预热天数
    if len(df) < min_required:
        st.caption(f""" 🔴数据不足，无法进行买卖点分析。当前数据两：{len(df)}个周期，最少需要：{min_required} 个周期，还需要：{min_required - len(df)} 个周期""")
        st.caption(f""" 🟢MA60均线需要60天数据、高低点分析需要回看20天、RSI背离检测需要回看10天、额外缓冲确保指标稳定：30天""")
        is_analyze =  False
    # 如果数据充足但不够多，给出提示
    if min_required < len(df) < 200:
        st.caption(f""" 🔴当前可以分析，但历史数据越多，趋势判断越准确。当前数据量：{len(df)}个周期，建议数据量：200个周期以上（约9个月）可以获得更准确的分析结果 """)
    if is_analyze :
        analyzer = TradingSignalAnalyzer(df)
        result = analyzer.analyze()
        # 解包新的数据结构
        signals = result['signals']
        stats = result['statistics']
        daily_analysis = result['daily_analysis']

        # 显示数据范围信息
        if 'warmup_days' in stats:
            warmup_days = stats['warmup_days']
            pre_warmup_end_date = df.iloc[warmup_days - 1]['date'].strftime('%Y-%m-%d')
            total_data = len(df)
            analysis_days = stats['total_days']
            st.caption(f""" 📅 当前数据量：共{total_data}个周期，使用前{warmup_days}天（{df.iloc[0]['date'].strftime('%Y-%m-%d')} 至 {pre_warmup_end_date}）作为指标预热，实际分析{analysis_days}天（{df.iloc[warmup_days]['date'].strftime('%Y-%m-%d')} 至 {df.iloc[-1]['date'].strftime('%Y-%m-%d')}）""")

        # 信号
        _build_stock_trading_analysis_single_info(stock, t, signals, stats)

        # 第一阶段（市场状态判定）
        _build_stock_trading_analysis_step1_info(stock, t, signals, stats)

        # 第二阶段（关键区域识别）
        _build_stock_trading_analysis_step2_info(stock, t, signals, stats)

        # 第三阶段（入场触发验证）
        _build_stock_trading_analysis_step3_info(stock, t, signals, stats)

        # 第四阶段（风险过滤）
        _build_stock_trading_analysis_step4_info(stock, t, signals, stats)

        # 统计信息
        _build_stock_trading_analysis_analysis_info(stock, t, signals, stats, daily_analysis)

    # 渲染分析结果UI
    # render_trading_analysis_ui(signals, df, analyzer, stats, daily_analysis)

    # 策略算法说明
    _build_stock_trading_analysis_algorithm_info()



def _build_stock_chart_data(stock, t: StockHistoryType, key_suffix: str = ""):
    df = _get_stock_history_data(stock, t, key_suffix)
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

    macd_data = {}
    if len(df) > 0:
        macd_df = calculate_macd(df)
        macd_data = {
            'dif': macd_df['DIFF'].tolist(),
            'dea': macd_df['DEA'].tolist(),
            'hist': macd_df['MACD_hist'].tolist()
        }
        df['MACD_DIFF'] = macd_df['DIFF']
        df['MACD_DEA'] = macd_df['DEA']
        df['MACD_HIST'] = macd_df['MACD_hist']
    rsi_data = {}
    if len(df) > 0:
        rsi_df = calculate_multi_period_rsi(df, periods=[6, 12, 24])
        for col in rsi_df.columns:
            df[col] = rsi_df[col]
            rsi_data[col] = rsi_df[col].tolist()

    return df, dates, k_line_data, volumes, extra_lines, ma_lines, macd_data, rsi_data


def _build_stock_patterns_info(t: StockHistoryType, df, candlestick_patterns: List[Dict]):
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
            height=min(600, len(pattern_df) * 35 + 38)
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

def _build_stock_trading_analysis_single_info(stock, t: StockHistoryType, signals, stats):
    # 信号信息
    st.markdown(f"""
                   <div class="chart-header">
                       <span class="chart-icon">⭕</span>
                       <span class="chart-title">信号信息</span>
                   </div>
            """, unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
                        <div class="metric-sub-card metric-card-20">
                            <div class="metric-label">总信号数</div>
                            <div class="metric-value">{stats['signal_days']}</div>
                        </div>
                """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
                        <div class="metric-sub-card metric-card-21">
                            <div class="metric-label">买信号(强/中/弱)</div>
                            <div class="metric-value">{stats['strong_buy_signals']}/{stats['medium_buy_signals']}/{stats['weak_buy_signals']}</div>
                        </div>
                """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
                        <div class="metric-sub-card metric-card-25">
                            <div class="metric-label">卖信号(强/中/弱)</div>
                            <div class="metric-value">{stats['strong_sell_signals']}/{stats['medium_sell_signals']}/{stats['weak_sell_signals']}</div>
                        </div>
                """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
                        <div class="metric-sub-card metric-card-26">
                            <div class="metric-label">卖出平多</div>
                            <div class="metric-value">{stats['exit_long_signals']}</div>
                        </div>
                """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
                        <div class="metric-sub-card metric-card-23">
                            <div class="metric-label">买入平空</div>
                            <div class="metric-value">{stats['exit_short_signals']}</div>
                        </div>
                """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # 构建信号数据
    signals_table_data = []
    for r in signals:
        signals_table_data.append({
            '类型': r['show_text'],
            '分数': r['score'],
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            '分数构成': '｜'.join(r['score_breakdowns']),
            '说明': '｜'.join(r['reasons']),
        })

    if len(signals_table_data) > 0:
        singles_df = pd.DataFrame(signals_table_data)
        columns_config = {
            '类型': st.column_config.TextColumn('类型', width='small'),
            '分数': st.column_config.NumberColumn('分数', width='small'),
            '日期': st.column_config.TextColumn('日期', width='small'),
            '收盘价': st.column_config.TextColumn('收盘价', width='small'),
            '分数构成': st.column_config.TextColumn('分数构成', width='medium'),
            '说明': st.column_config.TextColumn('说明', width='large'),
        }
        # 定义行选择处理函数
        def handle_row_select(selected_rows):
            if selected_rows:
                show_chart_dialog(stock.code)

        # 使用 paginate_dataframe 展示数据
        paginate_dataframe(
            data=singles_df,
            columns_config=columns_config,
            title="",
            key_prefix=f"{KEY_PREFIX}_{stock.code}_{t}_signals_chart",
            on_row_select=handle_row_select
        )

def _build_stock_trading_analysis_step1_info(stock, t, signals, stats):
    st.markdown(f"""
               <div class="chart-header">
                   <span class="chart-icon">⓵</span>
                   <span class="chart-title">市场状态分析</span>
               </div>
    """, unsafe_allow_html=True)
    col11, col12, col13, col14, col15 = st.columns(5)
    with col11:
        st.markdown(f"""
                       <div class="metric-sub-card metric-card-26">
                           <div class="metric-label">总天数</div>
                           <div class="metric-value">{stats['total_days']}</div>
                       </div>
               """, unsafe_allow_html=True)
    with col12:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-27">
                    <div class="metric-label">震荡天数</div>
                    <div class="metric-value">{stats['ranging_days']} / {stats['ranging_days']/stats['total_days']*100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col13:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-28">
                    <div class="metric-label">趋势天数</div>
                    <div class="metric-value">{stats['trend_days']} / {stats['trend_days']/stats['total_days']*100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col14:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-29">
                    <div class="metric-label">做多天数</div>
                    <div class="metric-value">{stats['long_days']} / {stats['long_days']/stats['total_days']*100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col15:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-30">
                    <div class="metric-label">做空天数</div>
                    <div class="metric-value">{stats['short_days']} / {stats['short_days']/stats['total_days']*100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    step1_table_data = []
    for r in stats['long_reasons']:
        step1_table_data.append({
            '类型': "做多",
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            'MACD': f"{r['macd']:.2f}",
            'RSI': f"{r['rsi']:.2f}",
            '说明': '｜'.join(r['reasons']),
        })
    for r in stats['short_reasons']:
        step1_table_data.append({
            '类型': "做空",
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            'MACD': f"{r['macd']:.2f}",
            'RSI': f"{r['rsi']:.2f}",
            '说明': '｜'.join(r['reasons']),
        })
    for r in stats['ranging_reasons']:
        step1_table_data.append({
            '类型': "震荡",
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            'MACD': f"{r['macd']:.2f}",
            'RSI': f"{r['rsi']:.2f}",
            '说明': '｜'.join(r['reasons']),
        })
    if len(step1_table_data) > 0:
        step1_df = pd.DataFrame(step1_table_data)
        st.dataframe(
            step1_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(step1_df) * 35 + 38)
        )

def _build_stock_trading_analysis_step2_info(stock, t, signals, stats):
    st.markdown(f"""
           <div class="chart-header">
               <span class="chart-icon">⓶</span>
               <span class="chart-title">关键区域分析</span>
           </div>
    """, unsafe_allow_html=True)
    col21, col22, col23, col24 = st.columns(4)
    with col21:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-36">
                    <div class="metric-label">MA均线天数</div>
                    <div class="metric-value">{stats['key_area_ma_days']} / {stats['key_area_ma_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col22:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-37">
                    <div class="metric-label">接近前期高点天数</div>
                    <div class="metric-value">{stats['key_area_past_high_days']} / {stats['key_area_past_high_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col23:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-38">
                    <div class="metric-label">接近前期低点天数</div>
                    <div class="metric-value">{stats['key_area_past_low_days']} / {stats['key_area_past_low_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col24:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-39">
                    <div class="metric-label">K线形态天数</div>
                    <div class="metric-value">{stats['key_area_candlestick_pattern_days']} / {stats['key_area_candlestick_pattern_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    step2_table_data = []
    for r in stats['key_area_reasons']:
        step2_table_data.append({
            '类型': "|".join(r['chinese_all_types']),
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            '说明': '｜'.join(r['reasons'])
        })
    if len(step2_table_data) > 0:
        step2_df = pd.DataFrame(step2_table_data)
        st.dataframe(
            step2_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(step2_df) * 35 + 38)
        )

def _build_stock_trading_analysis_step3_info(stock, t, signals, stats):
    st.markdown(f"""
               <div class="chart-header">
                   <span class="chart-icon">⓷</span>
                   <span class="chart-title">入场触发分析</span>
               </div>
        """, unsafe_allow_html=True)
    col31, col32, col33, col34, col35 = st.columns(5)
    with col31:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-1">
                    <div class="metric-label">全匹配天数</div>
                    <div class="metric-value">{stats['triggered_days']} / {stats['triggered_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col32:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-2">
                    <div class="metric-label">K线形态匹配天数</div>
                    <div class="metric-value">{stats['pattern_matched_days']} / {stats['pattern_matched_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col33:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-3">
                    <div class="metric-label">仅K线形态匹配天数</div>
                    <div class="metric-value">{stats['only_pattern_matched_days']} / {stats['only_pattern_matched_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col34:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-4">
                   <div class="metric-label">交易量匹配天数</div>
                   <div class="metric-value">{stats['volume_confirmed_days']} / {stats['volume_confirmed_days'] / stats['total_days'] * 100:.1f}%</div>
               </div>
       """, unsafe_allow_html=True)
    with col35:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-5">
                    <div class="metric-label">仅交易量匹配天数</div>
                    <div class="metric-value">{stats['only_volume_confirmed_days']} / {stats['only_volume_confirmed_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    step3_table_data = []
    for r in stats['triggered_reasons']:
        step3_table_data.append({
            '类型': "全匹配",
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            '说明': '｜'.join(r['reasons']),
        })
    for r in stats['not_triggered_reasons']:
        step3_table_data.append({
            '类型': "未全匹配",
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            '说明': '｜'.join(r['reasons']),
        })
    if len(step3_table_data) > 0:
        step3_df = pd.DataFrame(step3_table_data)
        st.dataframe(
            step3_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(step3_df) * 35 + 38)
        )

def _build_stock_trading_analysis_step4_info(stock, t, signals, stats):
    st.markdown(f"""
          <div class="chart-header">
              <span class="chart-icon">⓸</span>
              <span class="chart-title">风险过滤分析</span>
          </div>
   """, unsafe_allow_html=True)
    col41, col42, col43, col44 = st.columns(4)
    with col41:
        st.markdown(f"""
                <div class="metric-sub-card metric-card-11">
                    <div class="metric-label">风险天数</div>
                    <div class="metric-value">{stats['has_risk_days']} / {stats['has_risk_days'] / stats['total_days'] * 100:.1f}%</div>
                </div>
        """, unsafe_allow_html=True)
    with col42:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-12">
                   <div class="metric-label">顶背离天数</div>
                   <div class="metric-value">{stats['bearish_divergence_days']} / {stats['bearish_divergence_days'] / stats['total_days'] * 100:.1f}%</div>
               </div>
       """, unsafe_allow_html=True)
    with col43:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-13">
                   <div class="metric-label">底背离天数</div>
                   <div class="metric-value">{stats['bullish_divergence_days']} / {stats['bullish_divergence_days'] / stats['total_days'] * 100:.1f}%</div>
               </div>
       """, unsafe_allow_html=True)
    with col44:
        st.markdown(f"""
               <div class="metric-sub-card metric-card-14">
                   <div class="metric-label">成交量衰减天数</div>
                   <div class="metric-value">{stats['volume_weakening_days']} / {stats['volume_weakening_days'] / stats['total_days'] * 100:.1f}%</div>
               </div>
       """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    step4_table_data = []
    for r in stats['risk_reasons']:
        step4_table_data.append({
            '类型': r['risk_type'].text,
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            '成交量是否衰减': {r['volume_weakening']},
            '风险级别': f"{r['risk_level'].icon} {r['risk_level'].text}",
            '说明': '｜'.join(r['reasons']),
        })
    if len(step4_table_data) > 0:
        step4_df = pd.DataFrame(step4_table_data)
        st.dataframe(
            step4_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(step4_df) * 35 + 38)
        )

def _build_stock_trading_analysis_analysis_info(stock, t, signals, stats, daily_analysis):
    st.markdown(f"""
             <div class="chart-header">
                 <span class="chart-icon">🔍</span>
                 <span class="chart-title">每天分析</span>
             </div>
      """, unsafe_allow_html=True)
    table_data = []
    for r in daily_analysis:
        signal_show_text = r['signal_show_text'] if r['signal_show_text'] is not None else "⚪无信号"
        table_data.append({
            '日期': format_date_by_type(r['date'], t),
            '收盘价': f"{r['row']['closing']:.2f}",
            '信号': signal_show_text,
            '分数': {r['score']},
            '⓵市场状态': '｜'.join(r['step1_reasons']),
            '⓶关键区域': '｜'.join(r['step2_reasons']),
            '⓷入场触发': '｜'.join(r['step3_reasons']),
            '⓸风险过滤': '｜'.join(r['step4_reasons']),
            '分数构成': '｜'.join(r['signal_score_breakdowns']),
            '信号说明': '｜'.join(r['signal_reasons']),
        })
    if len(table_data) > 0:
        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(800, len(df) * 35 + 38)
        )

def _build_stock_trading_analysis_algorithm_info():
    st.markdown(f"""
               <div class="chart-header">
                   <span class="chart-icon">🔮</span>
                   <span class="chart-title">策略算法</span>
               </div>
    """, unsafe_allow_html=True)

    algorithm_infos = TradingSignalAnalyzer.get_algorithm_info()
    for info in algorithm_infos:
        with st.container():
            icon = info['icon']
            step = info['step']
            why = info['why']
            strategy = info['strategy']
            criteria = info['criteria']
            color_class = info['color_class']
            criteria_html = '<br>'.join([f"🗳 {criterion}" for criterion in criteria])
            st.markdown(f"""
                           <div class="sync-button-card {color_class}">
                               <div class="sync-card-icon {color_class}">
                                   <span class="sync-icon-large">{icon}</span>
                               </div>
                               <div class="sync-card-content">
                                   <div class="sync-card-title">{step}  -  {why}❓  -  {strategy}</div>
                                   <div class="sync-card-desc">{criteria_html}</div>
                               </div>
                           </div>
                           """, unsafe_allow_html=True)

def _get_stock_history_data(stock, t: StockHistoryType, key_suffix: str = "") -> pd.DataFrame:
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

            # 根据 key_suffix 生成不同的 key
            base_key_prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_{t}',category=stock.category)
            if key_suffix:
                key_prefix = f"{base_key_prefix}_{key_suffix}"
            else:
                key_prefix = base_key_prefix

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

            # 使用 session_state 中的日期值
            start_date = st.session_state[start_date_key]
            end_date = st.session_state[end_date_key]

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


