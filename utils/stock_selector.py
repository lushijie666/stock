from typing import Callable, Optional, TypeVar, Generic, List, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
import streamlit as st
import logging

from enums.category import Category
from models.stock import Stock
from utils.db import get_db_session
from utils.message import show_message
from utils.session import get_session_key, SessionKeys
from utils.table import format_pinyin_short

T = TypeVar('T')

@dataclass
class StockSelectorConfig:
    """股票选择器配置"""
    category: Category
    prefix: str
    on_select: Callable[[Stock], None]
    on_error: Optional[Callable[[Exception], None]] = None
    on_not_found: Optional[Callable[[], None]] = None

class StockSelectorManager:
    def __init__(self, config: StockSelectorConfig):
        self.config = config

    def get_stocks(self, session: Session) -> List[Stock]:
        """获取股票列表"""
        return session.query(Stock).filter(
            Stock.removed == False,
            Stock.category == self.config.category
        ).order_by(Stock.code.asc()).all()

    def create_options(self, stocks: List[Stock]) -> List[Tuple[str, str, str]]:
        """创建选择器选项"""
        options = [("", "请选择股票", "")]
        for stock in stocks:
            pinyin_short = format_pinyin_short(stock.pinyin) if stock.pinyin else ""
            options.append((stock.code, stock.name, pinyin_short))
        return options

    def show_selector(self) -> None:
        """显示选择器"""
        try:
            with get_db_session() as session:
                stocks = self.get_stocks(session)
                options = self.create_options(stocks)
                select_key = get_session_key(
                    SessionKeys.STOCK_SELECTOR,
                    prefix=self.config.prefix,
                    category=self.config.category.value
                )
                current_stock_key = get_session_key(
                    SessionKeys.CURRENT_STOCK,
                    prefix=self.config.prefix,
                    category=self.config.category.value,
                )

                # 初始化或同步 session state
                # 如果 select_key 不存在，或者与 current_stock_key 不一致，需要更新
                need_update = False
                if select_key not in st.session_state:
                    need_update = True
                elif current_stock_key in st.session_state:
                    # 检查当前选择是否与保存的股票代码一致
                    current_selected = st.session_state.get(select_key, ("", ""))
                    current_code = st.session_state[current_stock_key]
                    if current_selected[0] != current_code:
                        need_update = True
                
                if need_update:
                    # 如果之前有选中的股票，尝试恢复选择
                    if current_stock_key in st.session_state:
                        current_code = st.session_state[current_stock_key]
                        # 在 options 中查找匹配的选项
                        matched_option = None
                        for option in options:
                            if option[0] == current_code:
                                matched_option = option
                                break
                        if matched_option:
                            st.session_state[select_key] = matched_option
                        else:
                            st.session_state[select_key] = options[0]  # 如果找不到匹配项，使用默认值
                    else:
                        st.session_state[select_key] = options[0]  # 默认选择第一个选项（空选项）

                # 格式化函数
                def format_option(x):
                    if not x or len(x) < 2:
                        return "请选择股票"
                    if x[0] == "":
                        return x[1]
                    pinyin = x[2] if len(x) > 2 and x[2] else ""
                    if pinyin:
                        return f"{x[0]} ({x[1]}-{pinyin})"
                    return f"{x[0]} ({x[1]})"

                selected = st.selectbox(
                    "",
                    options=options,
                    format_func=format_option,
                    key=select_key,
                    on_change=self.handle_selection,
                    label_visibility="collapsed"
                )

                # 初始处理选择
                if selected and selected[0]:
                    self.handle_selection()

        except Exception as e:
            logging.error(f"Error showing selector: {str(e)}")
            if self.config.on_error:
                self.config.on_error(e)
            else:
                st.error(f"加载数据失败：{str(e)}")

    def handle_selection(self) -> None:
        """处理选择事件"""
        try:
            select_key = get_session_key(
                SessionKeys.STOCK_SELECTOR,
                prefix=self.config.prefix,
                category=self.config.category.value
            )
            current_stock_key = get_session_key(
                SessionKeys.CURRENT_STOCK,
                prefix=self.config.prefix,
                category = self.config.category.value,
            )
            # 安全地获取选择值
            selected = st.session_state.get(select_key, ("", ""))
            if selected[0]:
                st.session_state[current_stock_key] = selected[0]
            else:
                # 安全地移除 key
                st.session_state.pop(current_stock_key, None)

        except Exception as e:
            logging.error(f"Error handling selection: {str(e)}")
            if self.config.on_error:
                self.config.on_error(e)

    def handle_current_stock(self) -> None:
        """处理当前选中的股票"""
        try:
            current_stock_key = get_session_key(
                SessionKeys.CURRENT_STOCK,
                prefix=self.config.prefix,
                category = self.config.category.value
            )
            if current_stock_key in st.session_state:
                with get_db_session() as session:
                    stock = session.query(Stock).filter(
                        Stock.code == st.session_state[current_stock_key]
                    ).first()
                    if stock:
                        self.config.on_select(stock)
                    elif self.config.on_not_found:
                        self.config.on_not_found()
        except Exception as e:
            logging.error(f"Error handling current stock: {str(e)}")
            if self.config.on_error:
                self.config.on_error(e)

def create_stock_selector(
        category: Category,
        prefix: str,
        on_select: Callable[[Stock], None],
        on_error: Optional[Callable[[Exception], None]] = None,
        on_not_found: Optional[Callable[[], None]] = None
) -> StockSelectorManager:
    config = StockSelectorConfig(
        category=category,
        prefix=prefix,
        on_select=on_select,
        on_error=on_error or (lambda e: st.error(f"加载股票失败: {str(e)}")),
        on_not_found=on_not_found or (lambda: st.warning("未找到选中的股票"))
    )
    return StockSelectorManager(config)

def handle_error(e: Exception):
    """处理错误"""
    show_message(f"处理股票选择时出错: {str(e)}", type="error")

def handle_not_found():
    """处理未找到股票的情况"""
    show_message("请选择一个股票", type="warning")