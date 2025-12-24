import time

import streamlit as st
from datetime import date, timedelta
from enums.history_type import StockHistoryType
from service.stock import show_category_pie_chart, show_follow_chart, get_total_stocks_count, get_followed_stocks_count
from enums.category import Category
from service.stock_chart import show_detail, KEY_PREFIX
from utils.message import show_message
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found
from utils.scheduler import scheduler
from service.sync import sync_stock, sync_stock_history, SyncHistoryType, get_sync_summary, sync_stock_trade
from models.sync_history import SyncStatus
import pandas as pd
import streamlit_echarts
from utils.chart import ChartBuilder


def index():
    # 主要统计指标
    show_main_dashboard()

    st.markdown("---")

    dashboard_type = st.radio(
        "功能分类",
        ["📊 股票分类  ", "❤️ 关注股票  ", "📈 股票图表  ", "⏰ 定时同步  ", "📥 手动同步  ", "📡 同步图表  "],
        horizontal=True,
        key=f"dashboard_type",
        label_visibility="collapsed"
    )
    dashboard_handlers = {
        "📊 股票分类  ": lambda: show_stock_category_dashboard(),
        "❤️ 关注股票  ": lambda: show_follow_stock_dashboard(),
        "📈 股票图表  ": lambda: show_stock_chart_dashboard(),
        "⏰ 定时同步  ": lambda: show_scheduler_sync_dashboard(),
        "📥 手动同步  ": lambda: show_manual_sync_dashboard(),
        "📡 同步图表  ": lambda: show_sync_dashboard(),
    }
    dashboard_handlers.get(dashboard_type, lambda: None)()
        

