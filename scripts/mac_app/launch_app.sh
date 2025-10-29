#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Setting up for first time..."

    # Create virtual environment
    python3 -m venv venv

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt

    echo "Setup complete!"
else
    # Activate existing virtual environment
    source venv/bin/activate
fi

# Create log directory if it doesn't exist
mkdir -p logs

# Start the web server in background
python3 web_app.py > logs/app.log 2>&1 &

# Save the PID
echo $! > /tmp/ae_automation.pid

# Wait for server to start
sleep 3

# Open browser
open http://localhost:5001

# Show notification
osascript -e 'display notification "After Effects Automation is running!" with title "AE Automation"'

echo "Application started! Check your browser."
