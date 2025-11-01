#!/bin/bash

echo "Test: Open PSD and run JavaScript..."
echo ""

# Use the correct PSD file path
PSD_FILE="/Users/edf/aftereffects-automation/uploads/1761775746_7561b2e0_psd_test-photoshop-doc.psd"

if [ ! -f "$PSD_FILE" ]; then
    echo "❌ PSD file not found: $PSD_FILE"
    exit 1
fi

echo "✅ Found PSD: $PSD_FILE"
echo ""

echo "Opening PSD and listing layers..."

# Use osascript with -e flags to avoid heredoc variable expansion issues
osascript \
    -e 'tell application "Adobe Photoshop 2026"' \
    -e 'activate' \
    -e "open POSIX file \"$PSD_FILE\"" \
    -e 'tell current document' \
    -e 'set jsResult to do javascript "var doc = app.activeDocument; var results = []; for (var i = 0; i < doc.layers.length; i++) { var layer = doc.layers[i]; results.push({name: layer.name, type: layer.typename}); } JSON.stringify(results);"' \
    -e 'end tell' \
    -e 'close current document saving no' \
    -e 'return jsResult' \
    -e 'end tell'

echo ""
echo "✅ Test complete!"

