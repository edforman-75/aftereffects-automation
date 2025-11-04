"""
Batch Routes Blueprint

Handles batch upload, validation, and processing initiation.
"""

import time
import csv
import io
from pathlib import Path
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

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


@batch_bp.route('/api/batch/build-from-files', methods=['POST'])
def build_batch_from_files():
    """
    Build and validate a batch from selected PSD and AEPX files.

    Automatically generates CSV from file selections and optional metadata.
    """
    try:
        batch_validator, job_service, _ = get_services()

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        psd_files = data.get('psd_files', [])
        aepx_files = data.get('aepx_files', [])

        if not psd_files:
            return jsonify({
                'success': False,
                'error': 'No PSD files provided'
            }), 400

        if not aepx_files:
            return jsonify({
                'success': False,
                'error': 'No AEPX template files provided'
            }), 400

        # Get optional metadata
        client_name = data.get('client_name', '')
        project_name = data.get('project_name', '')
        priority = data.get('priority', 'medium')
        notes = data.get('notes', '')
        pairing_mode = data.get('pairing_mode', 'one-to-one')  # 'one-to-one' or 'template'
        user_id = data.get('user_id', 'anonymous')

        # Generate CSV rows
        csv_rows = []

        if pairing_mode == 'template':
            # Use first AEPX as template for all PSDs
            template_aepx = aepx_files[0]
            for idx, psd_path in enumerate(psd_files):
                job_id = _generate_job_id(psd_path, idx)
                output_name = f"{job_id}.aep"
                csv_rows.append({
                    'job_id': job_id,
                    'psd_path': psd_path,
                    'aepx_path': template_aepx,
                    'output_name': output_name,
                    'client_name': client_name,
                    'project_name': project_name,
                    'priority': priority,
                    'notes': notes
                })
        else:
            # One-to-one pairing
            min_count = min(len(psd_files), len(aepx_files))
            for idx in range(min_count):
                psd_path = psd_files[idx]
                aepx_path = aepx_files[idx]
                job_id = _generate_job_id(psd_path, idx)
                output_name = f"{job_id}.aep"
                csv_rows.append({
                    'job_id': job_id,
                    'psd_path': psd_path,
                    'aepx_path': aepx_path,
                    'output_name': output_name,
                    'client_name': client_name,
                    'project_name': project_name,
                    'priority': priority,
                    'notes': notes
                })

        if not csv_rows:
            return jsonify({
                'success': False,
                'error': 'No valid file pairs could be generated'
            }), 400

        # Generate CSV in memory
        csv_buffer = io.StringIO()
        fieldnames = ['job_id', 'psd_path', 'aepx_path', 'output_name',
                     'client_name', 'project_name', 'priority', 'notes']
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

        # Save CSV file
        csv_filename = f"batch_from_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_dir = Path('data/batches')
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = csv_dir / csv_filename

        with open(csv_path, 'w', newline='') as f:
            f.write(csv_buffer.getvalue())

        container.main_logger.info(f"CSV generated from files: {csv_path} by {user_id}")

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

        container.main_logger.info(f"Batch created from files: {batch_id} with {validation_result['valid_jobs']} jobs")

        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'validation': validation_result,
            'csv_filename': csv_filename,
            'message': f"Batch created successfully with {validation_result['valid_jobs']} jobs"
        })

    except Exception as e:
        container.main_logger.error(f"Build from files failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _generate_job_id(psd_path: str, index: int) -> str:
    """Generate a unique job ID from PSD filename."""
    psd_name = Path(psd_path).stem
    # Clean filename to alphanumeric + underscore/dash
    clean_name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in psd_name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{clean_name}_{timestamp}_{index:03d}"


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
