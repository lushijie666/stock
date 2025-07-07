from typing import Optional
import streamlit as st

class SessionKeys:
    STOCK_SELECTOR = "{prefix}_{category}_stock_selector"  # 股票选择器
    CURRENT_STOCK = "{prefix}_{category}_current_stock"  # 当前选中的股票
    PAGE = "{prefix}_{category}_page"  # 页面
    CURRENT_TAB = "{prefix}_current_tab"  # 当前选中的tab

def get_session_key(key_template: str, **kwargs) -> str:
    """获取会话状态键名"""
    return key_template.format(**kwargs)

def get_date_range(
    prefix: str = "",
    start_suffix: str = "start_date",
    end_suffix: str = "end_date"
) -> Optional[tuple[str, str]]:
    try:
        # 构建日期键
        start_key = f"{prefix}_date_{start_suffix}" #  field_key = f"{key_prefix}_{field.type}_{field.field}"
        end_key = f"{prefix}_date_{end_suffix}"

        # 获取日期
        start_date = st.session_state.get(start_key)
        end_date = st.session_state.get(end_key)
        if not start_date or not end_date:
            st.warning('请选择日期范围')
            return None
        return (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
    except Exception as e:
        st.error(f'获取日期范围失败: {str(e)}')
        return None