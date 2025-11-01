#!/usr/bin/env python3
"""
Simplified test using osascript with proper file path handling.
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

# Generate ExtendScript
width, height = THUMBNAIL_SIZE
psd_path_js = os.path.abspath(PSD_FILE).replace('\\', '/').replace('"', '\\"')
output_folder_js = OUTPUT_FOLDER.replace('\\', '/').replace('"', '\\"')

jsx_script = f'''
// Thumbnail Export Script
var psdFile = new File("{psd_path_js}");
var outputFolder = new Folder("{output_folder_js}");

if (!outputFolder.exists) {{
    outputFolder.create();
}}

// Open PSD
var doc = app.open(psdFile);

// Export options
var pngOptions = new PNGSaveOptions();
pngOptions.compression = 6;

var results = [];

try {{
    // Iterate through layers
    for (var i = 0; i < doc.layers.length; i++) {{
        var layer = doc.layers[i];
        
        try {{
            // Skip if layer is a group
            if (layer.typename === "LayerSet") {{
                results.push({{
                    layer: layer.name,
                    skipped: true,
                    reason: "Layer group"
                }});
                continue;
            }}
            
            // Hide all layers
            for (var j = 0; j < doc.layers.length; j++) {{
                doc.layers[j].visible = false;
            }}
            
            // Show only current layer
            layer.visible = true;
            
            // Get layer bounds
            var bounds = layer.bounds;
            var layerWidth = bounds[2].value - bounds[0].value;
            var layerHeight = bounds[3].value - bounds[1].value;
            
            if (layerWidth > 0 && layerHeight > 0) {{
                // Duplicate document
                var tempDoc = doc.duplicate();
                tempDoc.flatten();
                
                // Crop to layer bounds
                tempDoc.crop(bounds);
                
                // Resize to thumbnail size
                tempDoc.resizeImage(UnitValue({width}, "px"), undefined, 72, ResampleMethod.BICUBIC);
                
                // Save thumbnail
                var safeLayerName = layer.name.replace(/[^a-zA-Z0-9_-]/g, "_");
                var thumbFile = new File(outputFolder + "/" + safeLayerName + ".png");
                tempDoc.saveAs(thumbFile, pngOptions, true);
                
                results.push({{
                    layer: layer.name,
                    safeName: safeLayerName,
                    file: thumbFile.fsName,
                    success: true
                }});
                
                // Close temp document
                tempDoc.close(SaveOptions.DONOTSAVECHANGES);
            }} else {{
                results.push({{
                    layer: layer.name,
                    success: false,
                    reason: "Layer has no dimensions"
                }});
            }}
        }} catch (layerError) {{
            results.push({{
                layer: layer.name,
                error: layerError.toString(),
                success: false
            }});
        }}
    }}
}} catch (e) {{
    alert("Error generating thumbnails: " + e.toString());
}} finally {{
    // Close document
    doc.close(SaveOptions.DONOTSAVECHANGES);
}}

// Return results as JSON
$.writeln("THUMBNAIL_RESULTS:" + JSON.stringify(results));
'''

# Save script to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.jsx', delete=False) as f:
    jsx_file = f.name
    f.write(jsx_script)

print(f"Saved JSX to: {jsx_file}")
print()

# NEW APPROACH: Use osascript with stdin and proper quoting
applescript = f'''tell application "Adobe Photoshop 2025"
    activate
    set jsxPath to POSIX file "{jsx_file}" as alias
    do javascript jsxPath
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
        print("✅ SUCCESS - Script executed!")
        print()
        print("STDOUT:")
        print(result.stdout)
        print()
        
        # Check for thumbnails
        thumb_files = list(Path(OUTPUT_FOLDER).glob("*.png"))
        print(f"Generated {len(thumb_files)} thumbnail files:")
        for thumb in thumb_files:
            print(f"  - {thumb.name} ({thumb.stat().st_size} bytes)")
    
finally:
    # Cleanup
    try:
        os.unlink(jsx_file)
        print(f"\nCleaned up temp JSX file")
    except:
        pass

print("\n" + "=" * 60)
print("Test complete!")
print(f"Check output folder: {OUTPUT_FOLDER}")
