#!/usr/bin/env python3
"""
Mac menu bar application for After Effects Automation
Allows users to start/stop the tool from menu bar
"""

import rumps
import subprocess
import os
import webbrowser
from pathlib import Path

class AEAutomationApp(rumps.App):
    def __init__(self):
        super(AEAutomationApp, self).__init__("AE Auto", "🎬")
        self.project_root = Path(__file__).parent.parent.parent
        self.is_running = False
        self.check_if_running()

    def check_if_running(self):
        """Check if the web server is already running"""
        pid_file = Path("/tmp/ae_automation.pid")
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                # Check if process is actually running
                os.kill(pid, 0)
                self.is_running = True
                self.title = "🟢"
                return True
            except (OSError, ValueError):
                # Process not running or invalid PID
                pid_file.unlink()

        self.is_running = False
        self.title = "🔴"
        return False

    @rumps.clicked("Start Server")
    def start_server(self, _):
        """Start the web server"""
        if self.is_running:
            rumps.notification(
                title="Already Running",
                subtitle="",
                message="The server is already running!"
            )
            return

        try:
            # Run launch script
            launch_script = self.project_root / "scripts" / "mac_app" / "launch_app.sh"
            subprocess.Popen(
                ["bash", str(launch_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.is_running = True
            self.title = "🟢"

            rumps.notification(
                title="Server Started",
                subtitle="",
                message="Opening browser..."
            )

        except Exception as e:
            rumps.alert(
                title="Error Starting Server",
                message=str(e)
            )

    @rumps.clicked("Stop Server")
    def stop_server(self, _):
        """Stop the web server"""
        if not self.is_running:
            rumps.notification(
                title="Not Running",
                subtitle="",
                message="The server is not running!"
            )
            return

        try:
            # Run stop script
            stop_script = self.project_root / "scripts" / "mac_app" / "stop_app.sh"
            subprocess.run(
                ["bash", str(stop_script)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.is_running = False
            self.title = "🔴"

            rumps.notification(
                title="Server Stopped",
                subtitle="",
                message="Application stopped successfully"
            )

        except Exception as e:
            rumps.alert(
                title="Error Stopping Server",
                message=str(e)
            )

    @rumps.clicked("Open in Browser")
    def open_browser(self, _):
        """Open the tool in default browser"""
        if not self.is_running:
            rumps.alert(
                title="Server Not Running",
                message="Please start the server first!"
            )
            return

        webbrowser.open("http://localhost:5001")

    @rumps.clicked("View Logs")
    def view_logs(self, _):
        """Open log file in Console.app"""
        log_file = self.project_root / "logs" / "app.log"
        if log_file.exists():
            subprocess.run(["open", "-a", "Console", str(log_file)])
        else:
            rumps.alert(
                title="No Logs",
                message="Log file not found. Has the server been started?"
            )

    @rumps.clicked("About")
    def about(self, _):
        """Show about dialog"""
        rumps.alert(
            title="After Effects Automation",
            message="Version 1.0\n\nAutomates PSD to AEPX workflow\nwith intelligent layer matching\nand expression generation."
        )

if __name__ == "__main__":
    # Install rumps if not present
    try:
        import rumps
    except ImportError:
        print("Installing menu bar support...")
        subprocess.run(["pip", "install", "rumps"])
        import rumps

    AEAutomationApp().run()
