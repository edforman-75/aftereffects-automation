"""
Stage 6 Routes Blueprint

Handles Stage 6 Preview & Approval - generate previews and get user approval.
"""

from datetime import datetime
from typing import Tuple
from flask import Blueprint, request, jsonify, render_template, Response, send_file
from pathlib import Path

# Import services
from config.container import container
from database import db_session
from database.models import Job
from services.stage6_preview_service import Stage6PreviewService


# Create blueprint
stage6_bp = Blueprint('stage6', __name__)


@stage6_bp.route('/preview/<job_id>')
def preview_job_page(job_id: str) -> str | Tuple[str, int]:
    """
    Display Stage 6 preview and download page for a job.

    Args:
        job_id: Unique identifier for the job

    Returns:
        Rendered HTML template or error message with status code
    """
    try:
        container.main_logger.info(f"Loading Stage 6 preview page for job {job_id}")
        return render_template('stage6_preview.html', job_id=job_id)
    except Exception as e:
        container.main_logger.error(f"Error loading preview page: {e}", exc_info=True)
        return f"Error loading preview page: {e}", 500


@stage6_bp.route('/api/job/<job_id>/preview-data', methods=['GET'])
def get_preview_data(job_id: str) -> Tuple[Response, int]:
    """
    Get preview data for Stage 6 display.

    Returns job details, ExtendScript preview, and match statistics.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with preview data, plus HTTP status code
    """
    try:
        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Get ExtendScript
            extendscript = job.stage5_extendscript or ''

            # Get approved matches
            approved_matches_data = job.stage2_approved_matches
            if isinstance(approved_matches_data, str):
                import json
                approved_matches_data = json.loads(approved_matches_data)

            approved_matches = approved_matches_data.get('approved_matches', []) if approved_matches_data else []

            # Get validation results
            validation_results = job.stage3_validation_results
            if isinstance(validation_results, str):
                import json
                validation_results = json.loads(validation_results)

            # Build response
            response_data = {
                'success': True,
                'job_id': job_id,
                'job_details': {
                    'output_name': job.output_name,
                    'client_name': job.client_name,
                    'project_name': job.project_name,
                    'psd_path': job.psd_path,
                    'aepx_path': job.aepx_path,
                    'current_stage': job.current_stage,
                    'status': job.status,
                    'created_at': job.created_at.isoformat() if job.created_at else None
                },
                'extendscript': {
                    'has_script': bool(extendscript),
                    'script_length': len(extendscript),
                    'script_preview': extendscript[:1000] if extendscript else '',
                    'full_script': extendscript,
                    'generated_at': job.stage5_completed_at.isoformat() if job.stage5_completed_at else None
                },
                'statistics': {
                    'matches_count': len(approved_matches),
                    'text_matches': len([m for m in approved_matches if m.get('type') == 'text']),
                    'image_matches': len([m for m in approved_matches if m.get('type') == 'image']),
                    'validation_passed': not validation_results.get('critical_issues', []) if validation_results else True,
                    'validation_warnings': len(validation_results.get('warnings', [])) if validation_results else 0,
                    'override_used': job.stage4_override or False
                },
                'stages_completed': {
                    'stage1': job.stage1_completed_at.isoformat() if job.stage1_completed_at else None,
                    'stage2': job.stage2_completed_at.isoformat() if job.stage2_completed_at else None,
                    'stage3': job.stage3_completed_at.isoformat() if job.stage3_completed_at else None,
                    'stage4': job.stage4_completed_at.isoformat() if job.stage4_completed_at else None,
                    'stage5': job.stage5_completed_at.isoformat() if job.stage5_completed_at else None
                }
            }

            return jsonify(response_data)

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error getting preview data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage6_bp.route('/api/job/<job_id>/complete', methods=['POST'])
def complete_job(job_id: str) -> Tuple[Response, int]:
    """
    Mark job as complete after user reviews and downloads.

    Transitions job to completed status and logs completion.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with completion status, plus HTTP status code

    Request JSON body:
        {
            "user_id": "john_doe",
            "next_action": "next_job" | "dashboard"  # Optional
        }
    """
    try:
        data = request.json or {}
        user_id = data.get('user_id', 'anonymous')
        next_action = data.get('next_action', 'dashboard')

        container.main_logger.info(f"Job {job_id}: Completing job by {user_id}")

        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Mark Stage 6 as complete
            job.stage6_completed_at = datetime.utcnow()
            job.stage6_completed_by = user_id
            job.stage6_downloaded_at = datetime.utcnow()
            job.status = 'completed'

            session.commit()

            container.main_logger.info(f"Job {job_id}: Marked as complete")

            response_data = {
                'success': True,
                'job_id': job_id,
                'message': 'Job completed successfully'
            }

            # If next_action is "next_job", find the next Stage 6 job
            if next_action == 'next_job':
                try:
                    # Query for next Stage 6 job
                    next_job = session.query(Job).filter(
                        Job.current_stage == 6,
                        Job.job_id != job_id,
                        Job.status != 'completed'
                    ).order_by(Job.created_at.asc()).first()

                    if next_job:
                        response_data['next_job_id'] = next_job.job_id
                        container.main_logger.info(f"Next Stage 6 job: {next_job.job_id}")
                    else:
                        response_data['next_job_id'] = None
                        container.main_logger.info("No more Stage 6 jobs available")

                except Exception as e:
                    container.main_logger.error(f"Error finding next job: {e}", exc_info=True)
                    response_data['next_job_id'] = None

            return jsonify(response_data)

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error completing job: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage6_bp.route('/api/job/<job_id>/regenerate-extendscript', methods=['POST'])
def regenerate_extendscript(job_id: str) -> Tuple[Response, int]:
    """
    Regenerate ExtendScript if user finds issues.

    Clears existing script and returns job to Stage 5 for regeneration.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with regeneration status, plus HTTP status code
    """
    try:
        data = request.json or {}
        user_id = data.get('user_id', 'anonymous')
        reason = data.get('reason', '')

        container.main_logger.info(f"Job {job_id}: Regenerating ExtendScript by {user_id}")

        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Clear Stage 5 data
            job.stage5_extendscript = None
            job.stage5_completed_at = None
            job.current_stage = 5
            job.status = 'processing'

            session.commit()

            container.main_logger.info(f"Job {job_id}: Returned to Stage 5 for regeneration. Reason: {reason}")

            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': 'Job returned to Stage 5 for regeneration',
                'redirect_url': f'/api/job/{job_id}/generate-extendscript'
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error regenerating ExtendScript: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage6_bp.route('/api/job/<job_id>/generate-preview', methods=['POST'])
def generate_preview(job_id: str) -> Tuple[Response, int]:
    """
    Generate preview for a job in Stage 6.

    Creates PSD preview image and renders After Effects preview video.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with preview generation status, plus HTTP status code
    """
    try:
        container.main_logger.info(f"Job {job_id}: Generating Stage 6 preview")

        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Use Stage6PreviewService to generate preview
            preview_service = Stage6PreviewService(container.main_logger)
            success, error, result = preview_service.generate_preview_for_job(job, session)

            if success:
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'message': 'Preview generated successfully',
                    'psd_preview_path': result['psd_preview_path'],
                    'video_preview_path': result['video_preview_path'],
                    'preview_url': result['preview_url']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': error
                }), 500

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error generating preview: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage6_bp.route('/api/job/<job_id>/preview-status', methods=['GET'])
def preview_status(job_id: str) -> Tuple[Response, int]:
    """
    Get preview generation status for a job.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with preview status, plus HTTP status code
    """
    try:
        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            has_psd_preview = bool(job.stage6_psd_preview_path)
            has_video_preview = bool(job.stage6_preview_video_path)
            has_both = has_psd_preview and has_video_preview

            return jsonify({
                'success': True,
                'job_id': job_id,
                'stage': job.current_stage,
                'status': job.status,
                'has_psd_preview': has_psd_preview,
                'has_video_preview': has_video_preview,
                'preview_ready': has_both,
                'psd_preview_path': job.stage6_psd_preview_path if has_psd_preview else None,
                'video_preview_path': job.stage6_preview_video_path if has_video_preview else None,
                'approved': job.stage6_approved or False,
                'approval_notes': job.stage6_approval_notes
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error checking preview status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage6_bp.route('/api/job/<job_id>/preview-file/<file_type>', methods=['GET'])
def serve_preview_file(job_id: str, file_type: str) -> Tuple[Response, int]:
    """
    Serve preview files (PSD image or video).

    Args:
        job_id: Unique identifier for the job
        file_type: Type of file to serve ('psd' or 'video')

    Returns:
        File download response or error JSON
    """
    try:
        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            if file_type == 'psd':
                file_path = job.stage6_psd_preview_path
                mimetype = 'image/png'
            elif file_type == 'video':
                file_path = job.stage6_preview_video_path
                mimetype = 'video/mp4'
            else:
                return jsonify({
                    'success': False,
                    'error': f'Invalid file type: {file_type}'
                }), 400

            if not file_path or not Path(file_path).exists():
                return jsonify({
                    'success': False,
                    'error': f'Preview file not found: {file_type}'
                }), 404

            return send_file(
                file_path,
                mimetype=mimetype,
                as_attachment=False
            )

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error serving preview file: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage6_bp.route('/api/job/<job_id>/approve-preview', methods=['POST'])
def approve_preview(job_id: str) -> Tuple[Response, int]:
    """
    Approve the preview and mark job as ready for download.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with approval status, plus HTTP status code

    Request JSON body:
        {
            "user_id": "john_doe",
            "notes": "Looks great!"  # Optional
        }
    """
    try:
        data = request.json or {}
        user_id = data.get('user_id', 'anonymous')
        notes = data.get('notes', '')

        container.main_logger.info(f"Job {job_id}: Preview approved by {user_id}")

        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Verify preview exists
            if not job.stage6_psd_preview_path or not job.stage6_preview_video_path:
                return jsonify({
                    'success': False,
                    'error': 'Preview not generated yet'
                }), 400

            # Mark as approved
            job.stage6_approved = True
            job.stage6_approval_notes = notes
            job.stage6_completed_at = datetime.utcnow()
            job.stage6_completed_by = user_id
            job.status = 'completed'

            session.commit()

            container.main_logger.info(f"Job {job_id}: Preview approved - job complete")

            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': 'Preview approved - job completed',
                'status': 'completed'
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error approving preview: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage6_bp.route('/api/job/<job_id>/reject-preview', methods=['POST'])
def reject_preview(job_id: str) -> Tuple[Response, int]:
    """
    Reject the preview and return to matching stage for corrections.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with rejection status, plus HTTP status code

    Request JSON body:
        {
            "user_id": "john_doe",
            "reason": "Text doesn't match",  # Required
            "return_to_stage": 2  # Optional, defaults to Stage 2 (Matching)
        }
    """
    try:
        data = request.json or {}
        user_id = data.get('user_id', 'anonymous')
        reason = data.get('reason', '')
        return_to_stage = data.get('return_to_stage', 2)

        if not reason or len(reason.strip()) < 10:
            return jsonify({
                'success': False,
                'error': 'Rejection reason is required and must be at least 10 characters'
            }), 400

        container.main_logger.info(
            f"Job {job_id}: Preview rejected by {user_id}, returning to Stage {return_to_stage}"
        )

        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Store rejection info
            job.stage6_approved = False
            job.stage6_approval_notes = f"REJECTED: {reason}"

            # Return to specified stage
            job.current_stage = return_to_stage
            job.status = 'awaiting_review'

            # Clear stages after the return point
            if return_to_stage <= 2:
                job.stage2_completed_at = None
                job.stage3_completed_at = None
                job.stage3_validation_results = None
                job.stage4_completed_at = None
                job.stage5_extendscript = None
                job.stage5_completed_at = None
                job.stage6_psd_preview_path = None
                job.stage6_preview_video_path = None

            session.commit()

            container.main_logger.info(
                f"Job {job_id}: Preview rejected, returned to Stage {return_to_stage}. Reason: {reason}"
            )

            redirect_map = {
                2: f'/review-matching/{job_id}',
                4: f'/validate/{job_id}',
                5: f'/api/job/{job_id}/generate-extendscript'
            }

            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': f'Preview rejected - returned to Stage {return_to_stage}',
                'redirect_url': redirect_map.get(return_to_stage, '/'),
                'return_to_stage': return_to_stage
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error rejecting preview: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
