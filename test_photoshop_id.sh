#!/bin/bash

echo "Test 1: Finding Photoshop's application ID..."
osascript -e 'id of application "Adobe Photoshop 2025"'
echo ""

echo "Test 2: Using application ID instead of name..."
APP_ID=$(osascript -e 'id of application "Adobe Photoshop 2025"' 2>/dev/null)
echo "Application ID: $APP_ID"
echo ""

if [ -n "$APP_ID" ]; then
    echo "Test 3: Trying with application ID..."
    osascript <<APPLESCRIPT
tell application id "$APP_ID"
    activate
    do javascript "$.writeln('Hello from Photoshop');"
end tell
APPLESCRIPT
    echo ""
fi

echo "Test 4: Maybe the syntax requires 'of document'? Checking Photoshop docs..."
echo "Trying: tell application to do JavaScript of document..."
osascript <<'APPLESCRIPT'
tell application "Adobe Photoshop 2025"
    activate
    do JavaScript "$.writeln('test');" with JavaScript
end tell
APPLESCRIPT
echo ""

echo "Test 5: Try old Photoshop CC syntax..."
osascript <<'APPLESCRIPT'
tell application "Adobe Photoshop 2025"
    activate
    DoJavaScript "$.writeln('test');"
end tell
APPLESCRIPT

