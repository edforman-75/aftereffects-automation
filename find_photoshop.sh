#!/bin/bash

echo "Finding all Adobe Photoshop applications..."
echo ""

echo "Method 1: Search /Applications..."
find /Applications -name "*Photoshop*.app" -maxdepth 3 2>/dev/null
echo ""

echo "Method 2: List running processes..."
ps aux | grep -i photoshop | grep -v grep
echo ""

echo "Method 3: Try common Photoshop names..."
for name in "Adobe Photoshop 2025" "Adobe Photoshop" "Adobe Photoshop CC" "Photoshop"; do
    echo -n "Trying '$name': "
    result=$(osascript -e "tell application \"$name\" to get name" 2>&1)
    if [[ $? -eq 0 ]]; then
        echo "✅ WORKS - Name: $result"
        
        # Try do javascript with this name
        echo "  Testing do javascript..."
        osascript <<APPLESCRIPT
tell application "$name"
    do javascript "alert('test');"
end tell
APPLESCRIPT
        if [[ $? -eq 0 ]]; then
            echo "  ✅ do javascript WORKS!"
        else
            echo "  ❌ do javascript FAILED"
        fi
    else
        echo "❌ $result"
    fi
done
echo ""

echo "Method 4: Check what's in /Applications/Adobe Photoshop 2025/..."
if [ -d "/Applications/Adobe Photoshop 2025" ]; then
    ls -la "/Applications/Adobe Photoshop 2025/"
else
    echo "Directory not found"
fi

