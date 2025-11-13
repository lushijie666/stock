from datetime import datetime
from dataclasses import dataclass
from typing import Callable, TypeVar, Generic, List, Any, Dict, Optional, Union
import logging
import streamlit as st
from sqlalchemy.orm import Session
from utils.db import get_db_session, upsert_objects
from utils.message import show_message
from utils.session import get_date_range

T = TypeVar('T')  # 用于数据模型
D = TypeVar('D')  # 用于数据类型


@dataclass
class ReloadConfig(Generic[T, D]):
    model: type[T]  # 数据模型类
    fetch_func: Callable[..., List[D]]  # 数据获取函数
    unique_fields: List[str]  # 唯一字段
    build_filter: Callable[[Any, Session], Dict[str, Any]]
    loading_message: str = "请稍候，正在处理..."
    error_prefix: str = "处理失败"
    mark_existing: bool = False


class ReloadHandler(Generic[T, D]):
    def __init__(self, config: ReloadConfig[T, D]):
        self.config = config
        self.overlay_container = None
        self.progress_bar = None
        self.status_text = None

    def show_loading(self):
        """显示加载动画"""
        self.overlay_container = st.empty()
        self.overlay_container.markdown(f"""
            <div class="overlay">
                <div class="loading-spinner">
                    <div class="loading-message">{self.config.loading_message}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    def clear_displays(self):
        """清理显示组件"""
        if self.overlay_container:
            self.overlay_container.empty()
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_text:
            self.status_text.empty()

    def show_statistics(self, session: Session, filter_args: Dict[str, Any], result: Dict) -> None:
        """显示统计信息"""
        # 使用自定义过滤条件
        filter_conditions = self.config.build_filter(filter_args, session)
        base_query = session.query(self.config.model)

        # 统计活跃记录
        total_active = base_query.filter(
            *filter_conditions,
            self.config.model.removed == False
        ).count()

        # 统计已移除记录
        total_removed = base_query.filter(
            *filter_conditions,
            self.config.model.removed == True
        ).count()

        if result['failed'] > 0:
            show_message(
                message=f"部分数据更新失败\n"
                        f"成功: {result['processed']} 条\n"
                        f"失败: {result['failed']} 条",
                type="warning",
                duration=3,
            )
        else:
            show_message(
                message=f"数据更新完成！\n"
                        f"活跃记录: {total_active} 条\n"
                        f"已移除记录: {total_removed} 条",
                type="success",
                duration=3,
            )
    def refresh(self, *args, **kwargs) -> bool:
        try:
            self.show_loading()
            data = self.config.fetch_func(*args, **kwargs)
            if not data:
                show_message("获取数据为空！", "warning")
                return False

            with get_db_session() as session:
                if self.config.mark_existing:
                    filter_conditions = self.config.build_filter(kwargs, session)
                    session.query(self.config.model).filter(
                        *filter_conditions,
                        self.config.model.removed == False
                    ).update({
                        # 使用字典形式，不需要 == 操作符
                        'removed': True,
                        'updated_at': datetime.now()
                    }, synchronize_session=False)  # 添加 synchronize_session=False
                    session.commit()

                self.progress_bar = st.progress(0)
                self.status_text = st.empty()

                result = upsert_objects(
                    objects=data,
                    session=session,
                    model=self.config.model,
                    unique_fields=self.config.unique_fields
                )
                self.progress_bar.progress(1.0)
                self.status_text.text(
                    f"处理进度: {result['processed']}/{result['total']} "
                    f"(成功: {result['processed']} 失败: {result['failed']})"
                )
                self.show_statistics(session, kwargs, result)
                return result['processed'] > 0

        except Exception as e:
            logging.error(f"Refresh error: {str(e)}")
            show_message(
                message=f"{self.config.error_prefix}: {str(e)}",
                type="error"
            )
            return False
        finally:
            self.clear_displays()

    def refresh_ignore_message(self, *args, **kwargs):
        try:
            data = self.config.fetch_func(*args, **kwargs)
            if not data:
                return None
            with get_db_session() as session:
                if self.config.mark_existing:
                    filter_conditions = self.config.build_filter(kwargs, session)
                    session.query(self.config.model).filter(
                        *filter_conditions,
                        self.config.model.removed == False
                    ).update({
                        # 使用字典形式，不需要 == 操作符
                        'removed': True,
                        'updated_at': datetime.now()
                    }, synchronize_session=False)  # 添加 synchronize_session=False
                    session.commit()
                upsert_objects(
                    objects=data,
                    session=session,
                    model=self.config.model,
                    unique_fields=self.config.unique_fields
                )
                return None
        except Exception as e:
            logging.error(f"Refresh error: {str(e)}")
            return None
            
    def refresh_with_stats(self, *args, **kwargs) -> Dict[str, int]:
        """
        刷新数据并返回统计信息，不显示UI消息
        
        Returns:
            Dict: 包含成功和失败计数的字典
                {"success_count": int, "failed_count": int}
        """
        try:
            data = self.config.fetch_func(*args, **kwargs)
            if not data:
                return {"success_count": 0, "failed_count": 0}
                
            with get_db_session() as session:
                if self.config.mark_existing:
                    filter_conditions = self.config.build_filter(kwargs, session)
                    session.query(self.config.model).filter(
                        *filter_conditions,
                        self.config.model.removed == False
                    ).update({
                        'removed': True,
                        'updated_at': datetime.now()
                    }, synchronize_session=False)
                    session.commit()
                    
                # 调用 upsert_objects 获取详细统计信息
                upsert_result = upsert_objects(
                    objects=data,
                    session=session,
                    model=self.config.model,
                    unique_fields=self.config.unique_fields,
                    **kwargs.get('upsert_options', {})
                )
                
                return {
                    "success_count": upsert_result['processed'],
                    "failed_count": upsert_result['failed']
                }
        except Exception as e:
            logging.error(f"Refresh with stats error: {str(e)}")
            return {"success_count": 0, "failed_count": 1}


@dataclass
class DateRangeConfig:
    prefix: str = ""
    start_suffix: str = "start_date"
    end_suffix: str = "end_date"

class DateRangeReloadHandler(ReloadHandler[T, D]):
    """带日期范围处理的重载处理器"""
    def __init__(self, config: ReloadConfig[T, D], date_config: Optional[DateRangeConfig] = None):
        super().__init__(config)
        self.date_config = date_config or DateRangeConfig()

    def get_date_range(self) -> Optional[tuple[str, str]]:
       return get_date_range(self.date_config.prefix, self.date_config.start_suffix, self.date_config.end_suffix)

    def refresh_with_dates(self, **kwargs) -> bool:
        """使用日期范围刷新"""
        try:
            date_range = self.get_date_range()
            if not date_range:
                return False

            start_date, end_date = date_range
            return super().refresh(
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
        except Exception as e:
            st.error(f'处理失败: {str(e)}')
            return False

def create_reload_handler(
        model: type[T],
        fetch_func: Callable[..., List[D]],
        unique_fields: List[str],
        build_filter: Callable[[Any, Session], Dict[str, Any]],
        mark_existing: bool = False,
        with_date_range: bool = False,
        **kwargs
) -> Union[ReloadHandler[T, D], DateRangeReloadHandler[T, D]]:
    config = ReloadConfig(
        model=model,
        fetch_func=fetch_func,
        unique_fields=unique_fields,
        build_filter=build_filter,
        mark_existing=mark_existing,
        **kwargs
    )
    if with_date_range:
        return DateRangeReloadHandler(config)
    return ReloadHandler(config)

