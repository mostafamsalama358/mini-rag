import hashlib
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from models.db_schemes.algorag.schemes.celery_task_execution import CeleryTaskExecution

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

class IdempotencyManager:

    def __init__(self, db_client, db_engine):
        self.db_client = db_client
        self.db_engine = db_engine

    def create_args_hash(self, task_name: str, task_args: dict):
        combined_data = {
            **task_args,
            "task_name": task_name
        }
        json_string = json.dumps(combined_data, sort_keys=True, default=str)
        return hashlib.sha256(json_string.encode()).hexdigest()
    
    async def create_task_record(self, task_name: str, task_args: dict, celery_task_id: str = None) -> CeleryTaskExecution:
        """Create new task execution record."""
        args_hash = self.create_args_hash(task_name, task_args)
        
        task_record = CeleryTaskExecution(
            task_name=task_name,
            task_args_hash=args_hash,
            task_args=task_args,
            celery_task_id=celery_task_id,
            status='PENDING',
            started_at=_utcnow()
        )
        
        session = self.db_client()
        try:
            session.add(task_record)
            await session.commit()
            await session.refresh(task_record)
            return task_record
        finally:
            await session.close()

    async def update_task_status(self, execution_id: int, status: str, result: dict = None):
        """Update task status and result."""
        session = self.db_client()
        try:
            task_record = await session.get(CeleryTaskExecution, execution_id)
            if task_record:
                task_record.status = status
                if result:
                    task_record.result = result
                if status in ['SUCCESS', 'FAILURE']:
                    task_record.completed_at = _utcnow()
                await session.commit()
        finally:
            await session.close()

    async def get_existing_task(self, task_name: str, 
                                task_args: dict, celery_task_id: str) -> CeleryTaskExecution:
        """Find the latest task record for the same task name and arguments."""
        args_hash = self.create_args_hash(task_name, task_args)

        session = self.db_client()
        try:
            stmt = (
                select(CeleryTaskExecution)
                .where(
                    CeleryTaskExecution.task_name == task_name,
                    CeleryTaskExecution.task_args_hash == args_hash,
                )
                .order_by(CeleryTaskExecution.execution_id.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        finally:
            await session.close()

    async def update_task_for_retry(self, execution_id: int, celery_task_id: str):
        session = self.db_client()
        try:
            task_record = await session.get(CeleryTaskExecution, execution_id)
            if task_record:
                task_record.celery_task_id = celery_task_id
                task_record.status = 'PENDING'
                task_record.started_at = _utcnow()
                task_record.completed_at = None
                task_record.result = None
                await session.commit()
        finally:
            await session.close()

    async def should_execute_task(self, task_name: str, task_args: dict,
                                  celery_task_id: str, 
                                  task_time_limit: int = 1200) -> tuple[bool, CeleryTaskExecution]:
        """
        Check if task should be executed or return existing result.
        Args:
            task_time_limit: Time limit in seconds after which a stuck task can be re-executed
        Returns (should_execute, existing_task_or_none)
        """
        existing_task = await self.get_existing_task(task_name, task_args, celery_task_id)
        
        if not existing_task:
            return True, None
            
        # Don't execute if task is already completed successfully
        if existing_task.status == 'SUCCESS':
            return False, existing_task
            
        # Re-run if a worker died mid-task (OCR can take minutes and may OOM).
        stuck_after_seconds = min(120, max(90, task_time_limit // 5))
        if existing_task.status in ['PENDING', 'STARTED', 'RETRY']:
            started_at = _as_aware_utc(existing_task.started_at)
            if started_at:
                time_elapsed = (_utcnow() - started_at).total_seconds()
                if time_elapsed > stuck_after_seconds:
                    return True, existing_task
            return False, existing_task
            
        # Re-execute if previous task failed
        return True, existing_task
    
    async def cleanup_old_tasks(self, time_retention: int = 86400) -> int:
        """
        Delete old task records older than time_retention seconds.
        Args:
            time_retention: Time in seconds to retain tasks (default: 86400 = 24 hours)
        Returns:
            Number of deleted records
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=time_retention)
        
        session = self.db_client()
        try:
            stmt = delete(CeleryTaskExecution).where(
                CeleryTaskExecution.created_at < cutoff_time
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        finally:
            await session.close()
