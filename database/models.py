"""
Database Models for Production Batch Processing System

Tables:
- jobs: Main job table tracking all stages
- job_warnings: Warnings generated during processing
- job_logs: Activity logs for audit trail
- job_assets: Generated files and assets
- batches: Batch metadata and status
"""

from sqlalchemy import (
    Column, String, Integer, BigInteger, Text, Boolean,
    DateTime, JSON, ForeignKey, Index, Enum, case
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class PriorityEnum(enum.Enum):
    """Job priority levels."""
    high = 'high'
    medium = 'medium'
    low = 'low'


class JobStatusEnum(enum.Enum):
    """Job status values."""
    pending = 'pending'
    processing = 'processing'
    awaiting_review = 'awaiting_review'
    awaiting_approval = 'awaiting_approval'
    ready_for_validation = 'ready_for_validation'
    validation_failed = 'validation_failed'
    completed = 'completed'
    failed = 'failed'
    on_hold = 'on_hold'


class BatchStatusEnum(enum.Enum):
    """Batch status values."""
    validating = 'validating'
    validated = 'validated'
    processing = 'processing'
    partially_complete = 'partially_complete'
    complete = 'complete'
    failed = 'failed'


class SeverityEnum(enum.Enum):
    """Warning severity levels."""
    critical = 'critical'
    warning = 'warning'
    info = 'info'


class Job(Base):
    """
    Main jobs table tracking all processing stages.
    """
    __tablename__ = 'jobs'

    # Primary Key
    job_id = Column(String(50), primary_key=True)

    # Input Files
    psd_path = Column(Text, nullable=False)
    aepx_path = Column(Text, nullable=False)
    output_name = Column(String(255), nullable=False)

    # Metadata
    client_name = Column(String(100))
    project_name = Column(String(100))
    priority = Column(String(20), default='medium')
    notes = Column(Text)
    batch_id = Column(String(50), ForeignKey('batches.batch_id'))

    # Current Status
    current_stage = Column(Integer, default=0)
    status = Column(String(50), default='pending')

    # Archive Status (for completed jobs)
    archived = Column(Boolean, default=False)
    archived_at = Column(DateTime)
    archived_by = Column(String(100))

    # Stage 0: Validation
    stage0_completed_at = Column(DateTime)
    stage0_completed_by = Column(String(100))

    # Stage 1: Ingestion (Automated)
    stage1_started_at = Column(DateTime)
    stage1_completed_at = Column(DateTime)
    stage1_completed_by = Column(String(100), default='system')

    # Stage 2: Matching (Human)
    stage2_started_at = Column(DateTime)
    stage2_completed_at = Column(DateTime)
    stage2_completed_by = Column(String(100))

    # Stage 3: Automatic Validation
    stage3_started_at = Column(DateTime)
    stage3_completed_at = Column(DateTime)
    stage3_completed_by = Column(String(100), default='system')
    stage3_validation_results = Column(JSON)  # Validation report

    # Stage 4: Validation Review (conditional - only if critical issues)
    stage4_started_at = Column(DateTime)
    stage4_completed_at = Column(DateTime)
    stage4_completed_by = Column(String(100))
    stage4_override = Column(Boolean, default=False)
    stage4_override_reason = Column(Text)  # Override justification

    # Stage 5: ExtendScript Generation
    stage5_started_at = Column(DateTime)
    stage5_completed_at = Column(DateTime)
    stage5_completed_by = Column(String(100), default='system')
    stage5_extendscript = Column(Text)  # Generated .jsx script

    # Stage 6: Preview & Approval
    stage6_started_at = Column(DateTime)
    stage6_completed_at = Column(DateTime)
    stage6_completed_by = Column(String(100))
    stage6_preview_video_path = Column(String(500))  # Path to preview video render
    stage6_psd_preview_path = Column(String(500))  # Path to PSD preview image
    stage6_render_frame_path = Column(String(500))  # Path to rendered frame image for display
    stage6_approved = Column(Boolean, default=False)  # User approval status
    stage6_approval_notes = Column(Text)  # User feedback/notes
    stage6_downloaded_at = Column(DateTime)  # When user downloaded final files

    # Audit Trail
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Output
    final_aep_path = Column(Text)

    # Processing Data (JSON)
    stage1_results = Column(JSON)  # PSD/AEPX extraction results
    stage2_approved_matches = Column(JSON)  # Approved layer matches

    # Relationships
    batch = relationship("Batch", back_populates="jobs")
    warnings = relationship("JobWarning", back_populates="job", cascade="all, delete-orphan")
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")
    assets = relationship("JobAsset", back_populates="job", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_stage', 'current_stage'),
        Index('idx_client', 'client_name'),
        Index('idx_priority', 'priority'),
        Index('idx_batch', 'batch_id'),
        Index('idx_created', 'created_at'),
        Index('idx_archived', 'archived'),
    )

    def __repr__(self):
        return f"<Job(job_id='{self.job_id}', status='{self.status}', stage={self.current_stage})>"


class JobWarning(Base):
    """
    Job warnings table for tracking issues and warnings.
    """
    __tablename__ = 'job_warnings'

    warning_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey('jobs.job_id', ondelete='CASCADE'), nullable=False)

    # Warning Details
    stage = Column(Integer, nullable=False)  # Which stage detected this warning (0-4)
    warning_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON)  # Additional structured data about the warning

    # Resolution
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(100))
    resolution_notes = Column(Text)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="warnings")

    # Indexes
    __table_args__ = (
        Index('idx_job_warnings', 'job_id'),
        Index('idx_stage_warnings', 'stage'),
        Index('idx_severity', 'severity'),
        Index('idx_resolved', 'resolved'),
        Index('idx_warning_type', 'warning_type'),
    )

    def __repr__(self):
        return f"<JobWarning(warning_id={self.warning_id}, job_id='{self.job_id}', type='{self.warning_type}')>"


