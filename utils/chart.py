from datetime import datetime, date  # 添加这行导入

from pyecharts.charts import Pie, Kline, Bar, Grid, Line, Scatter
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
import pandas as pd
from enums.patterns import Patterns
from enums.signal import SignalType, SignalStrength


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
                    pos_top="45%",
                    pos_left="right",
                    orient="vertical",  # 改为垂直排列
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
    def create_bar_chart(x_data, y_data, series_name, colors=None):
        """
        创建柱状图

        Args:
            x_data: x轴数据列表
            y_data: y轴数据列表
            series_name: 系列名称
            colors: 颜色列表，用于设置柱子颜色

        Returns:
            Bar: pyecharts的Bar实例
        """
        if colors is None:
            colors = ["#3b82f6", "#87CEFA", "#98FB98", "#DDA0DD", "#F0E68C",
                      "#E6E6FA", "#FFA07A", "#B0E0E6", "#FFDAB9", "#D8BFD8"]

        bar = (
            Bar(init_opts=opts.InitOpts(theme="white", bg_color="white"))
            .add_xaxis(x_data)
            .add_yaxis(
                series_name=series_name,
                y_axis=y_data,
                itemstyle_opts=opts.ItemStyleOpts(
                    color=JsCode(f"""
                        function(params) {{
                            var colorList = {str(colors)};
                            return colorList[params.dataIndex % colorList.length];
                        }}
                    """),
                    opacity=0.8
                ),
                label_opts=opts.LabelOpts(
                    is_show=True,
                    position="top",
                    font_size=10,
                    color="#333"
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="",
                    subtitle="",
                    pos_left="left",
                    pos_bottom="5%",
                    title_textstyle_opts=opts.TextStyleOpts(
                        font_size=16,
                        font_weight="bold"
                    ),
                    subtitle_textstyle_opts=opts.TextStyleOpts(
                        font_size=12
                    )
                ),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    axislabel_opts=opts.LabelOpts(
                        font_size=10,
                        rotate=45
                    )
                ),
                yaxis_opts=opts.AxisOpts(
                    type_="value",
                    name="数量",
                    name_location="middle",
                    name_gap=40,
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True,
                        linestyle_opts=opts.LineStyleOpts(
                            color="#f0f0f0",
                            type_="dashed"
                        )
                    )
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="shadow"
                )
            )
        )
        return bar

    @staticmethod
    def create_kline_chart(dates, k_line_data, ma_lines=None, patterns=None, signals=None, strokes=None, segments=None, centers=None):
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
                    label_opts=opts.LabelOpts(is_show=False),  # 不显示标签
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
                    y_axis=[p[1] + 0.6 for p in top_points],  # 向上偏移一点
                    symbol='pin',  # 使用默认符号
                    symbol_size=10,
                    label_opts=opts.LabelOpts(
                        is_show=True,  # 显示标签
                        color="#FF4444",
                        font_size=14,
                        font_weight='bold',
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
                    y_axis=[p[1] - 0.6 for p in bottom_points],  # 向下偏移一点
                    symbol='pin',  # 使用默认符号
                    symbol_size=10,
                    label_opts=opts.LabelOpts(
                        is_show=True,  # 显示标签
                        color="#44FF44",
                        font_size=14,
                        font_weight='bold',
                        formatter="⬇"  # 显示"底"字
                    ),
                    itemstyle_opts=opts.ItemStyleOpts(color="#44FF44"),
                )
                kline = kline.overlap(scatter_bottom)
        # 添加信号
        if signals:
            buy_signals_strong = []
            buy_signals_weak = []
            sell_signals_strong = []
            sell_signals_weak = []

            for signal in signals:

                # 确保日期格式与 K 线图 x 轴一致
                if hasattr(signal['date'], 'strftime'):
                    date_str = signal['date'].strftime('%Y-%m-%d')
                else:
                    date_str = str(signal['date'])

                # 确保价格是数值类型
                price = float(signal['price'])
                point = [date_str, price, signal]

                if signal['type'] == SignalType.BUY:
                    if signal['strength'] == SignalStrength.STRONG:
                        buy_signals_strong.append(point)
                    else:
                        buy_signals_weak.append(point)
                elif signal['type'] == SignalType.SELL:
                    if signal['strength'] == SignalStrength.STRONG:
                        sell_signals_strong.append(point)
                    else:
                        sell_signals_weak.append(point)

            # 添加强买入信号
            if buy_signals_strong:
                scatter_buy_strong = (
                    Scatter()
                    .add_xaxis([p[0] for p in buy_signals_strong])
                    .add_yaxis(
                        series_name="MB-买入(强)",
                        y_axis=[p[1] for p in buy_signals_strong],
                        symbol_size=10,
                        symbol='triangle',  # 使用三角形符号更明显
                        itemstyle_opts=opts.ItemStyleOpts(color='#8B0000'),
                        label_opts=opts.LabelOpts(
                            is_show=True,
                            position="top",
                            formatter="MB\n(强)",
                            font_size=10,
                            color='#8B0000',
                        )
                    )
                )
                kline = kline.overlap(scatter_buy_strong)

            # 添加弱买入信号
            if buy_signals_weak:
                scatter_buy_weak = (
                    Scatter()
                    .add_xaxis([p[0] for p in buy_signals_weak])
                    .add_yaxis(
                        series_name="MB-买入(弱)",
                        y_axis=[p[1] for p in buy_signals_weak],
                        symbol_size=10,
                        symbol='triangle',
                        itemstyle_opts=opts.ItemStyleOpts(color='#FF7F7F'),
                        label_opts=opts.LabelOpts(
                            is_show=True,
                            position="top",
                            formatter="MB\n(弱)",
                            font_size=10,
                            color='#FF7F7F',
                        )
                    )
                )
                kline = kline.overlap(scatter_buy_weak)

            # 添加强卖出信号
            if sell_signals_strong:
                scatter_sell_strong = (
                    Scatter()
                    .add_xaxis([p[0] for p in sell_signals_strong])
                    .add_yaxis(
                        series_name="MS-卖出(强)",
                        y_axis=[p[1] for p in sell_signals_strong],
                        symbol_size=10,
                        symbol='diamond',  # 使用菱形符号
                        itemstyle_opts=opts.ItemStyleOpts(color='#006400'),
                        label_opts=opts.LabelOpts(
                            is_show=True,
                            position="bottom",
                            formatter="MS\n(强)",
                            font_size=10,
                            color='#006400'
                        )
                    )
                )
                kline = kline.overlap(scatter_sell_strong)

            # 添加弱卖出信号
            if sell_signals_weak:
                scatter_sell_weak = (
                    Scatter()
                    .add_xaxis([p[0] for p in sell_signals_weak])
                    .add_yaxis(
                        series_name="MS-卖出(弱)",
                        y_axis=[p[1] for p in sell_signals_weak],
                        symbol_size=10,
                        symbol='diamond',
                        itemstyle_opts=opts.ItemStyleOpts(color='#90EE90'),
                        label_opts=opts.LabelOpts(
                            is_show=True,
                            position="bottom",
                            formatter="MS\n(弱)",
                            font_size=10,
                            color='#90EE90'
                        )
                    )
                )
                kline = kline.overlap(scatter_sell_weak)
        # 添加笔的连线（按类型分组合并）
        if strokes:
            # 分别收集向上笔和向下笔的数据
            up_strokes_x_data = []
            up_strokes_y_data = []
            down_strokes_x_data = []
            down_strokes_y_data = []

            # 收集所有笔的数据点
            for i, stroke in enumerate(strokes):
                start_index = stroke['start_index']
                end_index = stroke['end_index']

                # 确保索引在有效范围内
                if start_index < len(dates) and end_index < len(dates):
                    start_date = dates[start_index]
                    end_date = dates[end_index]

                    if stroke['type'] == 'up':
                        # 添加向上笔的数据点
                        up_strokes_x_data.extend([start_date, end_date])
                        up_strokes_y_data.extend([stroke['start_value'], stroke['end_value']])
                        # 添加None值以分隔不同的笔
                        if i < len(strokes) - 1:  # 不是最后一条线
                            up_strokes_x_data.append(None)
                            up_strokes_y_data.append(None)
                    else:
                        # 添加向下笔的数据点
                        down_strokes_x_data.extend([start_date, end_date])
                        down_strokes_y_data.extend([stroke['start_value'], stroke['end_value']])
                        # 添加None值以分隔不同的笔
                        if i < len(strokes) - 1:  # 不是最后一条线
                            down_strokes_x_data.append(None)
                            down_strokes_y_data.append(None)

            # 创建向上笔系列
            if up_strokes_x_data and up_strokes_y_data:
                up_line = Line()
                up_line.add_xaxis(up_strokes_x_data)
                up_line.add_yaxis(
                    series_name="向上笔(S)",
                    y_axis=up_strokes_y_data,
                    is_connect_nones=False,  # 不连接空值
                    is_smooth=False,
                    symbol="none",
                    linestyle_opts=opts.LineStyleOpts(
                        width=3,
                        color="#EE3B3B",
                        type_="solid"
                    ),
                    itemstyle_opts=opts.ItemStyleOpts(color="#EE3B3B"),
                    label_opts=opts.LabelOpts(is_show=False)
                )
                kline = kline.overlap(up_line)

            # 创建向下笔系列
            if down_strokes_x_data and down_strokes_y_data:
                down_line = Line()
                down_line.add_xaxis(down_strokes_x_data)
                down_line.add_yaxis(
                    series_name="向下笔(X)",
                    y_axis=down_strokes_y_data,
                    is_connect_nones=False,  # 不连接空值
                    is_smooth=False,
                    symbol="none",
                    linestyle_opts=opts.LineStyleOpts(
                        width=3,
                        color="#32CD32",
                        type_="solid"
                    ),
                    itemstyle_opts=opts.ItemStyleOpts(color="#32CD32"),
                    label_opts=opts.LabelOpts(is_show=False)
                )
                kline = kline.overlap(down_line)

        # 添加线段的连线（按类型分组合并）
        if segments:
            # 分别收集向上线段和向号线段的数据
            up_segments_x_data = []
            up_segments_y_data = []
            down_segments_x_data = []
            down_segments_y_data = []

            # 收集所有线段的数据点
            for i, segment in enumerate(segments):
                start_index = segment['start_index']
                end_index = segment['end_index']

                # 确保索引在有效范围内
                if start_index < len(dates) and end_index < len(dates):
                    start_date = dates[start_index]
                    end_date = dates[end_index]

                    if segment['type'] == 'up':
                        # 添加向上线段的数据点
                        up_segments_x_data.extend([start_date, end_date])
                        up_segments_y_data.extend([segment['start_value'], segment['end_value']])
                        # 添加None值以分隔不同的线段
                        if i < len(segments) - 1:  # 不是最后一条线段
                            up_segments_x_data.append(None)
                            up_segments_y_data.append(None)
                    else:
                        # 添加向号线段的数据点
                        down_segments_x_data.extend([start_date, end_date])
                        down_segments_y_data.extend([segment['start_value'], segment['end_value']])
                        # 添加None值以分隔不同的线段
                        if i < len(segments) - 1:  # 不是最后一条线段
                            down_segments_x_data.append(None)
                            down_segments_y_data.append(None)

            # 创建向上线段系列
            if up_segments_x_data and up_segments_y_data:
                up_seg_line = Line()
                up_seg_line.add_xaxis(up_segments_x_data)
                up_seg_line.add_yaxis(
                    series_name="向上线段",
                    y_axis=up_segments_y_data,
                    is_connect_nones=False,  # 不连接空值
                    is_smooth=False,
                    symbol="none",
                    linestyle_opts=opts.LineStyleOpts(
                        width=4,
                        color="#A52A2A",
                        type_="dotted"
                    ),
                    itemstyle_opts=opts.ItemStyleOpts(color="#A52A2A"),
                    label_opts=opts.LabelOpts(is_show=False)
                )
                kline = kline.overlap(up_seg_line)

            # 创建向号线段系列
            if down_segments_x_data and down_segments_y_data:
                down_seg_line = Line()
                down_seg_line.add_xaxis(down_segments_x_data)
                down_seg_line.add_yaxis(
                    series_name="向下线段",
                    y_axis=down_segments_y_data,
                    is_connect_nones=False,  # 不连接空值
                    is_smooth=False,
                    symbol="none",
                    linestyle_opts=opts.LineStyleOpts(
                        width=4,
                        color="#228B22",
                        type_="dotted"
                    ),
                    itemstyle_opts=opts.ItemStyleOpts(color="#228B22"),
                    label_opts=opts.LabelOpts(is_show=False)
                )
                kline = kline.overlap(down_seg_line)
        # 绘制中枢框
        if centers:
            # 创建一个虚拟系列来显示中枢图例
            dummy_line = Line()
            dummy_line.add_xaxis([dates[0]])

            # 添加中枢区域图例项
            dummy_line.add_yaxis(
                series_name="中枢区域",
                y_axis=[None],
                linestyle_opts=opts.LineStyleOpts(
                    color="rgba(255, 175, 0, 0.2)",
                    width=10
                ),
                label_opts=opts.LabelOpts(is_show=False)
            )

            # 添加中枢高点图例项
            dummy_line.add_yaxis(
                series_name="中枢高点",
                y_axis=[None],
                linestyle_opts=opts.LineStyleOpts(
                    color="orange",
                    type_="dashed"
                ),
                label_opts=opts.LabelOpts(is_show=False)
            )

            # 添加中枢低点图例项
            dummy_line.add_yaxis(
                series_name="中枢低点",
                y_axis=[None],
                linestyle_opts=opts.LineStyleOpts(
                    color="orange",
                    type_="dashed"
                ),
                label_opts=opts.LabelOpts(is_show=False)
            )

            # 将虚拟系列添加到图表中
           # kline = kline.overlap(dummy_line)

            # 设置实际的标记区域和标记线
            markarea_data = []
            markline_data = []

            for i, center in enumerate(centers):
                # 添加中枢区域标记
                markarea_data.append(
                    opts.MarkAreaItem(
                        name="",  # 不设置名称，避免重复
                        x=(center['start_date'].strftime('%Y-%m-%d') if hasattr(center['start_date'],
                                                                                'strftime') else str(
                            center['start_date']),
                           center['end_date'].strftime('%Y-%m-%d') if hasattr(center['end_date'],
                                                                              'strftime') else str(
                               center['end_date'])),
                        y=(float(center['ZD']), float(center['ZG'])),
                        itemstyle_opts=opts.ItemStyleOpts(
                            color="rgba(255, 175, 0, 0.05)",  # 半透明橙色
                            border_color="rgba(255, 175, 0, 1)",
                            border_width=1
                        )
                    )
                )

                # 添加中枢高点和低点标记线
                markline_data.extend([
                    opts.MarkLineItem(
                        name="",  # 不设置名称
                        y=float(center['ZG']),
                        linestyle_opts=opts.LineStyleOpts(
                            color="orange",
                            type_="dashed"
                        )
                    ),
                    opts.MarkLineItem(
                        name="",  # 不设置名称
                        y=float(center['ZD']),
                        linestyle_opts=opts.LineStyleOpts(
                            color="orange",
                            type_="dashed"
                        )
                    )
                ])

            # 应用标记区域和标记线
            if markarea_data:
                kline.set_series_opts(
                    markarea_opts=opts.MarkAreaOpts(data=markarea_data)
                )

            if markline_data:
                kline.set_series_opts(
                    markline_opts=opts.MarkLineOpts(data=markline_data)
                )
        kline.set_global_opts(
            title_opts=opts.TitleOpts(
                title="",
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
                    """),
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=""),
                legend_opts=opts.LegendOpts(
                    type_="scroll",
                    pos_top="50%",
                    pos_left="right",
                    orient="vertical",
                    textstyle_opts=opts.TextStyleOpts(color="#000000")
                ),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    is_scale=True,
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
    def create_trade_points_chart(dates, open_prices=None, high_prices=None, low_prices=None, close_prices=None, signals=None):
        """
        创建带买卖点标记的价格折线图
        Args:
            dates: 日期列表
            open_prices: 开盘价列表
            high_prices: 最高价列表
            low_prices: 最低价列表
            close_prices: 收盘价列表
            signals: 信号列表，包含买卖点信息

        Returns:
            Line: pyecharts的Line实例
        """
        line_chart = Line()
        line_chart.add_xaxis(dates)

        # 添加开盘价横线
        if open_prices is not None:
            line_chart.add_yaxis(
                "开盘价",
                open_prices,
                symbol="none",
                color="#ffa940",
                linestyle_opts=opts.LineStyleOpts(width=2),  # 稍微加粗线条
            )

        # 添加最高价横线
        if high_prices is not None:
            line_chart.add_yaxis(
                "最高价",
                high_prices,
                symbol="none",
                color="#cc053f",
                linestyle_opts=opts.LineStyleOpts(width=2, type_="dashed")
            )

        # 添加最低价横线
        if low_prices is not None:
            line_chart.add_yaxis(
                "最低价",
                low_prices,
                symbol="none",
                color="#6feca5",
                linestyle_opts=opts.LineStyleOpts(width=2, type_="dashed")
            )

        # 添加收盘价折线
        if close_prices is not None:
            line_chart.add_yaxis(
                "收盘价",
                close_prices,
                symbol="none",
                color="#1f77b4",
                linestyle_opts=opts.LineStyleOpts(width=2)
            )

        # 添加买卖点标记
        if signals:
            # 按信号类型和强度分别收集数据
            strong_buy_dates = []
            strong_buy_prices = []
            weak_buy_dates = []
            weak_buy_prices = []
            strong_sell_dates = []
            strong_sell_prices = []
            weak_sell_dates = []
            weak_sell_prices = []

            for signal in signals:
                date_str = signal['date'].strftime('%Y-%m-%d') if hasattr(signal['date'], 'strftime') else str(
                    signal['date'])
                price = float(signal['price'])

                if signal['type'] == SignalType.BUY:
                    if signal['strength'] == SignalStrength.STRONG:
                        strong_buy_dates.append(date_str)
                        strong_buy_prices.append(price)
                    else:
                        weak_buy_dates.append(date_str)
                        weak_buy_prices.append(price)
                else:
                    if signal['strength'] == SignalStrength.STRONG:
                        strong_sell_dates.append(date_str)
                        strong_sell_prices.append(price)
                    else:
                        weak_sell_dates.append(date_str)
                        weak_sell_prices.append(price)

            # 强买入信号散点
            if strong_buy_dates:
                strong_buy_scatter = Scatter()
                strong_buy_scatter.add_xaxis(strong_buy_dates)
                strong_buy_scatter.add_yaxis(
                    "MB-买入(强)",
                    strong_buy_prices,
                    symbol="triangle",
                    symbol_size=12,  # 稍微增大标记
                    color="#8B0000",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="top",
                        distance=5,  # 增加标签与标记的距离
                        font_size=9,
                        color='#8B0000',
                        formatter="MB\n(强)"
                    )
                )
                line_chart = line_chart.overlap(strong_buy_scatter)

            # 弱买入信号散点
            if weak_buy_dates:
                weak_buy_scatter = Scatter()
                weak_buy_scatter.add_xaxis(weak_buy_dates)
                weak_buy_scatter.add_yaxis(
                    "MB-买入(弱)",
                    weak_buy_prices,
                    symbol="triangle",
                    symbol_size=12,
                    color="#FF7F7F",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="top",
                        distance=5,
                        font_size=9,
                        color='#FF7F7F',
                        formatter="MB\n(弱)"
                    )
                )
                line_chart = line_chart.overlap(weak_buy_scatter)

            # 强卖出信号散点
            if strong_sell_dates:
                strong_sell_scatter = Scatter()
                strong_sell_scatter.add_xaxis(strong_sell_dates)
                strong_sell_scatter.add_yaxis(
                    "MS-卖出(强)",
                    strong_sell_prices,
                    symbol="diamond",
                    symbol_size=12,
                    color="#006400",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="bottom",
                        distance=5,
                        font_size=9,
                        color='#006400',
                        formatter="MS\n(强)"
                    )
                )
                line_chart = line_chart.overlap(strong_sell_scatter)

            # 弱卖出信号散点
            if weak_sell_dates:
                weak_sell_scatter = Scatter()
                weak_sell_scatter.add_xaxis(weak_sell_dates)
                weak_sell_scatter.add_yaxis(
                    "MS-卖出(弱)",
                    weak_sell_prices,
                    symbol="diamond",
                    symbol_size=12,
                    color="#90EE90",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="bottom",
                        distance=5,
                        font_size=9,
                        color='#90EE90',
                        formatter="MS\n(弱)"
                    )
                )
                line_chart = line_chart.overlap(weak_sell_scatter)
        # 设置图表选项
        line_chart.set_global_opts(
            title_opts=opts.TitleOpts(
                title="",
                pos_left="left",
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="30%",
                pos_left="right",
                orient="vertical",  # 改为垂直排列
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000000"),  # 提示框文字改为黑色
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
            ]
        )
        return line_chart

    @staticmethod
    def create_backtest_performance_chart(dates, strategy_values, benchmark_values):
        """
        创建回测表现对比图
        """
        line = Line()
        line.add_xaxis(dates)

        # 添加策略收益线
        line.add_yaxis(
            "策略收益",
            strategy_values,
            is_smooth=True,
            color="#2e7ed6",
            linestyle_opts=opts.LineStyleOpts(width=3),
            symbol="none"
        )

        # 添加基准收益线
        line.add_yaxis(
            "基准收益",
            benchmark_values,
            is_smooth=True,
            color="#2caf18",
            linestyle_opts=opts.LineStyleOpts(width=3, type_="dashed"),
            symbol="none"
        )
        line.set_global_opts(
            title_opts=opts.TitleOpts(
                title="",
                pos_left="left",
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="50%",
                pos_left="right",
                orient="vertical",  # 改为垂直排列
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000000"),  # 提示框文字改为黑色
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
            ]
        )
        return line

    @staticmethod
    def create_backtest_trade_points_chart(dates, open_prices=None, high_prices=None, low_prices=None, close_prices=None, signals=None, trades=None):
        """
        创建带交易标记的回测图表
        """
        line_chart = Line()
        line_chart.add_xaxis(dates)

        # 添加开盘价横线
        if open_prices is not None:
            line_chart.add_yaxis(
                "开盘价",
                open_prices,
                symbol="none",
                color="#ffa940",
                linestyle_opts=opts.LineStyleOpts(width=2),  # 稍微加粗线条
            )

        # 添加最高价横线
        if high_prices is not None:
            line_chart.add_yaxis(
                "最高价",
                high_prices,
                symbol="none",
                color="#cc053f",
                linestyle_opts=opts.LineStyleOpts(width=2, type_="dashed")
            )

        # 添加最低价横线
        if low_prices is not None:
            line_chart.add_yaxis(
                "最低价",
                low_prices,
                symbol="none",
                color="#6feca5",
                linestyle_opts=opts.LineStyleOpts(width=2, type_="dashed")
            )

        # 添加收盘价折线
        if close_prices is not None:
            line_chart.add_yaxis(
                "收盘价",
                close_prices,
                symbol="none",
                color="#1f77b4",
                linestyle_opts=opts.LineStyleOpts(width=2)
            )

        # 添加买卖信号标记
        if signals:
            buy_dates = []
            buy_prices = []
            sell_dates = []
            sell_prices = []

            for signal in signals:
                date_str = signal['date'].strftime('%Y-%m-%d') if hasattr(signal['date'], 'strftime') else str(
                    signal['date'])
                price = float(signal['price'])

                if signal['type'] == SignalType.BUY:
                    buy_dates.append(date_str)
                    buy_prices.append(price)
                else:
                    sell_dates.append(date_str)
                    sell_prices.append(price)

            # 买入信号散点
            if buy_dates:
                buy_scatter = Scatter()
                buy_scatter.add_xaxis(buy_dates)
                buy_scatter.add_yaxis(
                    "MB-买入",
                    buy_prices,
                    symbol="triangle",
                    symbol_size=12,
                    color="#8B0000",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="top",
                        distance=5,
                        font_size=9,
                        formatter="MB"
                    )
                )
                line_chart = line_chart.overlap(buy_scatter)

            # 卖出信号散点
            if sell_dates:
                sell_scatter = Scatter()
                sell_scatter.add_xaxis(sell_dates)
                sell_scatter.add_yaxis(
                    "MS-卖出",
                    sell_prices,
                    symbol="diamond",
                    symbol_size=12,
                    color="#006400",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="bottom",
                        distance=5,
                        font_size=9,
                        formatter="MS"
                    )
                )
                line_chart = line_chart.overlap(sell_scatter)

        # 添加实际交易标记
        if trades:
            actual_buy_dates = []
            actual_buy_prices = []
            actual_sell_dates = []
            actual_sell_prices = []

            for trade in trades:
                date_str = trade['date'].strftime('%Y-%m-%d') if hasattr(trade['date'], 'strftime') else str(
                    trade['date'])
                price = float(trade['price'])

                if trade['type'] == SignalType.BUY:
                    actual_buy_dates.append(date_str)
                    actual_buy_prices.append(price)
                else:
                    actual_sell_dates.append(date_str)
                    actual_sell_prices.append(price)

            # 实际买入交易
            if actual_buy_dates:
                actual_buy_scatter = Scatter()
                actual_buy_scatter.add_xaxis(actual_buy_dates)
                actual_buy_scatter.add_yaxis(
                    "实际买入",
                    actual_buy_prices,
                    symbol="triangle",
                    symbol_size=20,
                    color="#8B0000",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="top",
                        distance=12,
                        font_size=14,
                        formatter="❤️"
                    )
                )
                line_chart = line_chart.overlap(actual_buy_scatter)

            # 实际卖出交易
            if actual_sell_dates:
                actual_sell_scatter = Scatter()
                actual_sell_scatter.add_xaxis(actual_sell_dates)
                actual_sell_scatter.add_yaxis(
                    "实际卖出",
                    actual_sell_prices,
                    symbol="diamond",
                    symbol_size=20,
                    color="#006400",
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="bottom",
                        distance=12,
                        font_size=14,
                        formatter="❤️"
                    )
                )
                line_chart = line_chart.overlap(actual_sell_scatter)

        line_chart.set_global_opts(
            title_opts=opts.TitleOpts(
                title="",
                pos_left="left",
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="30%",
                pos_left="right",
                orient="vertical",  # 改为垂直排列
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000000"),  # 提示框文字改为黑色
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
            ]
        )
        return line_chart

    @staticmethod
    def create_position_chart(dates, positions, cash_values):
        """
        创建持仓变化图表
        """
        line_chart = Line()
        line_chart.add_xaxis(dates)

        # 持仓价值线
        line_chart.add_yaxis(
            "持仓价值",
            positions,
            is_smooth=True,
            color="#2ca02c",
            linestyle_opts=opts.LineStyleOpts(width=3),
            symbol="none"
        )

        # 现金价值线
        line_chart.add_yaxis(
            "现金价值",
            cash_values,
            is_smooth=True,
            color="#d62728",
            linestyle_opts=opts.LineStyleOpts(width=3),
            symbol="none"
        )

        line_chart.set_global_opts(
            title_opts=opts.TitleOpts(
                title="",
                pos_left="left",
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="50%",
                pos_left="right",
                orient="vertical",  # 改为垂直排列
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000000"),  # 提示框文字改为黑色
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
            ]
        )
        return line_chart

    @staticmethod
    def create_macd_chart(dates: list, diff: list, dea: list, hist: list,
                          fast_period=12, slow_period=26, signal_period=9):
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
                                return params.value > 0 ? '#ef232a	' : '#14b143';
                            }
                            return '#14b143';
                        }
                    """)
                ),
                bar_width='40%',
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
                linestyle_opts=opts.LineStyleOpts(width=3),
                symbol="none",
                yaxis_index=1,
                z_level=1,
                label_opts=opts.LabelOpts(is_show=False)
            )
            .add_yaxis(
                series_name="DEA",
                y_axis=dea,
                is_smooth=True,
                linestyle_opts=opts.LineStyleOpts(width=3),
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
            title_opts=opts.TitleOpts(title=""),
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
                    pos_top="0%",
                    pos_left="10%",  # 左侧边距
                    pos_right="10%",  # 右侧边距
                    xaxis_index=[0, 1],
                    range_start=0,
                    range_end=100,
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