"""
Log Service

Manages job activity logs.
"""

from typing import List, Dict, Any, Optional
from database.models import JobLog
from database import db_session


class LogService:
    """
    Service for logging job activities.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def log_action(
        self,
        job_id: str,
        stage: int,
        action: str,
        user_id: str,
        message: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an action for a job.

        Args:
            job_id: Job identifier
            stage: Stage number (0-4)
            action: Action type (e.g., 'stage_started', 'stage_completed', 'error')
            user_id: User who performed action (or 'system')
            message: Optional message
            extra_data: Optional structured data

        Returns:
            log_id
        """
        log = JobLog(
            job_id=job_id,
            stage=stage,
            action=action,
            message=message,
            user_id=user_id,
            extra_data=extra_data
        )

        db_session.add(log)
        db_session.commit()

        return log.log_id

    def log_stage_started(
        self,
        job_id: str,
        stage: int,
        user_id: str = 'system',
        message: Optional[str] = None
    ) -> int:
        """Log stage start."""
        return self.log_action(
            job_id=job_id,
            stage=stage,
            action='stage_started',
            user_id=user_id,
            message=message or f"Stage {stage} started"
        )

    def log_stage_completed(
        self,
        job_id: str,
        stage: int,
        user_id: str,
        message: Optional[str] = None
    ) -> int:
        """Log stage completion."""
        return self.log_action(
            job_id=job_id,
            stage=stage,
            action='stage_completed',
            user_id=user_id,
            message=message or f"Stage {stage} completed"
        )

    def log_error(
        self,
        job_id: str,
        stage: int,
        error_message: str,
        user_id: str = 'system',
        error_details: Optional[Dict[str, Any]] = None
    ) -> int:
        """Log an error."""
        return self.log_action(
            job_id=job_id,
            stage=stage,
            action='error',
            user_id=user_id,
            message=error_message,
            extra_data=error_details
        )

    def log_user_action(
        self,
        job_id: str,
        stage: int,
        action_name: str,
        user_id: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """Log a user action."""
        return self.log_action(
            job_id=job_id,
            stage=stage,
            action=f"user_action:{action_name}",
            user_id=user_id,
            message=message,
            extra_data=details
        )

    def log_status_change(
        self,
        job_id: str,
        stage: int,
        old_status: str,
        new_status: str,
        user_id: str = 'system'
    ) -> int:
        """Log status change."""
        return self.log_action(
            job_id=job_id,
            stage=stage,
            action='status_changed',
            user_id=user_id,
            message=f"Status changed: {old_status} → {new_status}",
            extra_data={
                'old_status': old_status,
                'new_status': new_status
            }
        )

    def log_warning_added(
        self,
        job_id: str,
        stage: int,
        warning_type: str,
        severity: str,
        user_id: str = 'system'
    ) -> int:
        """Log warning addition."""
        return self.log_action(
            job_id=job_id,
            stage=stage,
            action='warning_added',
            user_id=user_id,
            message=f"Warning added: {warning_type} ({severity})",
            extra_data={
                'warning_type': warning_type,
                'severity': severity
            }
        )

    def log_approved_with_warnings(
        self,
        job_id: str,
        stage: int,
        warning_count: int,
        user_id: str
    ) -> int:
        """Log approval with warnings."""
        return self.log_action(
            job_id=job_id,
            stage=stage,
            action='approved_with_warnings',
            user_id=user_id,
            message=f"Approved WITH {warning_count} warnings",
            extra_data={
                'warning_count': warning_count
            }
        )

    def get_job_logs(
        self,
        job_id: str,
        stage: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[JobLog]:
        """
        Get logs for a job.

        Args:
            job_id: Job identifier
            stage: Optional stage filter
            action: Optional action filter
            limit: Max results
        """
        query = db_session.query(JobLog).filter_by(job_id=job_id)

        if stage is not None:
            query = query.filter_by(stage=stage)

        if action is not None:
            query = query.filter_by(action=action)

        return query.order_by(JobLog.created_at.desc()).limit(limit).all()

    def get_recent_logs(
        self,
        limit: int = 50,
        stage: Optional[int] = None,
        action: Optional[str] = None
    ) -> List[JobLog]:
        """
        Get recent logs across all jobs.

        Args:
            limit: Max results
            stage: Optional stage filter
            action: Optional action filter
        """
        query = db_session.query(JobLog)

        if stage is not None:
            query = query.filter_by(stage=stage)

        if action is not None:
            query = query.filter_by(action=action)

        return query.order_by(JobLog.created_at.desc()).limit(limit).all()

    def get_log_count(self, job_id: str) -> int:
        """Get total log count for a job."""
        from sqlalchemy import func

        return db_session.query(func.count(JobLog.log_id))\
            .filter_by(job_id=job_id)\
            .scalar() or 0

    def get_user_activity(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[JobLog]:
        """
        Get activity for a specific user.

        Args:
            user_id: User identifier
            limit: Max results
        """
        return db_session.query(JobLog)\
            .filter_by(user_id=user_id)\
            .order_by(JobLog.created_at.desc())\
            .limit(limit)\
            .all()

    def delete_logs_for_job(self, job_id: str):
        """Delete all logs for a job."""
        db_session.query(JobLog).filter_by(job_id=job_id).delete()
        db_session.commit()
