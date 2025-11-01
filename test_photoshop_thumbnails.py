#!/usr/bin/env python3
"""
Minimal Photoshop Thumbnail Generation Test
Addresses the "frontmost document" issue by explicitly managing active document state.
"""

import subprocess
import tempfile
import os
from pathlib import Path

# Configuration
PSD_FILE = "/Users/edf/aftereffects-automation/uploads/1761779221_6cda6f4d_psd_test-photoshop-doc.psd"
OUTPUT_FOLDER = "/tmp/thumb_test"
THUMBNAIL_WIDTH = 200

def generate_thumbnails():
    """Generate thumbnails for all layers in PSD."""
    
    print("="*70)
    print("Photoshop Thumbnail Generation Test")
    print("="*70)
    print(f"PSD: {PSD_FILE}")
    print(f"Output: {OUTPUT_FOLDER}")
    print(f"File exists: {os.path.exists(PSD_FILE)}")
    print()
    
    # Create output folder
    Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    
    # Generate ExtendScript
    jsx_script = f'''
// Thumbnail Generation Script
var psdFile = new File("{PSD_FILE}");
var outputFolder = new Folder("{OUTPUT_FOLDER}");

if (!psdFile.exists) {{
    alert("ERROR: PSD file not found!");
}} else {{
    try {{
        // Open the PSD
        var doc = app.open(psdFile);
        app.activeDocument = doc;  // CRITICAL: Set as frontmost document
        
        $.writeln("Opened: " + doc.name);
        $.writeln("Layers: " + doc.layers.length);
        
        // PNG export options
        var pngOptions = new PNGSaveOptions();
        pngOptions.compression = 6;
        
        // Process each layer
        for (var i = 0; i < doc.layers.length; i++) {{
            var layer = doc.layers[i];
            
            try {{
                // Skip layer groups
                if (layer.typename === "LayerSet") {{
                    $.writeln("Skipping group: " + layer.name);
                    continue;
                }}
                
                $.writeln("Processing: " + layer.name);
                
                // Hide all layers
                for (var j = 0; j < doc.layers.length; j++) {{
                    doc.layers[j].visible = false;
                }}
                
                // Show only current layer
                layer.visible = true;
                
                // CRITICAL: Re-confirm active document
                app.activeDocument = doc;
                
                // Get layer bounds
                var bounds = layer.bounds;
                var layerWidth = bounds[2].value - bounds[0].value;
                var layerHeight = bounds[3].value - bounds[1].value;
                
                if (layerWidth > 0 && layerHeight > 0) {{
                    // Duplicate and flatten
                    var tempDoc = doc.duplicate();
                    tempDoc.flatten();
                    
                    // Crop to layer bounds
                    tempDoc.crop(bounds);
                    
                    // Resize to target width
                    var scale = ({THUMBNAIL_WIDTH} / layerWidth) * 100;
                    tempDoc.resizeImage(UnitValue({THUMBNAIL_WIDTH}, "px"), undefined, 72, ResampleMethod.BICUBIC);
                    
                    // Save thumbnail
                    var safeName = layer.name.replace(/[^a-zA-Z0-9_-]/g, "_");
                    var thumbFile = new File(outputFolder + "/" + safeName + ".png");
                    tempDoc.saveAs(thumbFile, pngOptions, true);
                    
                    $.writeln("  ✓ Saved: " + safeName + ".png");
                    
                    // Close temp document
                    tempDoc.close(SaveOptions.DONOTSAVECHANGES);
                    
                    // CRITICAL: Re-activate original document for next iteration
                    app.activeDocument = doc;
                }} else {{
                    $.writeln("  ✗ Skipped (no dimensions): " + layer.name);
                }}
                
            }} catch (layerError) {{
                $.writeln("  ✗ Error: " + layer.name + " - " + layerError.toString());
            }}
        }}
        
        // Close original document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        $.writeln("✓ Complete!");
        
    }} catch (e) {{
        alert("ERROR: " + e.toString());
    }}
}}
'''
    
    # Save ExtendScript to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsx', delete=False) as f:
        jsx_file = f.name
        f.write(jsx_script)
    
    print(f"ExtendScript saved to: {jsx_file}")
    print()
    print("Executing in Photoshop 2026...")
    print("-" * 70)
    
    try:
        # Execute via AppleScript
        result = subprocess.run(
            ['osascript', '-e', f'tell application "Adobe Photoshop 2026" to do javascript file (POSIX file "{jsx_file}")'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print("Return code:", result.returncode)
        
        if result.returncode == 0:
            print("✅ SUCCESS")
        else:
            print("❌ FAILED")
            print("STDERR:", result.stderr)
        
        print()
        
        # List generated thumbnails
        print("-" * 70)
        print("Generated Thumbnails:")
        print("-" * 70)
        
        thumbs = list(Path(OUTPUT_FOLDER).glob("*.png"))
        if thumbs:
            for thumb in sorted(thumbs):
                size = thumb.stat().st_size
                print(f"  ✓ {thumb.name} ({size:,} bytes)")
            print()
            print(f"Total: {len(thumbs)} thumbnails")
        else:
            print("  ⚠️ No thumbnails generated")
        
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Script took longer than 120 seconds")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        # Cleanup
        try:
            os.unlink(jsx_file)
        except:
            pass
    
    print()
    print("="*70)

if __name__ == "__main__":
    generate_thumbnails()
