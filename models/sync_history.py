from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from config.database import Base
import enum
from datetime import datetime


class SyncType(enum.Enum):
    """同步类型枚举"""
    STOCK = "stock"
    HISTORY_DATA = "history_data"
    HISTORY_TRANSACTION = "history_transaction"
    REAL_TIME_DATA = "real_time_data"
    
    @property
    def display_name(self):
        """获取显示名称"""
        type_map = {
            SyncType.STOCK: "股票基本数据",
            SyncType.HISTORY_DATA: "历史数据",
            SyncType.HISTORY_TRANSACTION: "历史交易",
            SyncType.REAL_TIME_DATA: "实时数据"
        }
        return type_map.get(self, "未知")


class SyncStatus(enum.Enum):
    """同步状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SyncHistory(Base):
    """同步历史记录模型"""
    __tablename__ = "sync_history"
    
    id = Column(String, primary_key=True, index=True)
    sync_type = Column(SQLEnum(SyncType), nullable=False, index=True)
    status = Column(SQLEnum(SyncStatus), nullable=False, default=SyncStatus.PENDING)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # 单位：秒
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    @property
    def status_display(self):
        """获取状态显示文本"""
        status_map = {
            SyncStatus.PENDING: "等待中",
            SyncStatus.RUNNING: "运行中",
            SyncStatus.SUCCESS: "成功",
            SyncStatus.FAILED: "失败"
        }
        return status_map.get(self.status, "未知")
    
    @property
    def sync_type_display(self):
        """获取同步类型显示文本"""
        type_map = {
            SyncType.STOCK: "股票基本数据",
            SyncType.HISTORY_DATA: "历史数据",
            SyncType.HISTORY_TRANSACTION: "历史交易",
            SyncType.REAL_TIME_DATA: "实时数据"
        }
        return type_map.get(self.sync_type, "未知")