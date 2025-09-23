# 历史行情
import streamlit as st
import akshare as ak
import logging
from typing import Dict, Any, List
from functools import partial
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
import streamlit_echarts

from enums.patterns import Patterns
from utils.chart import ChartBuilder, calculate_macd, calculate_macd_signals, calculate_sma_signals
from utils.k_line_processor import KLineProcessor
from utils.table import format_pinyin_short

from service.stock import get_codes
from utils.convert import date_range_filter, convert_date_format
from utils.fetch_handler import create_reload_handler
from utils.message import show_message
from models.history_data import HistoryDateData
from enums.category import Category
from utils.db import get_db_session
from datetime import date, timedelta
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionButton, ActionConfig
from utils.session import get_session_key, SessionKeys, get_date_range
from utils.table import  format_percent, format_volume
from utils.uuid import generate_key

KEY_PREFIX = "history_data"


def show_date_page(stock):
    try:
        with get_db_session() as session:
            # 构建查询
            query = session.query(HistoryDateData).filter(
                HistoryDateData.code == stock.code,
                HistoryDateData.removed == False
            ).order_by(HistoryDateData.date.desc())
            paginate_dataframe(
                query,
                10,
                columns_config={
                    'code': st.column_config.TextColumn('股票代码', help="股票代码"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                    'date': st.column_config.DateColumn('日期', help="日期"),
                    'opening': st.column_config.NumberColumn('开盘', help="当日开盘价", format="%.3f"),
                    'closing': st.column_config.NumberColumn('收盘', help="当日收盘价", format="%.3f"),
                    'highest': st.column_config.NumberColumn('最高', help="当日最高价", format="%.3f"),
                    'lowest': st.column_config.NumberColumn('最低', help="当日最低价", format="%.3f"),
                    'turnover_count': st.column_config.TextColumn('成交量(手)', help="成交股数"),
                    'turnover_amount': st.column_config.TextColumn('成交额(元)', help="成交金额"),
                    'swing': st.column_config.NumberColumn('振幅', help="当日最高最低价格变动幅度", format="%.2f%%"),
                    'change': st.column_config.NumberColumn('涨跌幅', help="涨跌幅",format="%.2f%%"),
                    'change_amount': st.column_config.NumberColumn('涨跌额(元)', help="价格变动额", format="%.3f"),
                    'current_price': st.column_config.NumberColumn('最新价', help="当前交易价格", format="%.3f"),
                    'change_percent': st.column_config.NumberColumn('涨跌幅', help="价格变动百分比", format="%.2f%%"),
                    'turnover_ratio': st.column_config.NumberColumn('换手率', help="成交股数与流通股数之比",format="%.2f%%"),
                },
                # 格式化函数
                format_funcs={
                    'turnover_count': format_volume,
                    'swing': format_percent,
                    'turnover_ratio': format_percent,
                    'change': format_percent,
                },
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="start_date",
                            label="开始日期",
                            type="date",
                            default=date.today() - timedelta(days=30),
                            max_date=date.today(),
                            placeholder="输入开始日期",
                            filter_func=lambda q, v: date_range_filter(q, 'start_date', v)  # 添加过滤函数
                        ),
                        SearchField(
                            field="end_date",
                            label="结束日期",
                            type="date",
                            default=date.today(),
                            max_date=date.today(),
                            placeholder="输入结束日期",
                            filter_func=lambda q, v: date_range_filter(q, 'end_date', v)  # 添加过滤函数
                        )
                    ],
                    layout=[1, 1, 1, 1]
                ),
                action_config=ActionConfig(
                    buttons=[
                        ActionButton(
                            icon="🐙",
                            label="更新",
                            handler=partial(reload_by_code_date, category=stock.category, code=stock.code),
                            type="primary"
                        ),
                    ],
                    layout=[1, 0.1]  # 每个按钮占一列
                ),
                title=f'{stock.category} {stock.code} ({stock.name})',
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_date', category=stock.category),
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_chart_page(stock):
    try:
        with get_db_session() as session:
            # 获取该股票的最早和最晚日期
            date_range = session.query(
                func.min(HistoryDateData.date),
                func.max(HistoryDateData.date)
            ).filter(
                HistoryDateData.code == stock.code,
                HistoryDateData.removed == False
            ).first()

            if not date_range or None in date_range:
                st.warning("没有找到数据")
                return

            min_date, max_date = date_range
            default_start_date = max(max_date - timedelta(days=90), min_date)

            # 使用固定的 key 前缀来保持日期选择器状态
            chart_key_prefix = f"chart_page_{stock.code}"

            key_prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_chart',category=stock.category)
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
                HistoryDateData.date,
                HistoryDateData.opening,
                HistoryDateData.highest,
                HistoryDateData.lowest,
                HistoryDateData.closing,
                HistoryDateData.turnover_count
            ).filter(
                HistoryDateData.code == stock.code,
                HistoryDateData.removed == False,
                HistoryDateData.date >= start_date,
                HistoryDateData.date <= end_date
            ).order_by(HistoryDateData.date)

            # 读取数据到DataFrame
            df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                st.warning("所选日期范围内没有数据")
                return

            ma_lines = {}
            default_ma_periods = [5, 10, 30, 250]
            for period in default_ma_periods:
                ma_lines[f'MA{period}'] = df['closing'].rolling(window=period).mean().tolist()

            # 计算 MACD
            macd_df = calculate_macd(df)
            # 计算信号标记
            signals = calculate_macd_signals(df, macd_df)

            # 计算SMA信号
            sma_signals = calculate_sma_signals(df, ma_lines)
            # 合并信号
            all_signals = signals + sma_signals

            macd_dates = df['date'].astype(str).tolist()
            diff_values = macd_df['DIFF'].tolist()
            dea_values = macd_df['DEA'].tolist()
            macd_hist = macd_df['MACD_hist'].tolist()

            dates = df['date'].astype(str).tolist()
            k_line_data = df[['opening', 'closing', 'lowest', 'highest']].values.tolist()
            volumes = df['turnover_count'].tolist()
            colors = ['#ef232a' if close > open else '#14b143'
                      for open, close in zip(df['opening'], df['closing'])]

            # 创建 K 线图
            kline = ChartBuilder.create_kline_chart(dates, k_line_data, ma_lines=ma_lines, signals=all_signals)
            volume_bar = ChartBuilder.create_volume_bar(dates, volumes, colors)
            grid = ChartBuilder.create_combined_chart(kline, volume_bar)

            # 显示K线图
            streamlit_echarts.st_pyecharts(grid, theme="white", height="800px", key=f"{chart_key_prefix}_chart")
            # 显示 MACD 图
            macd_chart = ChartBuilder.create_macd_chart(
                dates=macd_dates,
                diff=diff_values,
                dea=dea_values,
                hist=macd_hist,
                fast_period=12,
                slow_period=26,
                signal_period=9,
                title="MACD"
            )
            streamlit_echarts.st_pyecharts(macd_chart, theme="white", height="400px", key=f"{chart_key_prefix}_macd")

    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")

