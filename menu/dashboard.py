import streamlit as st
from service.stock import show_category_pie_chart, show_follow_chart, get_total_stocks_count, get_followed_stocks_count
from enums.category import Category
from service.stock_chart import show_chart_page, KEY_PREFIX
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found
from utils.scheduler import scheduler
from service.sync_service import sync_stock_data, sync_history_data, sync_history_transaction, sync_real_time_data, get_sync_history, SyncType, get_sync_summary
from models.sync_history import SyncHistory, SyncStatus
import pandas as pd
import streamlit_echarts
from utils.chart import ChartBuilder



def index():
    # 主要统计指标
    show_main_dashboard()

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 股票分类  ", "❤️ 关注股票  ", "📈 股票图表  ", "⏰ 定时同步  ", "📥 手动同步  ", "📈 同步图表  "])

    with tab1:
        # show_category_pie_chart()
        #show_stock_category_dashboard()
        #show_category_pie_chart_wrapper()
        st.warning("注意：请勿重复点击同步按钮，否则可能会导致数据错误")

    with tab2:
        show_follow_stock_dashboard()

    with tab3:
        show_stock_dashboard()

    with tab4:
        show_scheduler_sync_dashboard()

    with tab5:
        show_manual_sync_dashboard()

    with tab6:
        show_category_pie_chart()
        # show_category_pie_chart_wrapper()

def show_category_pie_chart_wrapper():
    # 创建一个与tab1不同的容器，避免图表冲突
    with st.container(border=True, key="category_pie_chart_tab6_unique"):
        # 确保只导入和调用一次函数
        from service.stock import show_category_pie_chart
        show_category_pie_chart()  # 只调用一次，避免重复渲染

        

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
    #show_category_pie_chart()

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

