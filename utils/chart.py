from datetime import datetime, date  # 添加这行导入
import streamlit as st
from pyecharts.charts import Pie, Kline, Bar, Grid, Line, Scatter
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
import pandas as pd

from enums.candlestick_pattern import CandlestickPattern
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
    def create_kline_chart(dates, k_line_data, df, ma_lines=None, patterns=None, signals=None, strokes=None, segments=None, centers=None, extra_lines=None, candlestick_patterns=None):
        df_json = df.to_json(orient='records')
        kline = (
            Kline(init_opts=opts.InitOpts())
            .add_xaxis(dates)
            .add_yaxis(
                "K线",
                k_line_data,
                itemstyle_opts=opts.ItemStyleOpts(
                    color="#ef232a",
                    color0="#14b143",
                    border_color="#ef232a",
                    border_color0="#14b143",
                )
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
        # 添加额外的线（如支撑线、阻力线等）
        if extra_lines:
            lines = Line()
            lines.add_xaxis(dates)
            for name, line_data in extra_lines.items():
                values = line_data.get('values', [])
                color = line_data.get('color', None)
                # 确保值的数量与日期数量一致
                if len(values) != len(dates):
                    # 如果长度不一致，用最后一个值填充
                    if len(values) < len(dates):
                        values = values + [values[-1]] * (len(dates) - len(values))
                    else:
                        values = values[:len(dates)]
                line_opts = opts.LineStyleOpts(type_="dashed", width=1)  # 使用虚线
                if color:
                    line_opts.color = color
                lines.add_yaxis(
                    name,
                    values,
                    is_smooth=False,
                    label_opts=opts.LabelOpts(
                        is_show=True,
                        position="end",
                        formatter="{c}",
                        font_size=15,
                        font_weight="bold",
                        color=color if color else "#000"
                    ),
                    linestyle_opts=line_opts,
                    itemstyle_opts=opts.ItemStyleOpts(color=color) if color else None,
                    symbol = "none"
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

        # 添加蜡烛图形态标记（通用化处理）
        if candlestick_patterns:
            # 按形态类型分组
            pattern_groups = {}
            box_patterns = []
            arrow_lines = []  # 收集所有需要绘制箭头的形态

            for pattern in candlestick_patterns:
                pattern_type = pattern.get('type')
                # 排除窗口形态，窗口形态单独处理，不加入pattern_groups
                if 'window_top' not in pattern:
                    if pattern_type not in pattern_groups:
                        pattern_groups[pattern_type] = {
                            'points': [],
                            'name': pattern.get('name', pattern_type),
                            'icon': pattern.get('icon', ''),
                            'color': pattern.get('color', '#000000'),
                            'offset': pattern.get('offset', 0)
                        }
                    pattern_groups[pattern_type]['points'].append([pattern['date'], pattern['value']])

                if 'start_index' in pattern and 'end_index' in pattern and 'window_top' not in pattern:
                    box_patterns.append(pattern)

                # 收集需要绘制箭头的形态（排除窗口形态，窗口只显示边界线）
                if 'window_top' not in pattern:
                    arrow_lines.append({
                        'date': pattern['date'],
                        'value': pattern['value'],
                        'offset': pattern.get('offset', 0),
                        'color': pattern.get('color', '#000000')
                    })

            # 创建枚举顺序映射
            enum_order = {enum.value: i for i, enum in enumerate(CandlestickPattern)}
            # 对 pattern_groups 按照枚举顺序排序
            sorted_pattern_types = sorted(pattern_groups.keys(), key=lambda x: enum_order.get(x, float('inf')))
            # 为每种形态类型创建散点图
            for pattern_type in sorted_pattern_types:
                pattern_data = pattern_groups[pattern_type]
                points = pattern_data['points']
                if points:
                    scatter = Scatter()
                    scatter.add_xaxis([p[0] for p in points])
                    scatter.add_yaxis(
                        series_name=pattern_data['name'],
                        y_axis=[p[1] + pattern_data['offset'] for p in points],
                        symbol='pin',
                        symbol_size=12,
                        itemstyle_opts=opts.ItemStyleOpts(color=pattern_data['color']),
                        label_opts=opts.LabelOpts(
                            is_show=True,
                            color=pattern_data['color'],
                            font_size=16,
                            font_weight='bold',
                            formatter=pattern_data['icon']
                        )
                    )
                    kline = kline.overlap(scatter)

            # 为每个形态添加指向箭头线
            if arrow_lines:
                for arrow_data in arrow_lines:
                    arrow_line = Line()
                    date = arrow_data['date']
                    k_value = arrow_data['value']  # K线的价格点
                    offset = arrow_data['offset']
                    icon_value = k_value + offset  # 图标的位置
                    color = arrow_data['color']

                    # 计算箭头线的起点，留出间隙避免与K线价格标签重叠
                    # 根据偏移方向决定间隙大小
                    gap_ratio = 0.3  # 间隙占总偏移量的比例
                    if offset > 0:  # 向上偏移（顶部形态）
                        # 箭头线从K线上方一点开始，向上延伸到图标
                        arrow_start = k_value + abs(offset) * gap_ratio
                        arrow_end = icon_value
                    else:  # 向下偏移（底部形态）
                        # 箭头线从K线下方一点开始，向下延伸到图标
                        arrow_start = k_value - abs(offset) * gap_ratio
                        arrow_end = icon_value

                    # 绘制指向箭头线，不完全到达K线价格点
                    arrow_line.add_xaxis([date, date])
                    arrow_line.add_yaxis(
                        series_name="",  # 不显示图例
                        y_axis=[arrow_start, arrow_end],
                        is_symbol_show=False,  # 不显示数据点
                        is_smooth=False,
                        linestyle_opts=opts.LineStyleOpts(
                            type_='dashed',  # 虚线样式
                            width=1,  # 细线，更轻量
                            color=color,
                            opacity=0.25  # 更低的透明度，不影响K线展示
                        ),
                        areastyle_opts=opts.AreaStyleOpts(opacity=0),  # 不填充区域
                        label_opts=opts.LabelOpts(is_show=False)
                    )
                    kline = kline.overlap(arrow_line)

            # 虚线框标记
            if box_patterns:
                # 为每个三K线形态绘制矩形框
                for pattern in box_patterns:
                    start_idx = pattern.get('start_index')
                    end_idx = pattern.get('end_index')

                    # 确保索引在有效范围内
                    if start_idx < len(dates) and end_idx < len(dates):
                        start_date = dates[start_idx]
                        end_date = dates[end_idx]

                        # 获取三根K线的价格范围（最高和最低）
                        pattern_high = max([
                            df.iloc[start_idx]['highest'],
                            df.iloc[start_idx + 1]['highest'] if start_idx + 1 < len(df) else 0,
                            df.iloc[end_idx]['highest']
                        ])
                        pattern_low = min([
                            df.iloc[start_idx]['lowest'],
                            df.iloc[start_idx + 1]['lowest'] if start_idx + 1 < len(df) else float('inf'),
                            df.iloc[end_idx]['lowest']
                        ])

                        # 添加一些边距
                        price_range = pattern_high - pattern_low
                        margin = price_range * 0.05  # 5%边距

                        # 创建线条绘制矩形框（虚线）
                        # 使用Line图绘制矩形的四条边
                        box_line = Line()

                        # 矩形的四个顶点：左下 -> 左上 -> 右上 -> 右下 -> 左下（闭合）
                        box_x = [start_date, start_date, end_date, end_date, start_date]
                        box_y = [
                            pattern_low - margin,
                            pattern_high + margin,
                            pattern_high + margin,
                            pattern_low - margin,
                            pattern_low - margin
                        ]

                        box_line.add_xaxis(box_x)
                        box_line.add_yaxis(
                            series_name="",  # 不显示图例
                            y_axis=box_y,
                            is_symbol_show=False,  # 不显示数据点
                            is_smooth=False,
                            linestyle_opts=opts.LineStyleOpts(
                                type_='dashed',  # 虚线
                                width=1.5,  # 稍细的线条
                                color=pattern.get('color', '#888888'),
                                opacity=0.3  # 更低的透明度，不影响K线展示
                            ),
                            label_opts=opts.LabelOpts(is_show=False)
                        )

                        kline = kline.overlap(box_line)

            # 绘制窗口（使用填充区域+两条虚线标记窗口的上下边界）
            window_patterns = [p for p in candlestick_patterns
                             if 'window_top' in p and 'window_bottom' in p]

            if window_patterns:
                for pattern in window_patterns:
                    start_idx = pattern.get('start_index')
                    end_idx = pattern.get('end_index')
                    window_top = pattern.get('window_top')
                    window_bottom = pattern.get('window_bottom')
                    window_middle = (window_top + window_bottom) / 2  # 窗口中间位置

                    # 确保索引在有效范围内
                    if start_idx < len(dates) and end_idx < len(dates):
                        start_date = dates[start_idx]
                        # 延长窗口显示范围，使其更容易看到后续K线是否越过窗口
                        # 向右延伸到数据末尾或者延伸15个K线，取较小值
                        extended_end_idx = min(end_idx + 15, len(dates) - 1)
                        end_date = dates[extended_end_idx]

                        # 1. 绘制窗口上边界虚线
                        top_line = Line()
                        top_line.add_xaxis([start_date, end_date])
                        top_line.add_yaxis(
                            series_name="",  # 不显示图例
                            y_axis=[window_top, window_top],
                            is_symbol_show=False,
                            is_smooth=False,
                            linestyle_opts=opts.LineStyleOpts(
                                type_='dashed',  # 虚线
                                width=1.5,
                                color=pattern.get('color', '#FF6B6B'),
                                opacity=0.3
                            ),
                            label_opts=opts.LabelOpts(
                                is_show=True,
                                position="end",
                                formatter=f"{window_top:.2f}",
                                font_size=14,
                                color=pattern.get('color', '#FF6B6B')
                            )
                        )
                        kline = kline.overlap(top_line)

                        # 2. 绘制窗口下边界虚线
                        bottom_line = Line()
                        bottom_line.add_xaxis([start_date, end_date])
                        bottom_line.add_yaxis(
                            series_name="",  # 不显示图例
                            y_axis=[window_bottom, window_bottom],
                            is_symbol_show=False,
                            is_smooth=False,
                            linestyle_opts=opts.LineStyleOpts(
                                type_='dashed',  # 虚线
                                width=1.5,
                                color=pattern.get('color', '#FF6B6B'),
                                opacity=0.3
                            ),
                            label_opts=opts.LabelOpts(
                                is_show=True,
                                position="end",
                                formatter=f"{window_bottom:.2f}",
                                font_size=14,
                                color=pattern.get('color', '#FF6B6B')
                            )
                        )
                        kline = kline.overlap(bottom_line)

                        # 3. 绘制窗口填充区域（只填充上下虚线之间的区域）
                        # 使用markarea来精确填充窗口区域
                        fill_line = Line()
                        fill_line.add_xaxis([start_date])
                        fill_line.add_yaxis(
                            series_name="",
                            y_axis=[window_middle],
                            is_symbol_show=False,
                            linestyle_opts=opts.LineStyleOpts(width=0, opacity=0),
                            label_opts=opts.LabelOpts(is_show=False),
                            markarea_opts=opts.MarkAreaOpts(
                                data=[
                                    opts.MarkAreaItem(
                                        name="",
                                        x=(start_date, end_date),
                                        y=(window_bottom, window_top),
                                        itemstyle_opts=opts.ItemStyleOpts(
                                            color=pattern.get('color', '#FF6B6B'),
                                            opacity=0.1,
                                            border_width=0
                                        )
                                    )
                                ]
                            )
                        )
                        kline = kline.overlap(fill_line)
                        """
                        # 4. 在窗口中间位置添加图标标记
                        window_scatter = Scatter()
                        window_scatter.add_xaxis([start_date])
                        window_scatter.add_yaxis(
                            series_name=pattern.get('name', ''),
                            y_axis=[window_middle - 0.03],  # 放在窗口中间
                            symbol='pin',
                            symbol_size=12,
                            itemstyle_opts=opts.ItemStyleOpts(color=pattern.get('color', '#FF6B6B')),
                            label_opts=opts.LabelOpts(
                                is_show=True,
                                color=pattern.get('color', '#FF6B6B'),
                                font_size=16,
                                font_weight='bold',
                                formatter=pattern.get('icon', '📊')
                            )
                        )
                        kline = kline.overlap(window_scatter)
                        """

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

            # 应用标记区域
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
                textstyle_opts=opts.TextStyleOpts(color="#000000")
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
                position="left",  # 改为左侧
                name="价格(元/美元)",
                name_location="middle",
                name_gap=60,
                name_rotate=-90,
                name_textstyle_opts=opts.TextStyleOpts(color="#000000", font_size=12),
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
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
                formatter=JsCode(f"""
                    function(params) {{
                        if (!params || params.length === 0) return '';

                        function formatValue(value) {{
                            if (value >= 100000000) {{
                                return (value / 100000000).toFixed(2) + '亿';
                            }} else if (value >= 10000) {{
                                return (value / 10000).toFixed(2) + '万';
                            }} else {{
                                return value.toLocaleString();
                            }}
                        }}
                        var dfData = {df_json};
                        var currentDate = params[0].axisValue;
                        var result = '<div style="padding:2px; width:200px;"><strong>' + currentDate + '</strong><br/>';
                        params.forEach(function(item) {{
                            if (item.seriesName === 'K线') {{
                                var index = item.dataIndex;
                                var currentData = dfData[index];
                                var opening = parseFloat(currentData.opening).toFixed(2);
                                var closing = parseFloat(currentData.closing).toFixed(2);
                                var lowest = parseFloat(currentData.lowest).toFixed(2);
                                var highest = parseFloat(currentData.highest).toFixed(2);
                                var changeAmount = parseFloat(currentData.change_amount).toFixed(2);
                                var change = parseFloat(currentData.change).toFixed(2) + '%';
                                result += '<span style="color:#fa8c16;">开盘价</span> <span style="float:right;font-weight:bold;">' + opening + '</span><br/>';
                                result += '<span style="color:#52c41a;">收盘价</span> <span style="float:right;font-weight:bold;">' + closing + '</span><br/>';
                                result += '<span style="color:#13c2c2;">最低价</span> <span style="float:right;font-weight:bold;">' + lowest + '</span><br/>';
                                result += '<span style="color:#f5222d;">最高价</span> <span style="float:right;font-weight:bold;">' + highest + '</span><br/>';
                                result += '<span style="color:#FF3030;">涨跌额</span> <span style="float:right;font-weight:bold;">' + changeAmount + '</span><br/>';
                                result += '<span style="color:#fa8c16;">涨跌率</span> <span style="float:right;font-weight:bold;">' + change + '</span><br/>';
                            }} else if (item.seriesName === '成交量') {{
                                var index = item.dataIndex;
                                var currentData = dfData[index];
                                var value = item.value;
                                var shouValue = (value / 100).toFixed(0);
                                var formattedValue = formatValue(value);
                                var formattedShou = formatValue(Number(shouValue));
                                var formattedTurnover = formatValue(currentData.turnover_amount);
                                var turnoverRatio = parseFloat(currentData.turnover_ratio).toFixed(2) + '%';

                                result += '<span style="color:#722ed1;">成交量(股)</span> <span style="float:right;font-weight:bold;">' + formattedValue + '</span><br/>';
                                result += '<span style="color:#722ed1;">成交量(手)</span> <span style="float:right;font-weight:bold;">' + formattedShou + '</span><br/>';
                                result += '<span style="color:#eb2f96;">成交额</span> <span style="float:right;font-weight:bold;">' + formattedTurnover + '</span><br/>';
                                result += '<span style="color:#faad14;">换手率</span> <span style="float:right;font-weight:bold;">' + turnoverRatio + '</span><br/>';
                            }}
                        }});

                        result += '</div>';
                        return result;
                    }}
                """)
            ),
        )
        return kline

    @staticmethod
    def create_volume_bar(dates, volumes, df):
        colors = ['#ef232a' if close > open else '#14b143'
                  for open, close in zip(df['opening'], df['closing'])]
        df_json = df.to_json(orient='records')
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
                    name="成交量(股)",
                    name_location="middle",
                    name_gap=60,
                    name_rotate=-90,
                    name_textstyle_opts=opts.TextStyleOpts(color="#000000", font_size=12),
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
                        color="#000000",
                        formatter=JsCode("""
                                function(value) {
                                    if (value >= 100000000) {
                                        return (value / 100000000).toFixed(1) + '亿';
                                    } else if (value >= 10000) {
                                        return (value / 10000).toFixed(1) + '万';
                                    } else {
                                        return value;
                                    }
                                }
                            """)
                    ),
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="cross",
                    background_color="rgba(245, 245, 245, 0.8)",
                    border_width=1,
                    border_color="#ccc",
                    textstyle_opts=opts.TextStyleOpts(color="#000000"),
                    formatter=JsCode(f"""
                        function(params) {{
                            if (!params || params.length === 0) return '';

                            function formatValue(value) {{
                                if (value >= 100000000) {{
                                    return (value / 100000000).toFixed(2) + '亿';
                                }} else if (value >= 10000) {{
                                    return (value / 10000).toFixed(2) + '万';
                                }} else {{
                                    return value.toLocaleString();
                                }}
                            }}

                            var dfData = {df_json};
                            var result = '<div style="padding:2px; width:200px;"><strong>' + params[0].axisValue + '</strong><br/>';
                            params.forEach(function(item) {{
                                if (item.seriesName === '成交量') {{
                                    var index = item.dataIndex;
                                    var currentData = dfData[index];
                                    var value = item.value;
                                    var shouValue = (value / 100).toFixed(0);
                                    var formattedValue = formatValue(value);
                                    var formattedShou = formatValue(Number(shouValue));
                                    var formattedTurnover = formatValue(currentData.turnover_amount);
                                    var turnoverRatio = parseFloat(currentData.turnover_ratio).toFixed(2) + '%';

                                    result += '<span style="color:#722ed1;">成交量(股)</span> <span style="float:right;font-weight:bold;">' + formattedValue + '</span><br/>';
                                    result += '<span style="color:#722ed1;">成交量(手)</span> <span style="float:right;font-weight:bold;">' + formattedShou + '</span><br/>';
                                    result += '<span style="color:#eb2f96;">成交额</span> <span style="float:right;font-weight:bold;">' + formattedTurnover + '</span><br/>';
                                    result += '<span style="color:#faad14;">换手率</span> <span style="float:right;font-weight:bold;">' + turnoverRatio + '</span><br/>';
                                }}
                            }});

                            result += '</div>';
                            return result;
                        }}
                    """)
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
                    pos_top="70%",
                    height="20%"
                ),
            )
        )
        return grid

    @staticmethod
    def create_linked_charts(charts_config, total_height="1400px"):
        """
        创建联动的图表组合（通用方法）

        所有图表共享同一个dataZoom，实现时间轴联动

        Args:
            charts_config: 图表配置列表，每个配置包含：
                - chart: pyecharts图表对象
                - grid_pos: dict，包含 pos_top 和 height
                - title: 可选，图表标题
            total_height: Grid总高度，默认"1400px"

        Example:
            charts_config = [
                {
                    "chart": kline_chart,
                    "grid_pos": {"pos_top": "5%", "height": "28%"},
                    "title": "K线图"
                },
                {
                    "chart": volume_chart,
                    "grid_pos": {"pos_top": "37%", "height": "28%"},
                    "title": "成交量"
                }
            ]

        Returns:
            Grid: 包含所有联动图表的Grid对象
        """
        # 创建Grid
        grid = Grid(init_opts=opts.InitOpts(
            width="100%",
            height=total_height,
            animation_opts=opts.AnimationOpts(animation=False),
            theme="white",
            bg_color="white"
        ))
        # 添加所有图表到Grid
        for idx, config in enumerate(charts_config):
            chart = config.get("chart")
            grid_pos = config.get("grid_pos", {})

            if chart is None:
                continue

            # 获取图表原有的options，用于保留原有配置
            chart_options = chart.options

            # 更新 xAxis 配置（保留原有配置，只添加 gridIndex）
            if "xAxis" in chart_options:
                for xaxis in chart_options["xAxis"]:
                    xaxis["gridIndex"] = idx
                    # 所有图表都显示x轴标签（只是最后一个会完整显示）
                    # 不隐藏，让每个图表都能看到日期

            # 更新 yAxis 配置（保留原有配置，只添加 gridIndex）
            if "yAxis" in chart_options:
                for yaxis in chart_options["yAxis"]:
                    yaxis["gridIndex"] = idx

            # 处理 tooltip 显示配置
            # 注意：不在这里修改tooltip，而是在Grid层面统一处理
            show_tooltip = config.get("show_tooltip", True)
            # 将show_tooltip信息保存，稍后在Grid层面处理
            if not show_tooltip:
                # 标记该图表的series不显示tooltip
                if "series" in chart_options:
                    for series in chart_options["series"]:
                        if isinstance(series, dict):
                            series["tooltip"] = {"show": False}


            # 调整图例位置，避免重叠
            if "legend" in chart_options:
                for legend in chart_options["legend"] if isinstance(chart_options["legend"], list) else [chart_options["legend"]]:
                    # 根据图表索引调整图例的垂直位置
                    if idx == 0:
                        legend["top"] = "10%"  # 第一个图表的图例
                    elif idx == 1:
                        legend["top"] = "40%"  # 第二个图表的图例
                    elif idx == 2:
                        legend["top"] = "85%"  # 第三个图表的图例
                    else:
                        # 如果有更多图表，按比例计算
                        legend["top"] = f"{int(grid_pos.get('pos_top', '0%').rstrip('%')) + 1}%"

            # 添加到Grid
            grid.add(
                chart,
                grid_opts=opts.GridOpts(
                    pos_left="10%",
                    pos_right="10%",
                    pos_top=grid_pos.get("pos_top", "5%"),
                    height=grid_pos.get("height", "30%")
                ),
            )

        # 构建所有图表的索引列表
        chart_indices = list(range(len(charts_config)))

        # 添加全局的 dataZoom 控制器，控制所有图表的 x 轴
        grid.options.update({
            "dataZoom": [
                {
                    "type": "slider",
                    "xAxisIndex": chart_indices,  # 控制所有图表
                    "start": 0,
                    "end": 100,
                    "top": "1%",  # 移到顶部
                    "height": 25,
                    "handleSize": "110%",  # 增大滑块手柄大小，方便拖动
                    "handleStyle": {
                        "color": "#5470c6",
                        "borderColor": "#5470c6"
                    },
                    "textStyle": {
                        "color": "#333"
                    },
                    "borderColor": "#ccc"
                }
            ],
            # 配置 axisPointer 联动，让十字准星在所有图表间同步
            "axisPointer": {
                "link": [{"xAxisIndex": "all"}]
            },
        })

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
            "策略收益(%)",
            strategy_values,
            is_smooth=True,
            color="#2e7ed6",
            linestyle_opts=opts.LineStyleOpts(width=3),
            symbol="none",
            label_opts=opts.LabelOpts(is_show=False)
        )

        # 添加基准收益线（买入持有）
        line.add_yaxis(
            "基准收益(%)",
            benchmark_values,
            is_smooth=True,
            color="#2caf18",
            linestyle_opts=opts.LineStyleOpts(width=3, type_="dashed"),
            symbol="none",
            label_opts=opts.LabelOpts(is_show=False)
        )
        line.set_global_opts(
            title_opts=opts.TitleOpts(
                title="",
                pos_left="left",
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="5%",
                pos_left="right",
                orient="vertical",
                textstyle_opts=opts.TextStyleOpts(color="#000000", font_size=12),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.9)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
                formatter="{b}<br/>{a}: {c}%"
            ),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(
                    is_on_zero=False,
                    linestyle_opts=opts.LineStyleOpts(color="#666666")
                ),
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(color="#EEEEEE")
                ),
                axislabel_opts=opts.LabelOpts(color="#000000", rotate=45),
                min_="dataMin",
                max_="dataMax"
            ),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(color="#EEEEEE")
                ),
                axislabel_opts=opts.LabelOpts(
                    color="#000000",
                    formatter="{value}%"
                ),
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(color="#666666")
                )
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=True,
                    type_="slider",
                    pos_top="90%",
                    pos_left="10%",
                    pos_right="10%",
                    xaxis_index=[0],
                    range_start=0,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0],
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
        创建持仓变化图表（堆叠面积图）
        """
        # 计算总资产
        total_values = [p + c for p, c in zip(positions, cash_values)]

        bar = Bar()
        bar.add_xaxis(dates)

        # 添加持仓价值（堆叠柱状图）
        bar.add_yaxis(
            "持仓价值(¥)",
            positions,
            stack="资产",
            color="#5470c6",
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                border_color="#fff",
                border_width=0
            )
        )

        # 添加现金价值（堆叠柱状图）
        bar.add_yaxis(
            "现金价值(¥)",
            cash_values,
            stack="资产",
            color="#91cc75",
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                border_color="#fff",
                border_width=0
            )
        )

        # 添加总资产线
        line = Line()
        line.add_xaxis(dates)
        line.add_yaxis(
            "总资产(¥)",
            total_values,
            is_smooth=True,
            color="#ee6666",
            linestyle_opts=opts.LineStyleOpts(width=3),
            symbol="circle",
            symbol_size=6,
            label_opts=opts.LabelOpts(is_show=False),
        )

        bar.set_global_opts(
            title_opts=opts.TitleOpts(
                title="",
                pos_left="left",
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="5%",
                pos_left="right",
                orient="vertical",
                textstyle_opts=opts.TextStyleOpts(color="#000000", font_size=12),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.9)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000000"),
                formatter="{b}<br/>{a}: ¥{c}"
            ),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                boundary_gap=True,
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(color="#666666")
                ),
                splitline_opts=opts.SplitLineOpts(
                    is_show=False
                ),
                axislabel_opts=opts.LabelOpts(color="#000000", rotate=45),
            ),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(color="#EEEEEE")
                ),
                axislabel_opts=opts.LabelOpts(
                    color="#000000",
                    formatter="¥{value}"
                ),
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(color="#666666")
                )
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=True,
                    type_="slider",
                    pos_top="90%",
                    pos_left="10%",
                    pos_right="10%",
                    xaxis_index=[0],
                    range_start=0,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0],
                    range_start=0,
                    range_end=100,
                ),
            ]
        )

        # 组合柱状图和折线图
        bar.overlap(line)
        return bar

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