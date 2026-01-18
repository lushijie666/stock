# 股票

from functools import partial
from typing import  Dict, Any, List
import akshare as ak
import streamlit_echarts
import logging
import pandas as pd
from datetime import datetime as dt
import streamlit as st
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import func
from service.stock_chart import KEY_PREFIX as chartKP, show_detail_dialog
from enums.category import Category
from models.stock import Stock
from utils.chart import ChartBuilder
from utils.convert import get_column_value, clean_number_value,clean_name
from utils.db import get_db_session
from utils.fetch_handler import create_reload_handler
from utils.message import show_message
from utils.pagination import paginate_dataframe, SearchConfig, SearchField, ActionConfig, ActionButton
from utils.session import get_session_key, SessionKeys
from utils.stock_selector import create_stock_selector, handle_error, handle_not_found
from utils.table import  format_pinyin_short

KEY_PREFIX = "stock"


def get_codes(category: Category) -> List[str]:
    try:
        with get_db_session() as session:
            return Stock.get_codes_by_category(session, category)
    except Exception as e:
        logging.error(f"获取股票失败: {str(e)}")
        return []

def get_followed_codes(category: Category) -> List[str]:
    try:
        with get_db_session() as session:
            return Stock.get_followed_codes_by_category(session, category)
    except Exception as e:
        logging.error(f"获取股票失败: {str(e)}")
        return []

def show_category_pie_chart():
    try:
        with get_db_session() as session:
            result = (
                session.query(
                    Stock.category,
                    func.count(Stock.id).label('count')
                )
                .filter(Stock.removed == False)
                .group_by(Stock.category)
                .all()
            )
            df = pd.DataFrame(result, columns=['分类', '数量'])
            df['分类'] = df['分类'].apply(lambda x: Category(x).fullText)
            if df.empty:
                st.warning("暂无数据")
                return

            total_stocks = df['数量'].sum()
            data_pairs = [(cat, num) for cat, num in zip(df['分类'], df['数量'])]

            pie = ChartBuilder.create_pie_chart(data_pairs, total_stocks)
            # 显示图表
            streamlit_echarts.st_pyecharts(pie, height="300px")

            df['占比'] = (df['数量'] / total_stocks * 100).round(1)
            st.dataframe(
                df,
                column_config={
                    "分类": st.column_config.TextColumn("分类"),
                    "数量": st.column_config.NumberColumn("股票数量", format="%d"),
                    "占比": st.column_config.NumberColumn("占比", format="%.1f%%")
                },
                hide_index=True,
                use_container_width=True,
            )

    except Exception as e:
        st.error(f"显示股票分类分布图表失败: {str(e)}")


