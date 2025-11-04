#!/usr/bin/env python3
"""
Python Installation Checker
Double-click to verify Python is installed correctly
"""

import sys
import platform

def main():
    print("=" * 70)
    print("Python Installation Check")
    print("=" * 70)
    print()

    # Python version
    version = sys.version_info
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required!")
        print("   Please install Python 3.8+ from python.org")
    else:
        print("✓ Python version is compatible")

    print()

    # Platform
    print(f"✓ Platform: {platform.system()} ({platform.machine()})")
    print(f"✓ Python executable: {sys.executable}")

    print()

    # Check key packages
    print("Checking for required packages...")
    packages = [
        "flask",
        "flask_cors",
        "psd_tools",
        "PIL",
        "lxml"
    ]

    missing = []
    for package in packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            missing.append(package)

    print()

    if missing:
        print("=" * 70)
        print("⚠️  Some packages are missing!")
        print("=" * 70)
        print()
        print("Please run: install_dependencies.py")
        print("(Double-click install_dependencies.py to install)")
    else:
        print("=" * 70)
        print("✅ Everything looks good!")
        print("=" * 70)
        print()
        print("You're ready to run the server!")
        print("Double-click: start_server.py")

    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
