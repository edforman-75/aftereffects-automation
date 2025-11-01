#!/bin/bash

echo "Test 1: Open a document first, then run JavaScript..."
echo ""

# Use the correct PSD file path
PSD_FILE="/Users/edf/aftereffects-automation/uploads/1761775746_7561b2e0_psd_test-photoshop-doc.psd"

if [ ! -f "$PSD_FILE" ]; then
    echo "❌ PSD file not found: $PSD_FILE"
    exit 1
fi

echo "✅ Found PSD: $PSD_FILE"
echo ""

echo "Opening PSD and running JavaScript..."
osascript <<APPLESCRIPT
tell application "Adobe Photoshop 2026"
    activate
    
    -- Open the PSD file
    open POSIX file "$PSD_FILE"
    
    -- Now run JavaScript in the context of the current document
    tell current document
        do javascript "$.writeln('✅ JavaScript executed successfully!');"
    end tell
    
    -- Close without saving
    close current document saving no
end tell
APPLESCRIPT

echo ""
echo "Test 2: Now let's list all layers in the document..."

osascript <<APPLESCRIPT
tell application "Adobe Photoshop 2026"
    activate
    
    -- Open the PSD file
    open POSIX file "$PSD_FILE"
    
    -- Run JavaScript to list layers
    tell current document
        set jsResult to do javascript "
var doc = app.activeDocument;
var results = [];

for (var i = 0; i < doc.layers.length; i++) {
    var layer = doc.layers[i];
    results.push({
        name: layer.name,
        type: layer.typename,
        visible: layer.visible
    });
}

'LAYER_INFO:' + JSON.stringify(results);
"
    end tell
    
    -- Close without saving
    close current document saving no
    
    return jsResult
end tell
APPLESCRIPT

