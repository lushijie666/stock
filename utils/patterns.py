from enums.patterns import Patterns


def identify_patterns(df, body_ratio_threshold=0.2):
    """
    识别K线中的顶分型和底分型，过滤实体比例过小的K线（如十字星）。

    参数:
        df (pd.DataFrame): 包含K线数据的DataFrame，需有列 ['date', 'opening', 'closing', 'high', 'low']
        body_ratio_threshold (float): 实体比例阈值（默认0.3，即实体部分至少占K线范围的30%）

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

        # 顶分型条件：当前高点严格高于左右高点，且实体比例达标
        if (current_high > left_high and current_high > right_high):
            patterns.append({
                'index': i,
                'date': current['date'],
                'value': current_high,
                'type': Patterns.TOP
            })

        # 底分型条件：当前低点严格低于左右低点，且实体比例达标
        elif (current_low < left_low and current_low < right_low):
            patterns.append({
                'index': i,
                'date': current['date'],
                'value': current_low,
                'type': Patterns.BOTTOM
            })

    return patterns