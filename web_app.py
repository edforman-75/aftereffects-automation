#!/usr/bin/env python3
"""
After Effects Automation - Web Interface

Flask web application for the automation pipeline.
"""

import os
import time
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_file, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage

# Legacy module imports (still used by some functions)
from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.conflict_detector import detect_conflicts
from modules.phase3.font_checker import check_fonts
from modules.phase4.extendscript_generator import generate_extendscript
from modules.phase5.preview_generator import generate_preview, check_aerender_available

# Service layer (new architecture)
from config.container import container
from services.font_service import FontService

# Production batch processing services
from services.batch_validator import BatchValidator
from services.job_service import JobService
from services.warning_service import WarningService
from services.log_service import LogService
from services.stage1_processor import Stage1Processor
from database import init_database, db_session
from database.models import Job

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('output')
FONTS_FOLDER = Path('fonts')
PREVIEWS_FOLDER = Path(__file__).parent / 'previews'  # Absolute path for Photoshop
RENDERS_FOLDER = Path(__file__).parent / 'renders'  # Final renders
ALLOWED_PSD_EXTENSIONS = {'psd'}
ALLOWED_AEPX_EXTENSIONS = {'aepx', 'aep'}
ALLOWED_FONT_EXTENSIONS = {'ttf', 'otf', 'woff', 'woff2'}
MAX_PSD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_AEPX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FONT_SIZE = 5 * 1024 * 1024  # 5MB
CLEANUP_AGE = timedelta(hours=1)

# Preview & Sign-off Workflow Settings
VALIDATE_BEFORE_PREVIEW = os.getenv('VALIDATE_BEFORE_PREVIEW', 'true').lower() == 'true'
REQUIRE_SIGNOFF_FOR_RENDER = os.getenv('REQUIRE_SIGNOFF_FOR_RENDER', 'true').lower() == 'true'
AE_PREVIEW_PRESET = os.getenv('AE_PREVIEW_PRESET', 'draft_720p_4mbps')
AE_FINAL_PRESET = os.getenv('AE_FINAL_PRESET', 'hq_1080p_15mbps')

# Create Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_PSD_SIZE
CORS(app)

# Correlation ID middleware for request tracking
@app.before_request
def before_request():
    """Generate correlation ID for each request"""
    g.correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
    container.main_logger.info(f"[REQUEST] {request.method} {request.path} correlation_id={g.correlation_id}")

@app.after_request
def after_request(response):
    """Log request completion"""
    if hasattr(g, 'correlation_id'):
        response.headers['X-Correlation-ID'] = g.correlation_id
        container.main_logger.info(
            f"[RESPONSE] {request.path} status={response.status_code} correlation_id={g.correlation_id}"
        )
    return response

# Error handling middleware
@app.errorhandler(404)
def not_found_error(e):
    """Handle 404 errors."""
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    correlation_id = getattr(g, 'correlation_id', 'unknown')
    container.main_logger.error(f"Internal server error: {e} correlation_id={correlation_id}", exc_info=True)
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions."""
    container.main_logger.error(f"Unhandled exception: {e}", exc_info=True)

    if app.debug:
        return jsonify({
            'success': False,
            'message': 'An error occurred',
            'error': str(e),
            'type': type(e).__name__
        }), 500
    else:
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500

# Ensure directories exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
FONTS_FOLDER.mkdir(exist_ok=True)
PREVIEWS_FOLDER.mkdir(exist_ok=True)
RENDERS_FOLDER.mkdir(exist_ok=True)

# Configuration management
CONFIG_FILE = Path('config.json')
DEFAULT_CONFIG = {
    "directories": {
        "psd_input": "uploads/",
        "aepx_input": "uploads/",
        "output_scripts": "output/",
        "output_previews": "previews/",
        "fonts": "fonts/",
        "footage": "footage/"
    },
    "conflict_thresholds": {
        "text_overflow_critical": 10,
        "text_overflow_warning": 5,
        "aspect_ratio_critical": 0.2,
        "aspect_ratio_warning": 0.1,
        "resolution_mismatch_warning": 100
    },
    "preview_defaults": {
        "duration": 5,
        "resolution": "half",
        "fps": 15,
        "format": "mp4"
    },
    "advanced": {
        "ml_confidence_threshold": 0.7,
        "aerender_path": "/Applications/Adobe After Effects 2025/aerender",
        "auto_font_substitution": False,
        "cleanup_age_hours": 1,
        "max_psd_size_mb": 50,
        "max_aepx_size_mb": 10,
        "max_font_size_mb": 5
    }
}

def load_config():
    """Load configuration from config.json or create default."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        # Create default config file
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# Load configuration
config = load_config()

# Session storage (in-memory, use Redis for production)
sessions = {}


# Job State Management Utilities
import hashlib


def sha256_file(file_path: str) -> str:
    """Calculate SHA-256 hash of a file"""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        container.main_logger.error(f"Error hashing file {file_path}: {e}")
        return None


def log_state_transition(session_id: str, from_state: str, to_state: str, user: str = 'system'):
    """Log job state transitions for audit trail"""
    container.main_logger.info(
        f"[STATE_TRANSITION] session_id={session_id} from={from_state} to={to_state} by={user} at={datetime.now().isoformat()}"
    )


def update_job_state(session_id: str, new_state: str, user: str = 'system'):
    """Update job state with logging"""
    if session_id in sessions:
        old_state = sessions[session_id].get('state', 'UNKNOWN')
        sessions[session_id]['state'] = new_state
        log_state_transition(session_id, old_state, new_state, user)
        return True
    return False


def now_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def cleanup_old_files():
    """Remove files older than CLEANUP_AGE."""
    cutoff = datetime.now() - CLEANUP_AGE
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, FONTS_FOLDER, PREVIEWS_FOLDER]:
        for file_path in folder.glob('*'):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff:
                    file_path.unlink()


def list_uploaded_fonts():
    """Get list of uploaded font files."""
    fonts = []
    for font_path in FONTS_FOLDER.glob('*'):
        if font_path.is_file() and allowed_file(font_path.name, ALLOWED_FONT_EXTENSIONS):
            # Extract font name from filename (remove extension)
            font_name = font_path.stem
            fonts.append(font_name)
    return fonts


def check_font_availability(required_fonts):
    """
    Check which required fonts are available.

    Returns dict with required_fonts, installed_fonts, and missing_fonts.
    """
    # Get uploaded fonts
    uploaded = set(list_uploaded_fonts())

    # For now, treat uploaded fonts as installed
    # In a real implementation, this would check system fonts too
    installed = uploaded

    required_set = set(required_fonts)
    missing = list(required_set - installed)
    available = list(required_set & installed)

    return {
        'required_fonts': required_fonts,
        'installed_fonts': available,
        'missing_fonts': missing
    }


@app.route('/')
def index():
    """Serve the main page."""
    cleanup_old_files()
    return render_template('index.html',
                          VALIDATE_BEFORE_PREVIEW=VALIDATE_BEFORE_PREVIEW,
                          REQUIRE_SIGNOFF_FOR_RENDER=REQUIRE_SIGNOFF_FOR_RENDER)


@app.route('/projects-page')
def projects_page():
    """Serve the projects list page."""
    return render_template('projects.html')


@app.route('/projects/<project_id>')
def project_dashboard(project_id):
    """Serve the project dashboard page."""
    return render_template('project-dashboard.html', project_id=project_id)


@app.route('/dashboard')
def production_dashboard():
    """Serve the production batch processing dashboard."""
    return render_template('production_dashboard.html')


