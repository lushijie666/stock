
import streamlit as st
import pandas as pd
from sqlalchemy import func
import streamlit_echarts

from enums.strategy import StrategyType
from models.stock_history import get_history_model
from enums.history_type import StockHistoryType
from enums.patterns import Patterns
from utils.chart import ChartBuilder
from utils.signal import calculate_all_signals
from utils.strategy import calculate_macd, backtest_strategy, calculate_strategy_metrics, calculate_risk_metrics, \
    generate_trading_advice, calculate_strategy_performance, calculate_position_and_cash_values
from utils.k_line_processor import KLineProcessor


from utils.db import get_db_session
from utils.session import get_session_key, SessionKeys, get_date_range
from utils.uuid import generate_key

KEY_PREFIX = "stock_chart"


@st.dialog("股票图表", width="large")
def show_detail_dialog(stock):
    show_detail(stock)

def show_detail(stock):
    t = st.radio(
        "",
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
        "",
        ["K线图", "K线图处理", "买卖点分析", "回测分析"],
        horizontal=True,
        key=f"{KEY_PREFIX}_{stock.code}_{t}_radio2",
        label_visibility="collapsed"
    )
    strategy_required = chart_type in ["K线图", "买卖点分析", "回测分析"]
    if strategy_required:
        strategy_options = {
            StrategyType.MACD_STRATEGY: StrategyType.MACD_STRATEGY.fullText,
            StrategyType.SMA_STRATEGY: StrategyType.SMA_STRATEGY.fullText,
            StrategyType.TURTLE_STRATEGY: StrategyType.TURTLE_STRATEGY.fullText
        }
        selected_strategy_key = f"{KEY_PREFIX}_{stock.code}_{t}_strategies"
        if selected_strategy_key not in st.session_state:
            st.session_state[selected_strategy_key] = []

        temp_selection = st.session_state[selected_strategy_key].copy()
        selected_strategies = []
        cols = st.columns(len(strategy_options))
        for i, (strategy, strategy_text) in enumerate(strategy_options.items()):
            with cols[i]:
                currently_selected = strategy in temp_selection
                # 定义回调函数来切换选择状态
                def toggle_strategy(sel_strategy=strategy):
                    current = st.session_state[selected_strategy_key]
                    if sel_strategy in current:
                        st.session_state[selected_strategy_key] = [s for s in current if s != sel_strategy]
                    else:
                        st.session_state[selected_strategy_key] = current + [sel_strategy]
                is_selected = st.checkbox(
                    strategy_text,
                    value=currently_selected,
                    key=f"{selected_strategy_key}_{strategy.value}",
                    on_change=toggle_strategy,
                    label_visibility="visible"

                )
                if is_selected:
                    selected_strategies.append(strategy)
        # 更新session state
        st.session_state[selected_strategy_key] = selected_strategies
    chart_handlers = {
        "K线图": lambda: show_kline_chart(stock, t, selected_strategies),
        "K线图处理": lambda: show_kline_process_chart(stock, t),
        "买卖点分析": lambda: show_trade_points_chart(stock, t, selected_strategies),
        "回测分析": lambda: show_backtest_analysis(stock, t, selected_strategies)
    }
    chart_handlers.get(chart_type, lambda: None)()

