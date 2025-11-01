"""
Core Routes Blueprint

Handles dashboard pages and static file serving.
"""

from pathlib import Path
from flask import Blueprint, render_template, send_file, jsonify


# Create blueprint
core_bp = Blueprint('core', __name__)


@core_bp.route('/')
def index():
    """Serve the main page."""
    from web_app import cleanup_old_files, VALIDATE_BEFORE_PREVIEW, REQUIRE_SIGNOFF_FOR_RENDER
    cleanup_old_files()
    return render_template('index.html',
                          VALIDATE_BEFORE_PREVIEW=VALIDATE_BEFORE_PREVIEW,
                          REQUIRE_SIGNOFF_FOR_RENDER=REQUIRE_SIGNOFF_FOR_RENDER)


@core_bp.route('/projects-page')
def projects_page():
    """Serve the projects list page."""
    return render_template('projects.html')


@core_bp.route('/projects/<project_id>')
def project_dashboard(project_id):
    """Serve the project dashboard page."""
    return render_template('project-dashboard.html', project_id=project_id)


@core_bp.route('/dashboard')
def production_dashboard():
    """Serve the production batch processing dashboard."""
    return render_template('production_dashboard.html')


@core_bp.route('/completed-jobs')
def completed_jobs():
    """Serve the completed jobs archive page."""
    return render_template('completed_jobs.html')


@core_bp.route('/data/<path:filename>')
def serve_data_file(filename):
    """Serve files from the data directory (exports, thumbnails, etc)."""
    try:
        data_dir = Path(__file__).parent.parent / 'data'
        file_path = data_dir / filename

        # Security: ensure the file is within the data directory
        if not str(file_path.resolve()).startswith(str(data_dir.resolve())):
            return jsonify({'error': 'Invalid file path'}), 403

        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

        return send_file(str(file_path))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
