import threading
import logging
import time
from typing import Callable, Any, Dict
from utils.message import show_message


class BackgroundTaskExecutor:
    """通用后台任务执行器"""
    _tasks = {}  # 存储任务状态
    _lock = threading.Lock()

    @classmethod
    def execute(cls, task_func: Callable, *args, task_name: str = None, **kwargs) -> Dict[str, Any]:
        """
        在后台执行任务

        Args:
            task_func: 要执行的任务函数
            *args: 任务函数的位置参数
            task_name: 任务名称
            **kwargs: 任务函数的关键字参数

        Returns:
            Dict: 包含任务ID和状态信息的字典
        """
        # 生成任务ID
        task_id = f"task_{int(time.time() * 1000)}"
        task_name = task_name or task_func.__name__

        def wrapper():
            """包装任务函数，处理异常和状态更新"""
            with cls._lock:
                cls._tasks[task_id] = {
                    "status": "running",
                    "name": task_name,
                    "start_time": time.time(),
                    "result": None,
                    "error": None
                }
            logging.info(f"后台任务 {task_name}({task_id}) 开始执行")
            try:
                # 执行任务
                result = task_func(*args, **kwargs)

                # 更新成功状态
                with cls._lock:
                    cls._tasks[task_id].update({
                        "status": "completed",
                        "end_time": time.time(),
                        "result": result
                    })
                logging.info(f"后台任务 {task_name}({task_id}) 执行完成")
                return result

            except Exception as e:
                # 更新失败状态
                with cls._lock:
                    cls._tasks[task_id].update({
                        "status": "failed",
                        "end_time": time.time(),
                        "error": str(e)
                    })

                logging.error(f"后台任务 {task_name}({task_id}) 执行失败: {str(e)}")
                return None

        # 启动后台线程
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

        # 返回任务信息
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"任务 '{task_name}' 已在后台启动"
        }

    @classmethod
    def get_task_status(cls, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        with cls._lock:
            return cls._tasks.get(task_id, {"status": "not_found"})

    @classmethod
    def list_tasks(cls) -> Dict[str, Any]:
        """列出所有任务"""
        with cls._lock:
            return cls._tasks.copy()


# 通用后台执行装饰器
def background_task(task_name: str = None):
    """
    装饰器：将函数转换为后台执行

    Args:
        task_name: 任务名称
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            return BackgroundTaskExecutor.execute(
                func, *args, task_name=task_name or func.__name__, **kwargs
            )

        return wrapper

    return decorator