def show_process_chart_page(stock):
    try:
        with get_db_session() as session:
            # 获取该股票的最早和最晚日期
            date_range = session.query(
                func.min(HistoryDateData.date),
                func.max(HistoryDateData.date)
            ).filter(
                HistoryDateData.code == stock.code,
                HistoryDateData.removed == False
            ).first()

            if not date_range or None in date_range:
                st.warning("没有找到数据")
                return

            min_date, max_date = date_range
            default_start_date = max(max_date - timedelta(days=90), min_date)

            # 使用统一的 key_prefix 方式
            key_prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{stock.code}_process_chart', category=stock.category)

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
                HistoryDateData.date,
                HistoryDateData.opening,
                HistoryDateData.highest,
                HistoryDateData.lowest,
                HistoryDateData.closing,
                HistoryDateData.turnover_count
            ).filter(
                HistoryDateData.code == stock.code,
                HistoryDateData.removed == False,
                HistoryDateData.date >= start_date,
                HistoryDateData.date <= end_date
            ).order_by(HistoryDateData.date)

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
                streamlit_echarts.st_pyecharts(processed_kline,theme="white",height="500px",key=generate_key())

                # 显示处理信息表格
                if processing_records:
                    st.markdown("<h6 style='margin-bottom: 10px;'>包含关系信息</h6>", unsafe_allow_html=True)
                    st.markdown("""
                       <div style='font-size: 12px;'>
                       - 当两根K线互相包含时，根据前一根K线的趋势决定处理方向<br>
                       - 向上处理：取两根K线中较高的最高价和较高的最低价<br>
                       - 向下处理：取两根K线中较低的最高价和较低的最低价
                       </div>
                       """, unsafe_allow_html=True)

                    # 创建更直观的包含关系DataFrame
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
                        height=min(len(contains_df) * 35 + 38, 400),
                        use_container_width=True
                    )
                    st.markdown("---")
                # 原有的分型信息表格
                if patterns:
                    st.markdown("<h6 style='margin-bottom: 10px;'>分型标记信息</h6>", unsafe_allow_html=True)
                    pattern_df = pd.DataFrame({
                        '日期': [p['date'] for p in patterns],
                        '类型': ["⬆顶分型" if p['type'] == Patterns.TOP else "⬇底分型" for p in patterns],
                        '价格': [p['value'] for p in patterns]
                    })

                    st.dataframe(
                        pattern_df,
                        height=min(len(pattern_df) * 35 + 38, 400),
                        use_container_width=True
                    )
                    st.markdown("---")
                # 显示笔信息表格
                if strokes:
                    st.markdown("<h6 style='margin-bottom: 10px;'>笔信息</h6>", unsafe_allow_html=True)
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
                        height=min(len(stroke_df) * 35 + 38, 400),
                        use_container_width=True
                    )
                    st.markdown("---")
                # 显示线段信息表格
                if segments:
                    st.markdown("<h6 style='margin-bottom: 10px;'>线段信息</h6>", unsafe_allow_html=True)
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
                        height=min(len(segment_df) * 35 + 38, 400),
                        use_container_width=True
                    )
                    st.markdown("---")
                # 显示中枢信息表格
                if centers:
                    st.markdown("<h6 style='margin-bottom: 10px;'>中枢信息</h6>", unsafe_allow_html=True)
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
                        height=min(len(center_df) * 35 + 38, 400),
                        use_container_width=True
                    )
            except ValueError as e:
                st.error(f"数据处理失败：{str(e)}")


    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_stock_detail(stock):

    with st.expander(f"{stock.category} {stock.code} ({stock.name}-{format_pinyin_short(stock.pinyin)})   「数据」", expanded=True):
        show_date_page(stock)

    with st.expander(f"{stock.category} {stock.code} ({stock.name}-{format_pinyin_short(stock.pinyin)})   「k线图」", expanded=True):
        show_chart_page(stock)

    with st.expander(f"{stock.category} {stock.code} ({stock.name}-{format_pinyin_short(stock.pinyin)})   「k线图-包含&分型处理」", expanded=True):
        show_process_chart_page(stock)