def show_main_dashboard():
    total_stocks = get_total_stocks_count()
    followed_stocks = get_followed_stocks_count()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">总股票数</div>
            <div class="metric-value">{total_stocks:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card metric-card-secondary">
            <div class="metric-label">关注股票</div>
            <div class="metric-value">{followed_stocks}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        is_running = scheduler.is_running()
        status_text = "运行中" if is_running else "已停止"
        st.markdown(f"""
        <div class="metric-card metric-card-third">
            <div class="metric-label">同步状态</div>
            <div class="metric-value">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)


def show_stock_category_dashboard():
    st.markdown("""
    <div class="manual-header">
        <span class="manual-icon">📊</span>
        <div>
            <div class="manual-title-text">股票分类</div>
            <div class="manual-subtitle">股票分类统计</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    show_category_pie_chart()

def show_follow_stock_dashboard():
    st.markdown("""
    <div class="manual-header">
        <span class="manual-icon">❤️</span>
        <div>
            <div class="manual-title-text">关注股票</div>
            <div class="manual-subtitle">关注的股票统计</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    show_follow_chart()

def show_stock_chart_dashboard():
    st.markdown("""
    <div class="manual-header">
        <span class="manual-icon">📈</span>
        <div>
            <div class="manual-title-text">股票图表</div>
            <div class="manual-subtitle">股票的K线图等</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    selectors = {}
    tabs = st.tabs(Category.fullTexts())
    for tab, category in zip(tabs, Category):
        selector = create_stock_selector(
            category=category,
            prefix=KEY_PREFIX,
            on_select=show_detail,
            on_error=handle_error,
            on_not_found=handle_not_found
        )
        selectors[category] = selector

    # 在每个 tab 中显示对应的 selector 和详情
    for tab, category in zip(tabs, Category):
        with tab:
            # 股票选择
            selectors[category].show_selector()
            # 显示详情
            selectors[category].handle_current_stock()


def show_scheduler_sync_dashboard():
    """显示定时同步任务卡片和控制按钮"""
    is_running = scheduler.is_running()
    status_text = "运行中" if is_running else "已停止"
    status_class = "scheduler-running" if is_running else "scheduler-stopped"

    # 统一的定时同步卡片
    st.markdown(f"""
    <div class="scheduler-toggle-card {status_class}">
        <div class="scheduler-toggle-header">
            <div class="scheduler-toggle-title">
                <span class="scheduler-icon">⏰</span>
                <div>
                    <div class="manual-title-text">定时同步</div>
                    <div class="manual-subtitle">自动在指定时间同步相关数据</div>
                </div>
            </div>
            <div class="scheduler-toggle-control">
                <div class="scheduler-status-badge {status_class}">
                    <span class="status-dot {status_class}"></span>
                    <span class="status-text {status_class}">{status_text}</span>
                </div>
                <div class="scheduler-button-placeholder"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 使用按钮来切换状态
    st.markdown(f"""
    <div class="scheduler-button-container">
    """, unsafe_allow_html=True)

    # 定义定时任务列表
    scheduled_jobs = [
        {"time": "每天06:00", "name": "📊 股票信息", "func": sync_stock},
        {"time": "每天18:10", "name": "📈 历史数据(天)", "func": lambda: sync_stock_history(StockHistoryType.D, True, date.today(), date.today())},
        {"time": "每天18:30", "name": "📈 历史数据(30分钟)", "func": lambda: sync_stock_history(StockHistoryType.THIRTY_M, True, date.today(), date.today())},
        {"time": "每天19:00", "name": "💰 买卖记录(天)", "func": lambda: sync_stock_trade(StockHistoryType.D, True, date.today(), date.today())},
        {"time": "每天19:00", "name": "💰 买卖记录(30分钟)", "func": lambda: sync_stock_trade(StockHistoryType.THIRTY_M, True, date.today(), date.today())}
    ]

    # 显示定时任务列表和立即执行按钮
    for idx, job in enumerate(scheduled_jobs):
        col1, col2 = st.columns([2, 0.2])
        with col1:
            st.markdown(f"<div class='job-item'>{job['name']}   [{job['time']}]</div>", unsafe_allow_html=True)
        with col2:
            if st.button("立即执行", key=f"execute_now_{idx}", use_container_width=True):
                job['func']()

    # 任务控制按钮
    if is_running:
        if st.button("▶ 停止", use_container_width=True, type="secondary", key="scheduler_stop"):
            scheduler.stop()
            st.rerun()
    else:
        if st.button("▶ 启动", use_container_width=True, type="primary", key="scheduler_start"):
            scheduler.start()
            # 添加定时任务
            scheduler.add_daily_job("sync_stock_history_d", lambda: sync_stock_history(StockHistoryType.D, True, date.today(), date.today()), 18, 10)
            scheduler.add_daily_job("sync_stock_history_30m", lambda: sync_stock_history(StockHistoryType.THIRTY_M, True, date.today(),date.today()), 18, 30)
            scheduler.add_daily_job("sync_stock_trade", lambda: sync_stock_trade(StockHistoryType.D, True, date.today(),date.today()), 19, 00),
            scheduler.add_daily_job("sync_stock_trade", lambda: sync_stock_trade(StockHistoryType.THIRTY_M, True, date.today(),date.today()), 19, 00),
            st.rerun()
    st.markdown("""
    </div>
    """, unsafe_allow_html=True)


def show_manual_sync_dashboard():
    """显示手动同步按钮区域"""
    # 手动同步按钮区域 - 卡片样式
    st.markdown("""
    <div class="manual-header">
        <span class="manual-icon">📥</span>
        <div>
            <div class="manual-title-text">手动同步</div>
            <div class="manual-subtitle">立即同步相关数据</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    today_date = pd.Timestamp.now().date()
    sync_buttons = [
        [
            ("📊", "股票信息", "同步所有股票", sync_stock, "[股票信息]", "sync-card-purple"),
        ],
        [
            ("📈", "历史数据(天)", "同步关注的股票近N天的数据(天)", None, "[历史数据-天-关注]", "sync-card-blue"),
            ("💼", "历史数据(天)", "同步所有的股票近N天的数据(天)", None, "[历史数据-天-全部]","sync-card-orange"),
        ],
        [
            ("📈", "历史数据(周)", "同步关注的股票近N天的数据(周)", None, "[历史数据-周-关注]", "sync-card-blue"),
            ("💼", "历史数据(周)", "同步所有的股票近N天的数据(周)", None, "[历史数据-周-全部]", "sync-card-orange"),
        ],
        [
            ("📈", "历史数据(月)", "同步关注的股票近N天的数据(月)", None, "[历史数据-月-关注]", "sync-card-blue"),
            ("💼", "历史数据(月)", "同步所有的股票近N天的数据(月)", None, "[历史数据-月-全部]","sync-card-orange"),
        ],
        [
            ("📈", "历史数据(30分钟)", "同步关注的股票近N天的数据(30分钟)", None, "[历史数据-30分钟-关注]", "sync-card-blue"),
            ("💼", "历史数据(30分钟)", "同步所有的股票近N天的数据(30分钟)", None, "[历史数据-30分钟-全部]","sync-card-orange"),
        ],
        [
            ("💰", "买卖记录(天)", "同步关注的股票买卖记录(天)", None, "[买卖记录-天-关注]", "sync-card-blue"),
            ("💰", "买卖记录(天)", "同步所有的股票买卖记录(天)", None, "[买卖记录-天-全部]", "sync-card-orange"),
        ],
        [
            ("💰", "买卖记录(周)", "同步关注的股票买卖记录(周)", None, "[买卖记录-周-关注]", "sync-card-blue"),
            ("💰", "买卖记录(周)", "同步所有的股票买卖记录(周)", None, "[买卖记录-周-全部]", "sync-card-orange"),
        ],
        [
            ("💰", "买卖记录(月)", "同步关注的股票买卖记录(月)", None, "[买卖记录-月-关注]", "sync-card-blue"),
            ("💰", "买卖记录(月)", "同步所有的股票买卖记录(月)", None, "[买卖记录-月-全部]", "sync-card-orange"),
        ],
        [
            ("💰", "买卖记录(30分钟)", "同步关注的股票买卖记录(天)", None, "[买卖记录-30分钟-关注]", "sync-card-blue"),
            ("💰", "买卖记录(30分钟)", "同步所有的股票买卖记录(30分钟)", None, "[买卖记录-30分钟-全部]", "sync-card-orange"),
        ],
    ]
    sync_type_mapping = {
        1: (StockHistoryType.D, "sync_stock_history"),  # 历史数据(天)
        2: (StockHistoryType.W, "sync_stock_history"),  # 历史数据(周)
        3: (StockHistoryType.M, "sync_stock_history"),  # 历史数据(月)
        4: (StockHistoryType.THIRTY_M, "sync_stock_history"),  # 历史数据(30分钟)
        5: (StockHistoryType.D, "sync_stock_trade"),  # 买卖记录(天)
        6: (StockHistoryType.W, "sync_stock_trade"),  # 买卖记录(周)
        7: (StockHistoryType.M, "sync_stock_trade"),  # 买卖记录(月)
        8: (StockHistoryType.THIRTY_M, "sync_stock_trade"),  # 买卖记录(30分钟)
    }

    # 创建同步状态变量（使用st.session_state确保按钮置灰效果）
    if "is_syncing" not in st.session_state:
        st.session_state.is_syncing = False
    if "sync_data_type" not in st.session_state:
        st.session_state.sync_data_type = None
    if "sync_func" not in st.session_state:
        st.session_state.sync_func = None
    
    # 显示同步按钮
    for row_idx, button_row in enumerate(sync_buttons):
        sync_cols = st.columns(len(button_row))
        for col_idx, (icon, title, desc, sync_func, data_type, color_class) in enumerate(button_row):
            with sync_cols[col_idx]:
                st.markdown(f"""
                <div class="sync-button-card {color_class}">
                    <div class="sync-card-icon {color_class}">
                        <span class="sync-icon-large">{icon}</span>
                    </div>
                    <div class="sync-card-content">
                        <div class="sync-card-title">{title}</div>
                        <div class="sync-card-desc">{desc}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 对于历史数据类型的按钮，显示日期选择器
                if "历史数据" in title or "买卖记录" in title:
                    # 日期范围选项
                    date_options = {
                        "最近3天": 3,
                        "最近7天": 7,
                        "最近30天": 30,
                        "最近90天": 90,
                        "最近1年": 365,
                        "最近2年": 730
                    }
                    selected_range = st.selectbox(
                        "请选择同步几天",
                        options=list(date_options.keys()),
                        key=f"date_range_{row_idx}_{col_idx}"
                    )
                    days = date_options[selected_range]
                    start_date = today_date - pd.Timedelta(days=days)
                    end_date = today_date
                    # 构建同步函数
                    def create_sync_func(row_idx, col_idx, start_date, end_date):
                        if row_idx in sync_type_mapping:
                            history_type, func_type = sync_type_mapping[row_idx]
                            is_all = (col_idx == 1)  # 第二列是"全部"选项
                            if func_type == "sync_stock_history":
                                return lambda: sync_stock_history(history_type, is_all, start_date, end_date)
                            elif func_type == "sync_stock_trade":
                                return lambda: sync_stock_trade(history_type, is_all, start_date, end_date)
                        return None
                    sync_func = create_sync_func(row_idx, col_idx, start_date, end_date)
                # 按钮置灰：当任何同步操作正在进行时，禁用所有按钮
                if st.button(f"立即同步", use_container_width=True, type="primary", key=f"sync_btn_{row_idx}_{col_idx}", disabled=st.session_state.is_syncing):
                    # 标记为正在同步，并保存数据类型
                    st.session_state.is_syncing = True
                    st.session_state.sync_data_type = data_type
                    st.session_state.sync_func = sync_func
                    # 触发页面重新加载以更新按钮状态
                    st.rerun()
    
    # 在列外部显示同步结果（占据整行）
    if st.session_state.is_syncing and st.session_state.sync_data_type:
        show_message("正在异步同步, 请稍后...", "success")
        try:
            # 执行同步操作
            result = st.session_state.sync_func()
            # 显示结果
            if result["success"]:
                st.success(f"✅ {st.session_state.sync_data_type} 同步成功！成功: {result['success_count']}, 失败: {result['failed_count']}")
            else:
                st.error(f"❌ {st.session_state.sync_data_type} 同步失败: {result['error']}")
        finally:
            # 同步完成后，重置状态
            st.session_state.is_syncing = False
            st.session_state.sync_data_type = None
            time.sleep(5)
            st.rerun()





def show_sync_dashboard():
    st.markdown("""
    <div class="manual-header">
        <span class="manual-icon">📈</span>
        <div>
            <div class="manual-title-text">同步图表</div>
            <div class="manual-subtitle">同步记录图</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    summary_data = get_sync_summary()

    show_sync_main_dashboard(summary_data)
    st.divider()
    # 并排展示同步类型和状态分布图表
   # col_chart1, col_chart2 = st.columns(2)
   # with col_chart1:
    show_sync_type_distribution_chart(summary_data)
    #with col_chart2:
    show_sync_status_distribution_chart(summary_data)

    # 每日同步次数图表
    show_daily_sync_chart(summary_data)

    # 同步记录
    show_sync_history_records(summary_data)
        


def show_daily_sync_chart(summary_data):
    st.markdown("""
    <div class="chart-header">
        <span class="chart-icon">📅</span>
        <span class="chart-title">每日同步次数    (近90天)</span>
    </div>
    """, unsafe_allow_html=True)

    try:
        daily_counts_data = summary_data.get('daily_counts', [])
        if not daily_counts_data:
            st.warning("暂无数据")
            return
        # 转换为图表所需格式
        try:
            dates = [str(item.date) if hasattr(item, 'date') else str(item[0]) for item in daily_counts_data]
            counts = [item.count if hasattr(item, 'count') else item[1] for item in daily_counts_data]
        except Exception as data_error:
            st.error(f"数据处理过程中出现错误: {str(data_error)}")
            return
        bar_chart = ChartBuilder.create_bar_chart(
            x_data=dates,
            y_data=counts,
            series_name=""
        )
        streamlit_echarts.st_pyecharts(bar_chart, height="300px")
    except Exception as e:
        st.error(f"生成每日同步图表失败: {str(e)}")

def show_sync_main_dashboard(summary_data):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div class="metric-sub-card metric-card-1">
                <div class="metric-label">总同步次数</div>
                <div class="metric-value">{summary_data["total_count"]}</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-sub-card metric-card-2">
                <div class="metric-label">成功次数</div>
                <div class="metric-value">{summary_data["success_count"]}</div>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-sub-card metric-card-3">
                <div class="metric-label">失败次数</div>
                <div class="metric-value">{summary_data["failed_count"]}</div>
            </div>
            """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="metric-sub-card metric-card-4">
                <div class="metric-label">成功率</div>
                <div class="metric-value">{summary_data["success_rate"]}%</div>
            </div>
            """, unsafe_allow_html=True)
def show_sync_type_distribution_chart(summary_data):
    st.markdown("""
    <div class="chart-header">
        <span class="chart-icon">🎯</span>
        <span class="chart-title">同步类型分布    (近90天)</span>
    </div>
    """, unsafe_allow_html=True)
    try:
        # 使用传入的统计数据
        type_counts_data = summary_data.get('type_counts', [])
        if not type_counts_data:
            st.warning("暂无数据")
            return

        # 转换为图表所需格式，使用显示名称
        chart_data = []
        try:
            for item in type_counts_data:
                # 添加类型检查，确保item有正确的属性
                if hasattr(item, 'type') and hasattr(item, 'count'):
                    type_enum = SyncHistoryType(item.type) if isinstance(item.type, str) else item.type
                    display_name = type_enum.display_name
                    chart_data.append([display_name, item.count])
        except Exception as inner_e:
            st.warning(f"数据处理过程中出现错误: {str(inner_e)}")
            return
        if not chart_data:
            st.warning("暂无数据")
            return
        pie_chart = ChartBuilder.create_pie_chart(
            data_pairs=chart_data,
            total=sum(count for _, count in chart_data)
        )
        streamlit_echarts.st_pyecharts(pie_chart, height="300px")
    except Exception as e:
        st.error(f"生成同步类型分布图表失败: {str(e)}")

def show_sync_status_distribution_chart(summary_data):
    """显示同步状态分布图表"""
    st.markdown("""
    <div class="chart-header">
        <span class="chart-icon">📊</span>
        <span class="chart-title">同步状态分布</span>
    </div>
    """, unsafe_allow_html=True)

    try:
        # 使用传入的统计数据
        status_counts_data = summary_data.get('status_counts', [])
        if not status_counts_data:
            st.warning("暂无数据")
            return

        color_map = {
            'success': '#10b981',
            'failed': '#ef4444',
            'running': '#3b82f6',
            'waiting': '#f59e0b'
        }

        # 转换为图表所需格式，使用显示名称
        chart_data = []
        colors = []
        try:
            for item in status_counts_data:
                status_enum = SyncStatus(item.status) if isinstance(item.status, str) else item.status
                display_name = status_enum.display_name
                chart_data.append([display_name, item.count])
                colors.append(color_map.get(item.status, '#6b7280'))
        except Exception as inner_e:
            st.warning(f"数据处理过程中出现错误: {str(inner_e)}")
            return
        status_pie = ChartBuilder.create_pie_chart(
            data_pairs=chart_data,
            total=sum(count for _, count in chart_data),
            colors=colors
        )
        streamlit_echarts.st_pyecharts(status_pie, height="300px")
    except Exception as e:
        st.error(f"生成同步状态分布图表失败: {str(e)}")

def show_sync_history_records(summary_data):
    st.markdown("""
    <div class="chart-header">
        <div class="chart-icon">📋</div>
        <div>
            <div class="chart-title">同步历史记录</div>
            <div class="manual-subtitle">查看和管理所有同步操作的详细记录</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # 从summary_data获取DataFrame
        df = summary_data.get('df', pd.DataFrame())
        
        if df.empty:
            st.warning("暂无数据")
            return
        
        # 筛选控件 - 使用卡片容器
        with st.container(border=True, key="filter_container"):
            st.markdown("""
            <div class="filter-header">
                <span class="filter-icon">🔍</span>
                <span class="filter-title">筛选条件</span>
            </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                sync_type_filter = st.selectbox(
                    "选择同步类型",
                    ["全部"] + [t.display_name for t in SyncHistoryType],
                    key="sync_type_filter"
                )
            with col2:
                status_filter = st.selectbox(
                    "选择同步状态",
                    ["全部"] + [s.display_name for s in SyncStatus],
                    key="status_filter"
                )
            
            # 应用筛选条件
            filtered_df = df.copy()
            if sync_type_filter != "全部":
                filtered_df = filtered_df[filtered_df['类型'] == sync_type_filter]
            if status_filter != "全部":
                filtered_df = filtered_df[filtered_df['状态'] == status_filter]

            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.TextColumn("日期"),
                    "类型": st.column_config.TextColumn("同步类型"),
                    "状态": st.column_config.TextColumn("同步状态"),
                    "成功数": st.column_config.NumberColumn("成功数"),
                    "失败数": st.column_config.NumberColumn("失败数"),
                    "耗时(秒)": st.column_config.NumberColumn("耗时(秒)"),
                    "创建时间": st.column_config.TextColumn("创建时间")
                }
            )
    except Exception as e:
        st.error(f"显示历史记录失败: {str(e)}")

