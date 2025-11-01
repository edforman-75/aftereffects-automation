#!/bin/bash

echo "Checking Photoshop's AppleScript dictionary..."
echo ""

echo "Opening Script Editor to view Photoshop dictionary..."
echo "(Look for the exact syntax of the 'do javascript' command)"
echo ""

# Try to extract the dictionary programmatically
osascript <<'APPLESCRIPT'
tell application "System Events"
    tell process "Adobe Photoshop 2026"
        get properties
    end tell
end tell
APPLESCRIPT

echo ""
echo "Let's try checking the sdef (scripting definition)..."
sdef "/Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app" | grep -A 10 -i "javascript"

echo ""
echo "Alternate approach: Check what commands are available..."
osascript <<'APPLESCRIPT'
tell application "Adobe Photoshop 2026"
    activate
    -- Try to see what commands exist
end tell
APPLESCRIPT

echo ""
echo "Let's try the correct syntax based on Adobe documentation..."
echo "Testing: do javascript with parameters..."

osascript <<'APPLESCRIPT'
tell application "Adobe Photoshop 2026"
    activate
    tell current document
        do javascript "$.writeln('test');"
    end tell
end tell
APPLESCRIPT

