"""
Admin routes for server management
Provides web-based control of the server
"""

import os
import sys
import signal
import subprocess
from pathlib import Path
from flask import Blueprint, render_template, jsonify, request
from config.container import container

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_server_pid():
    """Get the server PID if running"""
    pid_file = Path("/tmp/ae_automation.pid") if sys.platform != "win32" else Path(__file__).parent.parent / "server.pid"

    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())
        # Check if process is actually running
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        # Process not running or invalid PID
        if pid_file.exists():
            pid_file.unlink()
        return None

def get_service_status():
    """Check if running as a system service"""
    if sys.platform == "linux":
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "ae-automation.service"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() == "active"
        except:
            return False

    elif sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True
            )
            return "com.aeautomation.server" in result.stdout
        except:
            return False

    return False

@admin_bp.route('/')
def admin_page():
    """Admin dashboard"""
    return render_template('admin.html')

@admin_bp.route('/status')
def get_status():
    """Get server status"""
    pid = get_server_pid()
    is_service = get_service_status()

    return jsonify({
        'success': True,
        'data': {
            'running': pid is not None,
            'pid': pid,
            'is_service': is_service,
            'platform': sys.platform,
            'python_version': sys.version,
            'project_root': str(Path(__file__).parent.parent)
        }
    })

@admin_bp.route('/restart', methods=['POST'])
def restart_server():
    """Restart the server"""
    try:
        container.main_logger.info("Server restart requested via admin interface")

        # If running as service, restart via service manager
        if get_service_status():
            if sys.platform == "linux":
                subprocess.run(["systemctl", "--user", "restart", "ae-automation.service"], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["launchctl", "stop", "com.aeautomation.server"], check=True)
                # launchd will automatically restart it

            return jsonify({
                'success': True,
                'message': 'Server restart initiated via service manager'
            })

        # Otherwise, we'll restart by exiting and letting the launcher restart us
        # Note: This requires the server to be run with an auto-restart wrapper
        return jsonify({
            'success': True,
            'message': 'Restart requires manual action. Stop and start the server again.'
        })

    except Exception as e:
        container.main_logger.error(f"Failed to restart server: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to restart: {str(e)}'
        }), 500

@admin_bp.route('/shutdown', methods=['POST'])
def shutdown_server():
    """Shutdown the server gracefully"""
    try:
        container.main_logger.info("Server shutdown requested via admin interface")

        # If running as service, stop via service manager
        if get_service_status():
            if sys.platform == "linux":
                subprocess.run(["systemctl", "--user", "stop", "ae-automation.service"], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["launchctl", "stop", "com.aeautomation.server"], check=True)

            return jsonify({
                'success': True,
                'message': 'Server stopped via service manager'
            })

        # Schedule shutdown
        def shutdown():
            import time
            time.sleep(1)
            os.kill(os.getpid(), signal.SIGTERM)

        from threading import Thread
        Thread(target=shutdown).start()

        return jsonify({
            'success': True,
            'message': 'Server shutdown initiated'
        })

    except Exception as e:
        container.main_logger.error(f"Failed to shutdown server: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to shutdown: {str(e)}'
        }), 500

@admin_bp.route('/logs')
def get_logs():
    """Get recent server logs"""
    try:
        log_file = Path(__file__).parent.parent / "logs" / "server.log"

        if not log_file.exists():
            return jsonify({
                'success': True,
                'data': {
                    'lines': [],
                    'message': 'No log file found'
                }
            })

        # Read last 100 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines

        return jsonify({
            'success': True,
            'data': {
                'lines': [line.strip() for line in recent_lines],
                'total_lines': len(lines)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin_bp.route('/service/install', methods=['POST'])
def install_service():
    """Install as system service"""
    try:
        project_root = Path(__file__).parent.parent
        installer = project_root / "install" / "install_service.py"

        result = subprocess.run(
            [sys.executable, str(installer)],
            capture_output=True,
            text=True
        )

        return jsonify({
            'success': result.returncode == 0,
            'message': result.stdout if result.returncode == 0 else result.stderr
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin_bp.route('/service/uninstall', methods=['POST'])
def uninstall_service():
    """Uninstall system service"""
    try:
        project_root = Path(__file__).parent.parent
        installer = project_root / "install" / "install_service.py"

        result = subprocess.run(
            [sys.executable, str(installer), "uninstall"],
            capture_output=True,
            text=True
        )

        return jsonify({
            'success': result.returncode == 0,
            'message': result.stdout if result.returncode == 0 else result.stderr
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
