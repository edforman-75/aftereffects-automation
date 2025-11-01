"""
Stage 5 Routes Blueprint

Handles Stage 5 ExtendScript generation - generates .jsx scripts from approved matches.
"""

from datetime import datetime
from typing import Tuple
from flask import Blueprint, request, jsonify, Response, send_file
import json
import os
from pathlib import Path

# Import services
from config.container import container
from database import db_session
from database.models import Job
from services.extendscript_service import ExtendScriptService


# Create blueprint
stage5_bp = Blueprint('stage5', __name__)


@stage5_bp.route('/api/job/<job_id>/generate-extendscript', methods=['POST'])
def generate_extendscript(job_id: str) -> Tuple[Response, int]:
    """
    Stage 5: Generate ExtendScript from approved matches.

    This is typically called automatically when job transitions to Stage 5,
    but can also be triggered manually.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with generation status and script preview, plus HTTP status code
    """
    try:
        container.main_logger.info(f"Job {job_id}: Generating ExtendScript")

        # Get database session
        session = db_session()

        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job not found: {job_id}'
                }), 404

            # Verify job is in Stage 5
            if job.current_stage != 5:
                return jsonify({
                    'success': False,
                    'error': f'Job is in Stage {job.current_stage}, not Stage 5'
                }), 400

            # Check if already generated
            if job.stage5_extendscript:
                container.main_logger.info(f"Job {job_id}: ExtendScript already generated")
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'message': 'ExtendScript already generated',
                    'script_preview': job.stage5_extendscript[:500] + '...' if len(job.stage5_extendscript) > 500 else job.stage5_extendscript
                })

            # Generate ExtendScript using shared service
            extendscript_service = ExtendScriptService(container.main_logger)
            success, error, gen_result = extendscript_service.generate_for_job(job, session)

            if success:
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'message': 'ExtendScript generated successfully',
                    'script_length': gen_result['script_length'],
                    'mappings_count': gen_result['mappings_count'],
                    'script_preview': gen_result['script_preview'],
                    'download_url': f'/api/job/{job_id}/download-extendscript'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': error
                }), 500

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error generating ExtendScript: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage5_bp.route('/api/job/<job_id>/extendscript-status', methods=['GET'])
def extendscript_status(job_id: str) -> Tuple[Response, int]:
    """
    Get ExtendScript generation status for a job.

    Args:
        job_id: Unique identifier for the job

    Returns:
        JSON response with generation status, plus HTTP status code
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

            has_script = bool(job.stage5_extendscript)

            return jsonify({
                'success': True,
                'job_id': job_id,
                'stage': job.current_stage,
                'has_extendscript': has_script,
                'generated_at': job.stage5_completed_at.isoformat() if job.stage5_completed_at else None,
                'script_length': len(job.stage5_extendscript) if has_script else 0,
                'status': 'complete' if has_script else 'pending'
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error checking ExtendScript status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stage5_bp.route('/api/job/<job_id>/download-extendscript', methods=['GET'])
def download_extendscript(job_id: str):
    """
    Download the generated ExtendScript as a .jsx file.

    Args:
        job_id: Unique identifier for the job

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

            if not job.stage5_extendscript:
                return jsonify({
                    'success': False,
                    'error': 'ExtendScript not generated yet'
                }), 400

            # Create temporary file for download
            temp_dir = Path('temp') / 'downloads'
            temp_dir.mkdir(parents=True, exist_ok=True)

            temp_file = temp_dir / f'{job_id}.jsx'

            # Write ExtendScript to temporary file
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(job.stage5_extendscript)

            container.main_logger.info(f"Job {job_id}: ExtendScript downloaded")

            # Return file for download
            return send_file(
                str(temp_file),
                as_attachment=True,
                download_name=f'{job.output_name}.jsx',
                mimetype='application/javascript'
            )

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error downloading ExtendScript: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
