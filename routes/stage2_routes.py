"""
Stage 2 Routes Blueprint

Handles Stage 2 layer matching review and approval.
"""

from datetime import datetime
from typing import Tuple
from flask import Blueprint, request, jsonify, render_template, Response
import json

# Import services from web_app (they're initialized there)
from config.container import container
from database import db_session
from database.models import Job
from services.extendscript_service import ExtendScriptService


# Create blueprint
stage2_bp = Blueprint('stage2', __name__)


# Get service instances
def get_services():
    """Get service instances (they're module-level in web_app.py)."""
    from web_app import match_validator
    return match_validator


@stage2_bp.route('/review-matching/<job_id>')
def review_matching(job_id: str) -> str:
    """
    Stage 2: Review layer matching interface.

    Args:
        job_id: Unique identifier for the job

    Returns:
        Rendered HTML template
    """
    return render_template('stage2_review.html', job_id=job_id)


@stage2_bp.route('/api/job/<job_id>/approve-stage2', methods=['POST'])
def approve_stage2_matching(job_id: str) -> Tuple[Response, int]:
    """
    Approve Stage 2 layer matching and run validation.

    6-STAGE PIPELINE WORKFLOW:
    - Save matches to stage2_approved_matches
    - Transition to Stage 3 (Auto-Validation)
    - Run validation checks automatically
    - If critical issues: Move to Stage 4 (Validation Review) and return validation_url
    - If no critical issues: Skip Stage 4, move directly to Stage 5 (ExtendScript Generation)

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with validation results and next steps, plus HTTP status code

    Request JSON body:
        {
            "user_id": "john_doe",
            "matches": [
                {"psd_layer_id": "psd_LayerName", "ae_layer_id": "ae_Placeholder", "confidence": 0.95, "method": "auto"},
                ...
            ],
            "next_action": "next_job" | "dashboard"  # Optional
        }
    """
    try:
        match_validator = get_services()

        data = request.json
        user_id = data.get('user_id', 'anonymous')
        # Support both "matches" and "approved_matches" for backwards compatibility
        matches = data.get('approved_matches', data.get('matches', []))
        next_action = data.get('next_action', 'dashboard')

        container.main_logger.info(f"Job {job_id}: Stage 2 approval by {user_id}, {len(matches)} matches")

        # Get database session
        session = db_session()

        # Query for the job using ORM
        job = session.query(Job).filter_by(job_id=job_id).first()

        if not job:
            session.close()
            return jsonify({
                'success': False,
                'error': f'Job not found: {job_id}'
            }), 404

        # Save matches using ORM (JSON column auto-serializes)
        job.stage2_approved_matches = {'approved_matches': matches}
        job.stage2_completed_at = datetime.utcnow()
        job.stage2_completed_by = user_id

        session.commit()

        # Run validation on approved matches
        container.main_logger.info(f"Job {job_id}: Running validation checks...")
        validation_results = match_validator.validate_job(job_id)

        # Save validation results
        match_validator.save_validation_results(job_id, validation_results)

        # Re-query job to get fresh data (save_validation_results uses its own session and commits)
        # The job object is now detached, so we need to get a fresh instance
        job = session.query(Job).filter_by(job_id=job_id).first()

        # Check for critical issues
        has_critical = validation_results.get('critical_issues') and len(validation_results['critical_issues']) > 0

        if has_critical:
            # Critical issues found - redirect to Stage 4 validation review
            container.main_logger.warning(
                f"Job {job_id}: {len(validation_results['critical_issues'])} critical validation issues found"
            )

            # Move to Stage 4 (Validation Review) using ORM
            job.current_stage = 4
            job.status = 'awaiting_approval'  # Human needs to review validation issues
            job.stage3_completed_at = datetime.utcnow()  # Mark Stage 3 (Auto-Validation) complete
            session.commit()
            session.close()

            return jsonify({
                'success': True,
                'requires_validation': True,
                'validation_url': f'/validate/{job_id}',
                'message': f'Critical validation issues found ({len(validation_results["critical_issues"])})',
                'critical_count': len(validation_results['critical_issues']),
                'warning_count': len(validation_results.get('warnings', []))
            })

        else:
            # No critical issues - skip Stage 4, proceed directly to Stage 5 (ExtendScript generation)
            warnings_count = len(validation_results.get('warnings', []))
            if warnings_count > 0:
                container.main_logger.info(
                    f"Job {job_id}: {warnings_count} warnings found, but no critical issues"
                )

            # Mark Stage 3 complete and Stage 4 as skipped
            job.current_stage = 5
            job.status = 'processing'  # Processing ExtendScript generation
            job.stage3_completed_at = datetime.utcnow()  # Mark Stage 3 (Auto-Validation) complete
            job.stage4_completed_at = datetime.utcnow()  # Mark Stage 4 as skipped (no review needed)
            job.stage5_started_at = datetime.utcnow()
            session.commit()

            container.main_logger.info(
                f"Job {job_id}: Validation passed, skipping Stage 4 review, proceeding to Stage 5"
            )

            # Trigger Stage 5 ExtendScript generation using shared service
            extendscript_service = ExtendScriptService(container.main_logger)
            success, error, gen_result = extendscript_service.generate_for_job(job, session)

            if success:
                container.main_logger.info(
                    f"Job {job_id}: ExtendScript generated successfully, transitioned to Stage 6"
                )
                result = {
                    'success': True,
                    'status': 'complete',
                    'message': 'ExtendScript generation complete'
                }
            else:
                container.main_logger.error(f"Job {job_id}: ExtendScript generation failed: {error}")
                job.status = 'failed'
                session.commit()
                result = {
                    'success': False,
                    'status': 'failed',
                    'message': error
                }

            response_data = {
                'success': True,
                'requires_validation': False,
                'message': 'Validation passed - proceeding to ExtendScript generation',
                'job_id': job_id,
                'warning_count': warnings_count,
                'status': result['status']
            }

            # If next_action is "next_job", find the next Stage 2 job
            if next_action == 'next_job':
                try:
                    # Query for next Stage 2 job using ORM
                    next_job = session.query(Job).filter(
                        Job.current_stage == 2,
                        Job.job_id != job_id
                    ).order_by(Job.created_at.asc()).first()

                    if next_job:
                        response_data['next_job_id'] = next_job.job_id
                        container.main_logger.info(f"Next Stage 2 job: {next_job.job_id}")
                    else:
                        response_data['next_job_id'] = None
                        container.main_logger.info("No more Stage 2 jobs available")

                except Exception as e:
                    container.main_logger.error(f"Error finding next job: {e}", exc_info=True)
                    response_data['next_job_id'] = None

            # Close session before returning
            session.close()
            return jsonify(response_data)

    except Exception as e:
        container.main_logger.error(f"Error approving Stage 2: {e}", exc_info=True)
        # Close session on error
        try:
            session.close()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