@app.route('/data/<path:filename>')
def serve_data_file(filename):
    """Serve files from the data directory (exports, thumbnails, etc)."""
    try:
        data_dir = Path(__file__).parent / 'data'
        file_path = data_dir / filename

        # Security: ensure the file is within the data directory
        if not str(file_path.resolve()).startswith(str(data_dir.resolve())):
            return jsonify({'error': 'Invalid file path'}), 403

        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

        return send_file(str(file_path))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads (PSD and AEPX) - using service layer."""
    try:
        # Check if files are present
        if 'psd_file' not in request.files or 'aepx_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Both PSD and AEPX files are required'
            }), 400

        psd_file = request.files['psd_file']
        aepx_file = request.files['aepx_file']

        # Validate filenames
        if psd_file.filename == '' or aepx_file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No files selected'
            }), 400

        # Validate file types
        if not allowed_file(psd_file.filename, ALLOWED_PSD_EXTENSIONS):
            return jsonify({
                'success': False,
                'message': 'Invalid PSD file. Must be .psd'
            }), 400

        if not allowed_file(aepx_file.filename, ALLOWED_AEPX_EXTENSIONS):
            return jsonify({
                'success': False,
                'message': 'Invalid template file. Must be .aepx or .aep'
            }), 400

        # Generate session ID
        session_id = f"{int(time.time())}_{os.urandom(4).hex()}"

        # Save files
        psd_filename = secure_filename(f"{session_id}_psd_{psd_file.filename}")
        aepx_filename = secure_filename(f"{session_id}_aepx_{aepx_file.filename}")

        psd_path = UPLOAD_FOLDER / psd_filename
        aepx_path = UPLOAD_FOLDER / aepx_filename

        psd_file.save(str(psd_path))
        aepx_file.save(str(aepx_path))

        container.main_logger.info(f"Files uploaded - Session: {session_id}")

        # Validate PSD using service
        psd_valid = container.psd_service.validate_psd_file(str(psd_path), max_size_mb=50)
        if not psd_valid.is_success():
            return jsonify({
                'success': False,
                'message': f'PSD validation failed: {psd_valid.get_error()}'
            }), 400

        # Parse PSD using service
        psd_result = container.psd_service.parse_psd(str(psd_path))
        if not psd_result.is_success():
            return jsonify({
                'success': False,
                'message': f'PSD parsing failed: {psd_result.get_error()}'
            }), 400

        psd_data = psd_result.get_data()

        # Extract all PSD layers as individual PNG files (HEADLESS - no Photoshop UI!)
        container.main_logger.info("Extracting PSD layers (headless mode)...")
        exports_dir = UPLOAD_FOLDER / "exports" / session_id
        exports_dir.mkdir(parents=True, exist_ok=True)

        from services.psd_layer_exporter import PSDLayerExporter
        layer_exporter = PSDLayerExporter(container.main_logger)
        export_result = layer_exporter.extract_all_layers(
            str(psd_path),
            str(exports_dir),
            generate_thumbnails=True
        )

        # Extract from result
        exported_layers = export_result.get('layers', {})
        flattened_preview = export_result.get('flattened_preview')
        psd_dimensions = export_result.get('dimensions', {})
        fonts_from_layers = export_result.get('fonts', [])

        # Format fonts for frontend
        fonts_installed = [f for f in fonts_from_layers if f.get('is_installed')]
        fonts_missing = [f for f in fonts_from_layers if not f.get('is_installed')]

        # Log summary
        summary = layer_exporter.get_export_summary(exported_layers)
        container.main_logger.info(summary)

        # Parse AEPX/AEP
        aepx_ext = Path(aepx_file.filename).suffix.lower()
        if aepx_ext == '.aep':
            # For AEP files, convert to AEPX format automatically
            container.main_logger.info("AEP file detected, converting to AEPX format...")

            # Generate output path for AEPX
            aepx_output_path = str(aepx_path.with_suffix('.aepx'))

            # Convert using AEP converter
            conversion_result = container.aep_converter.convert_aep_to_aepx_applescript(
                str(aepx_path),
                aepx_output_path
            )

            if not conversion_result.get('success'):
                error_msg = conversion_result.get('error', 'Unknown conversion error')
                container.main_logger.error(f"AEP conversion failed: {error_msg}")
                return jsonify({
                    'success': False,
                    'message': f'AEP conversion failed: {error_msg}. Please ensure After Effects is installed and the AEP file is valid.'
                }), 400

            # Update path to use converted AEPX
            aepx_path = Path(conversion_result['aepx_path'])
            container.main_logger.info(f"✅ AEP converted successfully: {aepx_path}")

            # Continue with normal AEPX parsing flow
            aepx_valid = container.aepx_service.validate_aepx_file(str(aepx_path), max_size_mb=10)
            if not aepx_valid.is_success():
                return jsonify({
                    'success': False,
                    'message': f'Converted AEPX validation failed: {aepx_valid.get_error()}'
                }), 400

            # Parse the converted AEPX
            aepx_result = container.aepx_service.parse_aepx(str(aepx_path))
            if not aepx_result.is_success():
                return jsonify({
                    'success': False,
                    'message': f'Converted AEPX parsing failed: {aepx_result.get_error()}'
                }), 400

            aepx_data = aepx_result.get_data()
        else:
            # Validate AEPX using service
            aepx_valid = container.aepx_service.validate_aepx_file(str(aepx_path), max_size_mb=10)
            if not aepx_valid.is_success():
                return jsonify({
                    'success': False,
                    'message': f'AEPX validation failed: {aepx_valid.get_error()}'
                }), 400

            # Parse AEPX using service
            aepx_result = container.aepx_service.parse_aepx(str(aepx_path))
            if not aepx_result.is_success():
                return jsonify({
                    'success': False,
                    'message': f'AEPX parsing failed: {aepx_result.get_error()}'
                }), 400

            aepx_data = aepx_result.get_data()

        # Comprehensive headless AEPX processing
        container.main_logger.info("Analyzing AEPX structure (headless mode)...")
        from services.aepx_processor import AEPXProcessor
        aepx_processor = AEPXProcessor(container.main_logger)

        # Process AEPX comprehensively (no AE UI will appear)
        aepx_analysis = aepx_processor.process_aepx(
            str(aepx_path),
            session_id,
            generate_thumbnails=False  # Keep headless for now
        )

        # Extract analysis results
        aepx_placeholders = aepx_analysis.get('placeholders', [])
        aepx_layer_categories = aepx_analysis.get('layer_categories', {})
        aepx_missing_footage = aepx_analysis.get('missing_footage', [])
        aepx_all_layers = aepx_analysis.get('layers', [])

        container.main_logger.info(f"✅ AEPX analysis complete:")
        container.main_logger.info(f"   - Compositions: {len(aepx_analysis.get('compositions', []))}")
        container.main_logger.info(f"   - Total layers: {len(aepx_all_layers)}")
        container.main_logger.info(f"   - Placeholders detected: {len(aepx_placeholders)}")
        container.main_logger.info(f"   - Missing footage: {len(aepx_missing_footage)}")

        # Extract fonts using service
        # IMPORTANT: If parse_method is 'photoshop', the psd_data already has correct text info
        parse_method = psd_data.get('parse_method', 'psd-tools')
        container.main_logger.info(f"PSD parsed with: {parse_method}")

        fonts_result = container.psd_service.extract_fonts(psd_data)
        if fonts_result.is_success():
            fonts = fonts_result.get_data()

            # Log which parse method was used and how many fonts found
            if parse_method == 'photoshop':
                container.main_logger.info(f'Using Photoshop-extracted font data: {len(fonts)} fonts found')
            elif parse_method == 'pillow':
                container.main_logger.warning(f'Using Pillow (limited parsing): {len(fonts)} fonts found (may be incomplete)')
            else:
                container.main_logger.info(f'Using psd-tools font data: {len(fonts)} fonts found')
        else:
            container.main_logger.warning(f'Font extraction failed: {fonts_result.get_error()}')
            fonts = []

        # Check fonts (using legacy function for now, will create service later)
        font_check = check_fonts(psd_data)

        # Check font installation status using new FontService
        font_service = FontService(container.main_logger)
        font_status_result = font_service.check_required_fonts(fonts)
        if font_status_result.is_success():
            font_status = font_status_result.get_data()
            font_summary = font_service.get_font_summary(font_status)
        else:
            container.main_logger.warning(f'Font status check failed: {font_status_result.get_error()}')
            font_status = {}
            font_summary = {"total": 0, "installed": 0, "missing": 0, "percentage": 0, "all_installed": False}

        # Store in session with job state
        sessions[session_id] = {
            'psd_path': str(psd_path),
            'aepx_path': str(aepx_path),
            'psd_data': psd_data,
            'aepx_data': aepx_data,
            'font_check': font_check,
            'font_status': font_status,
            'font_summary': font_summary,
            'fonts': fonts,
            'created_at': datetime.now(),
            # Layer exports (headless processing results)
            'exported_layers': exported_layers,
            'exports_dir': str(exports_dir),
            'flattened_preview': flattened_preview,
            'psd_dimensions': psd_dimensions,
            'fonts_from_layers': fonts_from_layers,  # Fonts detected during layer export
            'fonts_installed': fonts_installed,
            'fonts_missing': fonts_missing,
            # AEPX headless analysis results
            'aepx_analysis': aepx_analysis,
            'aepx_placeholders': aepx_placeholders,
            'aepx_layer_categories': aepx_layer_categories,
            'aepx_missing_footage': aepx_missing_footage,
            'aepx_all_layers': aepx_all_layers,
            # Job state fields
            'state': 'DRAFT',
            'preview': None,  # {psd_png, ae_mp4, generated_at}
            'validation': None,  # {ok, score, grade, report, generated_at}
            'signoff': None,  # {approved, approved_by, notes, timestamp, hashes}
            'final_render': None  # {output_mp4, status, started_at, finished_at, error}
        }

        container.main_logger.info(
            f"Session {session_id} created - PSD: {len(psd_data['layers'])} layers, "
            f"AEPX: {len(aepx_data['placeholders'])} placeholders"
        )

        return jsonify({
            'success': True,
            'message': 'Files uploaded successfully',
            'data': {
                'session_id': session_id,
                'psd': {
                    'filename': psd_data['filename'],
                    'width': psd_data['width'],
                    'height': psd_data['height'],
                    'layers': len(psd_data['layers'])
                },
                'aepx': {
                    'filename': aepx_data['filename'],
                    'composition': aepx_data['composition_name'],
                    'placeholders': len(aepx_data['placeholders']),
                    # Comprehensive headless analysis
                    'analysis': {
                        'total_layers': len(aepx_all_layers),
                        'placeholders_detected': len(aepx_placeholders),
                        'missing_footage': len(aepx_missing_footage),
                        'text_layers': len(aepx_layer_categories.get('text_layers', [])),
                        'image_layers': len(aepx_layer_categories.get('image_layers', [])),
                        'solid_layers': len(aepx_layer_categories.get('solid_layers', [])),
                        'shape_layers': len(aepx_layer_categories.get('shape_layers', [])),
                        'adjustment_layers': len(aepx_layer_categories.get('adjustment_layers', [])),
                        'unknown_layers': len(aepx_layer_categories.get('unknown_layers', []))
                    }
                },
                'fonts': {
                    'total': font_check['summary']['total'],
                    'uncommon': font_check['summary']['uncommon'],
                    'uncommon_list': font_check['uncommon_fonts'],
                    'installed': font_summary['installed'],
                    'missing': font_summary['missing'],
                    'percentage': font_summary['percentage'],
                    'all_installed': font_summary['all_installed'],
                    'status': font_status,
                    # From layer export (headless detection)
                    'from_layers': {
                        'installed': [{'family': f['family'], 'style': f['style'], 'layer': f.get('layer_name')} for f in fonts_installed],
                        'missing': [{'family': f['family'], 'style': f['style'], 'postscript_name': f.get('postscript_name'), 'layer': f.get('layer_name')} for f in fonts_missing]
                    }
                }
            }
        })

    except Exception as e:
        container.main_logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error processing files: {str(e)}'
        }), 500


@app.route('/api/upload-file', methods=['POST'])
def upload_single_file():
    """Handle single file upload for project graphics."""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        # Validate filename
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Generate unique filename
        timestamp = int(time.time())
        random_hex = os.urandom(4).hex()
        safe_filename = secure_filename(file.filename)
        unique_filename = f"{timestamp}_{random_hex}_{safe_filename}"

        # Save file
        file_path = UPLOAD_FOLDER / unique_filename
        file.save(str(file_path))

        container.main_logger.info(f"File uploaded: {unique_filename}")

        return jsonify({
            'success': True,
            'file_path': str(file_path),
            'filename': unique_filename
        })

    except Exception as e:
        container.main_logger.error(f"File upload failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'File upload failed'
        }), 500


@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get list of available AEPX templates"""
    try:
        # Check for templates in sample_files and uploads directories
        templates = []

        # Check sample_files directory
        sample_files_dir = Path('sample_files')
        if sample_files_dir.exists():
            for aepx_file in sample_files_dir.glob('*.aepx'):
                templates.append({
                    'id': aepx_file.stem,
                    'name': aepx_file.stem.replace('-', ' ').replace('_', ' ').title(),
                    'path': str(aepx_file),
                    'description': f'Template: {aepx_file.name}'
                })

        # Check uploads directory for templates
        if UPLOAD_FOLDER.exists():
            for aepx_file in UPLOAD_FOLDER.glob('*.aepx'):
                templates.append({
                    'id': aepx_file.stem,
                    'name': aepx_file.stem.replace('-', ' ').replace('_', ' ').title(),
                    'path': str(aepx_file),
                    'description': f'Template: {aepx_file.name}'
                })

        container.main_logger.info(f"Found {len(templates)} templates")

        return jsonify({
            'success': True,
            'templates': templates
        })

    except Exception as e:
        container.main_logger.error(f"Get templates failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/convert-aep', methods=['POST'])
def convert_aep():
    """Convert a single AEP file to AEPX"""
    try:
        data = request.json
        aep_path = data.get('aep_path')
        use_applescript = data.get('use_applescript', True)

        if not aep_path:
            return jsonify({'success': False, 'error': 'No AEP path provided'}), 400

        if use_applescript:
            result = container.aep_converter.convert_aep_to_aepx_applescript(aep_path)
        else:
            result = container.aep_converter.convert_aep_to_aepx_aerender(aep_path)

        if result['success']:
            return jsonify({
                'success': True,
                'aepx_path': result['aepx_path'],
                'message': 'Conversion successful'
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400

    except Exception as e:
        container.main_logger.error(f"AEP conversion failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/convert-aep-batch', methods=['POST'])
def convert_aep_batch():
    """Convert all AEP files in a directory to AEPX"""
    try:
        data = request.json or {}
        directory = data.get('directory', 'sample_files')
        use_applescript = data.get('use_applescript', True)

        result = container.aep_converter.batch_convert_directory(
            directory=directory,
            use_applescript=use_applescript
        )

        return jsonify({
            'success': result['success'],
            'total': result['total'],
            'converted': result['converted'],
            'failed': result['failed'],
            'message': result['message']
        })

    except Exception as e:
        container.main_logger.error(f"Batch AEP conversion failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scan-aep-files', methods=['GET'])
def scan_aep_files():
    """Scan for AEP files that need conversion"""
    try:
        directories = ['sample_files', 'uploads']
        all_aep_files = []

        for directory in directories:
            aep_files = container.aep_converter.find_aep_files(directory)

            for aep_path in aep_files:
                # Check if AEPX already exists
                aepx_path = aep_path.replace('.aep', '.aepx')
                needs_conversion = not os.path.exists(aepx_path)

                all_aep_files.append({
                    'path': aep_path,
                    'name': os.path.basename(aep_path),
                    'aepx_exists': os.path.exists(aepx_path),
                    'needs_conversion': needs_conversion
                })

        return jsonify({
            'success': True,
            'aep_files': all_aep_files,
            'total': len(all_aep_files),
            'needs_conversion': sum(1 for f in all_aep_files if f['needs_conversion'])
        })

    except Exception as e:
        container.main_logger.error(f"Scan AEP files failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/check-fonts', methods=['POST'])
def check_fonts_endpoint():
    """Check fonts for a PSD file - RE-CHECKS in real-time."""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]

        # Get original font check to know which fonts we need
        font_check = session.get('font_check', {})
        if not font_check:
            return jsonify({
                'success': False,
                'message': 'No font data available'
            }), 400

        # Get required fonts list
        required_fonts = font_check.get('fonts_used', [])

        if not required_fonts:
            # No fonts needed
            return jsonify({
                'success': True,
                'data': {
                    'required_fonts': [],
                    'installed_fonts': [],
                    'missing_fonts': [],
                    'missing_count': 0,
                    'total': len(required_fonts),
                    'previews': {},
                    'metadata': {}
                }
            })

        # RE-CHECK fonts in real-time using FontService
        font_service = FontService(container.main_logger)
        status_result = font_service.check_required_fonts(required_fonts)

        if not status_result.is_success():
            return jsonify({
                'success': False,
                'error': status_result.get_error()
            }), 500

        font_status = status_result.get_data()

        # Build installed and missing lists
        installed_fonts = [font for font, status in font_status.items() if status]
        missing_fonts = [font for font, status in font_status.items() if not status]

        # Generate preview images for missing fonts only
        font_previews = {}
        for font_name in missing_fonts:
            preview_filename = generate_font_preview_image(font_name)
            if preview_filename:
                font_previews[font_name] = f'/previews/{preview_filename}'

        # Build response
        response_data = {
            'required_fonts': required_fonts,
            'installed_fonts': installed_fonts,
            'missing_fonts': missing_fonts,
            'missing_count': len(missing_fonts),
            'total': len(required_fonts),
            'previews': font_previews,
            'metadata': {}  # Can be enhanced later
        }

        container.main_logger.info(
            f"Font check for session {session_id}: "
            f"{len(installed_fonts)}/{len(required_fonts)} installed"
        )

        return jsonify({
            'success': True,
            'data': response_data
        })

    except Exception as e:
        container.main_logger.error(f"Font check failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def generate_font_preview_image(font_name, sample_text="ABCabc123", size=(400, 120)):
    """
    Generate a PNG preview image showing the font.

    Args:
        font_name: Name of the font (without extension)
        sample_text: Text to render in the preview
        size: Image size (width, height)

    Returns:
        Path to the generated preview image, or None if font not found
    """
    # Find font file
    font_path = None
    for ext in ALLOWED_FONT_EXTENSIONS:
        candidate = FONTS_FOLDER / f"{font_name}.{ext}"
        if candidate.exists():
            font_path = candidate
            break

    if not font_path:
        # Font not found - generate a placeholder with system font
        img = Image.new('RGB', size, color='#f8f9fa')
        draw = ImageDraw.Draw(img)

        # Try to use default system font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except:
            font = ImageFont.load_default()

        # Draw text
        text_bbox = draw.textbbox((0, 0), sample_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (size[0] - text_width) / 2
        y = (size[1] - text_height) / 2

        draw.text((x, y), sample_text, fill='#dc3545', font=font)

        # Add "Missing" label
        try:
            label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except:
            label_font = ImageFont.load_default()
        draw.text((10, 10), "Font Missing", fill='#dc3545', font=label_font)

        # Save preview
        preview_filename = f"font_preview_{font_name}_missing_{int(time.time())}.png"
        preview_path = PREVIEWS_FOLDER / preview_filename
        img.save(preview_path)

        return preview_filename

    # Font found - generate preview with actual font
    try:
        img = Image.new('RGB', size, color='#ffffff')
        draw = ImageDraw.Draw(img)

        # Load the font
        font = ImageFont.truetype(str(font_path), 48)

        # Draw text centered
        text_bbox = draw.textbbox((0, 0), sample_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (size[0] - text_width) / 2
        y = (size[1] - text_height) / 2

        draw.text((x, y), sample_text, fill='#212529', font=font)

        # Add font name label at top
        try:
            label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except:
            label_font = ImageFont.load_default()
        draw.text((10, 10), font_name, fill='#6c757d', font=label_font)

        # Save preview
        preview_filename = f"font_preview_{font_name}_{int(time.time())}.png"
        preview_path = PREVIEWS_FOLDER / preview_filename
        img.save(preview_path)

        return preview_filename

    except Exception as e:
        print(f"Error generating font preview for {font_name}: {str(e)}")
        return None


@app.route('/generate-font-preview', methods=['POST'])
def generate_font_preview_endpoint():
    """Generate a preview image for a specific font."""
    try:
        data = request.json
        font_name = data.get('font_name')
        sample_text = data.get('sample_text', 'ABCabc123')

        if not font_name:
            return jsonify({
                'success': False,
                'message': 'Font name required'
            }), 400

        preview_filename = generate_font_preview_image(font_name, sample_text)

        if preview_filename:
            return jsonify({
                'success': True,
                'message': 'Font preview generated',
                'preview_path': f'/previews/{preview_filename}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate font preview'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating font preview: {str(e)}'
        }), 500


def generate_mapping_overlay_preview(psd_preview_path, aepx_preview_path, output_name):
    """
    Create a composite image showing PSD content overlaid on AEPX placeholder.

    Args:
        psd_preview_path: Path to PSD layer preview image
        aepx_preview_path: Path to AEPX placeholder preview image
        output_name: Name for the output composite file

    Returns:
        Filename of the generated composite preview, or None if failed
    """
    try:
        # Load both images
        psd_img = Image.open(psd_preview_path).convert('RGBA')
        aepx_img = Image.open(aepx_preview_path).convert('RGBA')

        # Get dimensions
        aepx_width, aepx_height = aepx_img.size
        psd_width, psd_height = psd_img.size

        # Resize PSD layer to fit AEPX placeholder while maintaining aspect ratio
        aspect_ratio = psd_width / psd_height
        target_aspect = aepx_width / aepx_height

        if aspect_ratio > target_aspect:
            # PSD is wider - fit to width
            new_width = aepx_width
            new_height = int(aepx_width / aspect_ratio)
        else:
            # PSD is taller - fit to height
            new_height = aepx_height
            new_width = int(aepx_height * aspect_ratio)

        psd_resized = psd_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create composite image (3 panels side by side)
        panel_width = max(aepx_width, psd_width)
        panel_height = max(aepx_height, psd_height)
        composite_width = panel_width * 3 + 40  # 3 panels + spacing
        composite_height = panel_height + 60  # Extra space for labels

        composite = Image.new('RGB', (composite_width, composite_height), color='#f8f9fa')
        draw = ImageDraw.Draw(composite)

        # Try to load a font for labels
        try:
            label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except:
            label_font = ImageFont.load_default()
            title_font = ImageFont.load_default()

        # Panel 1: PSD Layer Preview
        psd_x = 10
        psd_y = 40
        # Center PSD in panel if smaller
        psd_offset_x = (panel_width - psd_width) // 2 if psd_width < panel_width else 0
        psd_offset_y = (panel_height - psd_height) // 2 if psd_height < panel_height else 0
        composite.paste(psd_img, (psd_x + psd_offset_x, psd_y + psd_offset_y), psd_img)
        draw.text((psd_x + 5, 10), "PSD Layer", fill='#1e293b', font=label_font)
        draw.rectangle([psd_x, psd_y, psd_x + panel_width, psd_y + panel_height], outline='#667eea', width=2)

        # Panel 2: Overlay Composite
        overlay_x = panel_width + 20
        overlay_y = 40
        # Create overlay: AEPX as background with PSD on top at 70% opacity
        overlay_panel = aepx_img.copy()
        # Center the resized PSD on the AEPX placeholder
        paste_x = (aepx_width - new_width) // 2
        paste_y = (aepx_height - new_height) // 2
        # Create semi-transparent version of PSD
        psd_transparent = Image.new('RGBA', aepx_img.size, (0, 0, 0, 0))
        psd_transparent.paste(psd_resized, (paste_x, paste_y), psd_resized)
        # Blend
        overlay_panel = Image.blend(overlay_panel, psd_transparent, alpha=0.7)
        composite.paste(overlay_panel, (overlay_x, overlay_y), overlay_panel)
        draw.text((overlay_x + 5, 10), "Overlay Preview", fill='#1e293b', font=label_font)
        draw.rectangle([overlay_x, overlay_y, overlay_x + panel_width, overlay_y + panel_height], outline='#10b981', width=3)

        # Panel 3: AEPX Placeholder Preview
        aepx_x = (panel_width + 20) * 2
        aepx_y = 40
        composite.paste(aepx_img, (aepx_x, aepx_y), aepx_img)
        draw.text((aepx_x + 5, 10), "AEPX Placeholder", fill='#1e293b', font=label_font)
        draw.rectangle([aepx_x, aepx_y, aepx_x + panel_width, aepx_y + panel_height], outline='#f59e0b', width=2)

        # Add alignment info at bottom
        info_text = f"PSD: {psd_width}x{psd_height}  →  Resized: {new_width}x{new_height}  →  AEPX: {aepx_width}x{aepx_height}"
        draw.text((10, composite_height - 20), info_text, fill='#64748b', font=title_font)

        # Save composite
        composite_filename = f"mapping_preview_{output_name}_{int(time.time())}.png"
        composite_path = PREVIEWS_FOLDER / composite_filename
        composite.save(composite_path)

        return composite_filename

    except Exception as e:
        print(f"Error generating mapping overlay preview: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


@app.route('/generate-mapping-preview', methods=['POST'])
def generate_mapping_preview_endpoint():
    """Generate a composite preview showing PSD content overlaid on AEPX placeholder."""
    try:
        data = request.json
        session_id = data.get('session_id')
        psd_layer = data.get('psd_layer')
        aepx_placeholder = data.get('aepx_placeholder')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        if not psd_layer or not aepx_placeholder:
            return jsonify({
                'success': False,
                'message': 'PSD layer and AEPX placeholder names required'
            }), 400

        session = sessions[session_id]

        # Find PSD layer preview
        psd_preview_path = None
        if 'psd_layer_previews' in session:
            psd_preview_path = session['psd_layer_previews'].get(psd_layer)

        if not psd_preview_path or not Path(psd_preview_path).exists():
            return jsonify({
                'success': False,
                'message': f'PSD layer preview not found for: {psd_layer}'
            }), 404

        # Find AEPX placeholder preview
        aepx_preview_path = None
        if 'aepx_layer_previews' in session:
            aepx_preview_path = session['aepx_layer_previews'].get(aepx_placeholder)

        if not aepx_preview_path or not Path(aepx_preview_path).exists():
            return jsonify({
                'success': False,
                'message': f'AEPX placeholder preview not found for: {aepx_placeholder}'
            }), 404

        # Generate composite preview
        output_name = f"{psd_layer}_to_{aepx_placeholder}"
        composite_filename = generate_mapping_overlay_preview(
            psd_preview_path,
            aepx_preview_path,
            output_name
        )

        if composite_filename:
            return jsonify({
                'success': True,
                'message': 'Mapping preview generated',
                'preview_path': f'/previews/{composite_filename}',
                'psd_preview': f'/previews/{Path(psd_preview_path).name}',
                'aepx_preview': f'/previews/{Path(aepx_preview_path).name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate mapping preview'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating mapping preview: {str(e)}'
        }), 500


@app.route('/upload-fonts', methods=['POST'])
def upload_fonts():
    """Upload and install font files to system fonts directory."""
    try:
        if 'font_files' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No font files provided'
            }), 400

        files = request.files.getlist('font_files')
        installed = []
        errors = []

        # Create FontService instance
        font_service = FontService(container.main_logger)

        for font_file in files:
            if font_file.filename == '':
                continue

            # Validate file type
            if not allowed_file(font_file.filename, ALLOWED_FONT_EXTENSIONS):
                errors.append(f'{font_file.filename}: Invalid font format')
                continue

            # Check file size
            font_file.seek(0, os.SEEK_END)
            size = font_file.tell()
            font_file.seek(0)

            if size > MAX_FONT_SIZE:
                errors.append(f'{font_file.filename}: File too large (max 5MB)')
                continue

            # Save to temporary location with unique name
            filename = secure_filename(font_file.filename)
            temp_filename = f'{uuid.uuid4().hex}_{filename}'  # Unique temp name
            temp_path = UPLOAD_FOLDER / temp_filename
            font_file.save(str(temp_path))

            # Install font using FontService - pass original filename
            # FontService will use this as the target filename
            result = font_service.install_font(str(temp_path), filename)

            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass

            if result.is_success():
                installed.append(filename)
                container.main_logger.info(f'Font installed: {filename}')
            else:
                errors.append(f'{font_file.filename}: {result.get_error()}')
                container.main_logger.error(f'Font installation failed: {filename} - {result.get_error()}')

        if installed:
            return jsonify({
                'success': True,
                'message': f'Installed {len(installed)} font file(s) to ~/Library/Fonts',
                'data': {
                    'installed': installed,
                    'errors': errors
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No fonts were installed',
                'errors': errors
            }), 400

    except Exception as e:
        container.main_logger.error(f'Font upload failed: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Font upload failed: {str(e)}'
        }), 500


@app.route('/api/fonts/check', methods=['POST'])
def check_fonts_api():
    """Check font status for a list of required fonts."""
    try:
        data = request.json
        required_fonts = data.get('fonts', [])

        if not required_fonts:
            return jsonify({
                'success': False,
                'error': 'No fonts provided'
            }), 400

        # Create font service instance
        font_service = FontService(container.main_logger)

        # Check font status
        result = font_service.check_required_fonts(required_fonts)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 500

        font_status = result.get_data()
        summary = font_service.get_font_summary(font_status)

        return jsonify({
            'success': True,
            'fonts': font_status,
            'summary': summary
        })

    except Exception as e:
        container.main_logger.error(f"Font check failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/fonts/install', methods=['POST'])
def install_font_api():
    """Install a font file to ~/Library/Fonts."""
    try:
        if 'font_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No font file provided'
            }), 400

        font_file = request.files['font_file']
        font_name = request.form.get('font_name', '')

        if font_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Validate file type
        if not allowed_file(font_file.filename, ALLOWED_FONT_EXTENSIONS):
            return jsonify({
                'success': False,
                'error': 'Invalid font format (must be .ttf, .otf, .ttc, or .dfont)'
            }), 400

        # Save to temp location first
        filename = secure_filename(font_file.filename)
        temp_path = UPLOAD_FOLDER / filename
        font_file.save(str(temp_path))

        # Create font service and install
        font_service = FontService(container.main_logger)
        result = font_service.install_font(str(temp_path), font_name or filename)

        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'message': result.get_data()
        })

    except Exception as e:
        container.main_logger.error(f"Font installation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/fonts/copy', methods=['POST'])
def copy_font_api():
    """Copy an existing system font to AE fonts directory."""
    try:
        data = request.json
        font_name = data.get('font_name')

        if not font_name:
            return jsonify({
                'success': False,
                'error': 'No font name provided'
            }), 400

        # Create font service and copy font
        font_service = FontService(container.main_logger)
        result = font_service.copy_existing_font(font_name)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'message': result.get_data()
        })

    except Exception as e:
        container.main_logger.error(f"Font copy failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/settings', methods=['GET'])
def get_settings():
    """Get current settings."""
    try:
        result = container.settings_service.get_settings()

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'settings': result.get_data()
        })
    except Exception as e:
        container.main_logger.error(f"Get settings failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get settings'
        }), 500


@app.route('/settings', methods=['POST'])
def update_settings():
    """Update settings."""
    try:
        settings_data = request.json

        if not settings_data:
            return jsonify({
                'success': False,
                'error': 'No settings data provided'
            }), 400

        result = container.settings_service.update_settings(settings_data)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'settings': result.get_data(),
            'message': 'Settings updated successfully'
        })
    except Exception as e:
        container.main_logger.error(f"Update settings failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update settings'
        }), 500


