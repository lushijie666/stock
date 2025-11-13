import schedule
import time
import threading
from datetime import datetime
import logging
from typing import Dict, Callable

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SchedulerManager:
    """定时任务管理器"""
    
    def __init__(self):
        self.scheduler = schedule
        self.running = False
        self.thread = None
        self.jobs = {}
        
    def start(self):
        """启动定时任务线程"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_pending_jobs, daemon=True)
            self.thread.start()
            logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止定时任务线程"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1)
            self.scheduler.clear()
            self.jobs.clear()
            logger.info("定时任务调度器已停止")
    
    def _run_pending_jobs(self):
        """运行待执行的任务"""
        while self.running:
            self.scheduler.run_pending()
            time.sleep(1)

    def add_interval_job(self, job_id: str, func: Callable, interval_minutes: int = 10, *args, **kwargs):
        """添加间隔定时任务"""
        # 如果任务已存在，先移除
        if job_id in self.jobs:
            self.jobs[job_id].cancel()

        # 添加新任务
        job = self.scheduler.every(interval_minutes).minutes.do(func, *args, **kwargs)
        self.jobs[job_id] = job
        logger.info(f"添加间隔定时任务: {job_id} 每 {interval_minutes} 分钟执行一次")
    def add_daily_job(self, job_id: str, func: Callable, hour: int, minute: int, *args, **kwargs):
        """添加每日定时任务"""
        # 如果任务已存在，先移除
        if job_id in self.jobs:
            self.jobs[job_id].cancel()
        
        # 添加新任务
        job = self.scheduler.every().day.at(f"{hour:02d}:{minute:02d}").do(func, *args, **kwargs)
        self.jobs[job_id] = job
        logger.info(f"添加每日定时任务: {job_id} 在 {hour:02d}:{minute:02d}")
        
    def remove_job(self, job_id: str):
        """移除定时任务"""
        if job_id in self.jobs:
            self.jobs[job_id].cancel()
            del self.jobs[job_id]
            logger.info(f"移除定时任务: {job_id}")
    
    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self.running
    
    def get_jobs_info(self) -> Dict[str, str]:
        """获取所有任务信息"""
        return {
            job_id: f"下次执行时间: {job.next_run}" 
            for job_id, job in self.jobs.items()
        }


# 创建全局调度器实例
scheduler = SchedulerManager()