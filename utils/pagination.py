from dataclasses import dataclass, field
from time import time

import streamlit as st
from sqlalchemy.orm import Query
from typing import Any, List, Dict, Optional, Callable
import pandas as pd
import logging
from datetime import date, timedelta, datetime


@dataclass
class SearchField:
    """搜索字段配置"""
    field: str  # 字段名
    label: str  # 显示标签
    type: str = "text"  # 字段类型：text, select
    options: List[Any] = field(default_factory=list)  # 选择项（用于select类型）
    default: Any = None  # 默认值
    placeholder: str = ""  # 占位文本
    filter_func: Optional[Callable] = None  # 自定义过滤函数
    min_date: date = None
    max_date: date = None

@dataclass
class SearchConfig:
    """搜索配置"""
    fields: List[SearchField]
    layout: List[int]

@dataclass
class ActionButton:
    """操作按钮配置"""
    label: str  # 按钮文本
    icon: str = ""  # 按钮图标
    handler: Optional[Callable] = None  # 按钮点击处理函数
    type: str = "primary"  # 按钮类型：primary, secondary, success, danger
    tooltip: str = ""  # 按钮提示文本
    disabled: bool = False  # 是否禁用

@dataclass
class ActionConfig:
    """操作区域配置"""
    buttons: List[ActionButton]
    layout: List[int]  # 布局比例

class Pagination:
    def __init__(self, query: Query, page_size: int = 10, search_config: Optional[SearchConfig] = None):
        self.base_query = query
        self.page_size = page_size
        self.search_config = search_config
        self.search_values = {}
        self.query = query
        self.total_count = self.query.count()
        self.total_pages = (self.total_count + page_size - 1) // page_size

    def apply_search(self, search_values: Dict[str, Any]) -> None:
        if not search_values:
            return

        query = self.base_query

        for field in self.search_config.fields:
            value = search_values.get(field.field)
            if value and value not in ["全部", ""]:  # 忽略空值和"全部"选项
                if field.filter_func:
                    # 使用自定义过滤函数
                    query = field.filter_func(query, value)
                else:
                    # 默认过滤逻辑
                    try:
                        column = getattr(query.column_descriptions[0]['type'], field.field)
                        if isinstance(value, str):
                            query = query.filter(column.ilike(f'%{value}%'))
                        else:
                            query = query.filter(column == value)
                    except Exception as e:
                        logging.error(f"Error applying filter for field {field.field}: {str(e)}")

        self.query = query
        self.total_count = self.query.count()
        self.total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)

    def get_page(self, page: int) -> Query:
        offset = (page - 1) * self.page_size
        return self.query.offset(offset).limit(self.page_size)


