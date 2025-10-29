#!/bin/bash

# Read the PID
if [ -f /tmp/ae_automation.pid ]; then
    PID=$(cat /tmp/ae_automation.pid)

    # Kill the process
    kill $PID 2>/dev/null

    # Remove PID file
    rm /tmp/ae_automation.pid

    # Show notification
    osascript -e 'display notification "Application stopped" with title "AE Automation"'

    echo "Application stopped."
else
    echo "Application is not running."
fi