def show_page(category: Category):
    try:
        with get_db_session() as session:
            # 构建查询
            query = session.query(Stock).filter(
                Stock.category == category,
                Stock.removed == False
            ).order_by(Stock.code.asc())
            # 使用通用的分页
            paginate_dataframe(
                query,
                100,
                columns_config={
                    # 基础信息
                    # 'category': st.column_config.TextColumn('分类', help="股票分类"),
                    'code': st.column_config.TextColumn('股票代码', help="股票代码"),
                    'name': st.column_config.TextColumn('股票名称', help="股票名称"),
                    'pinyin': st.column_config.TextColumn('股票简拼', help="股票拼音简称"),
                    'full_name': st.column_config.TextColumn('全称', help="公司名称"),
                    'ipo_at': st.column_config.DatetimeColumn('上市时间', help="上市时间"),
                    'total_capital': st.column_config.TextColumn('总股本(股)', help="总股本"),
                    'flow_capital': st.column_config.TextColumn('流通股本(股)', help="流通股本"),
                    'industry': st.column_config.TextColumn('行业', help="行业"),
                    'updated_at': st.column_config.DatetimeColumn('最后更新时间', help="更新时间"),
                },
                # 格式化函数
                format_funcs={
                    'pinyin': format_pinyin_short,
                },
                search_config=SearchConfig(
                    fields=[
                        SearchField(
                            field="keyword",
                            label="股票代码/名称/简拼",
                            type="text",
                            placeholder="输入股票代码/名称/简拼",
                            search_fields = ["code", "name", "pinyin"]
                        )
                    ],
                    layout=[1, 1, 1, 1]
                ),
                action_config=ActionConfig(
                    buttons=[
                        ActionButton(
                            icon="🐙",
                            label="更新",
                            handler=partial(reload, category=category),
                            type="primary"
                        ),
                    ],
                    layout=[1, 0.2]  # 每个按钮占一列
                ),
                title= category.fullText,
                key_prefix=get_session_key(SessionKeys.PAGE, prefix=f'{KEY_PREFIX}', category=category),
            )
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_follow_chart():
    try:
        with get_db_session() as session:
            # 查询所有被关注的股票，按分类和代码排序
            stocks = session.query(Stock).filter(
                Stock.removed == False,
                Stock.is_followed == True
            ).order_by(Stock.category.asc(), Stock.code.asc()).all()

            if not stocks:
                st.info("暂无关注的股票")
                return

            # 按分类组织数据，使用字典存储每个分类的股票
            category_stocks = {}
            for stock_item in stocks:
                category_enum = Category(stock_item.category)
                category_name = category_enum.fullText
                if category_name not in category_stocks:
                    category_stocks[category_name] = []
                category_stocks[category_name].append(stock_item)

            # 使用固定顺序创建 tabs，与 show_kline_chart 方法保持一致
            tabs = st.tabs(Category.fullTexts())
            for tab, category in zip(tabs, Category):
                category_name = category.fullText
                # 获取该分类下的股票列表，如果没有则为空列表
                stocks_list = category_stocks.get(category_name, [])
                with tab:
                    original_category = category

                    # 如果该分类下没有关注的股票，显示提示信息
                    if not stocks_list:
                        st.info(f"{category_name}分类下暂无关注的股票")
                        continue

                    search_key = f"follow_search_{original_category}"
                    search_term = st.text_input(
                        "🔍 搜索股票（代码/名称/全称）",
                        key=search_key,
                        placeholder="输入股票代码/名称/简拼",
                        label_visibility="collapsed"
                    )
                    # 根据搜索词过滤股票
                    filtered_stocks = stocks_list
                    if search_term:
                        search_term_lower = search_term.lower()
                        filtered_stocks = [
                            stock_item for stock_item in stocks_list
                            if (search_term_lower in stock_item.code.lower() or
                                search_term_lower in stock_item.name.lower() or
                                (stock_item.full_name and search_term_lower in stock_item.full_name.lower()))
                        ]

                        if not filtered_stocks:
                            st.info(f"未找到包含 '{search_term}' 的股票")
                            continue

                    # 显示搜索结果数量
                    if search_term:
                        st.caption(f"找到 {len(filtered_stocks)} 只股票")

                    # 使用网格布局，每行显示多个股票卡片
                    for j in range(0, len(filtered_stocks), 3):
                        cols = st.columns(3)
                        for k, col in enumerate(cols):
                            if j + k < len(filtered_stocks):
                                stock_item = filtered_stocks[j + k]
                                with col:
                                    followed_time = stock_item.followed_at.strftime(
                                        '%Y-%m-%d %H:%M:%S') if stock_item.followed_at else '-'
                                    ipo_time = stock_item.ipo_at.strftime('%Y-%m-%d') if stock_item.ipo_at else '-'
                                    card_html = f"""
                                               <div class="stock-card">
                                                   <div class="stock-card-header">
                                                       <div class="stock-card-title">
                                                           <span class="stock-name">{stock_item.name}</span>
                                                           <span class="stock-code">({stock_item.code})</span>
                                                       </div>
                                                   </div>
                                                   <div class="stock-card-body">
                                                       <div class="stock-info-row">
                                                           <span class="info-label">全称:</span>
                                                           <span class="info-value">{stock_item.full_name or '-'}</span>
                                                       </div>
                                                        <div class="stock-info-row">
                                                           <span class="info-label">关注时间:</span>
                                                           <span class="info-value">{followed_time}</span>
                                                       </div>
                                                       <div class="stock-info-row">
                                                           <span class="info-label">上市时间:</span>
                                                           <span class="info-value">{ipo_time}</span>
                                                       </div>
                                                        <div class="stock-info-row">
                                                           <span class="info-label">行业:</span>
                                                           <span class="info-value">{stock_item.industry or '-'}</span>
                                                       </div>
                                                   </div>
                                               </div>
                                               """
                                    st.markdown(card_html, unsafe_allow_html=True)
                                    if st.button("股票图表", key=f"chart_{stock_item.code}", type="secondary",
                                                 use_container_width=True):
                                        st.session_state['show_stock_chart_dialog'] = stock_item.code
                                        st.rerun()
        if 'show_chart_dialog' in st.session_state:
            show_detail_dialog(st.session_state['show_stock_chart_dialog'])
            if 'show_chart_dialog' in st.session_state:
                del st.session_state['show_stock_chart_dialog']
    except Exception as e:
        st.error(f"加载关注股票数据失败：{str(e)}")


