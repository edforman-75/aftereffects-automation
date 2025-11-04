"""
Folder Management API Routes

Provides endpoints for managing the hierarchical folder structure
for clients, batches, and jobs.
"""

from flask import Blueprint, request, jsonify
from services.folder_manager import folder_manager
from config.settings import settings

folder_bp = Blueprint('folder', __name__, url_prefix='/api/folder')


@folder_bp.route('/setup/client', methods=['POST'])
def setup_client():
    """
    Set up folder structure for a new client.

    Request JSON:
        {
            "client_name": "ACME Corp"
        }

    Returns:
        {
            "success": true,
            "client_name": "ACME Corp",
            "folder_path": "projects/ACME_Corp",
            "message": "Client folder created successfully"
        }
    """
    try:
        data = request.get_json()
        client_name = data.get('client_name')

        if not client_name:
            return jsonify({
                'success': False,
                'error': 'client_name is required'
            }), 400

        folder_path = folder_manager.setup_client_folder(client_name)

        return jsonify({
            'success': True,
            'client_name': client_name,
            'folder_path': str(folder_path),
            'message': 'Client folder created successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/setup/batch', methods=['POST'])
def setup_batch():
    """
    Set up folder structure for a new batch.

    Request JSON:
        {
            "client_name": "ACME Corp",
            "batch_id": "batch_123"
        }

    Returns:
        {
            "success": true,
            "client_name": "ACME Corp",
            "batch_id": "batch_123",
            "folder_path": "projects/ACME_Corp/batch_123",
            "message": "Batch folder created successfully"
        }
    """
    try:
        data = request.get_json()
        client_name = data.get('client_name')
        batch_id = data.get('batch_id')

        if not client_name or not batch_id:
            return jsonify({
                'success': False,
                'error': 'client_name and batch_id are required'
            }), 400

        folder_path = folder_manager.setup_batch_folder(client_name, batch_id)

        return jsonify({
            'success': True,
            'client_name': client_name,
            'batch_id': batch_id,
            'folder_path': str(folder_path),
            'message': 'Batch folder created successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/setup/job', methods=['POST'])
def setup_job():
    """
    Set up complete folder structure for a new job.

    Request JSON:
        {
            "client_name": "ACME Corp",
            "batch_id": "batch_123",
            "job_id": "job_001"
        }

    Returns:
        {
            "success": true,
            "client_name": "ACME Corp",
            "batch_id": "batch_123",
            "job_id": "job_001",
            "paths": {
                "root": "projects/ACME_Corp/batch_123/job_001",
                "assets": "projects/ACME_Corp/batch_123/job_001/assets",
                "previews": "projects/ACME_Corp/batch_123/job_001/previews",
                "renders": "projects/ACME_Corp/batch_123/job_001/renders",
                "scripts": "projects/ACME_Corp/batch_123/job_001/scripts",
                "logs": "projects/ACME_Corp/batch_123/job_001/logs"
            },
            "message": "Job folders created successfully"
        }
    """
    try:
        data = request.get_json()
        client_name = data.get('client_name')
        batch_id = data.get('batch_id')
        job_id = data.get('job_id')

        if not client_name or not batch_id or not job_id:
            return jsonify({
                'success': False,
                'error': 'client_name, batch_id, and job_id are required'
            }), 400

        paths = folder_manager.setup_job_folders(client_name, batch_id, job_id)

        return jsonify({
            'success': True,
            'client_name': client_name,
            'batch_id': batch_id,
            'job_id': job_id,
            'paths': {
                'root': str(paths.root),
                'assets': str(paths.assets),
                'previews': str(paths.previews),
                'renders': str(paths.renders),
                'scripts': str(paths.scripts),
                'logs': str(paths.logs)
            },
            'message': 'Job folders created successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/list/clients', methods=['GET'])
def list_clients():
    """
    List all client folders.

    Returns:
        {
            "success": true,
            "clients": ["ACME_Corp", "XYZ_Industries"],
            "count": 2
        }
    """
    try:
        clients = folder_manager.list_clients()

        return jsonify({
            'success': True,
            'clients': clients,
            'count': len(clients)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/list/batches/<client_name>', methods=['GET'])
def list_batches(client_name):
    """
    List all batch folders for a client.

    URL Parameters:
        client_name: Name of the client (URL-encoded)

    Returns:
        {
            "success": true,
            "client_name": "ACME_Corp",
            "batches": ["batch_123", "batch_124"],
            "count": 2
        }
    """
    try:
        batches = folder_manager.list_batches(client_name)

        return jsonify({
            'success': True,
            'client_name': client_name,
            'batches': batches,
            'count': len(batches)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/list/jobs/<client_name>/<batch_id>', methods=['GET'])
def list_jobs(client_name, batch_id):
    """
    List all job folders for a batch.

    URL Parameters:
        client_name: Name of the client (URL-encoded)
        batch_id: Batch identifier (URL-encoded)

    Returns:
        {
            "success": true,
            "client_name": "ACME_Corp",
            "batch_id": "batch_123",
            "jobs": ["job_001", "job_002", "job_003"],
            "count": 3
        }
    """
    try:
        jobs = folder_manager.list_jobs(client_name, batch_id)

        return jsonify({
            'success': True,
            'client_name': client_name,
            'batch_id': batch_id,
            'jobs': jobs,
            'count': len(jobs)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/info/<client_name>', methods=['GET'])
@folder_bp.route('/info/<client_name>/<batch_id>', methods=['GET'])
@folder_bp.route('/info/<client_name>/<batch_id>/<job_id>', methods=['GET'])
def folder_info(client_name, batch_id=None, job_id=None):
    """
    Get information about a folder (size, file count, etc.).

    URL Parameters:
        client_name: Name of the client (URL-encoded)
        batch_id: Optional batch identifier (URL-encoded)
        job_id: Optional job identifier (URL-encoded)

    Returns:
        {
            "success": true,
            "info": {
                "exists": true,
                "path": "projects/ACME_Corp/batch_123",
                "size_bytes": 1234567,
                "size_mb": 1.18,
                "file_count": 42
            }
        }
    """
    try:
        info = folder_manager.get_folder_info(client_name, batch_id, job_id)

        return jsonify({
            'success': True,
            'info': info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/settings', methods=['GET'])
def get_folder_settings():
    """
    Get current folder organization settings.

    Returns:
        {
            "success": true,
            "settings": {
                "use_hierarchical_folders": true,
                "base_output_path": "projects",
                "sanitize_folder_names": true,
                ...
            }
        }
    """
    try:
        from dataclasses import asdict

        return jsonify({
            'success': True,
            'settings': asdict(settings.folder_organization)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@folder_bp.route('/settings', methods=['PUT'])
def update_folder_settings():
    """
    Update folder organization settings.

    Request JSON:
        {
            "use_hierarchical_folders": true,
            "base_output_path": "projects",
            "sanitize_folder_names": true,
            ...
        }

    Returns:
        {
            "success": true,
            "message": "Folder settings updated successfully"
        }
    """
    try:
        data = request.get_json()

        # Update settings
        for key, value in data.items():
            if hasattr(settings.folder_organization, key):
                setattr(settings.folder_organization, key, value)

        # Validate and save
        is_valid, error = settings.validate()
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        settings.save()

        return jsonify({
            'success': True,
            'message': 'Folder settings updated successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
