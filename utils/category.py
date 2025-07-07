from enums.category import Category

def get_category_text(category_str):
    try:
        # 如果已经是 Category 类型
        if isinstance(category_str, Category):
            return category_str.text
        # 将字符串转换为 Category
        if isinstance(category_str, str):
            category = Category(category_str)
            return category.text
        return str(category_str)
    except ValueError as e:
        return str(category_str)
    except Exception as e:
        return str(category_str)