def show_follow_page(category: Category):
    show_add_follow(category=category)
    try:
        with get_db_session() as session:
            query = session.query(Stock).filter(
                Stock.category == category,
                Stock.removed == False,
                Stock.is_followed == True
            ).order_by(Stock.code.asc())

            # 获取所有关注的股票
            stocks = query.all()
            if not stocks:
                st.info("暂无关注的股票")
                return

            # 添加搜索功能
            st.markdown("""
            <div class="table-header">
                <div class="table-title">
                    已关注的股票
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 搜索框
            search_key = f"follow_search_{category.value}"
            search_term = st.text_input(
                "🔍 搜索股票（代码/名称/全称）",
                key=search_key,
                placeholder="输入股票代码/名称/简拼",
                label_visibility="collapsed"
            )
            
            # 根据搜索词过滤股票
            if search_term:
                search_term_lower = search_term.lower()
                filtered_stocks = [
                    stock for stock in stocks
                    if (search_term_lower in stock.code.lower() or
                        search_term_lower in stock.name.lower() or
                        (stock.full_name and search_term_lower in stock.full_name.lower()))
                ]
                stocks = filtered_stocks
                
                if not filtered_stocks:
                    st.info(f"未找到包含 '{search_term}' 的股票")
                    return
            
            # 显示搜索结果数量
            if search_term:
                st.caption(f"找到 {len(stocks)} 只股票")
            
            # 使用网格布局，每行显示多个股票卡片
            for i in range(0, len(stocks), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(stocks):
                        stock = stocks[i + j]
                        with col:
                            followed_time = stock.followed_at.strftime('%Y-%m-%d %H:%M:%S') if stock.followed_at else '-'
                            ipo_time = stock.ipo_at.strftime('%Y-%m-%d') if stock.ipo_at else '-'
                            card_html = f"""
                            <div class="stock-card" style="border-left: 4px solid #9c27b0;">
                                <div class="stock-card-header">
                                    <div class="stock-card-title">
                                        <span class="stock-name">{stock.name}</span>
                                        <span class="stock-code">({stock.code})</span>
                                    </div>
                                </div>
                                <div class="stock-card-body">
                                    <div class="stock-info-row">
                                        <span class="info-label">全称:</span>
                                        <span class="info-value">{stock.full_name or '-'}</span>
                                    </div>
                                     <div class="stock-info-row">
                                        <span class="info-label">关注时间:</span>
                                        <span class="info-value">{followed_time}</span>
                                    </div>
                                    <div class="stock-info-row">
                                        <span class="info-label">上市时间:</span>
                                        <span class="info-value">{ipo_time}</span>
                                    </div>
                                     <div class="stock-info-row">
                                        <span class="info-label">行业:</span>
                                        <span class="info-value">{stock.industry or '-'}</span>
                                    </div>
                                </div>
                            </div>
                            """
                            st.markdown(card_html, unsafe_allow_html=True)
                            # 并行展示按钮，使用不同颜色区分
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("移除关注", key=f"remove_{stock.code}", use_container_width=True):
                                    remove_follow(category, stock.code)
                                    st.rerun()
                            with col2:
                                if st.button("股票图表", key=f"kline_{stock.code}", type="primary", use_container_width=True):
                                    current_stock_key = get_session_key(
                                        SessionKeys.CURRENT_STOCK,
                                        prefix=chartKP,
                                        category=stock.category
                                    )
                                    st.session_state[current_stock_key] = stock.code
                                    st.session_state.selected_page = "股票图表"
                                    st.rerun()
                            with col3:
                                if st.button("买卖记录", key=f"trade_{stock.code}", type="primary", use_container_width=True):
                                    current_stock_key = get_session_key(
                                        SessionKeys.CURRENT_STOCK,
                                        prefix=chartKP,
                                        category=stock.category
                                    )
                                    st.session_state[current_stock_key] = stock.code
                                    st.session_state.selected_page = "买卖记录"
                                    st.rerun()
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")


def show_add_follow(category: Category):
    with st.expander("添加关注股票"):
        prefix = f'add_follow_{KEY_PREFIX}_{category.value}'
        selected_stock_key = f'selected_stock_{prefix}'  # 用于存储选中的股票对象

        # 创建股票选择器
        selector = create_stock_selector(
            category=category,
            prefix=prefix,
            on_select=lambda stock: st.session_state.update({selected_stock_key: stock.code}),
            on_error=handle_error,
            on_not_found=handle_not_found,
            hide_followed=True,
        )
        selector.show_selector()
        selector.handle_current_stock()
        # 添加确定和取消按钮
        col1, = st.columns([1])  # 调整按钮布局
        with col1:
            if st.button("确定", key=f'confirm_follow_{KEY_PREFIX}_{category.value}', type="primary", use_container_width=True):
                if stock_code := st.session_state.get(selected_stock_key):
                    add_follow(category, stock_code)
                    # 清理状态并刷新
                    st.session_state.pop(selected_stock_key, None)
                    st.rerun()
                else:
                    show_message("请先选择股票", type="warning")


def add_follow(category: Category, stock_code: str):
    try:
        with get_db_session() as session:
            stock = session.query(Stock).filter(
                Stock.code == stock_code,
                Stock.category == category,
            ).first()
            if stock:
                stock.is_followed = True
                stock.followed_at = dt.now()
                session.commit()
                show_message(f"已添加关注：{stock.name}({stock.code})", type="success")
            else:
                show_message("未找到选中的股票", type="warning")
    except Exception as e:
        show_message(f"添加关注失败：{str(e)}", type="error")

def remove_follow(category: Category, stock_code: str):
    try:
        with get_db_session() as session:
            stock = session.query(Stock).filter(
                Stock.code == stock_code,
                Stock.category == category,
            ).first()
            if stock:
                stock.is_followed = False
                stock.followed_at = None
                session.commit()
                show_message(f"已取消关注：{stock.name}({stock.code})", type="success")
                st.rerun()  # 刷新页面以更新显示
            else:
                show_message("未找到选中的股票", type="warning")
    except Exception as e:
        show_message(f"取消关注失败：{str(e)}", type="error")

def reload(category: Category):
    """
    刷新股票数据

    Args:
        category: 股票分类
    """
    def build_filter(args: Dict[str, Any], session: Session) -> List:
        return [
            Stock.category == category,
        ]
    history_handler = create_reload_handler(
        model=Stock,
        fetch_func=fetch,
        unique_fields=['code'],
        build_filter=build_filter,
        mark_existing=True,
        excluded_columns=['is_followed', 'followed_at']
    )
    return history_handler.refresh(category=category)

def fetch(category: Category) -> list:
    # 拉取 https://akshare.akfamily.xyz/data/stock/stock.html#id11
    fetch_functions = {
        Category.A_SH: partial(ak.stock_info_sh_name_code, symbol="主板A股"),
        Category.A_SZ: partial(ak.stock_info_sz_name_code, symbol="A股列表"),
        Category.A_BJ: partial(ak.stock_info_bj_name_code),
    }
    try:
        if fetch_func := fetch_functions.get(category):
            logging.info(f"开始获取[{KEY_PREFIX}]数据..., 分类: {category.text}")
            df = fetch_func()
            logging.info(f"成功获取[{KEY_PREFIX}]数据, 分类: {category.text}, 共 {len(df)} 条记录")

            # 为A股获取额外的详情数据
            stock_individual_info = {}
            stock_profile_info = {}

            if category in [Category.A_SH, Category.A_SZ, Category.A_BJ]:
                try:
                    logging.info(f"开始获取[{KEY_PREFIX}]个股详情数据 (stock_individual_info_em)...")
                    individual_df = ak.stock_individual_info_em(symbol="全部A股")
                    if individual_df is not None and not individual_df.empty:
                        # 使用股票代码作为key建立映射
                        for _, info_row in individual_df.iterrows():
                            stock_code = str(info_row.get("代码", "")).strip()
                            if stock_code:
                                stock_individual_info[stock_code] = info_row
                        logging.info(f"成功获取个股详情数据，共 {len(stock_individual_info)} 条")
                except Exception as e:
                    logging.error(f"获取stock_individual_info_em数据失败: {str(e)}")

                try:
                    logging.info(f"开始获取[{KEY_PREFIX}]公司概况数据 (stock_profile_cninfo)...")
                    profile_df = ak.stock_profile_cninfo()
                    if profile_df is not None and not profile_df.empty:
                        # 使用股票代码作为key建立映射
                        for _, profile_row in profile_df.iterrows():
                            stock_code = str(profile_row.get("证券代码", "")).strip()
                            if stock_code:
                                stock_profile_info[stock_code] = profile_row
                        logging.info(f"成功获取公司概况数据，共 {len(stock_profile_info)} 条")
                except Exception as e:
                    logging.error(f"获取stock_profile_cninfo数据失败: {str(e)}")

            data = []
            for i, row in df.iterrows():
                try:
                    code = get_column_value(row, "code")

                    # 基础字段
                    s = Stock(
                        category=Category.from_stock_code(code),
                        code=code,
                        name=clean_name(get_column_value(row, "name")),
                        full_name=row.get("公司全称"),
                        ipo_at=get_column_value(row, "ipo_at"),
                        total_capital=clean_number_value(get_column_value(row, "total_capital")),
                        flow_capital=clean_number_value(get_column_value(row, "flow_capital")),
                        industry=row.get("所属行业"),
                    )

                    # 合并stock_individual_info_em的数据
                    if code in stock_individual_info:
                        individual_row = stock_individual_info[code]
                        # 获取"行业"字段
                        industry_from_individual = individual_row.get("行业", "")
                        # 获取"总市值"字段
                        total_market_value = individual_row.get("总市值", "")

                        # 合并行业字段（拼接）
                        industries = []
                        if s.industry:
                            industries.append(str(s.industry))
                        if industry_from_individual:
                            industries.append(str(industry_from_individual))
                        s.industry = " / ".join(industries) if industries else None

                        # 设置总市值
                        s.total_market_value = str(total_market_value) if total_market_value else None

                    # 合并stock_profile_cninfo的数据
                    if code in stock_profile_info:
                        profile_row = stock_profile_info[code]

                        # 使用"公司名称"更新full_name（如果存在）
                        company_name = profile_row.get("公司名称", "")
                        if company_name and not s.full_name:
                            s.full_name = str(company_name)

                        # 使用"上市日期"更新ipo_at（如果存在且原值为空）
                        ipo_date = profile_row.get("上市日期", "")
                        if ipo_date and pd.notna(ipo_date):
                            try:
                                if isinstance(ipo_date, str):
                                    s.ipo_at = pd.to_datetime(ipo_date)
                                elif isinstance(ipo_date, pd.Timestamp):
                                    s.ipo_at = ipo_date.to_pydatetime()
                            except Exception as date_error:
                                logging.warning(f"解析上市日期失败: {ipo_date}, 错误: {str(date_error)}")

                        # 获取"入选指数"
                        selected_indices = profile_row.get("入选指数", "")
                        s.selected_indices = str(selected_indices) if selected_indices else None

                        # 合并行业字段（拼接）
                        industry_from_profile = profile_row.get("所属行业", "")
                        if industry_from_profile:
                            if s.industry:
                                # 避免重复
                                existing_industries = set(s.industry.split(" / "))
                                if str(industry_from_profile) not in existing_industries:
                                    s.industry = f"{s.industry} / {industry_from_profile}"
                            else:
                                s.industry = str(industry_from_profile)

                        # 获取"成立日期"
                        founded_date = profile_row.get("成立日期", "")
                        if founded_date and pd.notna(founded_date):
                            try:
                                if isinstance(founded_date, str):
                                    s.founded_at = pd.to_datetime(founded_date)
                                elif isinstance(founded_date, pd.Timestamp):
                                    s.founded_at = founded_date.to_pydatetime()
                            except Exception as date_error:
                                logging.warning(f"解析成立日期失败: {founded_date}, 错误: {str(date_error)}")

                        # 获取"主营业务"
                        main_business = profile_row.get("主营业务", "")
                        s.main_business = str(main_business) if main_business else None

                        # 获取"经营范围"
                        business_scope = profile_row.get("经营范围", "")
                        s.business_scope = str(business_scope) if business_scope else None

                        # 合并地址字段（注册地址和办公地址）
                        registered_address = profile_row.get("注册地址", "")
                        office_address = profile_row.get("办公地址", "")
                        addresses = []
                        if registered_address:
                            addresses.append(f"注册地址: {registered_address}")
                        if office_address:
                            addresses.append(f"办公地址: {office_address}")
                        s.address = "; ".join(addresses) if addresses else None

                    s.pinyin = s.generate_pinyin()
                    logging.info(f"获取[{KEY_PREFIX}]的数据, 第{i}条, 信息为: {s}")
                    data.append(s)
                except Exception as row_error:
                    logging.error(f"获取[{KEY_PREFIX}]到的数据异常, 信息: {row}, 错误: {str(row_error)}")
                    continue
            return data
        # 处理美股数据
        elif category == Category.US_XX:
            logging.info(f"开始获取[{KEY_PREFIX}]数据..., 分类: {category.text}")
            data = []  # 在循环外初始化，收集所有分类的数据
            for symbol in [
                "科技类",
                "金融类",
                "医药食品类",
                "媒体类",
                "汽车能源类",
                "制造零售类",
            ]:
                df = ak.stock_us_famous_spot_em(symbol=symbol)
                logging.info(f"成功获取[{KEY_PREFIX}]数据, 分类: {category.text}, symbol: {symbol}, 共 {len(df)} 条记录")
                for i, row in df.iterrows():
                    try:
                        raw_code = row.get("代码", "")
                        if not raw_code or pd.isna(raw_code):
                            logging.warning(f"跳过无效美股数据，第{i}行，代码为空")
                            continue

                        # 提取前缀和代码
                        if '.' in str(raw_code):
                            prefix, code = str(raw_code).split('.', 1)
                        else:
                            prefix = ""
                            code = str(raw_code)

                        # 添加数据验证，跳过空代码或无效数据
                        if not code or code.strip() == '':
                            logging.warning(f"跳过无效美股数据，第{i}行，代码为空")
                            continue

                        # 检查是否已存在相同代码的数据（避免重复）
                        if any(existing_stock.code == code for existing_stock in data):
                            logging.warning(f"跳过重复美股数据，代码: {code}")
                            continue

                        name = row.get("名称", "")
                        if not name or pd.isna(name):
                            logging.warning(f"跳过无效美股数据，第{i}行，名称为空")
                            continue

                        # 将原始名称和前缀保存到 full_name 中
                        full_name = f"{name}({prefix})" if prefix else str(name)

                        s = Stock(
                            category=category,
                            code=code,
                            name=clean_name(str(name)),
                            full_name=full_name,  # 保存前缀信息，格式：名称(前缀)
                            ipo_at=None,
                            total_capital=None,
                            flow_capital=None,
                            industry=symbol,  # 使用美股分类作为行业
                        )
                        s.pinyin = s.generate_pinyin()
                        logging.info(f"获取[{KEY_PREFIX}]的数据, 第{i}条, 信息为: {s}")
                        data.append(s)
                    except Exception as row_error:
                        logging.error(f"获取[{KEY_PREFIX}]到的数据异常, 信息: {row}, 错误: {str(row_error)}")
                        continue
            return data
        return None
    except Exception as e:
        logging.error(f"获取[{KEY_PREFIX}]到的数据异常: {str(e)}")
        return None


def get_total_stocks_count():
    """获取总股票数"""
    try:
        with get_db_session() as session:
            count = session.query(func.count(Stock.id)).filter(Stock.removed == False).scalar()
            return count or 0
    except Exception as e:
        logging.error(f"获取总股票数失败: {str(e)}")
        return 0


def get_followed_stocks_count():
    """获取关注股票数"""
    try:
        with get_db_session() as session:
            count = session.query(func.count(Stock.id)).filter(
                Stock.removed == False,
                Stock.is_followed == True
            ).scalar()
            return count or 0
    except Exception as e:
        logging.error(f"获取关注股票数失败: {str(e)}")
        return 0


def sync() -> Dict[str, int]:
    success_count = 0
    failed_count = 0
    logging.info(f"开始同步{KEY_PREFIX}数据")
    categories = Category.get_all()
    for category in categories:
        #show_message(f"正在处理分类: {category.fullText}", type="warning")
        try:
            reload(category)
            success_count += 1
            #show_message(f"分类: {category.fullText} 处理完成", type="success")
        except Exception as e:
            failed_count += 1
            #show_message(f"分类: {category.fullText} 处理时出错: {str(e)}", type="error")
        logging.info(f"同步[{KEY_PREFIX}]的数据完成...，分类: {category.fullText}")
    logging.info(f"同步[{KEY_PREFIX}]数据完成，成功数: {success_count}, 失败数: {failed_count}")
    return {
        "success_count": success_count,
        "failed_count": failed_count
    }