import time
import random
import logging
from typing import Callable, Any, Optional, Tuple, Type


def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        logger: Optional[logging.Logger] = None
) -> Any:
    """
    带有指数退避和抖动的重试装饰器

    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_factor: 退避因子
        jitter: 是否添加随机抖动
        exceptions: 需要重试的异常类型元组
        logger: 日志记录器

    Returns:
        函数执行结果

    Raises:
        最后一次执行的异常，如果所有重试都失败
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e

            # 如果已达最大重试次数，抛出异常
            if attempt == max_retries:
                if logger:
                    logger.error(f"函数 {func.__name__} 执行失败，已达到最大重试次数 {max_retries}: {str(e)}")
                raise e

            # 计算延迟时间
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)

            # 添加随机抖动
            if jitter:
                delay *= (0.5 + random.random() * 0.5)

            if logger:
                logger.warning(
                    f"函数 {func.__name__} 执行失败，{delay:.2f}秒后进行第{attempt + 1}次重试: {str(e)}"
                )

            time.sleep(delay)

    # 这行代码实际上不会执行到，因为上面会抛出异常
    raise last_exception


class RetryConfig:
    """重试配置类"""

    def __init__(
            self,
            max_retries: int = 3,
            base_delay: float = 1.0,
            max_delay: float = 60.0,
            backoff_factor: float = 2.0,
            jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter


# 预定义的常用配置
RATE_LIMIT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=5.0,
    max_delay=60.0,
    backoff_factor=2.0
)

DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0
)
