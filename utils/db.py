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
                # 使用PostgreSQL的INSERT ... ON CONFLICT语法进行真正的批量UPSERT
                # 准备要插入的数据
                data_to_insert = []
                for obj in batch:
                    try:
                        # 准备单条记录数据
                        record_data = {}
                        for key, value in obj.__dict__.items():
                            # 跳过内部属性
                            if key.startswith('_'):
                                continue
                            # 处理 NaN 值
                            if isinstance(value, (float, np.float64)) and (math.isnan(value) or np.isnan(value)):
                                record_data[key] = None
                            else:
                                record_data[key] = value
                        # 确保更新时间和removed标志正确设置
                        record_data['updated_at'] = dt.now()
                        record_data['removed'] = False
                        data_to_insert.append(record_data)
                    except Exception as e:
                        failed += 1
                        logging.error(f"Record preparation failed: {str(e)}")
                        logging.error(f"Data: {obj.__dict__}")
                        continue
                
                # 构建INSERT语句
                stmt = pg_insert(model).values(data_to_insert)
                
                # 构建更新部分
                update_dict = {}
                for column in model.__table__.columns:
                    if column.name not in excluded_set and column.name not in unique_fields:
                        update_dict[column.name] = stmt.excluded[column.name]
                # 确保更新时间始终更新
                update_dict['updated_at'] = dt.now()
                update_dict['removed'] = False
                
                # 添加ON CONFLICT子句
                stmt = stmt.on_conflict_do_update(
                    index_elements=unique_fields,
                    set_=update_dict
                )
                
                # 执行语句
                session.execute(stmt)
                processed += len(data_to_insert)
                failed += len(batch) - len(data_to_insert)
                
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
