#!/usr/bin/env python3
"""
After Effects Automation - One-Click Launcher
Double-click this file to start the server (no terminal required!)
"""

import sys
import os
import subprocess
import time
import webbrowser
from pathlib import Path
import socket

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True

def start_server():
    """Start the Flask server"""
    project_root = Path(__file__).parent
    web_app = project_root / "web_app.py"

    # Check if server is already running
    if is_port_in_use(5001):
        print("Server is already running!")
        print("Opening browser...")
        webbrowser.open("http://localhost:5001")
        return

    print("=" * 70)
    print("After Effects Automation - Starting Server")
    print("=" * 70)
    print()
    print("🚀 Starting web server...")
    print()

    # Change to project directory
    os.chdir(project_root)

    # Determine Python command
    python_cmd = sys.executable

    # Start the server
    try:
        # Start server in background
        if sys.platform == "win32":
            # Windows: use CREATE_NO_WINDOW flag
            from subprocess import CREATE_NO_WINDOW
            process = subprocess.Popen(
                [python_cmd, str(web_app)],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            # Mac/Linux: redirect output to log file
            log_file = project_root / "logs" / "server.log"
            log_file.parent.mkdir(exist_ok=True)
            with open(log_file, 'a') as f:
                process = subprocess.Popen(
                    [python_cmd, str(web_app)],
                    stdout=f,
                    stderr=f
                )

        # Save PID file
        pid_file = Path("/tmp/ae_automation.pid") if sys.platform != "win32" else project_root / "server.pid"
        pid_file.write_text(str(process.pid))

        # Wait for server to start
        print("⏳ Waiting for server to start...")
        max_attempts = 30
        for i in range(max_attempts):
            if is_port_in_use(5001):
                print()
                print("✅ Server started successfully!")
                print()
                print("🌐 Server URL: http://localhost:5001")
                print()
                print("Opening browser in 2 seconds...")
                time.sleep(2)
                webbrowser.open("http://localhost:5001")
                print()
                print("=" * 70)
                print("Server is running! You can close this window.")
                print("To stop the server, visit: http://localhost:5001/admin")
                print("=" * 70)
                return
            time.sleep(0.5)

        print()
        print("⚠️  Server may have failed to start. Check logs/server.log")

    except Exception as e:
        print()
        print(f"❌ Error starting server: {e}")
        print()
        print("Please ensure:")
        print("  1. Python 3.8+ is installed")
        print("  2. Dependencies are installed: pip install -r requirements.txt")
        print("  3. Port 5001 is not in use by another application")
        sys.exit(1)

if __name__ == "__main__":
    start_server()

    # Keep script alive on Windows
    if sys.platform == "win32":
        input("\nPress Enter to exit...")