@app.route('/settings/reset', methods=['POST'])
def reset_settings():
    """Reset settings to defaults."""
    try:
        result = container.settings_service.reset_to_defaults()

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'settings': result.get_data(),
            'message': 'Settings reset to defaults'
        })
    except Exception as e:
        container.main_logger.error(f"Reset settings failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to reset settings'
        }), 500


@app.route('/settings/validate', methods=['POST'])
def validate_settings():
    """Validate settings."""
    try:
        result = container.settings_service.validate_settings()

        if not result.is_success():
            return jsonify({
                'success': False,
                'valid': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'valid': True
        })
    except Exception as e:
        container.main_logger.error(f"Validate settings failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to validate settings'
        }), 500


@app.route('/settings-page')
def settings_page():
    """Render settings page."""
    return render_template('settings.html')


@app.route('/match', methods=['POST'])
def match_content():
    """Run content matcher and return mappings - using service layer."""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        psd_data = session['psd_data']
        aepx_data = session['aepx_data']

        container.main_logger.info(f"Matching content for session: {session_id}")

        # Match content using service
        match_result = container.matching_service.match_content(psd_data, aepx_data)

        if not match_result.is_success():
            return jsonify({
                'success': False,
                'message': f'Matching failed: {match_result.get_error()}'
            }), 500

        mappings = match_result.get_data()

        # Get matching statistics using service
        stats_result = container.matching_service.get_matching_statistics(mappings)
        stats = stats_result.get_data() if stats_result.is_success() else {}

        # Detect conflicts (using legacy function for now)
        conflicts = detect_conflicts(psd_data, aepx_data, mappings)

        # Store mappings in session
        session['mappings'] = mappings
        session['conflicts'] = conflicts

        # Check fonts
        font_check = session.get('font_check', {})
        required_fonts = font_check.get('fonts_used', [])
        font_availability = check_font_availability(required_fonts)

        container.main_logger.info(
            f"Matching complete - Session: {session_id}, "
            f"Mappings: {stats.get('total_mappings', 0)}, "
            f"Avg confidence: {stats.get('average_confidence', 0):.2f}"
        )

        return jsonify({
            'success': True,
            'message': 'Content matched successfully',
            'data': {
                'mappings': mappings['mappings'],
                'unmapped_psd': mappings['unmapped_psd_layers'],
                'unfilled_placeholders': mappings['unfilled_placeholders'],
                'conflicts': {
                    'total': conflicts['summary']['total'],
                    'critical': conflicts['summary']['critical'],
                    'warning': conflicts['summary']['warning'],
                    'info': conflicts['summary']['info'],
                    'items': conflicts['conflicts']
                },
                'fonts': {
                    'required': font_availability['required_fonts'],
                    'installed': font_availability['installed_fonts'],
                    'missing': font_availability['missing_fonts'],
                    'missing_count': len(font_availability['missing_fonts'])
                },
                'statistics': stats  # New: matching statistics from service
            }
        })

    except Exception as e:
        container.main_logger.error(f"Matching failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error matching content: {str(e)}'
        }), 500


