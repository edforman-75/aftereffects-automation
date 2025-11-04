"""
Job Routes Blueprint

Handles job management and dashboard statistics.
"""

from flask import Blueprint, request, jsonify

# Import services from web_app (they're initialized there)
from config.container import container


# Create blueprint
job_bp = Blueprint('job', __name__)


# Get service instances
def get_services():
    """Get service instances (they're module-level in web_app.py)."""
    from web_app import job_service, warning_service, log_service
    return job_service, warning_service, log_service


@job_bp.route('/api/job/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get detailed job status."""
    try:
        job_service, warning_service, log_service = get_services()

        job = job_service.get_job(job_id)

        if not job:
            return jsonify({
                'success': False,
                'error': f'Job not found: {job_id}'
            }), 404

        # Get warnings
        warnings = warning_service.get_job_warnings(job_id, resolved=False)
        warning_count = len(warnings)
        critical_count = warning_service.get_critical_warning_count(job_id)

        # Get recent logs
        logs = log_service.get_job_logs(job_id, limit=20)

        return jsonify({
            'success': True,
            'job': {
                'job_id': job.job_id,
                'batch_id': job.batch_id,
                'current_stage': job.current_stage,
                'status': job.status,
                'priority': job.priority,
                'client_name': job.client_name,
                'project_name': job.project_name,
                'psd_path': job.psd_path,
                'aepx_path': job.aepx_path,
                'output_name': job.output_name,
                'final_aep_path': job.final_aep_path,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'updated_at': job.updated_at.isoformat() if job.updated_at else None,
                'stage0_completed_at': job.stage0_completed_at.isoformat() if job.stage0_completed_at else None,
                'stage1_completed_at': job.stage1_completed_at.isoformat() if job.stage1_completed_at else None,
                'stage2_completed_at': job.stage2_completed_at.isoformat() if job.stage2_completed_at else None,
                'stage3_completed_at': job.stage3_completed_at.isoformat() if job.stage3_completed_at else None,
                'stage4_completed_at': job.stage4_completed_at.isoformat() if job.stage4_completed_at else None
            },
            'stage1_results': job.stage1_results,
            'stage2_approved_matches': job.stage2_approved_matches,
            'warnings': {
                'total': warning_count,
                'critical': critical_count,
                'list': [{
                    'warning_id': w.warning_id,
                    'type': w.warning_type,
                    'severity': w.severity,
                    'message': w.message,
                    'stage': w.stage,
                    'created_at': w.created_at.isoformat() if w.created_at else None
                } for w in warnings]
            },
            'recent_logs': [{
                'log_id': log.log_id,
                'stage': log.stage,
                'action': log.action,
                'message': log.message,
                'user_id': log.user_id,
                'created_at': log.created_at.isoformat() if log.created_at else None
            } for log in logs]
        })

    except Exception as e:
        container.main_logger.error(f"Error getting job status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get production dashboard statistics."""
    try:
        job_service, _, _ = get_services()

        # Get summary stats
        summary = job_service.get_summary_stats()

        # Get counts by stage
        stage_counts = job_service.get_job_counts_by_stage()

        # Get counts by status
        status_counts = job_service.get_job_counts_by_status()

        # Get recent batches
        recent_batches = job_service.get_all_batches(limit=10)

        return jsonify({
            'success': True,
            'summary': summary,
            'stage_counts': stage_counts,
            'status_counts': status_counts,
            'recent_batches': [{
                'batch_id': b.batch_id,
                'status': b.status,
                'total_jobs': b.total_jobs,
                'valid_jobs': b.valid_jobs,
                'uploaded_at': b.uploaded_at.isoformat() if b.uploaded_at else None,
                'uploaded_by': b.uploaded_by
            } for b in recent_batches]
        })

    except Exception as e:
        container.main_logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/api/jobs/stage/<int:stage>', methods=['GET'])
def get_jobs_by_stage(stage: int):
    """Get all jobs in a specific stage."""
    try:
        job_service, _, _ = get_services()

        batch_id = request.args.get('batch_id')
        limit = int(request.args.get('limit', 100))

        jobs = job_service.get_jobs_for_stage(stage, batch_id=batch_id, limit=limit)

        return jsonify({
            'success': True,
            'stage': stage,
            'count': len(jobs),
            'jobs': [{
                'job_id': job.job_id,
                'batch_id': job.batch_id,
                'status': job.status,
                'priority': job.priority,
                'client_name': job.client_name,
                'project_name': job.project_name,
                'output_name': job.output_name,
                'created_at': job.created_at.isoformat() if job.created_at else None
            } for job in jobs]
        })

    except Exception as e:
        container.main_logger.error(f"Error getting jobs by stage: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get jobs with optional filtering."""
    try:
        from database import db_session
        from database.models import Job

        archived = request.args.get('archived', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 1000))

        query = db_session.query(Job)

        if archived:
            query = query.filter(Job.archived == True)
        else:
            query = query.filter((Job.archived == False) | (Job.archived == None))

        query = query.order_by(Job.created_at.desc()).limit(limit)
        jobs = query.all()

        return jsonify({
            'success': True,
            'count': len(jobs),
            'jobs': [{
                'job_id': job.job_id,
                'batch_id': job.batch_id,
                'current_stage': job.current_stage,
                'status': job.status,
                'priority': job.priority,
                'client_name': job.client_name,
                'project_name': job.project_name,
                'output_name': job.output_name,
                'psd_path': job.psd_path,
                'aepx_path': job.aepx_path,
                'final_aep_path': job.final_aep_path,
                'notes': job.notes,
                'archived': job.archived,
                'archived_at': job.archived_at.isoformat() if job.archived_at else None,
                'archived_by': job.archived_by,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'stage6_completed_at': job.stage6_completed_at.isoformat() if job.stage6_completed_at else None
            } for job in jobs]
        })

    except Exception as e:
        container.main_logger.error(f"Error getting jobs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_details(job_id: str):
    """Get detailed information for a specific job."""
    try:
        from database import db_session
        from database.models import Job

        job = db_session.query(Job).filter(Job.job_id == job_id).first()

        if not job:
            return jsonify({
                'success': False,
                'error': f'Job not found: {job_id}'
            }), 404

        return jsonify({
            'success': True,
            'job_id': job.job_id,
            'batch_id': job.batch_id,
            'current_stage': job.current_stage,
            'status': job.status,
            'priority': job.priority,
            'client_name': job.client_name,
            'project_name': job.project_name,
            'output_name': job.output_name,
            'psd_path': job.psd_path,
            'aepx_path': job.aepx_path,
            'final_aep_path': job.final_aep_path,
            'notes': job.notes,
            'archived': job.archived,
            'archived_at': job.archived_at.isoformat() if job.archived_at else None,
            'archived_by': job.archived_by,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'updated_at': job.updated_at.isoformat() if job.updated_at else None,
            'stage6_completed_at': job.stage6_completed_at.isoformat() if job.stage6_completed_at else None,
            'stage6_completed_by': job.stage6_completed_by
        })

    except Exception as e:
        container.main_logger.error(f"Error getting job details: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/api/jobs/<job_id>/archive', methods=['POST'])
def archive_job(job_id: str):
    """Archive a completed job."""
    try:
        from database import db_session
        from database.models import Job
        from datetime import datetime

        data = request.get_json() or {}
        user_id = data.get('user_id', 'system')

        job = db_session.query(Job).filter(Job.job_id == job_id).first()

        if not job:
            return jsonify({
                'success': False,
                'error': f'Job not found: {job_id}'
            }), 404

        # Verify job is in Stage 6 and approved
        if job.current_stage != 6:
            return jsonify({
                'success': False,
                'error': f'Job must be in Stage 6 to archive (currently in Stage {job.current_stage})'
            }), 400

        if not job.stage6_approved:
            return jsonify({
                'success': False,
                'error': 'Job must be approved before archiving'
            }), 400

        # Archive the job
        job.archived = True
        job.archived_at = datetime.utcnow()
        job.archived_by = user_id
        job.status = 'completed'

        db_session.commit()

        container.main_logger.info(f"Job {job_id} archived by {user_id}")

        return jsonify({
            'success': True,
            'message': f'Job {job_id} archived successfully',
            'archived_at': job.archived_at.isoformat()
        })

    except Exception as e:
        db_session.rollback()
        container.main_logger.error(f"Error archiving job: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/api/jobs/<job_id>/unarchive', methods=['POST'])
def unarchive_job(job_id: str):
    """Unarchive a job and return it to active status."""
    try:
        from database import db_session
        from database.models import Job

        job = db_session.query(Job).filter(Job.job_id == job_id).first()

        if not job:
            return jsonify({
                'success': False,
                'error': f'Job not found: {job_id}'
            }), 404

        if not job.archived:
            return jsonify({
                'success': False,
                'error': 'Job is not archived'
            }), 400

        # Unarchive the job
        job.archived = False
        job.archived_at = None
        job.archived_by = None
        job.status = 'awaiting_approval'  # Return to Stage 6 approval state

        db_session.commit()

        container.main_logger.info(f"Job {job_id} unarchived")

        return jsonify({
            'success': True,
            'message': f'Job {job_id} unarchived successfully'
        })

    except Exception as e:
        db_session.rollback()
        container.main_logger.error(f"Error unarchiving job: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/api/jobs/cleanup', methods=['POST'])
def cleanup_jobs():
    """
    Delete all non-archived jobs from the database.

    This is a utility endpoint for debugging and testing.
    Use with caution as it will delete all active jobs!

    Request JSON body:
        {
            "confirm": "DELETE_ALL_JOBS",  # Required confirmation
            "include_archived": false      # Optional: also delete archived jobs
        }
    """
    try:
        from database import db_session
        from database.models import Job, JobWarning, JobLog, JobAsset, Batch

        data = request.get_json() or {}
        confirmation = data.get('confirm', '')
        include_archived = data.get('include_archived', False)

        # Require confirmation
        if confirmation != 'DELETE_ALL_JOBS':
            return jsonify({
                'success': False,
                'error': 'Confirmation required. Set "confirm": "DELETE_ALL_JOBS" in request body.'
            }), 400

        container.main_logger.warning("=" * 80)
        container.main_logger.warning("CLEANUP JOBS ENDPOINT CALLED")
        container.main_logger.warning("This will delete jobs from the database!")
        container.main_logger.warning("=" * 80)

        # Query jobs to delete
        query = db_session.query(Job)
        if not include_archived:
            query = query.filter((Job.archived == False) | (Job.archived == None))

        jobs_to_delete = query.all()
        job_count = len(jobs_to_delete)

        container.main_logger.warning(f"Found {job_count} jobs to delete")

        # Delete jobs (cascade will delete related warnings, logs, assets)
        for job in jobs_to_delete:
            container.main_logger.info(f"Deleting job: {job.job_id}")
            db_session.delete(job)

        # Also delete batches if requested
        if include_archived:
            batches = db_session.query(Batch).all()
            batch_count = len(batches)
            container.main_logger.warning(f"Deleting {batch_count} batches")
            for batch in batches:
                db_session.delete(batch)

        db_session.commit()

        container.main_logger.warning(f"Successfully deleted {job_count} jobs")
        container.main_logger.warning("=" * 80)

        return jsonify({
            'success': True,
            'message': f'Deleted {job_count} jobs from database',
            'jobs_deleted': job_count
        })

    except Exception as e:
        db_session.rollback()
        container.main_logger.error(f"Error cleaning up jobs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
