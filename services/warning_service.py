"""
Warning Service

Manages job warnings throughout the pipeline.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from database.models import JobWarning
from database import db_session


class WarningService:
    """
    Service for managing job warnings.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def log_info(self, message: str):
        """Log info message."""
        if self.logger:
            self.logger.info(message)

    def add_warning(
        self,
        job_id: str,
        stage: int,
        warning_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add warning to job.

        Args:
            job_id: Job identifier
            stage: Stage number (0-4)
            warning_type: Type of warning (e.g., 'missing_font', 'missing_asset')
            severity: 'critical', 'warning', or 'info'
            message: Human-readable message
            details: Optional additional structured data

        Returns:
            warning_id
        """
        warning = JobWarning(
            job_id=job_id,
            stage=stage,
            warning_type=warning_type,
            severity=severity,
            message=message,
            details=details
        )

        db_session.add(warning)
        db_session.commit()

        self.log_info(f"Warning added to job {job_id}: {warning_type} ({severity}) - {message}")

        return warning.warning_id

    def add_missing_font_warning(
        self,
        job_id: str,
        stage: int,
        font_name: str,
        layer_name: str = None
    ) -> int:
        """Helper to add missing font warning."""
        message = f"Missing font: {font_name}"
        if layer_name:
            message += f" (used in layer '{layer_name}')"

        details = {
            'font_name': font_name,
            'layer_name': layer_name
        }

        return self.add_warning(
            job_id=job_id,
            stage=stage,
            warning_type='missing_font',
            severity='warning',
            message=message,
            details=details
        )

    def add_missing_asset_warning(
        self,
        job_id: str,
        stage: int,
        asset_path: str,
        asset_type: str = 'file'
    ) -> int:
        """Helper to add missing asset warning."""
        message = f"Missing {asset_type}: {asset_path}"

        details = {
            'asset_path': asset_path,
            'asset_type': asset_type
        }

        return self.add_warning(
            job_id=job_id,
            stage=stage,
            warning_type='missing_asset',
            severity='critical',
            message=message,
            details=details
        )

    def add_placeholder_not_matched_warning(
        self,
        job_id: str,
        stage: int,
        placeholder_name: str,
        placeholder_type: str = 'text'
    ) -> int:
        """Helper to add placeholder not matched warning."""
        message = f"Placeholder not matched: {placeholder_name} ({placeholder_type})"

        details = {
            'placeholder_name': placeholder_name,
            'placeholder_type': placeholder_type
        }

        return self.add_warning(
            job_id=job_id,
            stage=stage,
            warning_type='placeholder_not_matched',
            severity='warning',
            message=message,
            details=details
        )

    def get_job_warnings(
        self,
        job_id: str,
        resolved: Optional[bool] = None,
        severity: Optional[str] = None
    ) -> List[JobWarning]:
        """
        Get all warnings for a job.

        Args:
            job_id: Job identifier
            resolved: If True, only resolved warnings. If False, only unresolved. If None, all.
            severity: Optional severity filter ('critical', 'warning', 'info')
        """
        query = db_session.query(JobWarning).filter_by(job_id=job_id)

        if resolved is not None:
            query = query.filter_by(resolved=resolved)

        if severity is not None:
            query = query.filter_by(severity=severity)

        return query.order_by(JobWarning.created_at).all()

    def get_warning(self, warning_id: int) -> Optional[JobWarning]:
        """Get warning by ID."""
        return db_session.query(JobWarning).filter_by(warning_id=warning_id).first()

    def resolve_warning(
        self,
        warning_id: int,
        user_id: str,
        resolution_notes: Optional[str] = None
    ):
        """Mark warning as resolved."""
        warning = self.get_warning(warning_id)

        if not warning:
            raise ValueError(f"Warning not found: {warning_id}")

        warning.resolved = True
        warning.resolved_at = datetime.utcnow()
        warning.resolved_by = user_id
        warning.resolution_notes = resolution_notes

        db_session.commit()

        self.log_info(f"Warning {warning_id} resolved by {user_id}")

    def resolve_all_warnings(
        self,
        job_id: str,
        user_id: str,
        resolution_notes: Optional[str] = None
    ):
        """Resolve all unresolved warnings for a job."""
        warnings = self.get_job_warnings(job_id, resolved=False)

        for warning in warnings:
            warning.resolved = True
            warning.resolved_at = datetime.utcnow()
            warning.resolved_by = user_id
            warning.resolution_notes = resolution_notes

        db_session.commit()

        self.log_info(f"All warnings resolved for job {job_id} by {user_id}")

    def get_warning_count(
        self,
        job_id: str,
        resolved: bool = False,
        severity: Optional[str] = None
    ) -> int:
        """Get count of warnings for job."""
        from sqlalchemy import func

        query = db_session.query(func.count(JobWarning.warning_id))\
            .filter_by(job_id=job_id, resolved=resolved)

        if severity is not None:
            query = query.filter_by(severity=severity)

        return query.scalar() or 0

    def get_critical_warning_count(self, job_id: str) -> int:
        """Get count of unresolved critical warnings."""
        return self.get_warning_count(job_id, resolved=False, severity='critical')

    def has_unresolved_critical_warnings(self, job_id: str) -> bool:
        """Check if job has any unresolved critical warnings."""
        return self.get_critical_warning_count(job_id) > 0

    def delete_warning(self, warning_id: int):
        """Delete a warning."""
        warning = self.get_warning(warning_id)

        if not warning:
            raise ValueError(f"Warning not found: {warning_id}")

        db_session.delete(warning)
        db_session.commit()

        self.log_info(f"Warning {warning_id} deleted")