@app.route('/generate-preview', methods=['POST'])
def generate_preview_endpoint():
    """Generate video preview - using service layer."""
    try:
        data = request.json
        session_id = data.get('session_id')
        preview_options = data.get('options', {})

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        aepx_path = session['aepx_path']
        aepx_data = session['aepx_data']
        mappings = session.get('mappings')

        if not mappings:
            return jsonify({
                'success': False,
                'message': 'No mappings found. Run match first.'
            }), 400

        container.main_logger.info(f"Generating preview for session: {session_id}")

        # Check if aerender is available using service
        aerender_result = container.preview_service.check_aerender_available()
        if not aerender_result.is_success():
            return jsonify({
                'success': False,
                'message': aerender_result.get_error(),
                'aerender_available': False
            }), 400

        aerender_path = aerender_result.get_data()
        container.main_logger.info(f"After Effects found at: {aerender_path}")

        # Add composition name to mappings (from parsed AEPX data)
        # This ensures we use the actual composition name from the template
        if 'composition_name' not in mappings:
            mappings['composition_name'] = aepx_data.get('composition_name', 'Main Comp')

        # Generate preview filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        preview_filename = f"{session_id}_{timestamp}_preview.mp4"
        preview_path = PREVIEWS_FOLDER / preview_filename

        # Validate preview options using service
        if preview_options:
            options_valid = container.preview_service.validate_options(preview_options)
            if not options_valid.is_success():
                return jsonify({
                    'success': False,
                    'message': f'Invalid options: {options_valid.get_error()}'
                }), 400

        # Generate preview using service
        preview_result = container.preview_service.generate_preview(
            aepx_path=aepx_path,
            mappings=mappings,
            output_path=str(preview_path),
            options=preview_options
        )

        if not preview_result.is_success():
            return jsonify({
                'success': False,
                'message': preview_result.get_error()
            }), 500

        result = preview_result.get_data()

        # Store in session
        session['preview_path'] = result['video_path']
        session['preview_thumbnail'] = result.get('thumbnail_path')

        # Build response URLs
        preview_url = f"/previews/{preview_filename}"
        thumbnail_url = None
        if result.get('thumbnail_path'):
            thumbnail_filename = Path(result['thumbnail_path']).name
            thumbnail_url = f"/previews/{thumbnail_filename}"

        container.main_logger.info(
            f"Preview generated - Session: {session_id}, "
            f"Duration: {result.get('duration')}s, "
            f"Resolution: {result.get('resolution')}"
        )

        return jsonify({
            'success': True,
            'message': 'Preview generated successfully',
            'data': {
                'preview_url': preview_url,
                'thumbnail_url': thumbnail_url,
                'duration': result.get('duration'),
                'resolution': result.get('resolution'),
                'aerender_available': True
            }
        })

    except Exception as e:
        container.main_logger.error(f"Preview generation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error generating preview: {str(e)}'
        }), 500


@app.route('/previews/<filename>')
def serve_preview(filename):
    """Serve preview videos and thumbnails."""
    try:
        file_path = PREVIEWS_FOLDER / filename

        if not file_path.exists():
            return jsonify({
                'success': False,
                'message': 'Preview not found'
            }), 404

        # Determine content type
        suffix = file_path.suffix.lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.gif': 'image/gif',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png'
        }
        content_type = content_types.get(suffix, 'application/octet-stream')

        return send_file(
            file_path,
            mimetype=content_type
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error serving preview: {str(e)}'
        }), 500


