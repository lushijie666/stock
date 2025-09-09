from datetime import datetime, date  # 添加这行导入

from pyecharts.charts import Pie, Kline, Bar, Grid, Line, Scatter
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
import pandas as pd
from enums.patterns import Patterns


class ChartBuilder:
    @staticmethod
    def create_pie_chart(data_pairs, total=None, colors=None):
        if colors is None:
            colors = ["#FFB6C1", "#87CEFA", "#98FB98", "#DDA0DD", "#F0E68C",
                     "#E6E6FA", "#FFA07A", "#B0E0E6", "#FFDAB9", "#D8BFD8"]
        pie = (
            Pie(init_opts=opts.InitOpts(theme="white", bg_color="white"))
            .add(
                series_name="",
                data_pair=data_pairs,
                radius=["40%", "70%"],
                center=["50%", "50%"],
                label_opts=opts.LabelOpts(
                    formatter="{b}\n{c} \n({d}%)",
                    position="outside",
                    font_size=12,
                    font_style="normal",
                    font_weight="bold",
                ),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="",
                    subtitle=f"总数：{total}" if total else "",
                    pos_left="left",
                    pos_top="5%",
                    subtitle_textstyle_opts=opts.TextStyleOpts(
                        font_size=14,
                        font_style="normal",
                        font_weight="bold",
                    )
                ),
                legend_opts=opts.LegendOpts(
                    type_="scroll",
                    pos_left="center",
                    pos_bottom="5%",
                    orient="horizontal",
                    textstyle_opts=opts.TextStyleOpts(color="#000")
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="item",
                    formatter="{b}<br/>数量: {c}<br/>占比: {d}%"
                ),
            )
            .set_colors(colors)
        )
        return pie

    @staticmethod
    def create_kline_chart(dates, k_line_data, ma_lines=None, patterns=None):
        kline = (
            Kline()
            .add_xaxis(dates)
            .add_yaxis(
                "K线",
                k_line_data,
                itemstyle_opts=opts.ItemStyleOpts(
                    color="#ef232a",
                    color0="#14b143",
                    border_color="#ef232a",
                    border_color0="#14b143",
                ),
            )
        )
        # 添加均线
        if ma_lines:
            lines = Line()
            lines.add_xaxis(dates)
            for name, values in ma_lines.items():
                lines.add_yaxis(
                    name,
                    values,
                    is_smooth=True,
                    label_opts=opts.LabelOpts(is_show=False)  # 不显示标签
                )
            kline = kline.overlap(lines)

        # 添加分型标记
        if patterns:
            scatter_top = Scatter()
            scatter_bottom = Scatter()

            # 准备顶底分型数据
            top_points = []
            bottom_points = []

            for p in patterns:
                date_str = p['date'].strftime('%Y-%m-%d') if isinstance(p['date'], (datetime, date)) else str(p['date'])
                if p['type'] == Patterns.TOP:
                    top_points.append([date_str, p['value']])
                elif p['type'] == Patterns.BOTTOM:
                    bottom_points.append([date_str, p['value']])

            # 添加顶分型散点
            if top_points:
                scatter_top.add_xaxis([p[0] for p in top_points])
                scatter_top.add_yaxis(
                    series_name="顶分型",
                    y_axis=[p[1] + 0.8 for p in top_points],  # 向上偏移一点
                    symbol='pin',  # 使用默认符号
                    symbol_size=0,
                    label_opts=opts.LabelOpts(
                        is_show=True,  # 显示标签
                        color="#FF4444",
                        font_size=12,
                        formatter="⬆"  # 显示"顶"字
                    ),
                    itemstyle_opts=opts.ItemStyleOpts(color="#FF4444"),
                )
                kline = kline.overlap(scatter_top)

            # 添加底分型散点
            if bottom_points:
                scatter_bottom.add_xaxis([p[0] for p in bottom_points])
                scatter_bottom.add_yaxis(
                    series_name="底分型",
                    y_axis=[p[1] - 0.8 for p in bottom_points],  # 向下偏移一点
                    symbol='pin',  # 使用默认符号
                    symbol_size=0,  # 将符号大小设为0（隐藏默认符号）
                    label_opts=opts.LabelOpts(
                        is_show=True,  # 显示标签
                        color="#44FF44",
                        font_size=12,
                        formatter="⬇"  # 显示"底"字
                    ),
                    itemstyle_opts=opts.ItemStyleOpts(color="#44FF44"),
                )
                kline = kline.overlap(scatter_bottom)

        kline.set_global_opts(
            title_opts=opts.TitleOpts(
                title="K线图",
                pos_left="left",
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="30%",
                pos_left="right",
                orient="vertical",  # 改为垂直排列
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
            ),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(
                    is_on_zero=False,
                    linestyle_opts=opts.LineStyleOpts(color="#666666")  # 轴线颜色改为深灰
                ),
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(color="#EEEEEE")  # 分割线改为浅灰
                ),
                axislabel_opts=opts.LabelOpts(color="#000000"),  # 轴标签文字改为黑色
                min_="dataMin",
                max_="dataMax"
            ),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(color="#EEEEEE")  # 分割线改为浅灰
                ),
                axislabel_opts=opts.LabelOpts(color="#000000")  # 轴标签文字改为黑色
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=True,
                    type_="slider",
                    pos_top="0%",  # 放在顶部
                    pos_left="10%",  # 左侧边距
                    pos_right="10%",  # 右侧边距
                    xaxis_index=[0, 1],
                    range_start=0,
                    range_end=100,
                ),
            ],
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000000"),  # 提示框文字改为黑色
            ),
        )
        return kline

    @staticmethod
    def create_volume_bar(dates, volumes, colors):
        bar = (
            Bar()
            .add_xaxis(dates)
            .add_yaxis(
                "成交量",
                volumes,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(
                    color=JsCode(f"""
                        function(params) {{
                            var colorList = {str(colors)};
                            return colorList[params.dataIndex];
                        }}
                    """)
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=""),
                legend_opts=opts.LegendOpts(
                    type_="scroll",
                    pos_top="80%",
                    pos_left="right",
                    orient="horizontal",
                    textstyle_opts=opts.TextStyleOpts(color="#000000")
                ),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    is_scale=True,
                    grid_index=1,
                    boundary_gap=True,
                    axisline_opts=opts.AxisLineOpts(
                        is_on_zero=False,
                        linestyle_opts=opts.LineStyleOpts(color="#666666")
                    ),
                    axistick_opts=opts.AxisTickOpts(is_show=True),
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True,
                        linestyle_opts=opts.LineStyleOpts(color="#EEEEEE")
                    ),
                    axislabel_opts=opts.LabelOpts(
                        is_show=True,
                        color="#000000"
                    ),
                    min_="dataMin",
                    max_="dataMax"
                ),
                yaxis_opts=opts.AxisOpts(
                    grid_index=1,
                    is_scale=True,
                    split_number=2,
                    position="left",  # 改为左侧
                    axisline_opts=opts.AxisLineOpts(
                        linestyle_opts=opts.LineStyleOpts(color="#666666")
                    ),
                    axistick_opts=opts.AxisTickOpts(is_show=True),
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True,
                        linestyle_opts=opts.LineStyleOpts(color="#EEEEEE")
                    ),
                    axislabel_opts=opts.LabelOpts(
                        is_show=True,
                        margin=4,
                        color="#000000"
                    ),
                ),
            )
        )
        return bar

    @staticmethod
    def create_combined_chart(kline, volume_bar):
        grid = (
            Grid(init_opts=opts.InitOpts(
                width="100%",
                height="800px",
                animation_opts=opts.AnimationOpts(animation=False),
                theme="white",
                bg_color="white"
            ))
            .add(
                kline,
                grid_opts=opts.GridOpts(
                    pos_left="10%",
                    pos_right="10%",
                    pos_top="5%",
                    height="60%"
                ),
            )
            .add(
                volume_bar,
                grid_opts=opts.GridOpts(
                    pos_left="10%",
                    pos_right="10%",
                    pos_top="71%",
                    height="20%"
                ),
            )
        )
        return grid

    @staticmethod
    def create_macd_chart(dates: list, diff: list, dea: list, hist: list,
                          fast_period=12, slow_period=26, signal_period=9,
                          title: str = "MACD"):
        # 动态生成标题
        full_title = f"{title} ({fast_period},{slow_period},{signal_period})"

        # 计算Y轴范围
        y_min = min(min(diff or [0]), min(dea or [0]), min(hist or [0])) * 1.1
        y_max = max(max(diff or [0]), max(dea or [0]), max(hist or [0])) * 1.1

        # 创建柱状图（简化颜色设置）
        bar = (
            Bar()
            .add_xaxis(dates)
            .add_yaxis(
                series_name="MACD",
                y_axis=hist,
                itemstyle_opts=opts.ItemStyleOpts(
                    color=JsCode("""
                        function(params) {
                            if (params && params.value !== undefined) {
                                return params.value > 0 ? '#FF6B6B' : '#4ECDC4';
                            }
                            return '#4ECDC4';
                        }
                    """)
                ),
                bar_width='60%',
                yaxis_index=0,
                z_level=2,
                label_opts=opts.LabelOpts(is_show=False)
            )
        )

        # 创建线图（简化配置）
        line = (
            Line()
            .add_xaxis(dates)
            .add_yaxis(
                series_name="DIFF",
                y_axis=diff,
                is_smooth=True,
                color="#FF9F1C",
                linestyle_opts=opts.LineStyleOpts(width=2),
                symbol="none",
                yaxis_index=1,
                z_level=1,
                label_opts=opts.LabelOpts(is_show=False)
            )
            .add_yaxis(
                series_name="DEA",
                y_axis=dea,
                is_smooth=True,
                color="#2EC4B6",
                linestyle_opts=opts.LineStyleOpts(width=2),
                symbol="none",
                yaxis_index=1,
                z_level=1,
                label_opts=opts.LabelOpts(is_show=False)
            )
        )

        # 合并图表
        overlap = bar.overlap(line)

        # 设置全局选项（最简化可靠配置）
        overlap.set_global_opts(
            title_opts=opts.TitleOpts(title=full_title),
            legend_opts=opts.LegendOpts(
                pos_top="45%",
                pos_left="right",
                orient="vertical",  # 改为垂直排列
                inactive_color="#ccc"

            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                formatter=JsCode("""
                    function(params) {
                        if (!params || params.length === 0) return '';
                        let result = '';
                        if (params[0].axisValue) {
                            result = params[0].axisValue + '<br/>';
                        }
                        params.forEach(item => {
                            if (item) {
                                const value = (item.value !== undefined && item.value !== null) ? item.value : '-';
                                const color = item.color || '#666';
                                const seriesName = item.seriesName || '';
                                result += `
                                <span style="display:inline-block;
                                            margin-right:5px;
                                            width:10px;
                                            height:10px;
                                            background-color:${color}"></span>
                                ${seriesName}: <b>${typeof value === 'number' ? value.toFixed(4) : value}</b><br/>`;
                            }
                        });
                        return result;
                    }
                """)
            ),
            datazoom_opts=opts.DataZoomOpts(is_show=True,
                    type_="slider",
                    pos_bottom="0%",
                    pos_left="10%",  # 左侧边距
                    pos_right="10%",  # 右侧边距
                    xaxis_index=[0, 1],
                    range_start=0,
                    range_end=100,
            ),
            yaxis_opts=opts.AxisOpts(
                name="MACD",
                position="left",
                min_=y_min,
                max_=y_max,
                axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color="#666")),
                splitline_opts=opts.SplitLineOpts(is_show=True)
            ),
            xaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(color="#000000"),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axispointer_opts=opts.AxisPointerOpts(is_show=True, type_="line")
            )
        )

        # 添加第二个Y轴
        overlap.extend_axis(
            yaxis=opts.AxisOpts(
                name="DIFF/DEA",
                position="right",
                min_=y_min,
                max_=y_max,
                axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color="#666"))
            )
        )

        # 创建Grid布局（简化）
        grid = Grid(init_opts=opts.InitOpts(width="100%", height="600px"))
        grid.add(
            overlap,
            grid_opts=opts.GridOpts(
                pos_left="10%",
                pos_right="10%",
                pos_top="20%",
                pos_bottom="16%"
            )
        )
        return grid


def calculate_macd(df: pd.DataFrame, fast_period=12, slow_period=26, signal_period=9):
    df = df.copy()
    df['EMA12'] = df['closing'].ewm(span=fast_period, adjust=False).mean()
    df['EMA26'] = df['closing'].ewm(span=slow_period, adjust=False).mean()
    df['DIFF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIFF'].ewm(span=signal_period, adjust=False).mean()
    df['MACD_hist'] = df['DIFF'] - df['DEA']
    return df[['DIFF', 'DEA', 'MACD_hist']]