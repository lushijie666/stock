from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import func

from enums.history_type import StockHistoryType
from enums.sync_type import SyncHistoryType
from models.sync_history import SyncHistory, SyncStatus
from utils.db import get_db_session
from service import stock, stock_history, stock_trade
import logging
def _create_sync_record(sync_type: SyncHistoryType) -> int:
    """创建同步记录，返回记录ID"""
    try:
        with get_db_session() as session:
            record = SyncHistory(
                sync_type=sync_type.value,
                status=SyncStatus.RUNNING.value,
                start_time=datetime.now(timezone.utc),  # 添加时区信息
                end_time=None
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.id  
    except Exception as e:
        logging.error(f"创建同步记录失败: {str(e)}")
        raise


def _update_sync_record(record_id: int, data: Dict[str, Any]):
    """更新同步记录"""
    try:
        with get_db_session() as session:
            record = session.query(SyncHistory).filter(SyncHistory.id == record_id).first()
            if record:
                if 'end_time' in data:
                    # 计算持续时间
                    if record.start_time:
                        # 确保end_time有正确的时区信息
                        end_time = data['end_time']
                        if end_time.tzinfo is None:
                            end_time = end_time.replace(tzinfo=timezone.utc)
                        
                        # 确保start_time有正确的时区信息
                        start_time = record.start_time
                        if start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=timezone.utc)
                        
                        duration = int((end_time - start_time).total_seconds())
                        data['duration'] = duration
                
                for key, value in data.items():
                    setattr(record, key, value)
                
                session.commit()
    except Exception as e:
        logging.error(f"更新同步记录失败: {str(e)}")

def _execute_sync(sync_type: SyncHistoryType, sync_func, *args, **kwargs) -> Dict[str, Any]:
    """执行同步任务的公共方法"""
    record_id = _create_sync_record(sync_type)
    success_count = 0
    failed_count = 0
    error_msg = None
    try:
        result = sync_func(*args, **kwargs)
        success_count = result.get('success_count', 0)
        failed_count = result.get('failed_count', 0)

        _update_sync_record(
            record_id,
            {
                'status': SyncStatus.SUCCESS.value,
                'end_time': datetime.now(timezone.utc),
                'success_count': success_count,
                'failed_count': failed_count
            }
        )
        return {"success": True, "success_count": success_count, "failed_count": failed_count}
    except Exception as e:
        error_msg = str(e)
        _update_sync_record(
            record_id,
            {
                'status': SyncStatus.FAILED.value,
                'end_time': datetime.now(timezone.utc),
                'error': error_msg,
                'success_count': success_count,
                'failed_count': failed_count
            }
        )
        return {"success": False, "error": error_msg}


def sync_stock():
    return _execute_sync(SyncHistoryType.STOCK, stock.sync)


def sync_stock_history(t: StockHistoryType, is_all: bool = False, start_date=None, end_date=None):
    return _execute_sync(t.sync_history_type, stock_history.sync, t=t, is_all=is_all, start_date=start_date, end_date=end_date)


def sync_stock_trade(t: StockHistoryType, is_all: bool = False, start_date=None, end_date=None):
    return _execute_sync(t.sync_trade_type, stock_trade.sync, t=t, is_all=is_all, start_date=start_date, end_date=end_date)

def get_sync_history(limit: int = 50, offset: int = 0, sync_type: SyncHistoryType = None) -> List[SyncHistory]:
    """获取同步历史记录"""
    try:
        with get_db_session() as session:
            query = session.query(SyncHistory)
            if sync_type:
                query = query.filter(SyncHistory.sync_type == sync_type.value)  # 使用枚举值
            records = query.order_by(SyncHistory.start_time.desc()).limit(limit).offset(offset).all()
            return records
    except Exception as e:
        logging.error(f"获取同步历史失败: {str(e)}")
        return []


def get_sync_summary() -> Dict[str, Any]:
    """
    获取同步统计摘要，包括图表所需的各种统计数据
    """
    try:
        with get_db_session() as session:
            # 1. 获取总同步次数
            total_count = session.query(SyncHistory).count()
            
            # 2. 获取成功和失败次数
            success_count = session.query(SyncHistory).filter(SyncHistory.status == SyncStatus.SUCCESS.value).count()  # 使用枚举值
            failed_count = session.query(SyncHistory).filter(SyncHistory.status == SyncStatus.FAILED.value).count()  # 使用枚举值
            
            # 3. 获取最近一次同步记录
            last_sync_record = session.query(SyncHistory).order_by(SyncHistory.start_time.desc()).first()
            last_sync = {
                'id': last_sync_record.id,
                'sync_type': last_sync_record.sync_type,
                'status': last_sync_record.status,
                'start_time': last_sync_record.start_time,
                'end_time': last_sync_record.end_time,
                'duration': last_sync_record.duration,
                'success_count': last_sync_record.success_count,
                'failed_count': last_sync_record.failed_count
            } if last_sync_record else None

            # 4. 获取每日同步次数统计（近90天）
            daily_counts_query = session.query(
                func.date(SyncHistory.start_time).label('date'),
                func.count(SyncHistory.id).label('count')
            ).filter(
                SyncHistory.start_time >= datetime.now(timezone.utc) - timedelta(days=90)
            ).group_by(func.date(SyncHistory.start_time)).order_by('date')
            daily_counts_data = daily_counts_query.all()

            # 5. 获取同步类型分布（近90天）
            type_counts_query = session.query(
                SyncHistory.sync_type.label('type'),
                func.count(SyncHistory.id).label('count')
            ).filter(
                SyncHistory.start_time >= datetime.now(timezone.utc) - timedelta(days=90)
            ).group_by(SyncHistory.sync_type)
            type_counts_data = type_counts_query.all()

            # 6. 获取同步状态分布（近90天）
            status_counts_query = session.query(
                SyncHistory.status.label('status'),
                func.count(SyncHistory.id).label('count')
            ).filter(
                SyncHistory.start_time >= datetime.now(timezone.utc) - timedelta(days=90)
            ).group_by(SyncHistory.status)
            status_counts_data = status_counts_query.all()

            # 7. 获取最近的同步记录（近90天，限制50条用于基本信息显示）
            recent_records = session.query(SyncHistory).filter(
                SyncHistory.start_time >= datetime.now(timezone.utc) - timedelta(days=90)
            ).order_by(SyncHistory.start_time.desc()).limit(50).all()
            
            # 8. 创建用于图表显示的基础DataFrame
            if recent_records:
                records_data = [{
                    '日期': record.start_time.strftime('%Y-%m-%d'),
                    '类型': record.sync_type_display,
                    '状态': record.status_display,
                    '成功数': record.success_count,
                    '失败数': record.failed_count,
                    '耗时(秒)': record.duration or 0,
                    '创建时间': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                } for record in recent_records]
                df = pd.DataFrame(records_data)
            else:
                df = pd.DataFrame(columns=['日期', '类型', '状态', '成功数', '失败数', '耗时(秒)', '创建时间'])
            
            return {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
                "last_sync": last_sync,
                "daily_counts": daily_counts_data,
                "type_counts": type_counts_data,
                "status_counts": status_counts_data,
                "df": df
            }
    except Exception as e:
        logging.error(f"获取同步统计摘要失败: {str(e)}")
        # 返回空数据
        return {
            "total_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "success_rate": 0,
            "last_sync": None,
            "daily_counts": [],
            "type_counts": [],
            "status_counts": [],
            "df": pd.DataFrame(columns=['日期', '类型', '状态', '成功数', '失败数', '耗时(秒)'])
        }