def paginate_dataframe(
        query: Query,
        page_size: int = 20,
        columns_config: Dict = None,
        format_funcs: Dict = None,
        search_config: Optional[SearchConfig] = None,
        action_config: Optional[ActionConfig] = None,
        title: str = "",
        key_prefix: str = ""
) -> None:
    try:
        # 初始化session_state
        if f"{key_prefix}_current_page" not in st.session_state:
            st.session_state[f"{key_prefix}_current_page"] = 1
        if f"{key_prefix}_page_size" not in st.session_state:
            st.session_state[f"{key_prefix}_page_size"] = page_size
        if f"{key_prefix}_search_values" not in st.session_state:
            st.session_state[f"{key_prefix}_search_values"] = {}

        st.markdown(f"""
            <div class="table-header">
                <div class="table-title">{title}</div>
            </div>
            """, unsafe_allow_html=True)

        # 处理搜索和操作按钮区域
        if search_config or action_config:

            # 分成搜索区域和操作区域两部分
            search_area, action_area = st.columns([6, 1])  # 可以调整比例

            # 搜索区域
            with search_area:
                if search_config:
                    search_values = {}
                    # 创建搜索字段的列
                    search_cols = st.columns(search_config.layout)

                    # 创建搜索字段
                    for idx, field in enumerate(search_config.fields):
                        with search_cols[idx]:
                            field_key = f"{key_prefix}_{field.type}_{field.field}"
                            current_value = st.session_state[f"{key_prefix}_search_values"].get(field.field, field.default)
                            if field.type == "text":
                                value = st.text_input(
                                    field.label,
                                    value=current_value or "",
                                    placeholder=field.placeholder,
                                    key=field_key,
                                    label_visibility="collapsed"
                                )
                            elif field.type == "select":
                                value = st.selectbox(
                                    field.label,
                                    options=field.options,
                                    index=field.options.index(current_value) if current_value in field.options else 0,
                                    key=field_key,
                                    label_visibility="collapsed"
                                )
                            elif field.type == "date":
                                value = st.date_input(
                                    field.label,
                                    value=current_value if current_value else None,
                                    min_value=field.min_date,
                                    max_value=field.max_date,
                                    key=field_key,
                                    label_visibility="collapsed"
                                )
                            elif field.type == "datetime":
                                # 获取当前值
                                current_datetime = current_value if current_value else datetime.now()
                                datetime_str = current_datetime.strftime("%Y-%m-%d %H:%M:%S") if isinstance(current_datetime, datetime) else ""
                                # 文本输入框
                                input_str = st.text_input(
                                    field.label,
                                    value=datetime_str,
                                    placeholder="YYYY-MM-DD HH:MM:SS",
                                    key=field_key,
                                    label_visibility="collapsed"
                                )
                                if input_str.strip():
                                    try:
                                        value = datetime.strptime(input_str, "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        st.error("请输入正确的时间格式：YYYY-MM-DD HH:MM:SS")
                                        value = current_datetime
                        search_values[field.field] = value
                    # 搜索按钮
                    with search_cols[-2]:
                        if st.button("搜索", icon="♻", key=f"{key_prefix}_search_button", use_container_width=True):
                            st.session_state[f"{key_prefix}_search_values"] = search_values.copy()
                            st.session_state[f"{key_prefix}_current_page"] = 1
                            st.rerun()
            # 操作区域
            with action_area:
                if action_config:
                    # 创建操作按钮的列
                    action_cols = st.columns(action_config.layout)
                    # 处理操作按钮
                    for idx, button in enumerate(action_config.buttons):
                        with action_cols[idx]:
                            button_key = f"{key_prefix}_action_{button.label}"
                            if st.button(
                                    icon=button.icon,
                                    label=button.label,
                                    key=button_key,
                                    disabled=button.disabled,
                                    use_container_width=True
                            ):
                                if button.handler:
                                    button.handler()

        # 创建分页器并应用搜索条件
        paginator = Pagination(query, page_size, search_config)
        if search_config:
            paginator.apply_search(st.session_state[f"{key_prefix}_search_values"])

        if paginator.total_count == 0:
            st.info("没有找到数据")
            return

        # 更新分页器配置
        paginator.page_size = st.session_state[f"{key_prefix}_page_size"]
        # 获取当前页数据
        records = paginator.get_page(st.session_state[f"{key_prefix}_current_page"]).all()

        # 转换为DataFrame
        if records:
            # 转换记录为字典列表
            data = [record.__dict__ for record in records]
            for d in data:
                d.pop('_sa_instance_state', None)

            df = pd.DataFrame(data)

            # 应用格式化函数
            if format_funcs:
                for field, formats in format_funcs.items():
                    if isinstance(formats, dict):
                        for format_key, format_func in formats.items():
                            if format_key != 'raw':  # 如果不是 raw，创建新列
                                new_col = f"{field}_{format_key}"
                                df[new_col] = df[field].apply(format_func)
                            else:  # 如果是 raw，处理原列
                                df[field] = df[field].apply(format_func)
                    else:
                        # 处理普通的格式化函数
                        df[field] = df[field].apply(formats)

            # 如果提供了 columns_config，使用其键的顺序重排列
            if columns_config:
                ordered_columns = [col for col in columns_config.keys() if col in df.columns]
                df = df[ordered_columns]

            # 显示数据框
            st.dataframe(
                df,
                column_config=columns_config,
                hide_index=False,
                use_container_width=True
            )
            # 分页导航控件和信息显示在同一行
            col00, col0, col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1, 1, 2.5])
            with col1:
                current_page = st.number_input(
                    "",
                    min_value=1,
                    max_value=paginator.total_pages,
                    value=st.session_state[f"{key_prefix}_current_page"],
                    key=f"{key_prefix}_page_input",
                    label_visibility="collapsed"
                )
                if current_page != st.session_state[f"{key_prefix}_current_page"]:
                    st.session_state[f"{key_prefix}_current_page"] = current_page
                    st.rerun()
            with col2:
                if st.button("首页",
                             disabled=st.session_state[f"{key_prefix}_current_page"] == 1,
                             key=f"{key_prefix}_first_page",
                             use_container_width=True):
                    st.session_state[f"{key_prefix}_current_page"] = 1
                    st.rerun()
            with col3:
                if st.button("上一页",
                             disabled=st.session_state[f"{key_prefix}_current_page"] == 1,
                             key=f"{key_prefix}_prev_page",
                             use_container_width=True):
                    st.session_state[f"{key_prefix}_current_page"] -= 1
                    st.rerun()
            with col4:
                if st.button("下一页",
                             disabled=st.session_state[f"{key_prefix}_current_page"] == paginator.total_pages,
                             key=f"{key_prefix}_next_page",
                             use_container_width=True):
                    st.session_state[f"{key_prefix}_current_page"] += 1
                    st.rerun()
            with col5:
                if st.button("末页",
                             disabled=st.session_state[f"{key_prefix}_current_page"] == paginator.total_pages,
                             key=f"{key_prefix}_last_page",
                             use_container_width=True):
                    st.session_state[f"{key_prefix}_current_page"] = paginator.total_pages
                    st.rerun()
            # 显示记录范围信息
            with col6:
                current_page = st.session_state[f"{key_prefix}_current_page"]
                start_idx = (st.session_state[f"{key_prefix}_current_page"] - 1) * paginator.page_size + 1
                end_idx = min(start_idx + paginator.page_size - 1, paginator.total_count)
                st.markdown(
                    f'<div class="pagination-info">显示 {start_idx}-{end_idx} 条, {current_page}/{paginator.total_pages} 页, 共 {paginator.total_count} 条 ',
                    unsafe_allow_html=True
                )
        else:
            st.warning("当前页没有数据")

    except Exception as e:
        logging.error(f"Error in paginate_dataframe: {str(e)}")
        st.error(f"分页显示失败：{str(e)}")
