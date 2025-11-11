from dataclasses import dataclass, field
from typing import Callable, Optional, Dict
from menu import dashboard, stock, real_time_data, history_data, history_transaction
from utils import message

@dataclass
class PageConfig:
    title: str
    handler: Callable
    icon: Optional[str] = None


#options=["控制台", "股票列表", "实时行情", "历史行情", "历史分笔", "技术指标", "基本面"],
#        icons=["house", "bi bi-unity", "graph-up", "bank", "bar-chart", "gear", "clipboard-data"],
# https://icons.getbootstrap.com/
class Pages:
    """页面配置管理"""
    configs: Dict[str, PageConfig] = {
        "控制台": PageConfig(
            title="控制台",
            handler=dashboard.index,
            icon="house",
        ),
        "关注股票": PageConfig(
            title="关注股票",
            handler=stock.followIndex,
            icon="heart-fill",
        ),
        "股票图表": PageConfig(
            title="股票图表",
            handler=stock.chartIndex,
            icon="heart-fill",
        ),
        "所有股票": PageConfig(
            title="所有股票",
            handler=stock.index,
            icon="grid",
        ),
        "实时行情": PageConfig(
            title="实时行情",
            handler=real_time_data.index,
            icon="graph-up",
        ),
        "历史行情": PageConfig(
            title="历史行情",
            handler=history_data.index,
            icon="clipboard2-data",
        ),
        "历史分笔": PageConfig(
            title="历史分笔",
            handler=history_transaction.index,
            icon="terminal-split",
        ),
        # icon="bar-chart",
    }

    @classmethod
    def get_page_names(cls) -> list[str]:
        """获取所有页面名称"""
        return list(cls.configs.keys())

    @classmethod
    def render_page(cls, selected: str):
        """渲染选中的页面"""
        if config := cls.configs.get(selected):
            config.handler()
        else:
            message.show_message("页面不存在", type="error")