def show_stock_dashboard():
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
            on_select=show_chart_page,
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

    # 显示定时任务列表
    if is_running:
        st.markdown("""
            <div class="scheduled-jobs-list" style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 10px;">
                <div class="job-item">
                    <span class="job-time">09:30</span>
                    <span class="job-name">📊 股票信息</span>
                </div>
                <div class="job-item">
                    <span class="job-time" style="font-weight: bold; margin-right: 8px; color: #2563eb;">11:00</span>
                    <span class="job-name">⚡ 实时行情</span>
                </div>
                <div class="job-item">
                    <span class="job-time">10:00</span>
                    <span class="job-name">📈 历史行情</span>
                </div>
                <div class="job-item">
                    <span class="job-time">10:30</span>
                    <span class="job-name">💼 同步分笔</span>
                </div>
               
            </div>
            """, unsafe_allow_html=True)

    # 任务控制按钮
    if is_running:
        if st.button("▶ 停止", use_container_width=True, type="secondary", key="scheduler_stop"):
            scheduler.stop()
            st.rerun()
    else:
        if st.button("▶ 启动", use_container_width=True, type="primary", key="scheduler_start"):
            scheduler.start()
            # 添加定时任务
            scheduler.add_daily_job("sync_stock", sync_stock_data, 9, 30)
            scheduler.add_daily_job("sync_realtime", sync_real_time_data, 11, 0)
            scheduler.add_daily_job("sync_history", sync_history_data, 10, 0)
            scheduler.add_daily_job("sync_transaction", sync_history_transaction, 10, 30)
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

    sync_buttons = [
        ("📊", "股票信息", sync_stock_data, "股票信息", "sync-card-purple"),
        ("⚡", "实时行情", sync_real_time_data, "实时行情", "sync-card-blue"),
        ("📈", "历史行情", sync_history_data, "历史行情", "sync-card-green"),
        ("💼", "历史分笔", sync_history_transaction, "历史分笔", "sync-card-orange"),
    ]
    
    # 创建同步状态变量（使用st.session_state确保按钮置灰效果）
    if "is_syncing" not in st.session_state:
        st.session_state.is_syncing = False
    if "sync_data_type" not in st.session_state:
        st.session_state.sync_data_type = None
    
    # 显示同步按钮
    sync_cols = st.columns(4)
    for idx, (icon, title, sync_func, data_type, color_class) in enumerate(sync_buttons):
        with sync_cols[idx]:
            st.markdown(f"""
            <div class="sync-button-card {color_class}">
                <div class="sync-card-icon {color_class}">
                    <span class="sync-icon-large">{icon}</span>
                </div>
                <div class="sync-card-content">
                    <div class="sync-card-title">{title}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 按钮置灰：当任何同步操作正在进行时，禁用所有按钮
            if st.button(f"立即同步", use_container_width=True, type="primary", 
                       key=f"sync_btn_{idx}", disabled=st.session_state.is_syncing):
                # 标记为正在同步，并保存数据类型
                st.session_state.is_syncing = True
                st.session_state.sync_data_type = data_type
                # 触发页面重新加载以更新按钮状态
                st.rerun()
    
    # 在列外部显示同步结果（占据整行）
    if st.session_state.is_syncing and st.session_state.sync_data_type:
        try:
            # 执行同步操作
            result = sync_buttons[[btn[3] for btn in sync_buttons].index(st.session_state.sync_data_type)][2]()
            
            # 显示结果
            if result["success"]:
                st.success(f"✅ {st.session_state.sync_data_type}同步成功！成功: {result['success_count']}, 失败: {result['failed_count']}")
            else:
                st.error(f"❌ {st.session_state.sync_data_type}同步失败: {result['error']}")
        finally:
            # 同步完成后，重置状态
            st.session_state.is_syncing = False
            st.session_state.sync_data_type = None
            
            # st.rerun() todo 等待一会



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

    try:
        summary_data = get_sync_summary()
        # 每日同步次数图表
        show_daily_sync_chart(summary_data)

        _show_sync_type_distribution_chart(summary_data)
        
        # 同步状态分布图表
        _show_sync_status_distribution_chart(summary_data)
        
    except Exception as e:
        st.error(f"生成图表失败: {str(e)}")
        import traceback
        st.exception(e)

def show_daily_sync_chart(summary_data):


    with st.container(border=True, key="daily_sync_chart_container_unique"):
        st.markdown("""
        <div class="chart-header">
            <span class="chart-icon">📅</span>
            <span class="chart-title">每日同步次数</span>
        </div>
        """, unsafe_allow_html=True)

        try:
            daily_counts_data = summary_data.get('daily_counts', [])
            if not daily_counts_data:
                # 如果没有数据，直接显示警告信息
                st.warning("暂无数据")
                return

            # 转换为图表所需格式
            try:
                dates = [str(item.date) if hasattr(item, 'date') else str(item[0]) for item in daily_counts_data]
                counts = [item.count if hasattr(item, 'count') else item[1] for item in daily_counts_data]
            except Exception as data_error:
                st.error(f"数据转换失败: {str(data_error)}")
                return

            # 导入st_pyecharts函数
            from streamlit_echarts import st_pyecharts

            # 创建柱状图
            try:
                bar = ChartBuilder.create_bar_chart(
                    x_data=dates,
                    y_data=counts,
                    series_name="同步次数",
                    title="每日同步数量"
                )
                st.write(f"图表创建成功, bar类型: {type(bar)}")
            except Exception as chart_error:
                st.error(f"图表创建失败: {str(chart_error)}")
                import traceback
                st.exception(chart_error)
                return

            # 显示图表
            try:
                st.write("调用st_pyecharts显示图表...")
                st_pyecharts(bar, height="300px")
            except Exception as render_error:
                st.error(f"图表渲染失败: {str(render_error)}")
                import traceback
                st.exception(render_error)
        except Exception as e:
            st.error(f"生成每日同步图表失败: {str(e)}")
            import traceback
            st.exception(e)
            st.warning("暂无数据")

def _show_sync_type_distribution_chart(summary_data):
    """显示同步类型分布图表"""
    with st.container(border=True, key="sync_type_chart_container_unique"):
        st.markdown("""
        <div class="chart-header">
            <span class="chart-icon">🎯</span>
            <span class="chart-title">同步类型分布</span>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            # 使用传入的统计数据
            type_counts_data = summary_data.get('type_counts', [])
            
            if not type_counts_data:
                # 如果没有数据，直接显示警告信息
                st.warning("暂无数据")
                return
            
            # 创建类型显示名称映射
            type_display_names = {
                'stock_data': '股票数据',
                'history_data': '历史数据',
                'history_transaction': '历史分笔',
                'real_time_data': '实时行情',
                'all': '全部数据'
            }
            
            # 转换为图表所需格式，使用显示名称
            chart_data = []
            try:
                for item in type_counts_data:
                    # 添加类型检查，确保item有正确的属性
                    if hasattr(item, 'type') and hasattr(item, 'count'):
                        display_name = type_display_names.get(item.type, item.type)
                        chart_data.append([display_name, item.count])
            except Exception as inner_e:
                st.warning(f"数据处理过程中出现错误: {str(inner_e)}")
                st.warning("暂无数据")
                return
            
            if not chart_data:
                st.warning("暂无数据")
                return
            
            pie_chart = ChartBuilder.create_pie_chart(
                data_pairs=chart_data,
                total=sum(count for _, count in chart_data)
            )
            
            # 显示图表（使用与stock.py相同的st_pyecharts方法）
            streamlit_echarts.st_pyecharts(pie_chart, height="300px")
        except Exception as e:
            st.error(f"生成同步类型分布图表失败: {str(e)}")
            st.warning("暂无数据")

def _show_sync_status_distribution_chart(summary_data):
    """显示同步状态分布图表"""
    with st.container(border=True, key="sync_status_chart_container_unique"):
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
                # 如果没有数据，直接显示警告信息
                st.warning("暂无数据")
                return
            
            # 创建状态显示名称和颜色映射
            status_display_names = {
                'success': '成功',
                'failed': '失败',
                'running': '运行中',
                'waiting': '等待中'
            }
            
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
                    display_name = status_display_names.get(item.status, item.status)
                    chart_data.append([display_name, item.count])
                    colors.append(color_map.get(item.status, '#6b7280'))
            except Exception as inner_e:
                st.warning(f"数据处理过程中出现错误: {str(inner_e)}")
                st.warning("暂无数据")
                return
            
            if not chart_data:
                st.warning("暂无数据")
                return
            
            # 使用ChartBuilder中的create_pie_chart方法创建饼图
            from utils.chart import ChartBuilder
            status_pie = ChartBuilder.create_pie_chart(
                data_pairs=chart_data,
                total=sum(count for _, count in chart_data)
            )
            
            # 设置自定义颜色
            status_pie.set_colors(colors)
            
            # 显示图表（使用与stock.py相同的st_pyecharts方法）
            streamlit_echarts.st_pyecharts(status_pie, height="300px")
        except Exception as e:
            st.error(f"生成同步状态分布图表失败: {str(e)}")
            st.warning("暂无数据")

def _show_sync_history_records():
    """显示同步历史记录和筛选控件"""
    # 第三行：同步历史记录标题
    st.markdown("""
    <div class="sync-section-header sync-history-section">
        <div class="section-icon">📋</div>
        <div>
            <h2 class="section-title">同步历史记录</h2>
            <p class="section-description">查看和管理所有同步操作的详细记录</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
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
                    ["全部"] + [t.display_name for t in SyncType],
                    key="sync_type_filter"
                )
            with col2:
                status_filter = st.selectbox(
                    "选择同步状态",
                    ["全部"] + [s.value for s in SyncStatus],
                    key="status_filter"
                )
        
        # 转换筛选条件
        sync_type = None
        if sync_type_filter != "全部":
            sync_type_map = {t.display_name: t for t in SyncType}
            sync_type = sync_type_map.get(sync_type_filter)
        
        # 获取同步历史记录
        records = get_sync_history(limit=50, sync_type=sync_type)
        
        if records:
            # 转换为DataFrame
            records_data = [{
                '时间': record.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                '类型': record.sync_type_display,
                '状态': record.status_display,
                '成功数': record.success_count,
                '失败数': record.failed_count,
                '耗时(秒)': record.duration or 0,
                '错误信息': record.error
            } for record in records if status_filter == "全部" or record.status.value == status_filter]
            
            df = pd.DataFrame(records_data)
            
            # 显示表格
            if not df.empty:
                # 隐藏错误信息列，通过展开行显示
                display_df = df.drop(columns=['错误信息'])
                
                # 美化表格显示
                st.markdown(f"""
                <div class="history-list-header">
                    <span class="history-icon">📊</span>
                    <span class="history-title">历史记录列表</span>
                    <span class="history-count">(共 {len(df)} 条)</span>
                </div>
                """, unsafe_allow_html=True)
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # 显示失败记录详情
                failed_records = df[df['状态'] == '失败']
                if not failed_records.empty:
                    with st.expander(f"🔍 查看失败记录详情 ({len(failed_records)} 条)", expanded=False, key="failed_records_expander"):
                        for idx, record in failed_records.iterrows():
                            # 使用更美观的卡片显示错误详情
                            st.markdown(f"""
                            <div class="error-record-card" key="error_record_{idx}">
                                <div class="error-record-header">
                                    <div>
                                        <div class="error-record-time">🕐 {record['时间']}</div>
                                        <div class="error-record-badges">
                                            <span class="error-badge-type">📦 {record['类型']}</span>
                                            <span class="error-badge-status">❌ {record['状态']}</span>
                                        </div>
                                    </div>
                                    <div class="error-record-duration">
                                        <div class="duration-label">⏱️ 耗时</div>
                                        <div class="duration-value">{record['耗时(秒)']}秒</div>
                                    </div>
                                </div>
                                <div class="error-record-stats">
                                    <div class="stat-item">
                                        <span class="stat-label">✅ 成功:</span>
                                        <span class="stat-value-success">{record['成功数']}</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">❌ 失败:</span>
                                        <span class="stat-value-failed">{record['失败数']}</span>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if record['错误信息']:
                                # 使用更好看的卡片样式显示错误信息
                                st.markdown(f"""
                                <div class="error-message-card">
                                    <div class="error-message-header">
                                        <span>⚠️</span>
                                        <span>错误信息</span>
                                    </div>
                                    <div class="error-message-content">
                                        {record['错误信息']}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"显示历史记录失败: {str(e)}")
        import traceback
        st.exception(e)

