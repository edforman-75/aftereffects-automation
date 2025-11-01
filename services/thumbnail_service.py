"""
Service for generating PSD layer thumbnails using Photoshop.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from services.base_service import BaseService, Result


class ThumbnailService(BaseService):
    """Generates thumbnails of PSD layers using Photoshop automation."""

    def __init__(self, logger, photoshop_path: Optional[str] = None):
        super().__init__(logger)
        self.photoshop_path = photoshop_path or "/Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app"
        self.thumbnail_size = (200, 200)  # Default thumbnail dimensions

    def generate_layer_thumbnails(self, psd_path: str, output_folder: str,
                                  session_id: str) -> Result[Dict[str, str]]:
        """
        Generate thumbnails for all layers in a PSD file.

        Args:
            psd_path: Path to PSD file
            output_folder: Folder to save thumbnails
            session_id: Session identifier for cache naming

        Returns:
            Result containing dict mapping layer names to thumbnail file paths
        """
        # DIAGNOSTIC LOGGING
        self.log_info("=" * 70)
        self.log_info("THUMBNAIL GENERATION STARTED")
        self.log_info("=" * 70)
        self.log_info(f"PSD path: {psd_path}")
        self.log_info(f"PSD exists: {os.path.exists(psd_path)}")
        self.log_info(f"PSD is absolute: {os.path.isabs(psd_path)}")
        self.log_info(f"Output folder: {output_folder}")
        self.log_info(f"Session ID: {session_id}")

        try:
            # Create output folder
            thumb_folder = Path(output_folder) / "thumbnails" / session_id
            thumb_folder.mkdir(parents=True, exist_ok=True)
            self.log_info(f"Thumbnail folder: {thumb_folder}")
            self.log_info(f"Thumbnail folder exists: {thumb_folder.exists()}")

            # Create temp results file
            results_file = tempfile.mktemp(suffix='.json')
            self.log_info(f"Results file path: {results_file}")

            # Generate ExtendScript to export layer thumbnails
            jsx_script = self._generate_thumbnail_script(psd_path, str(thumb_folder), results_file)
            self.log_info(f"Generated ExtendScript: {len(jsx_script)} characters")

            # Execute via Photoshop
            thumbnails = self._execute_photoshop_script(jsx_script, results_file)

            self.log_info(f"FINAL RESULT: Generated {len(thumbnails)} thumbnails")
            self.log_info(f"Thumbnails keys: {list(thumbnails.keys())}")
            return Result.success(thumbnails)

        except Exception as e:
            self.log_error(f"Thumbnail generation failed: {e}", exc_info=True)
            return Result.failure(str(e))

    def _generate_thumbnail_script(self, psd_path: str, output_folder: str, results_file: str) -> str:
        """Generate ExtendScript to export layer thumbnails."""

        width, height = self.thumbnail_size

        # Escape paths for JavaScript
        psd_path_js = psd_path.replace('\\', '/').replace('"', '\\"')
        output_folder_js = output_folder.replace('\\', '/').replace('"', '\\"')
        results_file_js = results_file.replace('\\', '/').replace('"', '\\"')

        script = f'''
// Thumbnail Export Script
var psdFile = new File("{psd_path_js}");
var outputFolder = new Folder("{output_folder_js}");

if (!outputFolder.exists) {{
    outputFolder.create();
}}

// Suppress all dialogs for headless operation
app.displayDialogs = DialogModes.NO;

// Open PSD
var doc = app.open(psdFile);
app.activeDocument = doc;  // Make sure document is active and frontmost

// Export options
var pngOptions = new PNGSaveOptions();
pngOptions.compression = 6;

var results = [];

try {{
    // Iterate through layers
    for (var i = 0; i < doc.layers.length; i++) {{
        var layer = doc.layers[i];
        app.activeDocument = doc;  // Ensure doc is active at start of iteration

        try {{
            // Skip if layer is not visible or is a group
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

            // CRITICAL: Re-confirm active document after visibility changes
            app.activeDocument = doc;

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

                // Resize to target width (matches working test script)
                var scale = ({width} / layerWidth) * 100;
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
                app.activeDocument = doc;  // Re-activate original document
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
    // Silent error handling - errors are logged in results array
    // No alert dialog for headless operation
    results.push({{
        layer: "ERROR",
        error: e.toString(),
        success: false
    }});
}} finally {{
    // Close document
    doc.close(SaveOptions.DONOTSAVECHANGES);
}}

// Custom JSON stringifier (ExtendScript doesn't have native JSON.stringify)
function escapeJSON(str) {{
    return str.replace(/\\\\/g, "\\\\\\\\")
              .replace(/"/g, '\\\\"')
              .replace(/\\n/g, "\\\\n")
              .replace(/\\r/g, "\\\\r")
              .replace(/\\t/g, "\\\\t");
}}

function toJSON(results) {{
    var json = "[";
    for (var i = 0; i < results.length; i++) {{
        if (i > 0) json += ",";
        json += "{{";

        var props = [];
        if (results[i].layer !== undefined) {{
            props.push('\\"layer\\":\\"' + escapeJSON(results[i].layer.toString()) + '\\"');
        }}
        if (results[i].success !== undefined) {{
            props.push('\\"success\\":' + (results[i].success ? 'true' : 'false'));
        }}
        if (results[i].skipped !== undefined) {{
            props.push('\\"skipped\\":' + (results[i].skipped ? 'true' : 'false'));
        }}
        if (results[i].safeName !== undefined) {{
            props.push('\\"safeName\\":\\"' + escapeJSON(results[i].safeName.toString()) + '\\"');
        }}
        if (results[i].file !== undefined) {{
            props.push('\\"file\\":\\"' + escapeJSON(results[i].file.toString()) + '\\"');
        }}
        if (results[i].reason !== undefined) {{
            props.push('\\"reason\\":\\"' + escapeJSON(results[i].reason.toString()) + '\\"');
        }}
        if (results[i].error !== undefined) {{
            props.push('\\"error\\":\\"' + escapeJSON(results[i].error.toString()) + '\\"');
        }}

        json += props.join(",");
        json += "}}";
    }}
    json += "]";
    return json;
}}

// Write results to file
var resultsFile = new File("{results_file_js}");
resultsFile.open("w");
resultsFile.write(toJSON(results));
resultsFile.close();
'''
        return script

    def _execute_photoshop_script(self, jsx_script: str, results_file: str) -> Dict[str, str]:
        """Execute ExtendScript via Photoshop and parse results."""

        # Save script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsx', delete=False) as f:
            jsx_file = f.name
            f.write(jsx_script)

        # DIAGNOSTIC LOGGING
        self.log_info("=" * 70)
        self.log_info("THUMBNAIL GENERATION - DETAILED DIAGNOSTICS")
        self.log_info("=" * 70)
        self.log_info(f"ExtendScript length: {len(jsx_script)} characters")
        self.log_info(f"ExtendScript file: {jsx_file}")
        self.log_info(f"Results file: {results_file}")
        self.log_info(f"JSX file exists: {os.path.exists(jsx_file)}")
        self.log_info(f"First 300 chars of script:\n{jsx_script[:300]}")
        self.log_info(f"Last 300 chars of script:\n{jsx_script[-300:]}")

        try:
            # Escape the jsx_file path for AppleScript
            # Replace backslashes and escape quotes
            jsx_file_escaped = jsx_file.replace('\\', '\\\\').replace('"', '\\"')

            # Build AppleScript to run Photoshop script in background
            # Using separate osascript lines to avoid quoting issues
            applescript = f'''
            tell application "Adobe Photoshop 2026"
                -- Don't activate to keep Photoshop in background
                do javascript file (POSIX file "{jsx_file_escaped}")
            end tell

            -- Hide Photoshop after script execution
            tell application "System Events"
                set visible of process "Adobe Photoshop 2026" to false
            end tell
            '''

            self.log_info("Executing Photoshop script for thumbnail generation...")
            self.log_info(f"JSX file (original): {jsx_file}")
            self.log_info(f"JSX file (escaped): {jsx_file_escaped}")
            self.log_info(f"AppleScript:\n{applescript}")

            # Execute using osascript with the script passed via stdin for better handling
            result = subprocess.run(
                ['osascript', '-'],
                input=applescript,
                capture_output=True,
                text=True,
                timeout=120
            )

            self.log_info(f"AppleScript return code: {result.returncode}")
            self.log_info(f"AppleScript stdout: {result.stdout}")
            self.log_info(f"AppleScript stderr: {result.stderr}")

            if result.returncode != 0:
                self.log_error(f"Photoshop script error: {result.stderr}")
                return {}

            # Check if results file was created
            self.log_info(f"Results file exists after execution: {os.path.exists(results_file)}")
            if os.path.exists(results_file):
                file_size = os.path.getsize(results_file)
                self.log_info(f"Results file size: {file_size} bytes")
                if file_size > 0:
                    with open(results_file, 'r') as f:
                        content = f.read()
                        self.log_info(f"Results file content ({len(content)} chars):\n{content[:500]}")

            # Read results from file
            thumbnails = self._parse_thumbnail_results_file(results_file)

            self.log_info(f"Parsed thumbnails count: {len(thumbnails)}")
            self.log_info(f"Thumbnails dict: {thumbnails}")
            self.log_info("=" * 70)

            return thumbnails

        except subprocess.TimeoutExpired:
            self.log_error("Thumbnail generation timed out")
            return {}
        except Exception as e:
            self.log_error(f"Error executing Photoshop script: {e}")
            return {}
        finally:
            # Cleanup temp files
            try:
                os.unlink(jsx_file)
            except:
                pass
            try:
                if os.path.exists(results_file):
                    os.unlink(results_file)
            except:
                pass

    def _parse_thumbnail_results_file(self, results_file: str) -> Dict[str, str]:
        """Parse thumbnail generation results from JSON file."""

        thumbnails = {}

        try:
            # Check if results file exists
            if not os.path.exists(results_file):
                self.log_error(f"Results file not found: {results_file}")
                return thumbnails

            # Read and parse JSON
            with open(results_file, 'r') as f:
                results = json.load(f)

            # Process each result
            for result in results:
                if result.get('success'):
                    layer_name = result['layer']
                    safe_name = result.get('safeName', layer_name)

                    # Map original layer name to safe filename
                    thumbnails[layer_name] = safe_name + '.png'

                    self.log_debug(f"Thumbnail for '{layer_name}': {safe_name}.png")
                else:
                    reason = result.get('reason', result.get('error', 'Unknown'))
                    self.log_warning(f"Failed to generate thumbnail for '{result['layer']}': {reason}")

        except json.JSONDecodeError as e:
            self.log_error(f"Failed to parse thumbnail results: {e}")
        except Exception as e:
            self.log_error(f"Error reading thumbnail results: {e}")

        return thumbnails

    def _parse_thumbnail_results(self, stdout: str) -> Dict[str, str]:
        """Parse thumbnail generation results from stdout (deprecated - kept for compatibility)."""

        thumbnails = {}

        # Look for THUMBNAIL_RESULTS marker
        for line in stdout.split('\n'):
            if line.startswith('THUMBNAIL_RESULTS:'):
                try:
                    json_str = line.replace('THUMBNAIL_RESULTS:', '')
                    results = json.loads(json_str)

                    for result in results:
                        if result.get('success'):
                            layer_name = result['layer']
                            safe_name = result.get('safeName', layer_name)
                            file_path = result['file']

                            # Map original layer name to safe filename
                            thumbnails[layer_name] = safe_name + '.png'

                            self.log_debug(f"Thumbnail for '{layer_name}': {safe_name}.png")
                        else:
                            reason = result.get('reason', result.get('error', 'Unknown'))
                            self.log_warning(f"Failed to generate thumbnail for '{result['layer']}': {reason}")

                except json.JSONDecodeError as e:
                    self.log_error(f"Failed to parse thumbnail results: {e}")
                except Exception as e:
                    self.log_error(f"Error processing thumbnail results: {e}")

        return thumbnails

    def get_thumbnail_path(self, session_id: str, layer_name: str,
                          output_folder: str) -> Optional[str]:
        """Get path to cached thumbnail if it exists."""

        thumb_folder = Path(output_folder) / "thumbnails" / session_id

        # Try with original name
        thumb_file = thumb_folder / f"{layer_name}.png"
        if thumb_file.exists():
            return str(thumb_file)

        # Try with safe name (replace special chars)
        safe_name = layer_name.replace('/', '_').replace('\\', '_')
        safe_name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in safe_name)
        thumb_file = thumb_folder / f"{safe_name}.png"
        if thumb_file.exists():
            return str(thumb_file)

        return None

    def render_psd_to_png(self, psd_path: str, output_path: str) -> Result:
        """
        Render full PSD as flattened PNG for preview

        Args:
            psd_path: Path to PSD file
            output_path: Where to save PNG

        Returns:
            Result with output path
        """
        try:
            from psd_tools import PSDImage
            from PIL import Image

            # Open PSD
            psd = PSDImage.open(psd_path)

            # Convert to PIL Image (flattened)
            img = psd.compose()

            # Save as PNG
            img.save(output_path, 'PNG')

            self.log_info(f"Rendered PSD to PNG: {output_path}")
            return Result.success({'output_path': output_path})

        except Exception as e:
            self.log_error(f"PSD to PNG render failed: {e}", exc_info=True)
            return Result.failure(f"Render failed: {str(e)}")
