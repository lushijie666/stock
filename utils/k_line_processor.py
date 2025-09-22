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
            #if (current_high > left_high and current_high > right_high and
            #        current_low > left_low and current_low > right_low):
            if (current_high > left_high and current_high > right_high):
                patterns.append({
                    'index': i,
                    'date': current['date'],
                    'value': current_high,
                    'type': Patterns.TOP
                })

            # 底分型条件：当前低点严格低于左右低点，且当前高点也严格低于左右高点
            # 【a,b,c bG<aG && bG<cG && bD<aD &&bD<cD】
            #elif (current_low < left_low and current_low < right_low and
            #      current_high < left_high and current_high < right_high):
            elif (current_low < left_low and current_low < right_low) :
                patterns.append({
                    'index': i,
                    'date': current['date'],
                    'value': current_low,
                    'type': Patterns.BOTTOM
                })

        # 处理分型的有效性
        # 如果后面的顶分型比前面的高，则前面的顶分型无效
        # 如果后面的底分型比前面的低，则前面的底分型无效
        valid_patterns = []
        for i, pattern in enumerate(patterns):
            is_valid = True

            # 检查是否被后续的同性质分型覆盖
            if pattern['type'] == Patterns.TOP:
                # 对于顶分型，如果后面有更高的顶分型，则前面的无效
                for j in range(i + 1, len(patterns)):
                    if patterns[j]['type'] == Patterns.TOP and patterns[j]['value'] > pattern['value']:
                        is_valid = False
                        break
            else:  # Patterns.BOTTOM
                # 对于底分型，如果后面有更低的底分型，则前面的无效
                for j in range(i + 1, len(patterns)):
                    if patterns[j]['type'] == Patterns.BOTTOM and patterns[j]['value'] < pattern['value']:
                        is_valid = False
                        break

            if is_valid:
                valid_patterns.append(pattern)

        return valid_patterns

    @staticmethod
    def identify_strokes(patterns, df):
        if len(patterns) < 2:
            return []

        # 1. 处理相邻相同性质分型
        filtered_patterns = []
        i = 0
        while i < len(patterns):
            current = patterns[i]
            # 如果下一个分型存在且性质相同
            if i + 1 < len(patterns) and patterns[i + 1]['type'] == current['type']:
                next_pattern = patterns[i + 1]
                # 对于顶分型，保留高的
                if current['type'] == Patterns.TOP:
                    if current['value'] > next_pattern['value']:
                        filtered_patterns.append(current)
                    else:
                        filtered_patterns.append(next_pattern)
                # 对于底分型，保留低的
                else:  # Patterns.BOTTOM
                    if current['value'] < next_pattern['value']:
                        filtered_patterns.append(current)
                    else:
                        filtered_patterns.append(next_pattern)
                i += 2  # 跳过已处理的两个分型
            else:
                filtered_patterns.append(current)
                i += 1

        # 2. 构建笔，考虑笔的包含关系
        strokes = []
        if len(filtered_patterns) < 2:
            return []

        # 构建笔
        i = 0
        while i < len(filtered_patterns) - 1:
            start_pattern = filtered_patterns[i]

            # 寻找下一个相反性质的分型
            j = i + 1
            while j < len(filtered_patterns):
                if filtered_patterns[j]['type'] != start_pattern['type']:
                    end_pattern = filtered_patterns[j]
                    # 检查是否满足K线数量要求（至少5根K线）
                    start_index = start_pattern['index']
                    end_index = end_pattern['index']

                    # 确保索引有效且间隔足够
                    if abs(end_index - start_index) + 1 >= 5:
                        stroke_type = "up" if start_pattern['type'] == Patterns.BOTTOM else "down"
                        strokes.append({
                            'start_index': start_index,
                            'end_index': end_index,
                            'start_date': start_pattern['date'],
                            'end_date': end_pattern['date'],
                            'start_value': start_pattern['value'],
                            'end_value': end_pattern['value'],
                            'type': stroke_type,
                            'start_pattern': start_pattern,
                            'end_pattern': end_pattern
                        })
                    i = j  # 从找到的分型继续
                    break
                j += 1
            else:
                # 没有找到相反性质的分型
                i += 1

        # 3. 处理笔的包含关系
        # 这里添加笔的包含关系处理逻辑
        final_strokes = []
        i = 0

        while i < len(strokes):
            current_stroke = strokes[i]
            # 查找后续的同向笔
            j = i + 1
            while j < len(strokes):
                if strokes[j]['type'] == current_stroke['type']:
                    # 检查是否可以合并
                    if KLineProcessor._can_merge_strokes(current_stroke, strokes[j]):
                        # 合并两笔
                        merged_stroke = KLineProcessor._merge_strokes(current_stroke, strokes[j])
                        current_stroke = merged_stroke
                        j += 1
                    else:
                        break
                else:
                    break

            final_strokes.append(current_stroke)
            i = j

        return final_strokes

    @staticmethod
    def identify_segments(strokes):
        """
        识别线段的逻辑
        连续的三笔之间若存在重叠部分，其起点和终点之间的连线为线段
        """
        if len(strokes) < 3:
            return []

        segments = []
        i = 0

        while i <= len(strokes) - 3:
            # 获取连续的三笔
            stroke1 = strokes[i]
            stroke2 = strokes[i + 1]
            stroke3 = strokes[i + 2]

            # 检查三笔之间是否存在重叠部分
            if KLineProcessor._check_overlap(stroke1, stroke2, stroke3):
                # 创建线段：连接第一笔的起点和第三笔的终点
                segment = {
                    'start_index': stroke1['start_index'],
                    'end_index': stroke3['end_index'],
                    'start_date': stroke1['start_date'],
                    'end_date': stroke3['end_date'],
                    'start_value': stroke1['start_value'],
                    'end_value': stroke3['end_value'],
                    'type': stroke1['type'],  # 线段方向与第一笔相同
                    'strokes': [stroke1, stroke2, stroke3]  # 包含的三笔
                }
                segments.append(segment)
                i += 3  # 跳过已处理的三笔
            else:
                i += 1  # 移动到下一笔
        return segments

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

    @staticmethod
    def _check_overlap(stroke1, stroke2, stroke3):
        """
        检查三笔之间是否存在重叠部分
        """
        # 获取每笔的价格范围
        range1 = sorted([stroke1['start_value'], stroke1['end_value']])
        range2 = sorted([stroke2['start_value'], stroke2['end_value']])
        range3 = sorted([stroke3['start_value'], stroke3['end_value']])

        # 检查是否存在重叠：即range1与range2有交集，且range2与range3有交集
        overlap_12 = range1[1] >= range2[0] and range1[0] <= range2[1]
        overlap_23 = range2[1] >= range3[0] and range2[0] <= range3[1]
        return overlap_12 and overlap_23

    @staticmethod
    def _can_merge_strokes(stroke1, stroke2):
        """
        检查两笔是否可以合并
        """
        # 如果两笔方向相同且存在重叠，则可以合并
        if stroke1['type'] != stroke2['type']:
            return False

        # 获取价格范围
        range1 = sorted([stroke1['start_value'], stroke1['end_value']])
        range2 = sorted([stroke2['start_value'], stroke2['end_value']])

        # 检查是否存在重叠
        overlap = range1[1] >= range2[0] and range1[0] <= range2[1]
        return overlap

    @staticmethod
    def _merge_strokes(stroke1, stroke2):
        """
        合并两笔
        """
        # 合并后的起点和终点
        start_index = min(stroke1['start_index'], stroke2['start_index'])
        end_index = max(stroke1['end_index'], stroke2['end_index'])

        # 合并后的起始值和结束值
        start_value = stroke1['start_value']
        end_value = stroke2['end_value']

        return {
            'start_index': start_index,
            'end_index': end_index,
            'start_date': stroke1['start_date'],
            'end_date': stroke2['end_date'],
            'start_value': start_value,
            'end_value': end_value,
            'type': stroke1['type'],
            'start_pattern': stroke1['start_pattern'],
            'end_pattern': stroke2['end_pattern']
        }