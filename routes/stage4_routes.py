"""
Stage 4 Routes Blueprint

Handles Stage 4 validation review - user can return to matching or override issues.
"""

from datetime import datetime
from typing import Tuple, Any
from flask import Blueprint, request, jsonify, render_template, Response

# Import services from web_app (they're initialized there)
from config.container import container
from database import db_session
from database.models import Job


# Create blueprint
stage4_bp = Blueprint('stage4', __name__)


@stage4_bp.route('/validate/<job_id>')
def validate_job_page(job_id: str) -> str | Tuple[str, int]:
    """
    Display Stage 4 validation review page for a job.

    Args:
        job_id: Unique identifier for the job

    Returns:
        Rendered HTML template or error message with status code
    """
    try:
        container.main_logger.info(f"Loading validation page for job {job_id}")
        return render_template('stage3_validation.html', job_id=job_id)
    except Exception as e:
        container.main_logger.error(f"Error loading validation page: {e}", exc_info=True)
        return f"Error loading validation page: {e}", 500


@stage4_bp.route('/api/job/<job_id>/return-to-matching', methods=['POST'])
def return_to_matching(job_id: str) -> Tuple[Response, int]:
    """
    Stage 4: User chose to return to Stage 2 to fix matches.

    Transitions job from Stage 4 (Validation Review) back to Stage 2 (Matching).

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with success status and redirect URL, plus HTTP status code
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')

        container.main_logger.info(f"Job {job_id}: User {user_id} returning to Stage 2 matching")

        # Get database session
        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Verify job is in Stage 4
            if job.current_stage != 4:
                return jsonify({
                    'success': False,
                    'error': f'Job is in Stage {job.current_stage}, not Stage 4'
                }), 400

            # Transition back to Stage 2
            job.current_stage = 2
            job.stage3_completed_at = None  # Reset Stage 3 completion
            job.stage3_validation_results = None  # Clear validation results
            job.stage4_completed_at = None  # Reset Stage 4
            session.commit()

            container.main_logger.info(f"Job {job_id}: Returned to Stage 2 for matching adjustments")

            return jsonify({
                'success': True,
                'job_id': job_id,
                'redirect_url': f'/review-matching/{job_id}',
                'message': 'Returned to matching review'
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error returning to matching: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage4_bp.route('/api/job/<job_id>/override-validation', methods=['POST'])
def override_validation(job_id: str) -> Tuple[Response, int]:
    """
    Stage 4: User chose to override validation issues and proceed.

    Transitions job from Stage 4 (Validation Review) to Stage 5 (ExtendScript Generation).

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with success status and message, plus HTTP status code
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        override_reason = data.get('override_reason', '')

        if not override_reason or len(override_reason.strip()) < 10:
            return jsonify({
                'success': False,
                'error': 'Override reason is required and must be at least 10 characters'
            }), 400

        container.main_logger.info(f"Job {job_id}: User {user_id} overriding validation issues")

        # Get database session
        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Verify job is in Stage 4
            if job.current_stage != 4:
                return jsonify({
                    'success': False,
                    'error': f'Job is in Stage {job.current_stage}, not Stage 4'
                }), 400

            # Store override reason and transition to Stage 5
            job.stage4_override = True
            job.stage4_override_reason = override_reason
            job.stage4_completed_at = datetime.utcnow()
            job.stage4_completed_by = user_id
            job.current_stage = 5
            session.commit()

            container.main_logger.info(
                f"Job {job_id}: Validation overridden by {user_id}, proceeding to Stage 5"
            )

            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': 'Validation overridden - proceeding to ExtendScript generation'
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error overriding validation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
