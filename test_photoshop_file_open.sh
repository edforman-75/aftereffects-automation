#!/bin/bash

PSD_FILE="/Users/edf/aftereffects-automation/uploads/1761775746_7561b2e0_psd_test-photoshop-doc.psd"

echo "Test: Opening file with different approaches..."
echo ""

echo "Approach 1: Using 'file' type directly..."
osascript <<APPLESCRIPT
set psdPath to "$PSD_FILE"
set psdFile to POSIX file psdPath

tell application "Adobe Photoshop 2026"
    activate
    open psdFile
    
    tell current document
        set layerCount to count of layers
        do javascript "$.writeln('Document has ' + app.activeDocument.layers.length + ' layers');"
    end tell
    
    close current document saving no
end tell
APPLESCRIPT

echo ""
echo "Approach 2: Using file reference..."
osascript <<APPLESCRIPT
tell application "Adobe Photoshop 2026"
    activate
    open file "$PSD_FILE"
    
    tell current document
        do javascript "$.writeln('Opened successfully!');"
    end tell
    
    close current document saving no
end tell
APPLESCRIPT

echo ""
echo "Approach 3: Direct path as string..."
osascript -e "tell application \"Adobe Photoshop 2026\"" \
          -e "activate" \
          -e "open \"$PSD_FILE\"" \
          -e "tell current document" \
          -e "do javascript \"$.writeln('Success');\"" \
          -e "end tell" \
          -e "close current document saving no" \
          -e "end tell"

