import datetime
import logging
from contextlib import contextmanager
from typing import Generator,List, Any, Dict, Type
from datetime import datetime as dt
import numpy as np
import math
from sqlalchemy.dialects.postgresql import insert as pg_insert

from sqlalchemy import inspect, insert, text
from sqlalchemy.orm import Session
from config.database import SessionLocal, Base


def upsert_objects(
        objects: list,
        session: Session,
        model: Type[Base],
        unique_fields: List[str],  # 用于确定唯一记录的字段列表
        batch_size: int = 100,
        excluded_columns: List[str] = None,  # 排除不需要更新的列
) -> Dict[str, int]:
    try:
        total = len(objects)
        processed = 0
        failed = 0

        excluded_set = set(excluded_columns or [])
        # 添加一些默认排除的列
        excluded_set.update(['id', 'created_at'])

        # 分批处理
        for i in range(0, total, batch_size):
            batch = objects[i:i + batch_size]
            session.begin()
            try:
                # 清除 session
                session.expire_all()

                for obj in batch:
                    try:
                        # 构建唯一性查询条件
                        filter_conditions = []
                        for field in unique_fields:
                            filter_conditions.append(
                                getattr(model, field) == getattr(obj, field)
                            )

                        # 查找现有记录
                        existing = session.query(model).filter(
                            *filter_conditions
                        ).first()

                        if existing:
                            # 更新现有记录
                            for key, value in obj.__dict__.items():
                                # 跳过排除的列和内部属性
                                if key in excluded_set or key.startswith('_'):
                                    continue
                                # 处理 NaN 值
                                if isinstance(value, (float, np.float64)) and (math.isnan(value) or np.isnan(value)):
                                    setattr(existing, key, None)
                                else:
                                    setattr(existing, key, value)
                            existing.updated_at = dt.now()
                            existing.removed = False
                        else:
                            # 创建新记录
                            instance = model()
                            for key, value in obj.__dict__.items():
                                # 跳过排除的列和内部属性
                                if key in excluded_set or key.startswith('_'):
                                    continue
                                # 处理 NaN 值
                                if isinstance(value, (float, np.float64)) and (math.isnan(value) or np.isnan(value)):
                                    setattr(instance, key, None)
                                else:
                                    setattr(instance, key, value)
                            instance.updated_at = dt.now()
                            instance.removed = False
                            session.add(instance)
                        processed += 1
                    except Exception as e:
                        failed += 1
                        logging.error(f"Record update failed: {str(e)}")
                        logging.error(f"Data: {obj.__dict__}")
                        continue

                # 提交批次
                session.commit()

            except Exception as e:
                session.rollback()
                failed += len(batch)
                logging.error(f"Batch commit failed: {str(e)}")
                logging.error(f"Error details: {str(e)}")
        return {
            'total': total,
            'processed': processed,
            'failed': failed
        }
    except Exception as e:
        if session.is_active:
            session.rollback()
        logging.error(f"Upsert operation failed: {str(e)}")
        raise

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话的上下文管理器"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def bulk_save_objects(objects: list, session: Session = None) -> bool:
    """批量保存对象"""
    if not session:
        with get_db_session() as session:
            try:
                session.bulk_save_objects(objects)
                return True
            except Exception as e:
                logging.error(f"Bulk save error: {str(e)}")
                return False
    else:
        try:
            session.bulk_save_objects(objects)
            return True
        except Exception as e:
            logging.error(f"Bulk save error: {str(e)}")
            return False
