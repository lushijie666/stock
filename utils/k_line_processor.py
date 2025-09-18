from enums.patterns import Patterns


class KLineProcessor:
    @staticmethod
    def process_contains(df):
        # 备份原始日期列
        date_series = df['date'].copy()

        # 预计算技术指标（保持与日期列对齐）
        df = df.assign(
            body_size=abs(df['opening'] - df['closing']),
            total_range=df['highest'] - df['lowest'],
            body_ratio=lambda x: x['body_size'] / x['total_range'].replace(0, 0.001)
        )

        processed_data = df.copy()
        contains_marks = [False] * len(processed_data)
        processing_records = []

        changed = True
        iteration = 0
        max_iterations = 5

        while changed and iteration < max_iterations:
            iteration += 1
            changed = False
            directions = []

            # 计算方向（带1%缓冲）
            for i in range(1, len(processed_data)):
                prev = processed_data.iloc[i - 1]
                curr = processed_data.iloc[i]
                directions.append(1 if curr['closing'] > prev['closing'] * 1.01 else
                                  (-1 if curr['closing'] < prev['closing'] * 0.99 else 0))

            i = 1
            while i < len(processed_data) - 1:
                # 确保索引有效
                if i >= len(processed_data) - 1:
                    break

                k1 = processed_data.iloc[i - 1].copy()
                k2 = processed_data.iloc[i].copy()
                k3 = processed_data.iloc[i + 1].copy()

                # 实时计算body_ratio（避免依赖预处理列）
                k2_range = k2['highest'] - k2['lowest']
                k3_range = k3['highest'] - k3['lowest']
                k2_body_ratio = abs(k2['opening'] - k2['closing']) / (k2_range + 0.001)
                k3_body_ratio = abs(k3['opening'] - k3['closing']) / (k3_range + 0.001)

                # 包含关系检测
                # K2被K3包含：K2的最高价>=K3的最高价 且 K2的最低价<=K3的最低价
                # 或者K3被K2包含：K3的最高价>=K2的最高价 且 K3的最低价<=K2的最低价
                k2_body = (min(k2['opening'], k2['closing']), max(k2['opening'], k2['closing']))
                k3_body = (min(k3['opening'], k3['closing']), max(k3['opening'], k3['closing']))

                is_contained = (
                                       (k2_body[1] >= k3_body[1] and k2_body[0] <= k3_body[0]) or  # K2包含K3
                                       (k3_body[1] >= k2_body[1] and k3_body[0] <= k2_body[0])  # K3包含K2
                               ) and (k2_body_ratio > 0.2 or k3_body_ratio > 0.2)  # 实体比例达标

                if is_contained:
                    # 趋势判断（前3根）
                    lookback = min(3, i)
                    trend_up = sum(directions[i - lookback:i]) > 0

                    # 合并处理（显式保留日期）
                    new_date = k2['date']  # 保留K2的日期

                    # 正确的包含处理逻辑：
                    # 向上包含：取两K线中较高的最高价和较高的最低价
                    # 向下包含：取两K线中较低的最高价和较低的最低价
                    if trend_up:
                        new_high = max(k2['highest'], k3['highest'])
                        new_low = max(k2['lowest'], k3['lowest'])
                        # 开盘价取合并后第一根K线的开盘价，收盘价取合并后最高价所在K线的收盘价
                        new_open = k2['opening']
                        if k3['highest'] > k2['highest']:
                            new_close = k3['closing']
                        else:
                            new_close = k2['closing']
                    else:
                        new_high = min(k2['highest'], k3['highest'])
                        new_low = min(k2['lowest'], k3['lowest'])
                        # 开盘价取合并后第一根K线的开盘价，收盘价取合并后最低价所在K线的收盘价
                        new_open = k2['opening']
                        if k3['lowest'] < k2['lowest']:
                            new_close = k3['closing']
                        else:
                            new_close = k2['closing']

                    # 更新当前K线
                    processed_data.at[i, 'date'] = new_date
                    processed_data.at[i, 'opening'] = new_open
                    processed_data.at[i, 'closing'] = new_close
                    processed_data.at[i, 'highest'] = new_high
                    processed_data.at[i, 'lowest'] = new_low
                    processed_data.at[i, 'turnover_count'] = k2['turnover_count'] + k3['turnover_count']

                    # 记录处理信息
                    record = {
                        'date': new_date,
                        'trend': '⬆向上' if trend_up else '⬇向下',
                        'original_k1': k1.to_dict(),
                        'original_k2': k2.to_dict(),
                        'original_k3': k3.to_dict(),
                        'new_values': {
                            'date': new_date.strftime('%Y-%m-%d'),
                            'high': new_high,
                            'low': new_low,
                            'open': new_open,
                            'close': new_close
                        }
                    }
                    processing_records.append(record)

                    # 删除被合并K线（保持date列）
                    processed_data = processed_data.drop(i + 1).reset_index(drop=True)
                    contains_marks.pop(i + 1)
                    changed = True

                    # 重置方向计算
                    directions = []
                    for j in range(1, len(processed_data)):
                        prev = processed_data.iloc[j - 1]
                        curr = processed_data.iloc[j]
                        directions.append(1 if curr['closing'] > prev['closing'] * 1.01 else
                                          (-1 if curr['closing'] < prev['closing'] * 0.99 else 0))
                    i = max(1, i - 1)  # 回退检查
                else:
                    i += 1

        return processed_data, contains_marks, processing_records

    @staticmethod
    def identify_patterns(df, body_ratio_threshold=0.2):
        """
        识别K线中的顶分型和底分型，过滤实体比例过小的K线（如十字星）。

        参数:
            df (pd.DataFrame): 包含K线数据的DataFrame，需有列 ['date', 'opening', 'closing', 'high', 'low']
            body_ratio_threshold (float): 实体比例阈值（默认0.2，即实体部分至少占K线范围的30%）

        返回:
            list: 分型列表，每个元素为字典，包含 index/date/value/type
        """
        patterns = []

        for i in range(1, len(df) - 1):
            # 当前K线数据
            current = df.iloc[i]
            open_price = current['opening']
            close_price = current['closing']
            current_high = current['highest']  # 使用最高价和最低价（更精确）
            current_low = current['lowest']

            # 计算实体比例
            body_size = abs(open_price - close_price)
            candle_range = current_high - current_low

            # 跳过实体比例过小的K线（如十字星）
            if candle_range == 0 or (body_size / candle_range) < body_ratio_threshold:
                continue

            # 左右K线数据
            left = df.iloc[i - 1]
            right = df.iloc[i + 1]

            left_high = left['highest']
            left_low = left['lowest']
            right_high = right['highest']
            right_low = right['lowest']

            # 顶分型条件：当前高点严格高于左右高点，且当前低点也严格高于左右低点
            # 【a,b,c bG>aG && bG>cG && bD>aD &&bD>cD】
            if (current_high > left_high and current_high > right_high and
                    current_low > left_low and current_low > right_low):
                patterns.append({
                    'index': i,
                    'date': current['date'],
                    'value': current_high,
                    'type': Patterns.TOP
                })

            # 底分型条件：当前低点严格低于左右低点，且当前高点也严格低于左右高点
            # 【a,b,c bG<aG && bG<cG && bD<aD &&bD<cD】
            elif (current_low < left_low and current_low < right_low and
                  current_high < left_high and current_high < right_high):
                patterns.append({
                    'index': i,
                    'date': current['date'],
                    'value': current_low,
                    'type': Patterns.BOTTOM
                })

        return patterns

    @classmethod
    def identify_strokes_and_segments(cls, patterns, df):
        """
        识别笔和线段

        笔的概念：连续两个相临的顶和底，且顶和底至少有一根K线相连 【标记的顶点和低点中，算上顶和低点所在的两根K线，K线的数量应该大于等于5】
        画笔是关于顶底特殊情况的处理：
            1.如果前后分型属于同一性质，对于顶，前面的低于后面的，只保留后面的，前面的可以忽略掉；对于底，前面的高于后面的，前面的可以忽略掉，只保留后面的；
           翻译：【顶分型的下一个分型也是顶分型。则保留大的分型。不保留的分型标记失效。】
        【底分型的下一个分型也是底分型。则保留小的分型。不保留的分型标记失效。】
          向上一笔：从底到顶 。用S标记
          向下一笔：从顶到底。用X标记

        线段概念：连续的三笔之间若存在重叠部分，其起点和终点之间的连线为线段
        """
        if len(patterns) < 2:
            return [], []

        # 第一步：处理相同性质的分型
        filtered_patterns = []
        i = 0
        while i < len(patterns):
            current = patterns[i]
            # 检查下一个是否为相同类型的分型
            if i + 1 < len(patterns) and patterns[i + 1]['type'] == current['type']:
                next_pattern = patterns[i + 1]
                # 对于顶分型，保留高的
                if current['type'] == Patterns.TOP:
                    if current['value'] > next_pattern['value']:
                        filtered_patterns.append(current)
                    else:
                        filtered_patterns.append(next_pattern)
                # 对于底分型，保留低的
                else:  # BOTTOM
                    if current['value'] < next_pattern['value']:
                        filtered_patterns.append(current)
                    else:
                        filtered_patterns.append(next_pattern)
                i += 2  # 跳过下一个
            else:
                filtered_patterns.append(current)
                i += 1

        # 第二步：识别笔
        strokes = []
        i = 0
        while i < len(filtered_patterns) - 1:
            start_pattern = filtered_patterns[i]
            end_pattern = filtered_patterns[i + 1]

            # 确保是相邻的顶和底（或底和顶）
            if start_pattern['type'] != end_pattern['type']:
                # 计算K线数量（包括两个分型所在的K线）
                start_index = start_pattern['index']
                end_index = end_pattern['index']

                # 确保起始点在结束点之前
                if start_index < end_index:
                    kline_count = end_index - start_index + 1

                    # 至少需要5根K线
                    if kline_count >= 5:
                        direction = 'up' if start_pattern['type'] == Patterns.BOTTOM else 'down'
                        stroke = {
                            'start_date': start_pattern['date'],
                            'end_date': end_pattern['date'],
                            'start_price': start_pattern['value'],
                            'end_price': end_pattern['value'],
                            'start_index': start_index,
                            'end_index': end_index,
                            'direction': direction,
                            'kline_count': kline_count
                        }
                        strokes.append(stroke)
            i += 1

        # 第三步：识别线段（基于连续三笔的重叠）
        segments = []
        if len(strokes) >= 3:
            i = 0
            while i <= len(strokes) - 3:
                # 取连续三笔
                first_stroke = strokes[i]
                second_stroke = strokes[i + 1]
                third_stroke = strokes[i + 2]

                # 检查是否存在重叠部分
                # 向上线段：第一笔的高点 > 第二笔的低点 且 第三笔的高点 > 第二笔的低点
                # 向下线段：第一笔的低点 < 第二笔的高点 且 第三笔的低点 < 第二笔的高点

                # 判断方向是否一致（都向上或都向下）
                if (first_stroke['direction'] == second_stroke['direction'] == third_stroke['direction']):
                    # 创建线段：从第一笔起点到第三笔终点
                    segment = {
                        'start_date': first_stroke['start_date'],
                        'end_date': third_stroke['end_date'],
                        'start_price': first_stroke['start_price'],
                        'end_price': third_stroke['end_price'],
                        'direction': first_stroke['direction'],
                        'strokes': [first_stroke, second_stroke, third_stroke]
                    }
                    segments.append(segment)
                    i += 3  # 跳过已处理的三笔
                else:
                    i += 1

        return strokes, segments


    @classmethod
    def process_klines(cls, df, body_ratio_threshold=0.2):
        """
        完整的K线处理流程：先处理包含关系，再识别分型。

        Args:
            df (pd.DataFrame): 原始K线数据
            body_ratio_threshold (float): 分型识别的实体比例阈值

        Returns:
            tuple: (processed_df, contains_marks, patterns)
                processed_df: 处理包含关系后的DataFrame
                contains_marks: 包含关系标记列表
                patterns: 分型列表
        """
        # 1. 处理包含关系
        processed_df, contains_marks, processing_records = cls.process_contains(df)
        # 2. 识别分型
        patterns = cls.identify_patterns(processed_df, body_ratio_threshold)
        return processed_df, contains_marks, processing_records, patterns

    @staticmethod
    def validate_data(df):
        required_columns = ['date', 'opening', 'closing', 'highest', 'lowest', 'turnover_count']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"数据缺少必要的列: {missing_columns}")

        if len(df) < 3:
            raise ValueError("数据量太少，至少需要3根K线")

        # 验证数据类型和有效性
        if not all(df['highest'] >= df['lowest']):
            raise ValueError("存在最高价低于最低价的无效数据")

        if not all(df['highest'] >= df['opening']) or not all(df['highest'] >= df['closing']):
            raise ValueError("存在开盘价或收盘价高于最高价的无效数据")

        if not all(df['lowest'] <= df['opening']) or not all(df['lowest'] <= df['closing']):
            raise ValueError("存在开盘价或收盘价低于最低价的无效数据")