def show_kline_chart(stock, t: StockHistoryType, strategies=None):
    st.markdown(
        f"""
               <div class="table-header">
                   <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - K线图</div>
               </div>
               """,
        unsafe_allow_html=True
    )
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
                return
            min_date, max_date = date_range
            default_start_date = t.get_default_start_date(max_date, min_date)
            key_prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_{t}_history_chart',category=stock.category)
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
                model.turnover_count
            ).filter(
                model.code == stock.code,
                model.removed == False,
                model.date >= start_date,
                model.date <= end_date
            ).order_by(model.date)

            # 读取数据到DataFrame
            df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                st.warning("所选日期范围内没有数据")
                return

            ma_lines = {}
            default_ma_periods = [5, 10, 30, 250] # 5日移动平均线，10日移动平均线，30日移动平均线，250日移动平均线
            for period in default_ma_periods:
                ma_lines[f'MA{period}'] = df['closing'].rolling(window=period).mean().tolist()


            dates = df['date'].astype(str).tolist()
            k_line_data = df[['opening', 'closing', 'lowest', 'highest']].values.tolist()
            volumes = df['turnover_count'].tolist()
            colors = ['#ef232a' if close > open else '#14b143'
                      for open, close in zip(df['opening'], df['closing'])]

            all_signals = []
            if strategies:
                all_signals = calculate_all_signals(df, strategies)
            # 创建 K 线图
            st.markdown("""
                  <div class="chart-header">
                      <span class="chart-icon">🔍</span>
                      <span class="chart-title">K线图</span>
                  </div>
              """, unsafe_allow_html=True)
            kline = ChartBuilder.create_kline_chart(dates, k_line_data, ma_lines=ma_lines, signals=all_signals)
            volume_bar = ChartBuilder.create_volume_bar(dates, volumes, colors)
            #grid = ChartBuilder.create_combined_chart(kline, volume_bar)

            # 显示K线图
            streamlit_echarts.st_pyecharts(kline, theme="white", height="500px", key=f"{KEY_PREFIX}_{stock.code}_{t}_kline")

            # 计算 MACD
            macd_df = calculate_macd(df)
            macd_dates = df['date'].astype(str).tolist()
            diff_values = macd_df['DIFF'].tolist()
            dea_values = macd_df['DEA'].tolist()
            macd_hist = macd_df['MACD_hist'].tolist()
            # 显示 MACD 图
            fast_period = 12
            slow_period = 26
            signal_period = 9
            macd_full_title = f"MACD ({fast_period},{slow_period},{signal_period})"
            st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">🔍</span>
                      <span class="chart-title">{macd_full_title}</span>
                  </div>
              """, unsafe_allow_html=True)
            macd_chart = ChartBuilder.create_macd_chart(
                dates=macd_dates,
                diff=diff_values,
                dea=dea_values,
                hist=macd_hist,
                fast_period=fast_period,
                slow_period=slow_period,
                signal_period=signal_period,
            )
            streamlit_echarts.st_pyecharts(macd_chart, theme="white", height="350px", key=f"{KEY_PREFIX}_{stock.code}_{t}_macd")

            # 显示成交量
            st.markdown(f"""
                  <div class="chart-header">
                      <span class="chart-icon">🔍</span>
                      <span class="chart-title">成交量</span>
                  </div>
              """, unsafe_allow_html=True)
            streamlit_echarts.st_pyecharts(volume_bar, theme="white", height="300px", key=f"{KEY_PREFIX}_{stock.code}_{t}_volume")

            # 显示MACD数据表格
            if not macd_df.empty:
                st.markdown("""
                   <div class="chart-header">
                       <span class="chart-icon">🔍</span>
                       <span class="chart-title">MACD指标信息</span>
                   </div>
                   """, unsafe_allow_html=True)

                # 创建MACD数据DataFrame
                macd_display_df = pd.DataFrame({
                    '日期': df['date'].astype(str),
                    'DIFF': [round(x, 4) if not pd.isna(x) else None for x in macd_df['DIFF']],
                    'DEA': [round(x, 4) if not pd.isna(x) else None for x in macd_df['DEA']],
                    'MACD': [round(x, 4) if not pd.isna(x) else None for x in macd_df['MACD_hist']]
                })

                st.dataframe(
                    macd_display_df,
                    height=min(len(macd_display_df) * 35 + 38, 600),
                    use_container_width=True
                )

            # 显示信号数据表格
            if all_signals:
                st.markdown("""
                            <div class="chart-header">
                                <span class="chart-icon">🔍</span>
                                <span class="chart-title">买卖点信息</span>
                            </div>
                            """, unsafe_allow_html=True)
                # 创建信号DataFrame
                signal_df = pd.DataFrame([
                    {
                        '日期': s['date'].strftime('%Y-%m-%d') if hasattr(s['date'], 'strftime') else str( s['date']),
                        '信号类型': f"{s['type'].fullText}",
                        '信号强度': f"{s['strength'].fullText}",
                        '价格': round(s['price'], 2),
                        '策略': s.get('strategy_display', '未知')

                    }
                    for s in all_signals
                ]).sort_values('日期')
                st.dataframe(
                    signal_df,
                    height=min(len(signal_df) * 35 + 38, 600),
                    use_container_width=True
                )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")

def show_kline_process_chart(stock, t: StockHistoryType):
    st.markdown(
        f"""
            <div class="table-header">
                <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - K线图处理</div>
            </div>
        """,
        unsafe_allow_html=True
    )
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
                return
            min_date, max_date = date_range
            default_start_date = t.get_default_start_date(max_date, min_date)

            key_prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_{t}_process_history_chart', category=stock.category)
            # 初始化 session state 中的日期值
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
                model.turnover_count
            ).filter(
                model.code == stock.code,
                model.removed == False,
                model.date >= start_date,
                model.date <= end_date
            ).order_by(model.date)

            # 读取数据到DataFrame
            df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                st.warning("所选日期范围内没有数据")
                return

            # 创建处理器实例
            processor = KLineProcessor()
            try:
                processor.validate_data(df)
                processed_df, contains_marks, processing_records, patterns = processor.process_klines(
                    df,
                )
                # 识别笔
                strokes = KLineProcessor.identify_strokes(patterns, processed_df)
                # 识别线段
                segments = KLineProcessor.identify_segments(strokes)
                # 识别中枢
                centers = KLineProcessor.identify_centers(strokes)

                processed_dates = processed_df['date'].astype(str).tolist()
                processed_k_line_data = processed_df[['opening', 'closing', 'lowest', 'highest']].values.tolist()
                processed_kline = ChartBuilder.create_kline_chart(
                    processed_dates,
                    processed_k_line_data,
                    ma_lines=None,
                    patterns=patterns,
                    strokes=strokes,
                    segments=segments,
                    centers=centers

                )
                # 显示图表
                st.markdown("""
                      <div class="chart-header">
                          <span class="chart-icon">🔍</span>
                          <span class="chart-title">K线图</span>
                      </div>
                """, unsafe_allow_html=True)
                streamlit_echarts.st_pyecharts(processed_kline,theme="white",height="500px",key=generate_key())

                # 显示处理信息表格
                if processing_records:
                    st.markdown("""
                       <div class="chart-header">
                           <span class="chart-icon">🔍</span>
                           <span class="chart-title">包含关系信息</span>
                       </div>
                    """, unsafe_allow_html=True)
                    st.markdown("""
                       <div class='info-description'>
                       -  当两根K线互相包含时，根据前一根K线的趋势决定处理方向<br>
                       -  向上处理：取两根K线中较高的最高价和较高的最低价<br>
                       -  向下处理：取两根K线中较低的最高价和较低的最低价
                       
                       </div>
                       """, unsafe_allow_html=True)
                    # 创建更直观的包含关系DataFrame
                    contains_df = pd.DataFrame([
                        {
                            '上一K线日期': record['original_k1']['date'].strftime('%Y-%m-%d'),
                            '上一K线最高/低': f"{record['original_k1']['highest']}/{record['original_k1']['lowest']}",
                            '上一K线开/收盘': f"{record['original_k1']['opening']}/{record['original_k1']['closing']}",
                            '当前K线日期': record['date'].strftime('%Y-%m-%d'),
                            '当前K线最高/低': f"{record['original_k2']['highest']}/{record['original_k2']['lowest']}",
                            '当前K线开/收盘': f"{record['original_k2']['opening']}/{record['original_k2']['closing']}",
                            '下一K线日期': record['original_k3']['date'].strftime('%Y-%m-%d'),
                            '下一K线最高/低': f"{record['original_k3']['highest']}/{record['original_k3']['lowest']}",
                            '下一K线开/收盘': f"{record['original_k3']['opening']}/{record['original_k3']['closing']}",
                            '处理方向': record['trend'],
                            '合并后最高/低': f"{record['new_values']['high']}/{record['new_values']['low']}"
                        }
                        for record in processing_records
                    ])

                    # 显示包含关系表格
                    st.dataframe(
                        contains_df,
                        height=min(len(contains_df) * 35 + 38, 600),
                        use_container_width=True
                    )
                # 原有的分型信息表格
                if patterns:
                    st.markdown("""
                      <div class="chart-header">
                          <span class="chart-icon">🔍</span>
                          <span class="chart-title">分型标记信息</span>
                      </div>
                   """, unsafe_allow_html=True)
                    pattern_df = pd.DataFrame({
                        '日期': [p['date'] for p in patterns],
                        '类型': ["🚀 顶分型" if p['type'] == Patterns.TOP else "💣 底分型" for p in patterns],
                        '价格': [p['value'] for p in patterns]
                    })

                    st.dataframe(
                        pattern_df,
                        height=min(len(pattern_df) * 35 + 38, 600),
                        use_container_width=True
                    )
                # 显示笔信息表格
                if strokes:
                    st.markdown("""
                      <div class="chart-header">
                          <span class="chart-icon">🔍</span>
                          <span class="chart-title">笔信息</span>
                      </div>
                   """, unsafe_allow_html=True)
                    stroke_df = pd.DataFrame([
                        {
                            '起始日期': s['start_date'].strftime('%Y-%m-%d'),
                            '结束日期': s['end_date'].strftime('%Y-%m-%d'),
                            '起始价格': s['start_value'],
                            '结束价格': s['end_value'],
                            '类型': "向上(S)" if s['type'] == 'up' else "向下(X)",
                            'K线数量': abs(s['end_index'] - s['start_index']) + 1
                        }
                        for s in strokes
                    ])
                    st.dataframe(
                        stroke_df,
                        height=min(len(stroke_df) * 35 + 38, 600),
                        use_container_width=True
                    )
                # 显示线段信息表格
                if segments:
                    st.markdown("""
                          <div class="chart-header">
                              <span class="chart-icon">🔍</span>
                              <span class="chart-title">线段信息</span>
                          </div>
                       """, unsafe_allow_html=True)
                    segment_df = pd.DataFrame([
                        {
                            '起始日期': s['start_date'].strftime('%Y-%m-%d'),
                            '结束日期': s['end_date'].strftime('%Y-%m-%d'),
                            '起始价格': s['start_value'],
                            '结束价格': s['end_value'],
                            '类型': "向上" if s['type'] == 'up' else "向下",
                            '包含笔数': len(s['strokes'])
                        }
                        for s in segments
                    ])
                    st.dataframe(
                        segment_df,
                        height=min(len(segment_df) * 35 + 38, 600),
                        use_container_width=True
                    )
                # 显示中枢信息表格
                if centers:
                    st.markdown("""
                         <div class="chart-header">
                             <span class="chart-icon">🔍</span>
                             <span class="chart-title">中枢信息</span>
                         </div>
                      """, unsafe_allow_html=True)
                    center_df = pd.DataFrame([
                        {
                            '起始日期': c['start_date'].strftime('%Y-%m-%d') if hasattr(c['start_date'],
                                                                                        'strftime') else str(
                                c['start_date']),
                            '结束日期': c['end_date'].strftime('%Y-%m-%d') if hasattr(c['end_date'],
                                                                                      'strftime') else str(
                                c['end_date']),
                            '中枢类型': "上涨中枢" if c['type'] == 'up_center' else "下跌中枢",
                            '中枢高点(ZG)': round(c['ZG'], 2),
                            '中枢低点(ZD)': round(c['ZD'], 2),
                            '中枢波动最高点(GG)': round(c['GG'], 2),
                            '中枢波动最低点(DD)': round(c['DD'], 2),
                            '包含笔数': len(c['strokes'])
                        }
                        for c in centers
                    ])
                    st.dataframe(
                        center_df,
                        height=min(len(center_df) * 35 + 38, 600),
                        use_container_width=True
                    )
            except ValueError as e:
                st.error(f"数据处理失败：{str(e)}")
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_trade_points_chart(stock, t: StockHistoryType, strategies=None):
    st.markdown(
        f"""
               <div class="table-header">
                   <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - 买卖点分析</div>
               </div>
               """,
        unsafe_allow_html=True
    )
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
                return
            min_date, max_date = date_range
            default_start_date = t.get_default_start_date(max_date, min_date)

            key_prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_{t}_trade_points',category=stock.category)
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
                model.closing
            ).filter(
                model.code == stock.code,
                model.removed == False,
                model.date >= start_date,
                model.date <= end_date
            ).order_by(model.date)

            # 读取数据到DataFrame
            df = pd.read_sql(query.statement, session.bind)
            if df.empty:
                st.warning("所选日期范围内没有数据")
                return
            # 计算所有信号
            all_signals = calculate_all_signals(df, strategies)
            # 准备数据
            dates = df['date'].astype(str).tolist()
            open_prices = df['opening'].tolist()
            high_prices = df['highest'].tolist()
            low_prices = df['lowest'].tolist()
            close_prices = df['closing'].tolist()

            line_chart = ChartBuilder.create_trade_points_chart(
                dates,
                open_prices,
                high_prices,
                low_prices,
                close_prices,
                all_signals
            )
            st.markdown("""
                  <div class="chart-header">
                      <span class="chart-icon">🔍</span>
                      <span class="chart-title">交易点</span>
                  </div>
              """, unsafe_allow_html=True)
            # 显示图表
            streamlit_echarts.st_pyecharts(line_chart, theme="white", height="600px", key=f"{KEY_PREFIX}_{stock.code}_{t}_trade_points")

            # 显示买卖点表格
            if all_signals:
                st.markdown("""
                     <div class="chart-header">
                         <span class="chart-icon">🔍</span>
                         <span class="chart-title">买卖点信息</span>
                     </div>
                  """, unsafe_allow_html=True)

                # 创建买卖点DataFrame - 在表格中用相应的图标表示信号强度
                trade_points_df = pd.DataFrame([
                    {
                        '日期': s['date'].strftime('%Y-%m-%d') if hasattr(s['date'], 'strftime') else str(s['date']),
                        '信号类型': f"{s['type'].fullText}",
                        '信号强度': f"{s['strength'].fullText}",
                        '价格': round(s['price'], 2),
                        '策略': s.get('strategy_display', '未知')
                    }
                    for s in all_signals
                ]).sort_values('日期')
                st.dataframe(
                    trade_points_df,
                    height=min(len(trade_points_df) * 35 + 38, 800),
                    use_container_width=True
                )
            else:
                st.info("所选时间范围内未发现符合条件的买卖点信号")

    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_backtest_analysis(stock, t: StockHistoryType, strategies=None):
    st.markdown(
        f"""
        <div class="table-header">
            <div class="table-title">{stock.category} {stock.code} ({stock.name}) - [{t.text}] - 回测分析</div>
        </div>
        """,
        unsafe_allow_html=True
    )
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
                return

            min_date, max_date = date_range
            default_start_date = t.get_default_start_date(max_date, min_date)

            key_prefix = get_session_key(
                SessionKeys.PAGE,
                prefix=f'{KEY_PREFIX}_{stock.code}_{t}_backtest',
                category=stock.category
            )
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
                model.closing
            ).filter(
                model.code == stock.code,
                model.removed == False,
                model.date >= start_date,
                model.date <= end_date
            ).order_by(model.date)

            # 读取数据到DataFrame
            df = pd.read_sql(query.statement, session.bind)
            if df.empty:
                st.warning("所选日期范围内没有数据")
                return

            st.markdown("""
              <div class="chart-header">
                  <span class="chart-icon">🔧</span>
                  <span class="chart-title">参数设置</span>
              </div>
            """, unsafe_allow_html=True)
            col_config1, col_config2, col_config3 = st.columns(3)

            with col_config1:
                initial_capital = st.number_input(
                    "初始资金 (¥)",
                    min_value=1000.0,
                    value=100000.0,
                    step=1000.0,
                    key=f"{KEY_PREFIX}_{stock.code}_{t}_initial_capital"
                )

            with col_config2:
                buy_ratio_default = {'strong': 0.8, 'weak': 0.5}
                buy_ratio_strong = st.number_input(
                    "强买比例",
                    min_value=0.1,
                    max_value=1.0,
                    value=0.8,
                    step=0.1,
                    key=f"{KEY_PREFIX}_{stock.code}_{t}_buy_ratio_strong"
                )
                buy_ratio_weak = st.number_input(
                    "弱买比例",
                    min_value=0.1,
                    max_value=1.0,
                    value=0.5,
                    step=0.1,
                    key=f"{KEY_PREFIX}_{stock.code}_{t}_buy_ratio_weak"
                )
                buy_ratios = {'strong': buy_ratio_strong, 'weak': buy_ratio_weak}

            with col_config3:
                sell_ratio_default = {'strong': 0.8, 'weak': 0.5}
                sell_ratio_strong = st.number_input(
                    "强卖比例",
                    min_value=0.1,
                    max_value=1.0,
                    value=0.8,
                    step=0.1,
                    key=f"{KEY_PREFIX}_{stock.code}_{t}_sell_ratio_strong"
                )
                sell_ratio_weak = st.number_input(
                    "弱卖比例",
                    min_value=0.1,
                    max_value=1.0,
                    value=0.5,
                    step=0.1,
                    key=f"{KEY_PREFIX}_{stock.code}_{t}_sell_ratio_weak"
                )
                sell_ratios = {'strong': sell_ratio_strong, 'weak': sell_ratio_weak}

            # 计算所有信号
            all_signals = calculate_all_signals(df, strategies)

            if not all_signals:
                st.warning("所选时间范围内未发现交易信号")
                return

            # 执行回测
            backtest_result = backtest_strategy(
                df,
                all_signals,
                initial_capital=initial_capital,
                buy_ratios=buy_ratios,
                sell_ratios=sell_ratios
            )
            dates = df['date'].astype(str).tolist()
            open_prices = df['opening'].tolist()
            high_prices = df['highest'].tolist()
            low_prices = df['lowest'].tolist()
            close_prices = df['closing'].tolist()
            trades = backtest_result['trades']

            # 计算
            trading_advice = generate_trading_advice(df, all_signals)
            risk_metrics = calculate_risk_metrics(df, all_signals)
            strategy_metrics = calculate_strategy_metrics(df, all_signals)
            strategy_cumulative, benchmark_cumulative = calculate_strategy_performance(df, all_signals, backtest_result)
            position_values, cash_values = calculate_position_and_cash_values(df, backtest_result)

            # 交易建议
            st.markdown(f"""
                <div class="chart-header">
                    <div class="chart-icon">📋</div>
                    <div>
                        <div class="chart-title">交易建议</div>
                        <div class="chart-title">{trading_advice}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # 显示关键指标
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                        <div class="metric-sub-card metric-card-1">
                            <div class="metric-label">初始资金</div>
                            <div class="metric-value">¥{backtest_result['initial_capital']:,.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                        <div class="metric-sub-card metric-card-2">
                            <div class="metric-label">最终价值</div>
                            <div class="metric-value">¥{backtest_result['final_value']:,.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                        <div class="metric-sub-card metric-card-3">
                            <div class="metric-label">总收益率</div>
                            <div class="metric-value">{backtest_result['total_return']:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("")
            st.markdown("""
                <div class="chart-header">
                    <span class="chart-icon">🔍</span>
                    <span class="chart-title">风险指标</span>
                </div>
            """, unsafe_allow_html=True)

            col4, col5, col6 = st.columns(3)
            with col4:
                st.markdown(f"""
                        <div class="metric-sub-card metric-card-4">
                            <div class="metric-label">夏普比率</div>
                            <div class="metric-value">{risk_metrics['sharpe_ratio']:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
            with col5:
                st.markdown(f"""
                       <div class="metric-sub-card metric-card-5">
                           <div class="metric-label">年化波动率</div>
                           <div class="metric-value">{risk_metrics['volatility'] * 100:.2f}%</div>
                       </div>
                       """, unsafe_allow_html=True)
            with col6:
                st.markdown(f"""
                       <div class="metric-sub-card metric-card-6">
                           <div class="metric-label">最大回撤</div>
                           <div class="metric-value">{risk_metrics['max_drawdown'] * 100:.2f}%</div>
                       </div>
                       """, unsafe_allow_html=True)

            st.markdown("")
            st.markdown("""
               <div class="chart-header">
                   <span class="chart-icon">🔍</span>
                   <span class="chart-title">交易策略</span>
               </div>
           """, unsafe_allow_html=True)
            col7, col8, col9, col10 = st.columns(4)
            with col7:
                st.markdown(f"""
                       <div class="metric-sub-card metric-card-7">
                           <div class="metric-label">总信号数</div>
                           <div class="metric-value">{strategy_metrics['total_signals']}</div>
                       </div>
                       """, unsafe_allow_html=True)
            with col8:
                st.markdown(f"""
                      <div class="metric-sub-card metric-card-8">
                          <div class="metric-label">买入信号</div>
                          <div class="metric-value">{strategy_metrics['buy_signals']}</div>
                      </div>
                      """, unsafe_allow_html=True)
            with col9:
                st.markdown(f"""
                      <div class="metric-sub-card metric-card-9">
                          <div class="metric-label">卖出信号</div>
                          <div class="metric-value">{strategy_metrics['sell_signals']}</div>
                      </div>
                      """, unsafe_allow_html=True)
            with col10:
                st.markdown(f"""
                      <div class="metric-sub-card metric-card-9">
                          <div class="metric-label">平均持股天数</div>
                          <div class="metric-value">{strategy_metrics['avg_holding_period']:.1f}天</div>
                      </div>
                      """, unsafe_allow_html=True)


            st.markdown("")
            st.markdown("""
                    <div class="chart-header">
                        <span class="chart-icon">🔍</span>
                        <span class="chart-title">收益对比</span>
                    </div>
            """, unsafe_allow_html=True)
            performance_chart = ChartBuilder.create_backtest_performance_chart(
                dates,
                strategy_cumulative,
                benchmark_cumulative
            )
            # 创建收益对比图
            streamlit_echarts.st_pyecharts(performance_chart, height="450px", key=f"{KEY_PREFIX}_{stock.code}_{t}_performance_chart")


            st.markdown("""
                    <div class="chart-header">
                        <span class="chart-icon">🔍</span>
                        <span class="chart-title">交易点</span>
                    </div>
            """, unsafe_allow_html=True)
            backtest_trade_points_chart = ChartBuilder.create_backtest_trade_points_chart(
                dates,
                open_prices,
                high_prices,
                low_prices,
                close_prices,
                all_signals,
                trades
            )
            streamlit_echarts.st_pyecharts(backtest_trade_points_chart, height="450px", key=f"{KEY_PREFIX}_{stock.code}_{t}_backtest_trade_points_chart")

            st.markdown("""
                    <div class="chart-header">
                        <span class="chart-icon">🔍</span>
                        <span class="chart-title">资金分布变化</span>
                    </div>
                """, unsafe_allow_html=True)
            position_chart = ChartBuilder.create_position_chart(
                dates,
                position_values,
                cash_values
            )
            streamlit_echarts.st_pyecharts(position_chart, height="450px", key=f"{KEY_PREFIX}_{stock.code}_{t}_position_chart")


            st.markdown("""
                   <div class="chart-header">
                       <span class="chart-icon">🔍</span>
                       <span class="chart-title">交易信息</span>
                   </div>
           """, unsafe_allow_html=True)
            if backtest_result['trades']:
                trades_df = pd.DataFrame([
                    {
                        '日期': trade['date'].strftime('%Y-%m-%d'),
                        '操作': f"{trade['type'].icon} {trade['type'].display_name}",
                        '信号强度': '🔥 强' if trade['strength'] == 'strong' else '🥀 弱',
                        '价格': f"¥{trade['price']:.2f}",
                        '数量': trade['shares'],
                        '金额': f"¥{trade['amount']:.2f}",
                        '剩余资金': f"¥{trade['capital']:.2f}",
                        '持仓数量': trade['position']
                    }
                    for trade in backtest_result['trades']
                ])
                st.dataframe(
                    trades_df,
                    height=min(len(trades_df) * 35 + 38, 600),
                    use_container_width=True
                )
            else:
                st.info("没有交易记录")
    except Exception as e:
        st.error(f"回测分析失败：{str(e)}")