class JobLog(Base):
    """
    Job activity logs for complete audit trail.
    """
    __tablename__ = 'job_logs'

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey('jobs.job_id', ondelete='CASCADE'), nullable=False)

    # Log Details
    stage = Column(Integer, nullable=False)  # Which stage (0-4)
    action = Column(String(100), nullable=False)
    message = Column(Text)
    user_id = Column(String(100))  # User who performed action (or 'system')
    extra_data = Column(JSON)  # Additional structured data

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="logs")

    # Indexes
    __table_args__ = (
        Index('idx_job_logs', 'job_id'),
        Index('idx_stage_logs', 'stage'),
        Index('idx_user', 'user_id'),
        Index('idx_action', 'action'),
        Index('idx_created_logs', 'created_at'),
    )

    def __repr__(self):
        return f"<JobLog(log_id={self.log_id}, job_id='{self.job_id}', action='{self.action}')>"


class JobAsset(Base):
    """
    Job assets table for tracking generated files.
    """
    __tablename__ = 'job_assets'

    asset_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey('jobs.job_id', ondelete='CASCADE'), nullable=False)

    # Asset Details
    asset_type = Column(String(50), nullable=False)
    asset_path = Column(Text, nullable=False)
    asset_name = Column(String(255))
    file_size = Column(BigInteger)  # Size in bytes
    mime_type = Column(String(100))

    # Metadata
    stage = Column(Integer)  # Which stage generated this asset
    extra_metadata = Column(JSON)  # Additional info (dimensions, duration, etc.)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="assets")

    # Indexes
    __table_args__ = (
        Index('idx_job_assets', 'job_id'),
        Index('idx_asset_type', 'asset_type'),
        Index('idx_stage_assets', 'stage'),
    )

    def __repr__(self):
        return f"<JobAsset(asset_id={self.asset_id}, job_id='{self.job_id}', type='{self.asset_type}')>"


class Batch(Base):
    """
    Batches table for tracking CSV batch uploads.
    """
    __tablename__ = 'batches'

    batch_id = Column(String(50), primary_key=True)

    # Batch Info
    csv_filename = Column(String(255), nullable=False)
    csv_path = Column(Text, nullable=False)
    total_jobs = Column(Integer, nullable=False)
    valid_jobs = Column(Integer, nullable=False)
    invalid_jobs = Column(Integer, nullable=False)

    # Status
    status = Column(String(50), default='validating')

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime)
    completed_at = Column(DateTime)

    # User
    uploaded_by = Column(String(100), nullable=False)

    # Validation Results
    validation_errors = Column(JSON)
    validation_warnings = Column(JSON)

    # Relationships
    jobs = relationship("Job", back_populates="batch")

    # Indexes
    __table_args__ = (
        Index('idx_status_batch', 'status'),
        Index('idx_uploaded_by', 'uploaded_by'),
        Index('idx_uploaded_at', 'uploaded_at'),
    )

    def __repr__(self):
        return f"<Batch(batch_id='{self.batch_id}', status='{self.status}', jobs={self.total_jobs})>"
