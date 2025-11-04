#!/usr/bin/env python3
"""
Install After Effects Automation as a system service
This allows the server to start automatically on boot
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

def get_username():
    """Get current username"""
    return os.environ.get('USER') or os.environ.get('USERNAME')

def get_project_root():
    """Get absolute path to project root"""
    return Path(__file__).parent.parent.resolve()

def install_linux_service():
    """Install systemd service on Linux"""
    print("Installing systemd service...")

    username = get_username()
    project_root = get_project_root()

    # Create systemd user directory
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    # Read service file template
    service_template = project_root / "install" / "ae-automation.service"
    service_content = service_template.read_text()

    # Replace placeholders
    service_content = service_content.replace("/home/%i/aftereffects-automation", str(project_root))
    service_content = service_content.replace("User=%i", f"User={username}")

    # Write service file
    service_file = systemd_dir / "ae-automation.service"
    service_file.write_text(service_content)

    print(f"✓ Service file created: {service_file}")

    # Reload systemd
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print("✓ Systemd daemon reloaded")

    # Enable service
    subprocess.run(["systemctl", "--user", "enable", "ae-automation.service"], check=True)
    print("✓ Service enabled (will start on login)")

    # Start service now
    subprocess.run(["systemctl", "--user", "start", "ae-automation.service"], check=True)
    print("✓ Service started")

    print()
    print("Service installed successfully!")
    print()
    print("Useful commands:")
    print("  Check status:  systemctl --user status ae-automation")
    print("  View logs:     journalctl --user -u ae-automation -f")
    print("  Stop service:  systemctl --user stop ae-automation")
    print("  Disable:       systemctl --user disable ae-automation")

def install_macos_service():
    """Install launchd service on macOS"""
    print("Installing launchd service...")

    username = get_username()
    project_root = get_project_root()

    # Create LaunchAgents directory
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    # Read plist template
    plist_template = project_root / "install" / "com.aeautomation.server.plist"
    plist_content = plist_template.read_text()

    # Replace placeholders
    plist_content = plist_content.replace("YOUR_USERNAME", username)
    plist_content = plist_content.replace(
        "/Users/YOUR_USERNAME/aftereffects-automation",
        str(project_root)
    )

    # Write plist file
    plist_file = launch_agents_dir / "com.aeautomation.server.plist"
    plist_file.write_text(plist_content)

    print(f"✓ Launch agent created: {plist_file}")

    # Load the service
    subprocess.run(["launchctl", "load", str(plist_file)], check=True)
    print("✓ Service loaded (will start on login)")

    # Start service now
    subprocess.run(["launchctl", "start", "com.aeautomation.server"], check=True)
    print("✓ Service started")

    print()
    print("Service installed successfully!")
    print()
    print("Useful commands:")
    print("  Check status:  launchctl list | grep aeautomation")
    print("  View logs:     tail -f ~/aftereffects-automation/logs/server.log")
    print("  Stop service:  launchctl stop com.aeautomation.server")
    print("  Unload:        launchctl unload ~/Library/LaunchAgents/com.aeautomation.server.plist")

def install_windows_service():
    """Provide instructions for Windows Task Scheduler"""
    print("Windows Service Setup")
    print()
    print("To make the server start automatically on Windows:")
    print()
    print("1. Press Win+R and type: taskschd.msc")
    print("2. Click 'Create Basic Task'")
    print("3. Name: 'After Effects Automation'")
    print("4. Trigger: 'When I log on'")
    print("5. Action: 'Start a program'")
    print(f"6. Program: {sys.executable}")
    print(f"7. Arguments: {get_project_root() / 'start_server.py'}")
    print(f"8. Start in: {get_project_root()}")
    print()
    print("Alternatively, add start_server.py to your Startup folder:")
    print("  1. Press Win+R and type: shell:startup")
    print("  2. Create a shortcut to start_server.py in that folder")

def uninstall_service():
    """Uninstall the service"""
    if sys.platform == "linux":
        print("Uninstalling Linux service...")
        subprocess.run(["systemctl", "--user", "stop", "ae-automation.service"])
        subprocess.run(["systemctl", "--user", "disable", "ae-automation.service"])
        service_file = Path.home() / ".config" / "systemd" / "user" / "ae-automation.service"
        if service_file.exists():
            service_file.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"])
        print("✓ Service uninstalled")

    elif sys.platform == "darwin":
        print("Uninstalling macOS service...")
        plist_file = Path.home() / "Library" / "LaunchAgents" / "com.aeautomation.server.plist"
        subprocess.run(["launchctl", "unload", str(plist_file)])
        if plist_file.exists():
            plist_file.unlink()
        print("✓ Service uninstalled")

    else:
        print("For Windows, remove the task from Task Scheduler or the shortcut from Startup folder")

def main():
    """Main installation script"""
    print("=" * 70)
    print("After Effects Automation - Service Installer")
    print("=" * 70)
    print()

    # Check for uninstall flag
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall_service()
        return

    # Detect platform and install
    if sys.platform == "linux":
        print("Detected: Linux")
        print()
        try:
            install_linux_service()
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif sys.platform == "darwin":
        print("Detected: macOS")
        print()
        try:
            install_macos_service()
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif sys.platform == "win32":
        print("Detected: Windows")
        print()
        install_windows_service()

    else:
        print(f"Unsupported platform: {sys.platform}")
        sys.exit(1)

    print()
    print("=" * 70)
    print("The server will now start automatically when you log in!")
    print("Open your browser to: http://localhost:5001")
    print("=" * 70)

if __name__ == "__main__":
    main()
