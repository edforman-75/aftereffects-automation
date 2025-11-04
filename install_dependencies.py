#!/usr/bin/env python3
"""
Dependency Installer - No Terminal Required!
Double-click this file to install all required dependencies
"""

import sys
import subprocess
from pathlib import Path

def main():
    print("=" * 70)
    print("After Effects Automation - Dependency Installer")
    print("=" * 70)
    print()
    print("📦 Installing required Python packages...")
    print("This may take 2-3 minutes...")
    print()

    # Get project root
    project_root = Path(__file__).parent
    requirements_file = project_root / "requirements.txt"

    if not requirements_file.exists():
        print("❌ Error: requirements.txt not found!")
        print(f"Expected location: {requirements_file}")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Install requirements
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        print("✓ pip upgraded\n")

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True
        )

        print()
        print("=" * 70)
        print("✅ Installation complete!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Double-click 'start_server.py' to start the server")
        print("  2. Or visit: http://localhost:5001/admin to set up auto-start")
        print()

    except subprocess.CalledProcessError as e:
        print()
        print("=" * 70)
        print("❌ Installation failed!")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Make sure Python 3.8+ is installed")
        print("  2. Make sure you have internet connection")
        print("  3. Try running as administrator (Windows) or with sudo (Mac/Linux)")
        sys.exit(1)

    # Keep window open
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
