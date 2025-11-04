#!/bin/bash
# After Effects Automation - Quick Start Script
# Makes starting the HTML-based server simple

echo "=========================================="
echo "After Effects Automation - Starting..."
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if in correct directory
if [ ! -f "web_app.py" ]; then
    echo "❌ Error: web_app.py not found"
    echo "Please run this script from the aftereffects-automation directory"
    exit 1
fi

echo "✅ Project directory confirmed"

# Check if dependencies are installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo ""
    echo "⚠️  Dependencies not installed. Installing now..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed"
fi

echo "✅ Dependencies verified"
echo ""
echo "=========================================="
echo "🚀 Starting Web Server..."
echo "=========================================="
echo ""
echo "📱 Open your browser to:"
echo "   http://localhost:5001"
echo ""
echo "⚡ The HTML interface will be ready in a moment"
echo ""
echo "🛑 To stop the server: Press Ctrl+C"
echo ""
echo "=========================================="
echo ""

# Start the Flask web server
python3 web_app.py
