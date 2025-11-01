"""
Batch Routes Blueprint

Handles batch upload, validation, and processing initiation.
"""

import time
from pathlib import Path
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

# Import services from web_app (they're initialized there)
from config.container import container
from services.batch_validator import BatchValidator
from services.job_service import JobService
from services.stage1_processor import Stage1Processor


# Create blueprint
batch_bp = Blueprint('batch', __name__)


# Get service instances
def get_services():
    """Get service instances (they're module-level in web_app.py)."""
    from web_app import batch_validator, job_service, stage1_processor
    return batch_validator, job_service, stage1_processor


@batch_bp.route('/api/batch/upload', methods=['POST'])
def upload_batch_csv():
    """
    Upload and validate CSV batch file.

    Returns validated batch ready for processing.
    """
    try:
        batch_validator, job_service, _ = get_services()

        # Check if file is present
        if 'csv_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No CSV file provided'
            }), 400

        csv_file = request.files['csv_file']
        user_id = request.form.get('user_id', 'anonymous')

        if csv_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Save CSV file
        csv_filename = secure_filename(csv_file.filename)
        csv_dir = Path('data/batches')
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = csv_dir / f"{int(time.time())}_{csv_filename}"
        csv_file.save(str(csv_path))

        container.main_logger.info(f"CSV uploaded: {csv_path} by {user_id}")

        # Validate CSV
        validation_result = batch_validator.validate_csv(str(csv_path))

        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'validation': validation_result,
                'message': f"Batch validation failed: {validation_result['invalid_jobs']} invalid jobs"
            }), 400

        # Create batch and jobs in database
        batch_id = job_service.create_batch_from_csv(
            batch_id=validation_result['batch_id'],
            csv_path=str(csv_path),
            csv_filename=csv_filename,
            jobs=validation_result['jobs'],
            validation_result=validation_result,
            user_id=user_id
        )

        container.main_logger.info(f"Batch created: {batch_id} with {validation_result['valid_jobs']} jobs")

        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'validation': validation_result,
            'message': f"Batch created successfully with {validation_result['valid_jobs']} jobs"
        })

    except Exception as e:
        container.main_logger.error(f"Batch upload failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@batch_bp.route('/api/batch/<batch_id>/start-processing', methods=['POST'])
def start_batch_processing(batch_id: str):
    """
    Start Stage 1 automated processing for a batch.

    Processes all jobs in the batch through automated ingestion.
    """
    try:
        _, job_service, stage1_processor = get_services()

        max_jobs = request.json.get('max_jobs', 100) if request.json else 100

        container.main_logger.info(f"Starting Stage 1 processing for batch {batch_id}")

        # Process batch
        result = stage1_processor.process_batch(batch_id, max_jobs=max_jobs)

        # Update batch status
        if result['succeeded'] > 0:
            job_service.update_batch_status(batch_id, 'processing')

        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'result': result,
            'message': f"Processed {result['processed']} jobs: {result['succeeded']} succeeded, {result['failed']} failed"
        })

    except Exception as e:
        container.main_logger.error(f"Batch processing failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@batch_bp.route('/api/batch/<batch_id>', methods=['GET'])
def get_batch_status(batch_id: str):
    """Get batch status and job summary."""
    try:
        _, job_service, _ = get_services()

        batch = job_service.get_batch(batch_id)

        if not batch:
            return jsonify({
                'success': False,
                'error': f'Batch not found: {batch_id}'
            }), 404

        # Get job counts by stage
        jobs = job_service.get_batch_jobs(batch_id)
        stage_counts = {}
        status_counts = {}

        for job in jobs:
            stage_counts[job.current_stage] = stage_counts.get(job.current_stage, 0) + 1
            status_counts[job.status] = status_counts.get(job.status, 0) + 1

        return jsonify({
            'success': True,
            'batch': {
                'batch_id': batch.batch_id,
                'status': batch.status,
                'csv_filename': batch.csv_filename,
                'total_jobs': batch.total_jobs,
                'valid_jobs': batch.valid_jobs,
                'invalid_jobs': batch.invalid_jobs,
                'uploaded_at': batch.uploaded_at.isoformat() if batch.uploaded_at else None,
                'validated_at': batch.validated_at.isoformat() if batch.validated_at else None,
                'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
                'uploaded_by': batch.uploaded_by
            },
            'stage_counts': stage_counts,
            'status_counts': status_counts
        })

    except Exception as e:
        container.main_logger.error(f"Error getting batch status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
