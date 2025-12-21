"""
通用防封策略工具

提供统一的请求频率控制、冷却机制等防封功能，
适用于所有需要频繁调用外部API的场景。
"""

import time
import random
import logging
import threading
from typing import Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class RateLimiterConfig:
    """防封配置"""
    min_interval: float = 0.5  # 最小请求间隔（秒）
    random_delay_min: float = 0.2  # 随机延迟最小值（秒）
    random_delay_max: float = 0.8  # 随机延迟最大值（秒）
    cooldown_level_1: int = 5  # 1-2次失败后的冷却时间（秒）
    cooldown_level_2: int = 15  # 3-5次失败后的冷却时间（秒）
    cooldown_level_3: int = 60  # 6次以上失败后的冷却时间（秒）
    enable_random_delay: bool = True  # 是否启用随机延迟
    enable_cooldown: bool = True  # 是否启用冷却机制


class RateLimiter:
    """
    通用请求频率控制器

    功能：
    1. 请求间隔控制
    2. 随机延迟（模拟人类行为）
    3. 失败冷却机制
    4. 线程安全

    使用示例：
        # 创建限流器
        limiter = RateLimiter(name="my_api")

        # 在请求前调用
        limiter.wait_before_request()

        # 请求成功后调用
        limiter.handle_success()

        # 请求失败后调用
        limiter.handle_failure()
    """

    def __init__(self, name: str, config: Optional[RateLimiterConfig] = None):
        """
        初始化限流器

        Args:
            name: 限流器名称（用于日志标识）
            config: 配置对象，如果为None则使用默认配置
        """
        self.name = name
        self.config = config or RateLimiterConfig()

        # 线程锁
        self._lock = threading.Lock()

        # 状态变量
        self._last_request_time = 0.0  # 上次请求时间
        self._failure_count = 0  # 连续失败次数
        self._cooldown_until = 0.0  # 冷却截止时间

        self._logger = logging.getLogger(f"RateLimiter[{name}]")

    def wait_before_request(self) -> None:
        """
        在发送请求前进行智能等待

        执行策略：
        1. 检查是否在冷却期，如果是则等待
        2. 确保满足最小请求间隔
        3. 添加随机延迟（如果启用）
        """
        with self._lock:
            current_time = time.time()

            # 策略1: 如果正在冷却期，等待冷却完成
            if self.config.enable_cooldown and current_time < self._cooldown_until:
                cooldown_wait = self._cooldown_until - current_time
                self._logger.warning(
                    f"[{self.name}] 处于冷却期，等待 {cooldown_wait:.1f} 秒..."
                )
                time.sleep(cooldown_wait)
                current_time = time.time()

            # 策略2: 确保最小请求间隔
            if self._last_request_time > 0:
                elapsed = current_time - self._last_request_time
                if elapsed < self.config.min_interval:
                    wait_time = self.config.min_interval - elapsed
                    self._logger.debug(
                        f"[{self.name}] 请求间隔控制，等待 {wait_time:.2f} 秒"
                    )
                    time.sleep(wait_time)

            # 策略3: 随机延迟（模拟人类行为）
            if self.config.enable_random_delay:
                random_delay = random.uniform(
                    self.config.random_delay_min,
                    self.config.random_delay_max
                )
                self._logger.debug(
                    f"[{self.name}] 随机延迟 {random_delay:.2f} 秒（模拟人类行为）"
                )
                time.sleep(random_delay)

            # 更新最后请求时间
            self._last_request_time = time.time()

    def handle_success(self) -> None:
        """处理请求成功"""
        with self._lock:
            if self._failure_count > 0:
                self._logger.info(
                    f"[{self.name}] 请求成功，重置失败计数（之前失败 {self._failure_count} 次）"
                )
            self._failure_count = 0

    def handle_failure(self) -> None:
        """
        处理请求失败，启动冷却机制

        失败策略：
        - 1-2次失败：冷却 cooldown_level_1 秒
        - 3-5次失败：冷却 cooldown_level_2 秒
        - 6次以上：冷却 cooldown_level_3 秒
        """
        if not self.config.enable_cooldown:
            return

        with self._lock:
            self._failure_count += 1

            # 根据失败次数计算冷却时间
            if self._failure_count <= 2:
                cooldown_seconds = self.config.cooldown_level_1
            elif self._failure_count <= 5:
                cooldown_seconds = self.config.cooldown_level_2
            else:
                cooldown_seconds = self.config.cooldown_level_3

            self._cooldown_until = time.time() + cooldown_seconds

            self._logger.warning(
                f"[{self.name}] 请求失败（连续失败 {self._failure_count} 次），"
                f"启动冷却 {cooldown_seconds} 秒"
            )

    def reset(self) -> None:
        """重置所有状态"""
        with self._lock:
            self._last_request_time = 0.0
            self._failure_count = 0
            self._cooldown_until = 0.0
            self._logger.info(f"[{self.name}] 状态已重置")

    def get_status(self) -> dict:
        """获取当前状态"""
        with self._lock:
            current_time = time.time()
            return {
                "name": self.name,
                "failure_count": self._failure_count,
                "in_cooldown": current_time < self._cooldown_until,
                "cooldown_remaining": max(0, self._cooldown_until - current_time),
                "last_request_ago": current_time - self._last_request_time if self._last_request_time > 0 else None,
            }

    def __enter__(self):
        """支持上下文管理器"""
        self.wait_before_request()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出时自动处理成功/失败"""
        if exc_type is None:
            self.handle_success()
        else:
            self.handle_failure()
        return False  # 不抑制异常


# ============================================
# 预定义的限流器配置
# ============================================

# 激进模式配置（速度快，风险高）
AGGRESSIVE_CONFIG = RateLimiterConfig(
    min_interval=0.3,
    random_delay_min=0.1,
    random_delay_max=0.3,
    cooldown_level_1=3,
    cooldown_level_2=10,
    cooldown_level_3=30,
)

# 平衡模式配置（默认）
BALANCED_CONFIG = RateLimiterConfig(
    min_interval=0.5,
    random_delay_min=0.2,
    random_delay_max=0.8,
    cooldown_level_1=5,
    cooldown_level_2=15,
    cooldown_level_3=60,
)

# 保守模式配置（速度慢，几乎不会被封）
CONSERVATIVE_CONFIG = RateLimiterConfig(
    min_interval=1.0,
    random_delay_min=0.5,
    random_delay_max=1.5,
    cooldown_level_1=10,
    cooldown_level_2=30,
    cooldown_level_3=120,
)

# 无延迟模式（仅用于测试，生产环境慎用）
NO_DELAY_CONFIG = RateLimiterConfig(
    min_interval=0.0,
    random_delay_min=0.0,
    random_delay_max=0.0,
    enable_random_delay=False,
    enable_cooldown=False,
)


# ============================================
# 全局限流器管理
# ============================================

_global_limiters = {}
_global_limiters_lock = threading.Lock()


def get_rate_limiter(
    name: str,
    config: Optional[RateLimiterConfig] = None,
    create_if_missing: bool = True
) -> Optional[RateLimiter]:
    """
    获取或创建全局限流器

    Args:
        name: 限流器名称
        config: 配置对象，仅在创建新限流器时使用
        create_if_missing: 如果不存在是否自动创建

    Returns:
        限流器实例，如果不存在且不自动创建则返回None
    """
    with _global_limiters_lock:
        if name not in _global_limiters:
            if create_if_missing:
                _global_limiters[name] = RateLimiter(name, config)
            else:
                return None
        return _global_limiters[name]


def reset_all_limiters() -> None:
    """重置所有全局限流器"""
    with _global_limiters_lock:
        for limiter in _global_limiters.values():
            limiter.reset()


def get_all_limiter_status() -> dict:
    """获取所有限流器的状态"""
    with _global_limiters_lock:
        return {
            name: limiter.get_status()
            for name, limiter in _global_limiters.items()
        }


# ============================================
# 装饰器
# ============================================

def rate_limited(
    limiter_name: str,
    config: Optional[RateLimiterConfig] = None,
    handle_result: bool = True
):
    """
    装饰器：为函数添加防封保护

    Args:
        limiter_name: 限流器名称
        config: 配置对象
        handle_result: 是否自动处理成功/失败（根据是否抛异常判断）

    使用示例：
        @rate_limited("my_api", BALANCED_CONFIG)
        def fetch_data():
            # ... 你的代码
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            limiter = get_rate_limiter(limiter_name, config)
            limiter.wait_before_request()

            try:
                result = func(*args, **kwargs)
                if handle_result:
                    limiter.handle_success()
                return result
            except Exception as e:
                if handle_result:
                    limiter.handle_failure()
                raise

        return wrapper
    return decorator