@app.route('/render-psd-preview', methods=['POST'])
def render_psd_preview():
    """Generate preview images for PSD file and its layers."""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        psd_path = session.get('psd_path')

        if not psd_path or not os.path.exists(psd_path):
            return jsonify({
                'success': False,
                'message': 'PSD file not found'
            }), 400

        # Generate unique prefix for this preview set
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        preview_prefix = f"{session_id}_{timestamp}"

        # Open PSD file
        psd = PSDImage.open(psd_path)

        # Render full PSD preview
        full_preview_filename = f"psd_full_{preview_prefix}.png"
        full_preview_path = PREVIEWS_FOLDER / full_preview_filename

        # Composite the full PSD and save as PNG
        full_image = psd.composite()

        # Resize to reasonable preview size (max 800px width)
        if full_image.width > 800:
            ratio = 800 / full_image.width
            new_height = int(full_image.height * ratio)
            full_image = full_image.resize((800, new_height), Image.Resampling.LANCZOS)

        full_image.save(full_preview_path, 'PNG')

        # Render individual layer previews
        layer_previews = {}
        psd_data = session.get('psd_data')

        if psd_data and 'layers' in psd_data:
            for layer_info in psd_data['layers']:
                layer_name = layer_info.get('name')

                if not layer_name:
                    continue

                try:
                    # Find the layer in the PSD
                    layer = None
                    for psd_layer in psd:
                        if psd_layer.name == layer_name:
                            layer = psd_layer
                            break

                    if layer and layer.is_visible():
                        # Generate layer preview filename
                        safe_layer_name = "".join(c if c.isalnum() else "_" for c in layer_name)
                        layer_filename = f"psd_layer_{safe_layer_name}_{preview_prefix}.png"
                        layer_path = PREVIEWS_FOLDER / layer_filename

                        # Render layer to image
                        layer_image = layer.composite()

                        if layer_image:
                            # Resize if needed
                            if layer_image.width > 400:
                                ratio = 400 / layer_image.width
                                new_height = int(layer_image.height * ratio)
                                layer_image = layer_image.resize((400, new_height), Image.Resampling.LANCZOS)

                            layer_image.save(layer_path, 'PNG')
                            layer_previews[layer_name] = f"/previews/{layer_filename}"

                except Exception as layer_error:
                    # Skip layers that fail to render
                    print(f"Warning: Failed to render layer '{layer_name}': {str(layer_error)}")
                    continue

        return jsonify({
            'success': True,
            'data': {
                'full_preview': f"/previews/{full_preview_filename}",
                'layer_previews': layer_previews
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error rendering PSD preview: {str(e)}'
        }), 500


@app.route('/render-aepx-preview', methods=['POST'])
def render_aepx_preview():
    """Generate preview images for AEPX placeholders."""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        aepx_data = session.get('aepx_data')

        if not aepx_data:
            return jsonify({
                'success': False,
                'message': 'AEPX data not found'
            }), 400

        # Generate unique prefix for this preview set
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        preview_prefix = f"{session_id}_{timestamp}"

        # Create placeholder previews
        placeholder_previews = {}
        placeholders = aepx_data.get('placeholders', [])

        for placeholder in placeholders:
            placeholder_name = placeholder.get('name')

            if not placeholder_name:
                continue

            try:
                # Create a simple image showing the placeholder name
                # Size: 400x300 with placeholder name text
                img = Image.new('RGB', (400, 300), color=(50, 50, 60))
                draw = ImageDraw.Draw(img)

                # Try to use a nice font, fall back to default
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
                    small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
                except:
                    font = ImageFont.load_default()
                    small_font = ImageFont.load_default()

                # Draw placeholder type at top
                placeholder_type = placeholder.get('type', 'text')
                draw.text((10, 10), f"Type: {placeholder_type}", fill=(180, 180, 180), font=small_font)

                # Draw placeholder name in center
                text_bbox = draw.textbbox((0, 0), placeholder_name, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (400 - text_width) // 2
                text_y = (300 - text_height) // 2
                draw.text((text_x, text_y), placeholder_name, fill=(255, 255, 255), font=font)

                # Draw dimensions if available
                if 'width' in placeholder and 'height' in placeholder:
                    dims_text = f"{placeholder['width']}x{placeholder['height']}"
                    draw.text((10, 270), dims_text, fill=(180, 180, 180), font=small_font)

                # Save preview
                safe_name = "".join(c if c.isalnum() else "_" for c in placeholder_name)
                filename = f"aepx_placeholder_{safe_name}_{preview_prefix}.png"
                filepath = PREVIEWS_FOLDER / filename
                img.save(filepath, 'PNG')

                placeholder_previews[placeholder_name] = f"/previews/{filename}"

            except Exception as placeholder_error:
                print(f"Warning: Failed to render placeholder '{placeholder_name}': {str(placeholder_error)}")
                continue

        return jsonify({
            'success': True,
            'data': {
                'placeholder_previews': placeholder_previews
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error rendering AEPX preview: {str(e)}'
        }), 500


@app.route('/generate', methods=['POST'])
def generate_script():
    """Generate ExtendScript file."""
    try:
        data = request.json
        session_id = data.get('session_id')
        custom_mappings = data.get('mappings')  # Allow custom mappings

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        psd_data = session['psd_data']
        aepx_data = session['aepx_data']

        # Use custom mappings if provided, otherwise use session mappings
        if custom_mappings:
            mappings = {'mappings': custom_mappings}
        else:
            mappings = session.get('mappings')
            if not mappings:
                return jsonify({
                    'success': False,
                    'message': 'No mappings found. Run match first.'
                }), 400

        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{session_id}_{timestamp}_script.jsx"
        output_path = OUTPUT_FOLDER / output_filename

        # Prepare options
        options = {
            'psd_file_path': session['psd_path'],
            'aepx_file_path': session['aepx_path'],
            'output_project_path': str((OUTPUT_FOLDER / f"{session_id}_output.aep").resolve()),
            'render_output': False,
            'render_path': ''
        }

        # Generate script
        jsx_path = generate_extendscript(psd_data, aepx_data, mappings, str(output_path), options)

        # Store in session
        session['jsx_path'] = jsx_path
        session['jsx_filename'] = output_filename

        return jsonify({
            'success': True,
            'message': 'Script generated successfully',
            'data': {
                'filename': output_filename,
                'download_url': f'/download/{output_filename}'
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating script: {str(e)}'
        }), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download generated script."""
    try:
        file_path = OUTPUT_FOLDER / filename

        if not file_path.exists():
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error downloading file: {str(e)}'
        }), 500


@app.route('/generate-thumbnails', methods=['POST'])
def generate_thumbnails():
    """Generate thumbnail previews for PSD layers."""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        psd_path = session.get('psd_path')

        if not psd_path:
            return jsonify({
                'success': False,
                'message': 'No PSD file in session'
            }), 400

        # Import ThumbnailService
        from services.thumbnail_service import ThumbnailService

        # Generate thumbnails
        thumbnail_service = ThumbnailService(container.main_logger)
        # Convert to absolute path for Photoshop
        psd_path = os.path.abspath(psd_path)
        
        result = thumbnail_service.generate_layer_thumbnails(
            psd_path,
            str(PREVIEWS_FOLDER),
            session_id
        )

        if not result.is_success():
            return jsonify({
                'success': False,
                'message': f'Thumbnail generation failed: {result.get_error()}'
            }), 500

        thumbnails = result.get_data()

        # Store in session
        session['thumbnails'] = thumbnails

        return jsonify({
            'success': True,
            'message': f'Generated {len(thumbnails)} thumbnails',
            'thumbnails': {
                name: f'/thumbnail/{session_id}/{filename}'
                for name, filename in thumbnails.items()
            }
        })

    except Exception as e:
        container.main_logger.error(f"Thumbnail generation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/thumbnail/<session_id>/<filename>')
def serve_thumbnail(session_id, filename):
    """Serve a layer thumbnail image."""
    try:
        # Build thumbnail path
        thumb_folder = PREVIEWS_FOLDER / "thumbnails" / session_id
        thumb_path = thumb_folder / filename

        if not thumb_path.exists():
            # Return placeholder SVG
            placeholder_svg = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="200" fill="#f0f0f0"/>
  <text x="100" y="100" font-family="Arial" font-size="14"
        fill="#999" text-anchor="middle" dominant-baseline="middle">
    No Preview
  </text>
</svg>'''
            return placeholder_svg, 200, {'Content-Type': 'image/svg+xml'}

        return send_file(thumb_path, mimetype='image/png')

    except Exception as e:
        container.main_logger.error(f"Error serving thumbnail: {e}")
        # Return error SVG
        error_svg = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="200" fill="#ffe0e0"/>
  <text x="100" y="100" font-family="Arial" font-size="14"
        fill="#cc0000" text-anchor="middle" dominant-baseline="middle">
    Error
  </text>
</svg>'''
        return error_svg, 200, {'Content-Type': 'image/svg+xml'}


@app.route('/apply-resolution', methods=['POST'])
def apply_resolution():
    """Apply a conflict resolution."""
    try:
        data = request.json
        session_id = data.get('session_id')
        conflict_id = data.get('conflict_id')
        resolution_id = data.get('resolution_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        conflicts_data = session.get('conflicts', {})

        # Find the conflict
        conflict = next(
            (c for c in conflicts_data.get('conflicts', []) if c['id'] == conflict_id),
            None
        )

        if not conflict:
            return jsonify({
                'success': False,
                'message': 'Conflict not found'
            }), 404

        # Import and create resolution service
        from services.conflict_resolution_service import ConflictResolutionService
        resolution_service = ConflictResolutionService(container.main_logger)

        psd_path = session.get('psd_path')
        output_folder = OUTPUT_FOLDER

        # Apply resolution
        result = resolution_service.apply_resolution(
            conflict, resolution_id, psd_path, str(output_folder)
        )

        if result.is_success():
            data = result.get_data()

            # Update session if file was modified
            if 'modified_path' in data:
                session['psd_path'] = data['modified_path']
                container.main_logger.info(f"Updated session PSD path to: {data['modified_path']}")

            # Mark conflict as resolved
            conflict['resolved'] = True
            conflict['resolution_applied'] = resolution_id

            return jsonify({
                'success': True,
                'message': data.get('message', 'Resolution applied successfully'),
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get_error()
            }), 400

    except Exception as e:
        container.main_logger.error(f"Resolution failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/validate-plainly', methods=['POST'])
def validate_plainly():
    """Validate AEP/AEPX file for Plainly compatibility."""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        aepx_path = session.get('aepx_path')
        aepx_data = session.get('aepx_data')

        if not aepx_path:
            return jsonify({
                'success': False,
                'message': 'No AEPX file in session'
            }), 400

        # Validate using Plainly validator service
        validation_result = container.plainly_validator_service.validate_aep(
            str(aepx_path),
            aepx_data
        )

        if not validation_result.is_success():
            return jsonify({
                'success': False,
                'message': f'Validation failed: {validation_result.get_error()}'
            }), 500

        report = validation_result.get_data()

        # Store validation report in session
        session['validation_report'] = {
            'score': report.score,
            'grade': report.grade,
            'is_valid': report.is_valid,
            'plainly_ready': report.plainly_ready,
            'summary': report.summary,
            'issues': [
                {
                    'severity': issue.severity.value,
                    'category': issue.category,
                    'message': issue.message,
                    'details': issue.details,
                    'fix_suggestion': issue.fix_suggestion,
                    'layer_name': issue.layer_name,
                    'composition_name': issue.composition_name
                }
                for issue in report.issues
            ]
        }

        # Get summary for UI display
        summary = container.plainly_validator_service.get_validation_summary(report)

        # Update session validation state for preview/sign-off workflow
        session['validation'] = {
            'ok': report.is_valid and report.plainly_ready,
            'score': report.score,
            'grade': report.grade,
            'report': session['validation_report'],
            'generated_at': now_iso()
        }

        # Update state based on result
        new_state = 'VALIDATED_OK' if (report.is_valid and report.plainly_ready) else 'VALIDATED_FAIL'
        update_job_state(session_id, new_state)

        return jsonify({
            'success': True,
            'message': 'Validation completed',
            'validation': {
                'score': report.score,
                'grade': report.grade,
                'is_valid': report.is_valid,
                'plainly_ready': report.plainly_ready,
                'summary': report.summary,
                'status_message': summary['status_message'],
                'issues': session['validation_report']['issues']
            }
        })

    except Exception as e:
        container.main_logger.error(f"Plainly validation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/apply-plainly-fixes', methods=['POST'])
def apply_plainly_fixes():
    """Automatically fix Plainly compatibility issues."""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'success': False,
                'message': 'Invalid session'
            }), 400

        session = sessions[session_id]
        aepx_data = session.get('aepx_data')
        validation_report = session.get('validation_report')

        if not aepx_data:
            return jsonify({
                'success': False,
                'message': 'No AEPX data in session'
            }), 400

        if not validation_report:
            return jsonify({
                'success': False,
                'message': 'No validation report found. Run validation first.'
            }), 400

        # Reconstruct ValidationReport object from stored data
        from modules.phase6.plainly_validator import ValidationReport, ValidationIssue, ValidationSeverity

        issues = [
            ValidationIssue(
                severity=ValidationSeverity(issue['severity']),
                category=issue['category'],
                message=issue['message'],
                details=issue['details'],
                fix_suggestion=issue['fix_suggestion'],
                layer_name=issue.get('layer_name'),
                composition_name=issue.get('composition_name')
            )
            for issue in validation_report['issues']
        ]

        report = ValidationReport(
            is_valid=validation_report['is_valid'],
            score=validation_report['score'],
            grade=validation_report['grade'],
            issues=issues,
            summary=validation_report['summary'],
            plainly_ready=validation_report['plainly_ready']
        )

        # Apply auto-fixes
        fix_result = container.plainly_validator_service.apply_auto_fixes(aepx_data, report)

        if not fix_result.is_success():
            return jsonify({
                'success': False,
                'message': f'Auto-fix failed: {fix_result.get_error()}'
            }), 500

        fix_data = fix_result.get_data()

        # Update session with modified aepx_data
        session['aepx_data'] = aepx_data

        # Re-validate to get updated report
        aepx_path = session.get('aepx_path')
        new_validation_result = container.plainly_validator_service.validate_aep(
            str(aepx_path),
            aepx_data
        )

        if new_validation_result.is_success():
            new_report = new_validation_result.get_data()

            # Update session with new report
            session['validation_report'] = {
                'score': new_report.score,
                'grade': new_report.grade,
                'is_valid': new_report.is_valid,
                'plainly_ready': new_report.plainly_ready,
                'summary': new_report.summary,
                'issues': [
                    {
                        'severity': issue.severity.value,
                        'category': issue.category,
                        'message': issue.message,
                        'details': issue.details,
                        'fix_suggestion': issue.fix_suggestion,
                        'layer_name': issue.layer_name,
                        'composition_name': issue.composition_name
                    }
                    for issue in new_report.issues
                ]
            }

            summary = container.plainly_validator_service.get_validation_summary(new_report)

            return jsonify({
                'success': True,
                'message': f'Successfully fixed {fix_data.fixed_count} issues!',
                'fix_result': {
                    'fixed_count': fix_data.fixed_count,
                    'changes': fix_data.changes,
                    'errors': fix_data.errors
                },
                'validation': {
                    'score': new_report.score,
                    'grade': new_report.grade,
                    'is_valid': new_report.is_valid,
                    'plainly_ready': new_report.plainly_ready,
                    'summary': new_report.summary,
                    'status_message': summary['status_message'],
                    'issues': session['validation_report']['issues']
                }
            })
        else:
            # Return fix results even if re-validation fails
            return jsonify({
                'success': True,
                'message': f'Fixed {fix_data.fixed_count} issues (re-validation failed)',
                'fix_result': {
                    'fixed_count': fix_data.fixed_count,
                    'changes': fix_data.changes,
                    'errors': fix_data.errors
                }
            })

    except Exception as e:
        container.main_logger.error(f"Auto-fix failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================================
# PREVIEW & SIGN-OFF WORKFLOW
# ============================================================================

@app.route('/previews/generate', methods=['POST'])
def previews_generate():
    """Generate PSD PNG and AE MP4 preview renders"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({'success': False, 'error': 'Invalid session'}), 400

        session = sessions[session_id]

        # Guard: Check validation requirement (Mode A)
        if VALIDATE_BEFORE_PREVIEW:
            validation = session.get('validation')
            if not (validation and validation.get('ok')):
                return jsonify({
                    'success': False,
                    'error': 'Validation must pass before generating previews (Mode A).'
                }), 400

        psd_path = session.get('psd_path')
        aepx_path = session.get('aepx_path')

        # Create preview directory for this session
        preview_dir = PREVIEWS_FOLDER / "session_previews" / session_id
        preview_dir.mkdir(parents=True, exist_ok=True)

        # Generate PSD PNG (left preview)
        psd_png_path = str(preview_dir / f"psd_preview_{session_id}.png")
        from services.thumbnail_service import ThumbnailService
        thumb_service = ThumbnailService(container.main_logger)

        # Render full PSD as flattened PNG
        psd_result = thumb_service.render_psd_to_png(psd_path, psd_png_path)

        if not psd_result.is_success():
            return jsonify({
                'success': False,
                'error': f'PSD preview generation failed: {psd_result.get_error()}'
            }), 500

        # Generate AE MP4 (right preview)
        ae_mp4_path = str(preview_dir / f"ae_preview_{session_id}.mp4")

        # Get mappings from session
        mappings_data = {
            'mappings': session.get('mappings', []),
            'composition_name': session.get('aepx_data', {}).get('compositions', [{}])[0].get('name', 'Main Comp')
        }

        # Build image_sources from exported layers
        exported_layers = session.get('exported_layers', {})
        image_sources = {}
        for layer_name, layer_info in exported_layers.items():
            if layer_info.get('type') == 'pixel':
                # Add both by layer name and safe filename
                image_sources[layer_name] = layer_info['path']
                # Also add lowercase version for case-insensitive matching
                image_sources[layer_name.lower()] = layer_info['path']

        # Use existing preview generator with draft settings
        from modules.phase5.preview_generator import generate_preview
        preview_result = generate_preview(
            aepx_path=aepx_path,
            mappings=mappings_data,
            output_path=ae_mp4_path,
            options={
                'resolution': 'half',  # Draft quality
                'duration': 5.0,
                'format': 'mp4',
                'quality': 'draft',
                'fps': 15,
                'image_sources': image_sources,  # Pass exported layer images
                'psd_path': psd_path  # Pass PSD path for reference
            }
        )

        if not preview_result['success']:
            return jsonify({
                'success': False,
                'error': f'AE preview generation failed: {preview_result.get("message")}'
            }), 500

        # Store preview info in session
        session['preview'] = {
            'psd_png': psd_png_path,
            'ae_mp4': ae_mp4_path,
            'generated_at': now_iso()
        }

        # Update state
        update_job_state(session_id, 'PREVIEW_READY')

        return jsonify({
            'success': True,
            'message': 'Previews generated successfully',
            'state': session['state'],
            'preview': {
                'psd_png_url': f'/preview-file/{session_id}/psd',
                'ae_mp4_url': f'/preview-file/{session_id}/ae',
                'generated_at': session['preview']['generated_at']
            }
        })

    except Exception as e:
        container.main_logger.error(f"Preview generation error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/preview-file/<session_id>/<file_type>')
def serve_preview_file(session_id, file_type):
    """Serve preview files (psd or ae)"""
    try:
        if session_id not in sessions:
            return "Session not found", 404

        preview = sessions[session_id].get('preview')
        if not preview:
            return "Preview not generated", 404

        if file_type == 'psd':
            file_path = preview.get('psd_png')
        elif file_type == 'ae':
            file_path = preview.get('ae_mp4')
        else:
            return "Invalid file type", 400

        if not file_path or not Path(file_path).exists():
            return "File not found", 404

        return send_file(file_path)

    except Exception as e:
        container.main_logger.error(f"Error serving preview: {e}")
        return "Error serving file", 500


@app.route('/signoff/approve', methods=['POST'])
def signoff_approve():
    """Approve previews and kick off final render"""
    try:
        data = request.json
        session_id = data.get('session_id')
        notes = data.get('notes', '')
        user = data.get('user', 'user')  # Could integrate with auth system

        if not session_id or session_id not in sessions:
            return jsonify({'success': False, 'error': 'Invalid session'}), 400

        session = sessions[session_id]

        # Guards
        if REQUIRE_SIGNOFF_FOR_RENDER:
            # Check validation (Mode A only)
            if VALIDATE_BEFORE_PREVIEW:
                validation = session.get('validation')
                if not (validation and validation.get('ok')):
                    return jsonify({
                        'success': False,
                        'error': 'Validation must pass before sign-off (Mode A).'
                    }), 400

            # Check previews exist
            preview = session.get('preview')
            if not (preview and preview.get('psd_png') and preview.get('ae_mp4')):
                return jsonify({
                    'success': False,
                    'error': 'Generate previews before sign-off.'
                }), 400

        # Calculate hashes for audit trail
        preview = session.get('preview', {})
        hashes = {
            'psd_png_sha256': sha256_file(preview.get('psd_png')) if preview.get('psd_png') else None,
            'ae_mp4_sha256': sha256_file(preview.get('ae_mp4')) if preview.get('ae_mp4') else None
        }

        # Store signoff
        session['signoff'] = {
            'approved': True,
            'approved_by': user,
            'notes': notes,
            'timestamp': now_iso(),
            'hashes': hashes
        }

        # Update state
        update_job_state(session_id, 'APPROVED', user=user)

        # Kick off final render (async)
        # For now, just prepare - actual render would be background task
        session['final_render'] = {
            'status': 'queued',
            'queued_at': now_iso()
        }

        container.main_logger.info(
            f"Sign-off approved for session {session_id} by {user}. Final render queued."
        )

        return jsonify({
            'success': True,
            'message': 'Approved! Final render queued.',
            'state': session['state'],
            'signoff': {
                'approved': True,
                'approved_by': user,
                'timestamp': session['signoff']['timestamp']
            }
        })

    except Exception as e:
        container.main_logger.error(f"Sign-off error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PROJECT MANAGEMENT API - With Audit Trail
# ============================================================================

@app.route('/api/projects', methods=['GET', 'POST'])
def projects():
    """List all projects or create a new project"""
    if request.method == 'GET':
        try:
            result = container.project_service.list_projects()

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 400

            return jsonify({
                'success': True,
                'projects': result.get_data()
            })
        except Exception as e:
            container.logger.error(f"List projects failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to list projects'}), 500

    else:  # POST
        try:
            data = request.json or {}
            name = data.get('name')
            client = data.get('client', '')
            description = data.get('description', '')

            if not name:
                return jsonify({
                    'success': False,
                    'error': 'Project name is required'
                }), 400

            result = container.project_service.create_project(name, client, description)

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 400

            return jsonify({
                'success': True,
                'project': result.get_data()
            })
        except Exception as e:
            container.logger.error(f"Create project failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to create project'}), 500


@app.route('/api/projects/<project_id>', methods=['GET', 'DELETE'])
def project_detail(project_id):
    """Get or delete a specific project"""
    if request.method == 'GET':
        try:
            result = container.project_service.get_project(project_id)

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 404

            return jsonify({
                'success': True,
                'project': result.get_data()
            })
        except Exception as e:
            container.logger.error(f"Get project failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to get project'}), 500

    else:  # DELETE
        try:
            result = container.project_service.delete_project(project_id)

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 404

            return jsonify({
                'success': True,
                'message': 'Project deleted successfully'
            })
        except Exception as e:
            container.logger.error(f"Delete project failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to delete project'}), 500


@app.route('/api/projects/<project_id>/graphics', methods=['GET', 'POST'])
def graphics(project_id):
    """List graphics in a project or create a new graphic"""
    if request.method == 'GET':
        try:
            result = container.project_service.get_project(project_id)

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 404

            project = result.get_data()
            return jsonify({
                'success': True,
                'graphics': project['graphics']
            })
        except Exception as e:
            container.logger.error(f"List graphics failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to list graphics'}), 500

    else:  # POST
        try:
            data = request.json or {}
            name = data.get('name')
            psd_path = data.get('psd_path')

            if not name:
                return jsonify({
                    'success': False,
                    'error': 'Graphic name is required'
                }), 400

            result = container.project_service.create_graphic(project_id, name, psd_path)

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 400

            return jsonify({
                'success': True,
                'graphic': result.get_data()
            })
        except Exception as e:
            container.logger.error(f"Create graphic failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to create graphic'}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>', methods=['GET', 'PUT'])
def graphic_detail(project_id, graphic_id):
    """Get or update a specific graphic"""
    if request.method == 'GET':
        try:
            result = container.project_service.get_graphic(project_id, graphic_id)

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 404

            return jsonify({
                'success': True,
                'graphic': result.get_data()
            })
        except Exception as e:
            container.logger.error(f"Get graphic failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to get graphic'}), 500

    else:  # PUT
        try:
            data = request.json or {}
            user = data.pop('user', 'system')

            result = container.project_service.update_graphic(project_id, graphic_id, data, user)

            if not result.is_success():
                return jsonify({
                    'success': False,
                    'error': result.get_error()
                }), 400

            return jsonify({
                'success': True,
                'graphic': result.get_data()
            })
        except Exception as e:
            container.logger.error(f"Update graphic failed: {e}", exc_info=True)
            return jsonify({'error': 'Failed to update graphic'}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/approve', methods=['POST'])
def approve_graphic(project_id, graphic_id):
    """Approve a graphic for production - requires user identity"""
    try:
        data = request.json or {}
        approved_by = data.get('approved_by')

        # Validate user identity is provided
        if not approved_by:
            return jsonify({
                'success': False,
                'error': 'User identity (approved_by) is required'
            }), 400

        result = container.project_service.approve_graphic(project_id, graphic_id, approved_by)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        graphic = result.get_data()

        return jsonify({
            'success': True,
            'graphic': graphic,
            'message': f'Graphic approved by {approved_by} at {graphic["approved_at"]}'
        })
    except Exception as e:
        container.logger.error(f"Approve graphic failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to approve graphic'}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/unapprove', methods=['POST'])
def unapprove_graphic(project_id, graphic_id):
    """Unapprove a graphic - requires user identity"""
    try:
        data = request.json or {}
        unapproved_by = data.get('unapproved_by')

        if not unapproved_by:
            return jsonify({
                'success': False,
                'error': 'User identity (unapproved_by) is required'
            }), 400

        result = container.project_service.unapprove_graphic(project_id, graphic_id, unapproved_by)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'graphic': result.get_data(),
            'message': f'Graphic unapproved by {unapproved_by} - you can now edit it'
        })
    except Exception as e:
        container.logger.error(f"Unapprove graphic failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to unapprove graphic'}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/audit-log', methods=['GET'])
def get_audit_log(project_id, graphic_id):
    """Get complete audit history for a graphic"""
    try:
        result = container.project_service.get_graphic_audit_log(project_id, graphic_id)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'audit': result.get_data()
        })
    except Exception as e:
        container.logger.error(f"Get audit log failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get audit log'}), 500


@app.route('/api/projects/<project_id>/audit-report', methods=['GET'])
def export_audit_report(project_id):
    """Export complete audit trail for project"""
    try:
        result = container.project_service.export_audit_report(project_id)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        return jsonify({
            'success': True,
            'report': result.get_data()
        })
    except Exception as e:
        container.logger.error(f"Export audit report failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to export audit report'}), 500


@app.route('/api/projects/<project_id>/process-batch', methods=['POST'])
def process_batch(project_id):
    """Process all graphics in project using batch processing"""
    try:
        data = request.json or {}

        # Get current user
        user = data.get('user', 'system')

        # Get settings with defaults
        settings_result = container.settings_service.get_settings()
        default_settings = settings_result.get_data() if settings_result.is_success() else {}

        auto_process_threshold = data.get(
            'auto_process_threshold',
            default_settings.get('advanced', {}).get('ml_confidence_threshold', 0.85)
        )

        require_manual_review = data.get(
            'require_manual_review',
            False
        )

        # Process batch
        result = container.project_service.process_project_batch(
            project_id=project_id,
            auto_process_threshold=auto_process_threshold,
            require_manual_review=require_manual_review,
            user=user
        )

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

        data = result.get_data()

        return jsonify({
            'success': True,
            'project': data['project'],
            'batch_results': data['batch_results'],
            'message': f"Processed {data['batch_results']['total']} graphics - "
                      f"{data['batch_results']['completed']} completed, "
                      f"{data['batch_results']['needs_review']} need review, "
                      f"{data['batch_results']['failed']} failed"
        })

    except Exception as e:
        container.main_logger.error(f"Batch processing failed: {e}", exc_info=True)
        return jsonify({'error': 'Batch processing failed'}), 500


@app.route('/api/projects/<project_id>/export', methods=['POST'])
def export_project(project_id):
    """Export project as ZIP file"""
    try:
        # Get project
        result = container.project_service.get_project(project_id)

        if not result.is_success():
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404

        project = result.get_data()

        # Export project
        export_result = container.export_service.export_project(project)

        if not export_result.is_success():
            return jsonify({
                'success': False,
                'error': export_result.get_error()
            }), 400

        export_data = export_result.get_data()

        return jsonify({
            'success': True,
            'zip_path': export_data['zip_path'],
            'zip_filename': export_data['zip_filename'],
            'file_size': export_data['file_size'],
            'graphics_count': export_data['graphics_count'],
            'message': f"Exported {export_data['graphics_count']} graphics"
        })

    except Exception as e:
        container.main_logger.error(f"Project export failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/exports/<filename>')
def download_export(filename):
    """Download exported ZIP file"""
    try:
        export_path = os.path.join('exports', filename)

        if not os.path.exists(export_path):
            return jsonify({'error': 'Export file not found'}), 404

        return send_file(
            export_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        container.main_logger.error(f"Download failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# EXPRESSION SYSTEM API ENDPOINTS
# ============================================================================

@app.route('/api/projects/<project_id>/graphics/<graphic_id>/expression-recommendations', methods=['GET'])
def get_expression_recommendations(project_id, graphic_id):
    """Get AI recommendations for expressions on a graphic"""
    try:
        # Get project and graphic
        project_result = container.project_service.get_project(project_id)
        if not project_result.is_success():
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = project_result.get_data()
        graphic = next((g for g in project['graphics'] if g['id'] == graphic_id), None)

        if not graphic:
            return jsonify({'success': False, 'error': 'Graphic not found'}), 404

        # Check if graphic has been processed
        if not graphic.get('aepx_output_path'):
            return jsonify({
                'success': False,
                'error': 'Graphic has not been processed yet'
            }), 400

        # Get expression recommendations
        result = container.project_service._generate_expressions_for_graphic(
            project_id=project_id,
            graphic_id=graphic_id,
            aepx_path=graphic['aepx_output_path']
        )

        if result.is_success():
            data = result.get_data()
            return jsonify({
                'success': True,
                'recommendations': data.get('recommendations', []),
                'statistics': {
                    'applied_count': data.get('applied_count', 0),
                    'skipped_count': data.get('skipped_count', 0),
                    'total_count': data.get('total_count', 0),
                    'avg_confidence': data.get('avg_confidence', 0.0)
                },
                'total': len(data.get('recommendations', []))
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

    except Exception as e:
        container.main_logger.error(f"Get recommendations failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/generate-expressions', methods=['POST'])
def generate_expressions_manual(project_id, graphic_id):
    """Manually trigger expression generation for a graphic"""
    try:
        data = request.json or {}
        confidence_threshold = data.get('confidence_threshold', 0.7)

        # Get graphic
        project_result = container.project_service.get_project(project_id)
        if not project_result.is_success():
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = project_result.get_data()
        graphic = next((g for g in project['graphics'] if g['id'] == graphic_id), None)

        if not graphic or not graphic.get('aepx_output_path'):
            return jsonify({
                'success': False,
                'error': 'Graphic not ready for expression generation'
            }), 400

        # Generate expressions
        result = container.project_service._generate_expressions_for_graphic(
            project_id=project_id,
            graphic_id=graphic_id,
            aepx_path=graphic['aepx_output_path']
        )

        if result.is_success():
            data = result.get_data()
            return jsonify({
                'success': True,
                'applied_count': data.get('applied_count', 0),
                'skipped_count': data.get('skipped_count', 0),
                'confidence': data.get('avg_confidence', 0.0),
                'message': f"Applied {data.get('applied_count', 0)} expressions"
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

    except Exception as e:
        container.main_logger.error(f"Generate expressions failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/hard-card/info', methods=['GET'])
def get_hard_card_info():
    """Get Hard Card composition information"""
    try:
        hard_card_dict = container.hard_card_generator.generate_hard_card_dict()

        # Group variables by category for easier display
        variables_by_category = {}
        for layer in hard_card_dict['layers']:
            # Parse category from layer name (simplified)
            var_name = layer['name'][1:]  # Remove 'z' prefix

            # Determine category (simplified logic)
            if var_name.startswith('home') or var_name.startswith('away'):
                category = 'Team'
            elif var_name.startswith('player'):
                category = 'Player'
            elif var_name.startswith('event'):
                category = 'Event'
            elif 'score' in var_name.lower():
                category = 'Score'
            elif var_name.startswith('featured') or 'logo' in var_name.lower():
                category = 'Media'
            else:
                category = 'Template'

            if category not in variables_by_category:
                variables_by_category[category] = []

            variables_by_category[category].append({
                'name': layer['name'],
                'display_name': var_name,
                'default_value': layer['source_text']
            })

        return jsonify({
            'success': True,
            'hard_card': {
                'name': hard_card_dict['name'],
                'width': hard_card_dict['width'],
                'height': hard_card_dict['height'],
                'total_variables': len(hard_card_dict['layers']),
                'variables_by_category': variables_by_category
            }
        })

    except Exception as e:
        container.main_logger.error(f"Get Hard Card info failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/hard-card/download', methods=['GET'])
def download_hard_card():
    """Download Hard_Card.json file"""
    try:
        import tempfile

        # Generate Hard Card
        hard_card_dict = container.hard_card_generator.generate_hard_card_dict()

        # Convert to JSON
        hard_card_json = json.dumps(hard_card_dict, indent=2)

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(hard_card_json)
            temp_path = f.name

        # Send file
        from flask import make_response

        response = make_response(send_file(
            temp_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='Hard_Card.json'
        ))

        # Clean up temp file after sending
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(temp_path)
            except:
                pass

        return response

    except Exception as e:
        container.main_logger.error(f"Download Hard Card failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_id>/expression-stats', methods=['GET'])
def get_project_expression_stats(project_id):
    """Get expression statistics for entire project"""
    try:
        project_result = container.project_service.get_project(project_id)
        if not project_result.is_success():
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = project_result.get_data()
        graphics = project.get('graphics', [])

        # Calculate statistics
        total_graphics = len(graphics)
        graphics_with_expressions = [g for g in graphics if g.get('has_expressions', False)]
        total_expressions = sum(g.get('expression_count', 0) for g in graphics_with_expressions)

        avg_confidence = 0.0
        if graphics_with_expressions:
            avg_confidence = sum(
                g.get('expression_confidence', 0) for g in graphics_with_expressions
            ) / len(graphics_with_expressions)

        # Hard Card info
        has_hard_card = project.get('metadata', {}).get('hard_card', {}).get('generated', False)

        return jsonify({
            'success': True,
            'statistics': {
                'total_graphics': total_graphics,
                'graphics_with_expressions': len(graphics_with_expressions),
                'total_expressions': total_expressions,
                'average_confidence': round(avg_confidence, 2),
                'has_hard_card': has_hard_card,
                'hard_card_variables': 185 if has_hard_card else 0
            }
        })

    except Exception as e:
        container.main_logger.error(f"Get expression stats failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ASPECT RATIO REVIEW API
# ============================================================================

@app.route('/api/projects/<project_id>/graphics/<graphic_id>/aspect-ratio-review', methods=['GET'])
def get_aspect_ratio_review(project_id, graphic_id):
    """Get aspect ratio review details including preview paths"""
    try:
        project_result = container.project_service.get_project(project_id)
        if not project_result.is_success():
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = project_result.get_data()
        graphic = next((g for g in project['graphics'] if g['id'] == graphic_id), None)

        if not graphic:
            return jsonify({'success': False, 'error': 'Graphic not found'}), 404

        # Get aspect ratio check data
        aspect_check = graphic.get('aspect_ratio_check', {})

        if not aspect_check:
            return jsonify({
                'success': False,
                'error': 'No aspect ratio check data available'
            }), 404

        # Build response with preview URLs
        response_data = {
            'success': True,
            'graphic_id': graphic_id,
            'graphic_name': graphic.get('name', 'Unknown'),
            'psd_category': aspect_check.get('psd_category'),
            'aepx_category': aspect_check.get('aepx_category'),
            'psd_dimensions': aspect_check.get('psd_dimensions'),
            'aepx_dimensions': aspect_check.get('aepx_dimensions'),
            'transformation_type': aspect_check.get('transformation_type'),
            'ratio_difference': aspect_check.get('ratio_difference'),
            'confidence': aspect_check.get('confidence'),
            'reasoning': aspect_check.get('reasoning'),
            'recommended_action': aspect_check.get('recommended_action'),
            'needs_review': aspect_check.get('needs_review', False)
        }

        # Add preview URLs if available
        previews = aspect_check.get('previews', {})
        if previews:
            # Convert file paths to API URLs
            response_data['previews'] = {
                'original_url': f"/api/projects/{project_id}/graphics/{graphic_id}/aspect-ratio-preview/original",
                'fit_url': f"/api/projects/{project_id}/graphics/{graphic_id}/aspect-ratio-preview/fit",
                'fill_url': f"/api/projects/{project_id}/graphics/{graphic_id}/aspect-ratio-preview/fill"
            }
            response_data['has_previews'] = True
        else:
            response_data['has_previews'] = False

        return jsonify(response_data)

    except Exception as e:
        container.main_logger.error(f"Get aspect ratio review failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/aspect-ratio-preview/<preview_type>', methods=['GET'])
def get_aspect_ratio_preview_image(project_id, graphic_id, preview_type):
    """Serve aspect ratio preview images"""
    try:
        from flask import send_file

        # Validate preview type
        if preview_type not in ['original', 'fit', 'fill']:
            return jsonify({'error': 'Invalid preview type'}), 400

        # Get project and graphic
        project_result = container.project_service.get_project(project_id)
        if not project_result.is_success():
            return jsonify({'error': 'Project not found'}), 404

        project = project_result.get_data()
        graphic = next((g for g in project['graphics'] if g['id'] == graphic_id), None)

        if not graphic:
            return jsonify({'error': 'Graphic not found'}), 404

        # Get preview path
        aspect_check = graphic.get('aspect_ratio_check', {})
        previews = aspect_check.get('previews', {})

        # Try thumbnail first (for UI), fall back to full-size
        thumbnails = previews.get('thumbnails', {})
        if preview_type in thumbnails:
            preview_path = thumbnails[preview_type]
        elif preview_type in previews:
            preview_path = previews[preview_type]
        else:
            return jsonify({'error': 'Preview not found'}), 404

        # Check if file exists
        if not os.path.exists(preview_path):
            return jsonify({'error': 'Preview file not found'}), 404

        # Serve image
        return send_file(
            preview_path,
            mimetype='image/jpeg',
            as_attachment=False
        )

    except Exception as e:
        container.main_logger.error(f"Serve preview image failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/aspect-ratio-decision', methods=['POST'])
def submit_aspect_ratio_decision(project_id, graphic_id):
    """Process human decision on aspect ratio transformation"""
    try:
        data = request.json or {}
        human_decision = data.get('decision')  # 'proceed', 'skip', 'manual_fix'
        transform_method = data.get('method', 'fit')  # 'fit' or 'fill'

        # Validate decision
        if human_decision not in ['proceed', 'skip', 'manual_fix']:
            return jsonify({
                'success': False,
                'error': 'Invalid decision. Must be: proceed, skip, or manual_fix'
            }), 400

        # Validate method
        if transform_method not in ['fit', 'fill']:
            return jsonify({
                'success': False,
                'error': 'Invalid method. Must be: fit or fill'
            }), 400

        container.main_logger.info(
            f"Processing aspect ratio decision for {graphic_id}: "
            f"decision={human_decision}, method={transform_method}"
        )

        # Process decision
        result = container.project_service.handle_aspect_ratio_decision(
            project_id=project_id,
            graphic_id=graphic_id,
            human_decision=human_decision,
            transform_method=transform_method
        )

        if result.is_success():
            data = result.get_data()
            return jsonify({
                'success': True,
                'status': data.get('status'),
                'message': f"Decision '{human_decision}' processed successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get_error()
            }), 400

    except Exception as e:
        container.main_logger.error(f"Submit aspect ratio decision failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/aspect-ratio/learning-stats', methods=['GET'])
def get_aspect_ratio_learning_stats():
    """Get aspect ratio learning system statistics"""
    try:
        stats = container.project_service.aspect_ratio_handler.get_learning_stats()

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        container.main_logger.error(f"Get learning stats failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/aspect-ratio/learning-data/export', methods=['GET'])
def export_aspect_ratio_learning_data():
    """Download aspect ratio learning data as JSON"""
    try:
        from flask import send_file
        import tempfile
        import json

        # Get learning data
        learning_data = container.project_service.aspect_ratio_handler.learning_data

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(learning_data, f, indent=2)
            temp_path = f.name

        # Send file
        return send_file(
            temp_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='aspect_ratio_learning_data.json'
        )

    except Exception as e:
        container.main_logger.error(f"Export learning data failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ERROR RECOVERY ENDPOINTS
# ============================================================================

@app.route('/api/projects/<project_id>/graphics/<graphic_id>/retry', methods=['POST'])
def retry_graphic(project_id, graphic_id):
    """Retry a failed graphic"""
    try:
        data = request.json or {}
        from_step = data.get('from_step')

        result = container.recovery_service.retry_graphic(
            project_id=project_id,
            graphic_id=graphic_id,
            from_step=from_step
        )

        if result.is_success():
            return jsonify({'success': True, 'data': result.get_data()})
        else:
            return jsonify({'success': False, 'error': result.get_error()}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/diagnose', methods=['GET'])
def diagnose_graphic_error(project_id, graphic_id):
    """Diagnose why a graphic failed"""
    try:
        result = container.recovery_service.diagnose_error(
            project_id=project_id,
            graphic_id=graphic_id
        )

        if result.is_success():
            return jsonify({'success': True, 'diagnosis': result.get_data()})
        else:
            return jsonify({'success': False, 'error': result.get_error()}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>/graphics/<graphic_id>/reset', methods=['POST'])
def reset_graphic_state(project_id, graphic_id):
    """Reset graphic to specific state"""
    try:
        data = request.json or {}
        to_state = data.get('state', 'pending')

        result = container.recovery_service.reset_graphic_state(
            project_id=project_id,
            graphic_id=graphic_id,
            to_state=to_state
        )

        if result.is_success():
            return jsonify({'success': True, 'data': result.get_data()})
        else:
            return jsonify({'success': False, 'error': result.get_error()}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>/bulk-retry', methods=['POST'])
def bulk_retry_graphics(project_id):
    """Retry multiple or all failed graphics"""
    try:
        data = request.json or {}
        graphic_ids = data.get('graphic_ids')
        from_step = data.get('from_step')

        result = container.recovery_service.bulk_retry(
            project_id=project_id,
            graphic_ids=graphic_ids,
            from_step=from_step
        )

        if result.is_success():
            return jsonify({'success': True, 'data': result.get_data()})
        else:
            return jsonify({'success': False, 'error': result.get_error()}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PERFORMANCE & DEBUGGING
# ============================================================================

@app.route('/api/performance-summary', methods=['GET'])
def get_performance_summary():
    """Get performance summary from enhanced logging (if enabled)"""
    try:
        # Check if enhanced logging is enabled
        if not hasattr(container, 'enhanced_logging') or container.enhanced_logging is None:
            return jsonify({
                'success': False,
                'error': 'Enhanced logging is not enabled. Set USE_ENHANCED_LOGGING=true to enable.'
            }), 400

        # Get performance summary
        summary = container.enhanced_logging.get_performance_summary()

        return jsonify({
            'success': True,
            'data': {
                'summary': summary,
                'total_operations': len(summary),
                'note': 'Performance data collected since server start'
            }
        })

    except Exception as e:
        container.main_logger.error(f"Error getting performance summary: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/thumbnail-test')
def thumbnail_test():
    """Simple test page for viewing thumbnails"""
    return render_template('thumbnail_test.html')


# ============================================================================
# PRODUCTION BATCH PROCESSING API
# ============================================================================

# Initialize database on startup
init_database()

# Initialize services
batch_validator = BatchValidator(container.main_logger)
job_service = JobService(container.main_logger)
warning_service = WarningService(container.main_logger)
log_service = LogService(container.main_logger)
stage1_processor = Stage1Processor(container.main_logger)

# Import and initialize Stage Transition Manager
from services.stage_transition_manager import StageTransitionManager
transition_manager = StageTransitionManager(container.main_logger)

# Import and initialize Match Validation Service
from services.match_validation_service import MatchValidationService
match_validator = MatchValidationService(container.main_logger)


@app.route('/api/batch/upload', methods=['POST'])
def upload_batch_csv():
    """
    Upload and validate CSV batch file.

    Returns validated batch ready for processing.
    """
    try:
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


@app.route('/api/batch/<batch_id>/start-processing', methods=['POST'])
def start_batch_processing(batch_id: str):
    """
    Start Stage 1 automated processing for a batch.

    Processes all jobs in the batch through automated ingestion.
    """
    try:
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


@app.route('/api/batch/<batch_id>', methods=['GET'])
def get_batch_status(batch_id: str):
    """Get batch status and job summary."""
    try:
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


@app.route('/api/job/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get detailed job status."""
    try:
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


@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get production dashboard statistics."""
    try:
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


@app.route('/api/jobs/stage/<int:stage>', methods=['GET'])
def get_jobs_by_stage(stage: int):
    """Get all jobs in a specific stage."""
    try:
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


# ============================================================================
# STAGE TRANSITION & APPROVAL ENDPOINTS
# ============================================================================

@app.route('/api/job/<job_id>/approve-stage2', methods=['POST'])
def approve_stage2_matching(job_id: str):
    """
    Approve Stage 2 layer matching and run validation.

    6-STAGE PIPELINE WORKFLOW:
    - Save matches to stage2_approved_matches
    - Transition to Stage 3 (Auto-Validation)
    - Run validation checks automatically
    - If critical issues: Move to Stage 4 (Validation Review) and return validation_url
    - If no critical issues: Skip Stage 4, move directly to Stage 5 (ExtendScript Generation)

    Expects JSON body with approved matches:
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
            job.status = 'awaiting_download'  # ExtendScript ready for download (after Stage 5 preprocessing)
            job.stage3_completed_at = datetime.utcnow()  # Mark Stage 3 (Auto-Validation) complete
            job.stage4_completed_at = datetime.utcnow()  # Mark Stage 4 as skipped (no review needed)
            session.commit()

            container.main_logger.info(
                f"Job {job_id}: Validation passed, skipping Stage 4 review, proceeding to Stage 5"
            )

            # Start Stage 5 preprocessing (ExtendScript generation)
            result = {
                'success': True,
                'status': 'processing',
                'message': 'Proceeding to Stage 5 ExtendScript generation'
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


# ============================================================================
# STAGE 4: VALIDATION REVIEW ROUTES (6-Stage Pipeline)
# ============================================================================

@app.route('/api/job/<job_id>/return-to-matching', methods=['POST'])
def return_to_matching(job_id: str):
    """
    Stage 4: User chose to return to Stage 2 to fix matches.

    Transitions job from Stage 4 (Validation Review) back to Stage 2 (Matching).
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


@app.route('/api/job/<job_id>/override-validation', methods=['POST'])
def override_validation(job_id: str):
    """
    Stage 4: User chose to override validation issues and proceed.

    Transitions job from Stage 4 (Validation Review) to Stage 5 (ExtendScript Generation).
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


@app.route('/validate/<job_id>')
def validate_job_page(job_id: str):
    """Display Stage 4 validation review page for a job."""
    try:
        container.main_logger.info(f"Loading validation page for job {job_id}")
        return render_template('stage3_validation.html', job_id=job_id)
    except Exception as e:
        container.main_logger.error(f"Error loading validation page: {e}", exc_info=True)
        return f"Error loading validation page: {e}", 500


@app.route('/api/job/<job_id>/validation-results', methods=['GET'])
def get_validation_results(job_id: str):
    """
    Get validation results for a job.

    Returns:
    {
        "job_id": "TEST_JOB",
        "client_name": "Client Name",
        "project_name": "Project Name",
        "validated_at": "2025-10-31T12:00:00",
        "total_matches": 6,
        "validation_results": {
            "valid": false,
            "critical_issues": [...],
            "warnings": [...],
            "info": [...]
        }
    }
    """
    try:
        session = db_session()
        try:
            # Use ORM to query job
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': 'Job not found'
                }), 404

            # JSON columns auto-deserialize, no need for json.loads()
            validation_results = job.stage3_validation_results

            # If no validation results exist, run validation now
            if not validation_results:
                container.main_logger.info(f"No validation results found for {job_id}, running validation...")
                validation_results = match_validator.validate_job(job_id)
                match_validator.save_validation_results(job_id, validation_results)

            # Count total matches
            stage2_data = job.stage2_results or {}
            total_matches = len(stage2_data.get('approved_matches', []))

            return jsonify({
                'success': True,
                'job_id': job.job_id,
                'client_name': job.client_name,
                'project_name': job.project_name,
                'validated_at': job.stage3_completed_at.isoformat() if job.stage3_completed_at else None,
                'total_matches': total_matches,
                'validation_results': validation_results
            })

        finally:
            session.close()

    except Exception as e:
        container.main_logger.error(f"Error getting validation results: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/job/<job_id>/complete-validation', methods=['POST'])
def complete_validation(job_id: str):
    """
    Complete validation (no critical issues) and proceed to Stage 4.

    Expects JSON body:
    {
        "user_id": "john_doe"
    }
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')

        container.main_logger.info(f"Job {job_id}: Validation completed by {user_id}")

        # Move to Stage 4 using ORM
        session = db_session()
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()

            if not job:
                return jsonify({
                    'success': False,
                    'error': 'Job not found'
                }), 404

            job.current_stage = 4
            session.commit()

        finally:
            session.close()

        container.main_logger.info(f"Job {job_id}: Moved to Stage 4 after validation")

        return jsonify({
            'success': True,
            'message': 'Validation complete, proceeding to Stage 4',
            'redirect_url': '/dashboard'
        })

    except Exception as e:
        container.main_logger.error(f"Error completing validation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/job/<job_id>/approve-stage3', methods=['POST'])
def approve_stage3_preview(job_id: str):
    """
    Approve Stage 3 preview and transition to Stage 4.

    Expects JSON body:
    {
        "user_id": "john_doe",
        "approval_notes": "Looks good!"
    }
    """
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        notes = data.get('approval_notes', '')

        container.main_logger.info(f"Job {job_id}: Stage 3 approval by {user_id}")

        # Transition from Stage 3 to Stage 4
        result = transition_manager.transition_stage(
            job_id=job_id,
            from_stage=3,
            to_stage=4,
            user_id=user_id,
            approved_data={'approval_notes': notes}
        )

        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Stage 3 approved - validating and deploying in background',
                'job_id': job_id,
                'status': result['status']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Transition failed')
            }), 400

    except Exception as e:
        container.main_logger.error(f"Error approving Stage 3: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/job/<job_id>/preprocessing-status/<int:stage>', methods=['GET'])
def get_preprocessing_status(job_id: str, stage: int):
    """
    Get the pre-processing status for a job at a specific stage.

    Returns whether background pre-processing is active or completed.
    """
    try:
        status = transition_manager.get_preprocessing_status(job_id, stage)

        return jsonify({
            'success': True,
            **status
        })

    except Exception as e:
        container.main_logger.error(f"Error getting preprocessing status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# MAIN
# ============================================================================

@app.route('/review-matching/<job_id>')
def review_matching(job_id):
    """Stage 2: Review layer matching interface."""
    return render_template('stage2_review.html', job_id=job_id)

if __name__ == '__main__':
    print("="*70)
    print("After Effects Automation - Web Interface")
    print("="*70)
    print("\n🌐 Starting server at http://localhost:5001")
    print("\n📝 Instructions:")
    print("   1. Open http://localhost:5001 in your browser")
    print("   2. Upload your PSD and AEPX files")
    print("   3. Review mappings and conflicts")
    print("   4. Generate and download ExtendScript")
    print("\n⚠️  Press Ctrl+C to stop the server")
    print("="*70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5001)

