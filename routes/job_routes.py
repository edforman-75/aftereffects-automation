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
