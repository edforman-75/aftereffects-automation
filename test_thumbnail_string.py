#!/usr/bin/env python3
"""
Test by reading JSX content and passing it as a JavaScript string.
"""

import os
import subprocess
import tempfile
from pathlib import Path

# Configuration
PSD_FILE = "uploads/1761775746_7561b2e0_psd_test-test-photoshop-doc.psd"
OUTPUT_FOLDER = "/tmp/thumbnail_test"
THUMBNAIL_SIZE = (200, 200)

# Create output folder
Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

print(f"Testing thumbnail generation...")
print(f"PSD File: {PSD_FILE}")
print(f"Output Folder: {OUTPUT_FOLDER}")
print()

# Generate SIMPLIFIED ExtendScript for testing
width, height = THUMBNAIL_SIZE
psd_path_js = os.path.abspath(PSD_FILE).replace('\\', '/').replace('"', '\\"')
output_folder_js = OUTPUT_FOLDER.replace('\\', '/').replace('"', '\\"')

# Start with a VERY simple test script
jsx_script = '''
$.writeln("Test script executed successfully!");
$.writeln("THUMBNAIL_RESULTS:" + JSON.stringify([{layer: "test", success: true}]));
'''

print("Testing with simple script first...")
print()

# Read JSX content
jsx_content = jsx_script

# Escape for AppleScript - escape backslashes first, then quotes, then newlines
jsx_escaped = jsx_content.replace('\\', '\\\\')  # Escape backslashes
jsx_escaped = jsx_escaped.replace('"', '\\"')    # Escape quotes
jsx_escaped = jsx_escaped.replace('\n', '\\n')   # Escape newlines
jsx_escaped = jsx_escaped.replace('\r', '')      # Remove carriage returns

# Build AppleScript - pass JSX content as string to do javascript
applescript = f'''tell application "Adobe Photoshop 2025"
    activate
    do javascript "{jsx_escaped}"
end tell'''

print("Generated AppleScript:")
print("=" * 60)
print(applescript)
print("=" * 60)
print()

print("Executing Photoshop script...")
print("(This may take 10-30 seconds)")
print()

try:
    # Execute using osascript with stdin
    result = subprocess.run(
        ['osascript'],
        input=applescript,
        capture_output=True,
        text=True,
        timeout=120
    )
    
    print("Return Code:", result.returncode)
    print()
    
    if result.returncode != 0:
        print("❌ ERROR - Photoshop script failed!")
        print("STDERR:")
        print(result.stderr)
    else:
        print("✅ SUCCESS - Simple script executed!")
        print()
        print("STDOUT:")
        print(result.stdout)
        print()
        print("Now let's try the full thumbnail generation script...")
    
except Exception as e:
    print(f"Exception: {e}")

print("\n" + "=" * 60)
print("Test complete!")
