#!/bin/bash

echo "========================================="
echo "After Effects Automation - Mac Setup"
echo "========================================="
echo ""
echo "This will set up everything you need."
echo "This only needs to run ONCE."
echo ""

# Get project root
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$PROJECT_ROOT"

# Check for Python
echo "Checking for Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo ""
    echo "Please install Python first:"
    echo "1. Go to https://www.python.org/downloads/"
    echo "2. Download and install Python 3.10 or newer"
    echo "3. Run this setup again"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing required packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
echo "Creating data directories..."
mkdir -p data/projects
mkdir -p data/uploads
mkdir -p data/templates
mkdir -p data/exports
mkdir -p logs

# Create the Mac app
echo "Creating Mac application..."
bash scripts/create_mac_app.sh

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "What to do next:"
echo "1. Find 'AE Automation.app' in this folder"
echo "2. Double-click it to start the tool"
echo "3. Click the 🎬 icon in your menu bar"
echo "4. Click 'Start Server'"
echo "5. Your browser will open automatically!"
echo ""
echo "Optional: Drag 'AE Automation.app' to your Applications folder"
echo ""
echo "Need help? Check docs/TROUBLESHOOTING.md"
echo ""
