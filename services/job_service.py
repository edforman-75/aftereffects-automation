"""
Job Service

Manages job CRUD operations, status transitions, and queries.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from database.models import Job, JobWarning, JobLog, JobAsset, Batch
from database import db_session
from services.folder_manager import folder_manager


class JobService:
    """
    Central service for job management.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def log_info(self, message: str):
        """Log info message."""
        if self.logger:
            self.logger.info(message)

    def log_error(self, message: str):
        """Log error message."""
        if self.logger:
            self.logger.error(message)

    def create_batch_from_csv(
        self,
        batch_id: str,
        csv_path: str,
        csv_filename: str,
        jobs: List[Dict[str, Any]],
        validation_result: Dict[str, Any],
        user_id: str
    ) -> str:
        """
        Create batch and jobs from validated CSV.

        Args:
            batch_id: Unique batch identifier
            csv_path: Path to CSV file
            csv_filename: Original filename
            jobs: List of validated job dicts
            validation_result: Full validation results
            user_id: User who uploaded batch

        Returns:
            batch_id
        """
        self.log_info(f"Creating batch {batch_id} with {len(jobs)} jobs")

        # Create batch record
        batch = Batch(
            batch_id=batch_id,
            csv_filename=csv_filename,
            csv_path=csv_path,
            total_jobs=validation_result['total_jobs'],
            valid_jobs=validation_result['valid_jobs'],
            invalid_jobs=validation_result['invalid_jobs'],
            status='validated',
            uploaded_by=user_id,
            validated_at=datetime.utcnow(),
            validation_errors=validation_result.get('errors'),
            validation_warnings=validation_result.get('warnings')
        )
        db_session.add(batch)

        # Set up batch folder if hierarchical folders are enabled
        if len(jobs) > 0:
            first_client = jobs[0].get('client_name', 'default_client')
            try:
                folder_manager.setup_batch_folder(first_client, batch_id)
                self.log_info(f"Created folder structure for batch {batch_id}")
            except Exception as e:
                self.log_error(f"Failed to create batch folder: {str(e)}")

        # Create job records
        for job_data in jobs:
            job = Job(
                job_id=job_data['job_id'],
                psd_path=job_data['psd_path'],
                aepx_path=job_data['aepx_path'],
                output_name=job_data['output_name'],
                client_name=job_data.get('client_name'),
                project_name=job_data.get('project_name'),
                priority=job_data.get('priority', 'medium'),
                notes=job_data.get('notes'),
                batch_id=batch_id,
                current_stage=0,
                status='pending',
                stage0_completed_at=datetime.utcnow(),
                stage0_completed_by=user_id
            )
            db_session.add(job)

            # Set up job folder structure if hierarchical folders are enabled
            try:
                client_name = job_data.get('client_name', 'default_client')
                folder_manager.setup_job_folders(client_name, batch_id, job_data['job_id'])
                self.log_info(f"Created folder structure for job {job_data['job_id']}")
            except Exception as e:
                self.log_error(f"Failed to create job folder for {job_data['job_id']}: {str(e)}")

        db_session.commit()

        print(f"✅ Created batch {batch_id} with {len(jobs)} jobs")
        self.log_info(f"Batch {batch_id} created successfully")

        return batch_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return db_session.query(Job).filter_by(job_id=job_id).first()

    def get_job_folders(self, job: Job):
        """
        Get folder paths for a job.

        Args:
            job: Job model instance

        Returns:
            FolderPaths object with all paths for the job
        """
        client_name = job.client_name or 'default_client'
        return folder_manager.get_job_paths(client_name, job.batch_id, job.job_id)

    def get_jobs_for_stage(
        self,
        stage: int,
        batch_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Job]:
        """
        Get jobs currently in specified stage.

        Args:
            stage: Stage number (0-4)
            batch_id: Optional batch filter
            limit: Max results
        """
        from sqlalchemy import case as sql_case

        query = db_session.query(Job).filter_by(current_stage=stage)

        if batch_id:
            query = query.filter_by(batch_id=batch_id)

        # Order by priority then created time
        query = query.order_by(
            sql_case(
                (Job.priority == 'high', 1),
                (Job.priority == 'medium', 2),
                (Job.priority == 'low', 3),
                else_=2
            ),
            Job.created_at
        )

        return query.limit(limit).all()

    def get_job_counts_by_stage(self) -> Dict[int, int]:
        """
        Get count of jobs in each stage.

        Returns:
            {0: 5, 1: 10, 2: 3, 3: 7, 4: 2}
        """
        from sqlalchemy import func

        counts = db_session.query(
            Job.current_stage,
            func.count(Job.job_id)
        ).group_by(Job.current_stage).all()

        return {stage: count for stage, count in counts}

    def get_job_counts_by_status(self) -> Dict[str, int]:
        """
        Get count of jobs by status.

        Returns:
            {'pending': 5, 'processing': 10, 'completed': 20, ...}
        """
        from sqlalchemy import func

        counts = db_session.query(
            Job.status,
            func.count(Job.job_id)
        ).group_by(Job.status).all()

        return {status: count for status, count in counts}

    def update_job_status(
        self,
        job_id: str,
        status: str,
        current_stage: Optional[int] = None
    ):
        """Update job status and optionally stage."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.status = status
        if current_stage is not None:
            job.current_stage = current_stage
        job.updated_at = datetime.utcnow()

        db_session.commit()

        self.log_info(f"Job {job_id}: Status updated to {status}, stage={current_stage}")

    def start_stage(
        self,
        job_id: str,
        stage: int,
        user_id: str = 'system'
    ):
        """
        Mark stage as started.

        Updates stage{N}_started_at field.
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Update stage start field
        setattr(job, f'stage{stage}_started_at', datetime.utcnow())
        job.current_stage = stage
        job.updated_at = datetime.utcnow()

        db_session.commit()

        self.log_info(f"Job {job_id}: Stage {stage} started by {user_id}")

    def complete_stage(
        self,
        job_id: str,
        stage: int,
        user_id: str
    ):
        """
        Mark stage as completed.

        Updates stage{N}_completed_at and stage{N}_completed_by fields.
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Update stage completion fields
        setattr(job, f'stage{stage}_completed_at', datetime.utcnow())
        setattr(job, f'stage{stage}_completed_by', user_id)

        job.updated_at = datetime.utcnow()

        db_session.commit()

        print(f"✅ Job {job_id}: Stage {stage} completed by {user_id}")
        self.log_info(f"Job {job_id}: Stage {stage} completed by {user_id}")

    def store_stage1_results(
        self,
        job_id: str,
        psd_result: Dict[str, Any],
        aepx_result: Dict[str, Any],
        match_result: Dict[str, Any]
    ):
        """Store results from Stage 1 processing."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.stage1_results = {
            'psd': psd_result,
            'aepx': aepx_result,
            'matches': match_result,
            'processed_at': datetime.utcnow().isoformat()
        }

        db_session.commit()

        self.log_info(f"Job {job_id}: Stage 1 results stored")

    def get_stage1_results(self, job_id: str) -> Dict[str, Any]:
        """Get Stage 1 processing results."""
        job = self.get_job(job_id)
        if not job or not job.stage1_results:
            return {}

        return job.stage1_results

    def store_approved_matches(
        self,
        job_id: str,
        matches: Dict[str, Any]
    ):
        """Store Stage 2 approved matches."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.stage2_approved_matches = matches

        db_session.commit()

        self.log_info(f"Job {job_id}: Stage 2 matches approved and stored")

    def get_approved_matches(self, job_id: str) -> Dict[str, Any]:
        """Get Stage 2 approved matches."""
        job = self.get_job(job_id)
        if not job or not job.stage2_approved_matches:
            return {}

        return job.stage2_approved_matches

    def store_stage3_adjustments(
        self,
        job_id: str,
        adjustments: Dict[str, Any]
    ):
        """Store Stage 3 adjustments."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.stage3_adjustments = adjustments

        db_session.commit()

        self.log_info(f"Job {job_id}: Stage 3 adjustments stored")

    def approve_with_warnings(
        self,
        job_id: str,
        user_id: str
    ):
        """Mark job as approved with warnings at Stage 3."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.stage3_approved_with_warnings = True
        job.updated_at = datetime.utcnow()

        db_session.commit()

        self.log_info(f"Job {job_id}: Approved WITH WARNINGS by {user_id}")

    def store_final_aep_path(
        self,
        job_id: str,
        aep_path: str
    ):
        """Store final AEP output path."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.final_aep_path = aep_path
        job.updated_at = datetime.utcnow()

        db_session.commit()

        self.log_info(f"Job {job_id}: Final AEP path stored: {aep_path}")

    def get_batch(self, batch_id: str) -> Optional[Batch]:
        """Get batch by ID."""
        return db_session.query(Batch).filter_by(batch_id=batch_id).first()

    def get_batch_jobs(self, batch_id: str) -> List[Job]:
        """Get all jobs for a batch."""
        return db_session.query(Job).filter_by(batch_id=batch_id).all()

    def update_batch_status(self, batch_id: str, status: str):
        """Update batch status."""
        batch = self.get_batch(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        batch.status = status

        if status == 'complete':
            batch.completed_at = datetime.utcnow()

        db_session.commit()

        self.log_info(f"Batch {batch_id}: Status updated to {status}")

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        from sqlalchemy import func

        total = db_session.query(func.count(Job.job_id)).scalar() or 0
        completed = db_session.query(func.count(Job.job_id)).filter_by(status='completed').scalar() or 0
        failed = db_session.query(func.count(Job.job_id)).filter_by(status='failed').scalar() or 0

        # Calculate average completion time for completed jobs
        avg_time = self._calculate_avg_completion_time()

        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'in_progress': total - completed - failed,
            'avg_completion_time': avg_time
        }

    def _calculate_avg_completion_time(self) -> str:
        """Calculate average time from creation to completion."""
        completed_jobs = db_session.query(Job).filter_by(status='completed').all()

        if not completed_jobs:
            return "N/A"

        total_seconds = 0
        for job in completed_jobs:
            if job.stage4_completed_at and job.created_at:
                delta = job.stage4_completed_at - job.created_at
                total_seconds += delta.total_seconds()

        if total_seconds == 0:
            return "N/A"

        avg_seconds = total_seconds / len(completed_jobs)

        # Format as human-readable
        hours = int(avg_seconds // 3600)
        minutes = int((avg_seconds % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def get_all_batches(self, limit: int = 50) -> List[Batch]:
        """Get all batches, most recent first."""
        return db_session.query(Batch).order_by(Batch.uploaded_at.desc()).limit(limit).all()

    def delete_job(self, job_id: str):
        """Delete a job (cascades to warnings, logs, assets)."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        db_session.delete(job)
        db_session.commit()

        self.log_info(f"Job {job_id}: Deleted")