def reload_by_code_date(category: Category, code: str):
    prefix = get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}_{code}_date', category=category)
    date_range = get_date_range(prefix=prefix)
    if not date_range:
        return False
    start_date, end_date = date_range
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        return [
            HistoryDateData.code == code,
            HistoryDateData.date >= start_date,
            HistoryDateData.date <= end_date,
        ]
    history_handler = create_reload_handler(
        model=HistoryDateData,
        fetch_func=fetch_by_date,
        unique_fields=['code', 'date'],
        build_filter=build_filter,
        with_date_range=True,
    )
    return history_handler.refresh(
        code=code,
        start_date=start_date,
        end_date=end_date)

def reload_by_category_date(category: Category, start_date: str, end_date: str):
    codes = get_codes(category)
    for code in codes:
        logging.info(f"开始处理[{code}]数据..., 开始日期: {start_date}, 结束日期: {end_date}")
        def build_filter(args: Dict[str, Any], session: Session) -> List:
            return [
                HistoryDateData.code == code,
                HistoryDateData.date >= start_date,
                HistoryDateData.date <= end_date,
            ]
        history_handler = create_reload_handler(
            model=HistoryDateData,
            fetch_func=fetch_by_date,
            unique_fields=['code', 'date'],
            build_filter=build_filter,
            with_date_range=True,
        )
        history_handler.refresh_ignore_message(
            code=code,
            start_date=start_date,
            end_date=end_date)
    logging.info(f"结束处理[{code}]数据..., 开始日期: {start_date}, 结束日期: {end_date}")


def fetch_by_date(code: str, start_date: str, end_date: str) -> list:
    # 拉取 https://akshare.akfamily.xyz/data/stock/stock.html#id22
    start_date_str = convert_date_format(start_date)
    end_date_str = convert_date_format(end_date)
    fetch_functions = {
        Category.A_SH: partial(ak.stock_zh_a_hist, symbol=code, period="daily", start_date=start_date_str, end_date=end_date_str, adjust="hfq"),
        Category.A_SZ: partial(ak.stock_zh_a_hist, symbol=code, period="daily", start_date=start_date_str, end_date=end_date_str, adjust="hfq"),
        Category.A_BJ: partial(ak.stock_zh_a_hist, symbol=code, period="daily", start_date=start_date_str, end_date=end_date_str, adjust="hfq"),
        Category.X_XX: partial(ak.stock_zh_a_hist, symbol=code, period="daily", start_date=start_date_str, end_date=end_date_str, adjust="hfq"),
    }
    try:
        category = Category.from_stock_code(code)
        if fetch_func := fetch_functions.get(category):
            logging.info(f"开始获取[{KEY_PREFIX}]数据..., 股票:{code}, 开始日期: {start_date}, 结束日期: {end_date}")
            df = fetch_func()
            logging.info(f"成功获取[{KEY_PREFIX}]数据..., 股票:{code}, 开始日期: {start_date}, 结束日期: {end_date}, 共{len(df)}条记录")
            data = []
            for _, row in df.iterrows():
                try:
                    data.append(HistoryDateData(
                        category=category,
                        code=code,
                        date=row.get("日期"),
                        opening=row.get("开盘"),
                        closing=row.get("收盘"),
                        highest=row.get("最高"),
                        lowest=row.get("最低"),
                        turnover_count=row.get("成交量"),
                        turnover_amount=row.get("成交额"),
                        swing=row.get("振幅"),
                        change=row.get("涨跌幅"),
                        change_amount=row.get("涨跌额"),
                        turnover_ratio=row.get("换手率"),
                    ))

                except Exception as row_error:
                    logging.error(f"Error processing row: {row}, Error: {str(row_error)}")
                    continue
            return data
        else:
            show_message(f"不支持的分类: {category}", type="error")
            return None
    except Exception as e:
        logging.error(f"Error fetching data: {str(e)}")
        return None
