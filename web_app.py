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

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('output')
FONTS_FOLDER = Path('fonts')
PREVIEWS_FOLDER = Path('previews')
ALLOWED_PSD_EXTENSIONS = {'psd'}
ALLOWED_AEPX_EXTENSIONS = {'aepx', 'aep'}
ALLOWED_FONT_EXTENSIONS = {'ttf', 'otf', 'woff', 'woff2'}
MAX_PSD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_AEPX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FONT_SIZE = 5 * 1024 * 1024  # 5MB
CLEANUP_AGE = timedelta(hours=1)

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
    return render_template('index.html')


@app.route('/projects-page')
def projects_page():
    """Serve the projects list page."""
    return render_template('projects.html')


@app.route('/projects/<project_id>')
def project_dashboard(project_id):
    """Serve the project dashboard page."""
    return render_template('project-dashboard.html', project_id=project_id)


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

        # Parse AEPX/AEP
        aepx_ext = Path(aepx_file.filename).suffix.lower()
        if aepx_ext == '.aep':
            # For AEP files, use default composition name
            container.main_logger.info("AEP file detected, using default structure")
            aepx_data = {
                'filename': aepx_file.filename,
                'composition_name': 'Main Comp',
                'compositions': [{'name': 'Main Comp', 'width': 1920, 'height': 1080}],
                'placeholders': []
            }
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

        # Store in session
        sessions[session_id] = {
            'psd_path': str(psd_path),
            'aepx_path': str(aepx_path),
            'psd_data': psd_data,
            'aepx_data': aepx_data,
            'font_check': font_check,
            'font_status': font_status,
            'font_summary': font_summary,
            'fonts': fonts,
            'created_at': datetime.now()
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
                    'placeholders': len(aepx_data['placeholders'])
                },
                'fonts': {
                    'total': font_check['summary']['total'],
                    'uncommon': font_check['summary']['uncommon'],
                    'uncommon_list': font_check['uncommon_fonts'],
                    'installed': font_summary['installed'],
                    'missing': font_summary['missing'],
                    'percentage': font_summary['percentage'],
                    'all_installed': font_summary['all_installed'],
                    'status': font_status
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


# ============================================================================
# MAIN
# ============================================================================

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
