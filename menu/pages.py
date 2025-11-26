from dataclasses import dataclass
from typing import Callable, Optional, Dict
from menu import dashboard, stock, stock_history, stock_trade
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
        "买卖记录": PageConfig(
            title="买卖记录",
            handler=stock_trade.index,
            icon="clipboard2-data",
        ),
        "股票信息": PageConfig(
            title="股票信息",
            handler=stock.index,
            icon="grid",
        ),
        "股票数据": PageConfig(
            title="股票数据",
            handler=stock_history.index,
            icon="clipboard2-data",
        ),
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


