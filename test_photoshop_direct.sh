#!/bin/bash

# Test 1: Can we even talk to Photoshop?
echo "Test 1: Checking if Photoshop is available..."
osascript -e 'tell application "Adobe Photoshop 2025" to get name'
echo ""

# Test 2: Try the simplest possible JavaScript
echo "Test 2: Testing simple JavaScript execution..."
osascript <<'APPLESCRIPT'
tell application "Adobe Photoshop 2025"
    activate
    do javascript "$.writeln('Hello from Photoshop');"
end tell
APPLESCRIPT
echo ""

# Test 3: What does the error position 60:70 correspond to?
echo "Test 3: Examining the AppleScript that causes error at position 60:70..."
echo "Position 60:70 in the original command likely corresponds to characters in 'Adobe Photoshop 2025'"
echo "Let's check the exact character positions:"
echo 'tell application "Adobe Photoshop 2025"' | awk '{for(i=1;i<=length($0);i++) printf "%d:%s ", i, substr($0,i,1); print ""}'
echo ""

# Test 4: Try without activate
echo "Test 4: Try without activate command..."
osascript <<'APPLESCRIPT'
tell application "Adobe Photoshop 2025"
    do javascript "$.writeln('Test without activate');"
end tell
APPLESCRIPT

