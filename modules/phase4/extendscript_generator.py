"""
Module 4.1: ExtendScript Generator

Generates After Effects ExtendScript (.jsx) files that automate template population.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime


def generate_extendscript(psd_data: Dict[str, Any], aepx_data: Dict[str, Any],
                          mappings: Dict[str, Any], output_path: str,
                          options: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate After Effects ExtendScript (.jsx) file for template automation.

    Args:
        psd_data: Parsed PSD data from Module 1.1
        aepx_data: Parsed AEPX data from Module 2.1
        mappings: Mapping results from Module 3.1
        output_path: Path where .jsx file should be saved
        options: Optional configuration dictionary with:
            - psd_file_path: Full path to source PSD
            - aepx_file_path: Full path to template AEPX
            - output_project_path: Full path to save output AEP
            - render_output: Whether to render video (default: False)
            - render_path: Full path to rendered video output
            - image_sources: Dict mapping layer names to image file paths
              (e.g., {'featuredimage1': '/path/to/image.png'})

    Returns:
        Path to generated .jsx file
    """
    # Default options
    opts = {
        "psd_file_path": "",
        "aepx_file_path": "",
        "output_project_path": "",
        "render_output": False,
        "render_path": "",
        "image_sources": {}
    }
    if options:
        opts.update(options)

    # Generate the ExtendScript code
    script_content = _generate_script_content(psd_data, aepx_data, mappings, opts)

    # Write to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(script_content)

    return str(output_file.absolute())


def _generate_script_content(psd_data: Dict, aepx_data: Dict,
                             mappings: Dict, opts: Dict) -> str:
    """Generate the actual ExtendScript code content."""

    # Extract mapping information
    text_mappings = [m for m in mappings['mappings'] if m['type'] == 'text']
    image_mappings = [m for m in mappings['mappings'] if m['type'] == 'image']

    # Build text replacement data
    text_replacements = []
    for mapping in text_mappings:
        psd_layer = next((l for l in psd_data['layers'] if l['name'] == mapping['psd_layer']), None)
        if psd_layer and 'text' in psd_layer:
            text_replacements.append({
                'placeholder': mapping['aepx_placeholder'],
                'content': psd_layer['text']['content'],
                'font_size': psd_layer['text'].get('font_size', None),
                'color': psd_layer['text'].get('color', None)
            })

    # Build image replacement data
    image_replacements = []
    image_sources = opts.get('image_sources', {})
    for mapping in image_mappings:
        # Get image path from image_sources (keyed by aepx_placeholder or psd_layer)
        image_path = image_sources.get(mapping['aepx_placeholder']) or image_sources.get(mapping['psd_layer'])

        if image_path:
            image_replacements.append({
                'placeholder': mapping['aepx_placeholder'],
                'psd_layer': mapping['psd_layer'],
                'image_path': str(image_path)  # Absolute path to image file
            })
        else:
            # Skip if no image path provided
            pass

    # Generate script sections
    header = _generate_header(psd_data, aepx_data, opts)
    helpers = _generate_helper_functions()
    main = _generate_main_function(text_replacements, image_replacements, opts, aepx_data)
    footer = _generate_footer()

    return f"{header}\n\n{helpers}\n\n{main}\n\n{footer}"


def _generate_header(psd_data: Dict, aepx_data: Dict, opts: Dict) -> str:
    """Generate script header with metadata."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""/*
 * After Effects Template Automation Script
 *
 * Generated: {timestamp}
 * Source PSD: {psd_data['filename']}
 * Template: {aepx_data['filename']}
 * Composition: {aepx_data['composition_name']}
 *
 * SETUP INSTRUCTIONS:
 * 1. Open your template file manually in After Effects
 *    File: {_escape_path(opts['aepx_file_path'])}
 * 2. Then run this script: File → Scripts → Run Script File
 *
 * The script will update the currently open project.
 */

// Configuration
var CONFIG = {{
    psdFile: "{_escape_path(opts['psd_file_path'])}",
    outputProject: "{_escape_path(opts['output_project_path'])}",
    renderOutput: {str(opts['render_output']).lower()},
    renderPath: "{_escape_path(opts['render_path'])}",
    compositionName: "{aepx_data['composition_name']}"
}};"""


def _generate_helper_functions() -> str:
    """Generate helper functions for the script."""

    return """// Helper Functions

function repeatString(str, count) {
    /*
     * Repeat a string count times (ES3-compatible).
     * ES3 doesn't support String.repeat().
     */
    var result = "";
    for (var i = 0; i < count; i++) {
        result += str;
    }
    return result;
}

function findLayerByName(comp, layerName) {
    /*
     * Find a layer in a composition by name.
     * Returns the layer object or null if not found.
     */
    for (var i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).name === layerName) {
            return comp.layer(i);
        }
    }
    return null;
}

function updateTextLayer(layer, newText, fontSize, color) {
    /*
     * Update text layer content and optionally formatting.
     * Args:
     *   layer: Text layer object
     *   newText: New text content string
     *   fontSize: Font size in points (optional, pass null to skip)
     *   color: Color array [r, g, b, a] (optional, pass null to skip)
     */
    try {
        var textProp = layer.property("ADBE Text Properties").property("ADBE Text Document");
        var textDoc = textProp.value;

        // Update text content
        textDoc.text = newText;

        // Update font size if provided
        if (fontSize !== null) {
            textDoc.fontSize = fontSize;
        }

        // Update color if provided
        if (color !== null) {
            textDoc.fillColor = color;
        }

        textProp.setValue(textDoc);
        return true;
    } catch (e) {
        alert("Error updating text layer '" + layer.name + "': " + e.toString());
        return false;
    }
}

function replaceImageSource(layer, imagePath) {
    /*
     * Replace the source of an image/video layer.
     * Imports the new image file and replaces the layer's source.
     * Args:
     *   layer: Layer object to update
     *   imagePath: Absolute path to new image file
     */
    try {
        // Check if file exists
        var imageFile = new File(imagePath);
        if (!imageFile.exists) {
            logMessage("ERROR: Image file not found: " + imagePath);
            return false;
        }

        // Import the new image file
        var importOptions = new ImportOptions(imageFile);
        var footage = app.project.importFile(importOptions);

        if (!footage) {
            logMessage("ERROR: Failed to import image: " + imagePath);
            return false;
        }

        // Replace the layer's source
        layer.replaceSource(footage, false);  // false = don't fix expressions

        logMessage("  ✓ Replaced with: " + imageFile.name);
        return true;
    } catch (e) {
        logMessage("ERROR replacing image for layer '" + layer.name + "': " + e.toString());
        return false;
    }
}

function logMessage(message) {
    /*
     * Log a message to the console and optionally display.
     */
    $.writeln(message);
}"""


def _generate_main_function(text_replacements: list, image_replacements: list,
                            opts: Dict, aepx_data: Dict) -> str:
    """Generate the main execution function."""

    # Build text update code
    text_updates = []
    for tr in text_replacements:
        color_str = "null"
        if tr['color']:
            # Color is stored as dict with 'r', 'g', 'b', 'a' keys
            color = tr['color']
            r_norm = float(color['r']) / 255.0
            g_norm = float(color['g']) / 255.0
            b_norm = float(color['b']) / 255.0
            color_str = f"[{r_norm:.3f}, {g_norm:.3f}, {b_norm:.3f}]"

        font_size = tr['font_size'] if tr['font_size'] else "null"
        escaped_text = _escape_js_string(tr['content'])

        text_updates.append(f"""
    // Update text: {tr['placeholder']}
    layer = findLayerByName(comp, "{tr['placeholder']}");
    if (layer) {{
        logMessage("Updating text layer: {tr['placeholder']}");
        updateTextLayer(layer, "{escaped_text}", {font_size}, {color_str});
    }} else {{
        logMessage("WARNING: Layer not found: {tr['placeholder']}");
    }}""")

    # Build image update code
    image_updates = []
    for ir in image_replacements:
        escaped_path = _escape_path(ir['image_path'])
        image_updates.append(f"""
    // Replace image: {ir['placeholder']}
    layer = findLayerByName(comp, "{ir['placeholder']}");
    if (layer) {{
        logMessage("Replacing image layer: {ir['placeholder']}");
        replaceImageSource(layer, "{escaped_path}");
    }} else {{
        logMessage("WARNING: Layer not found: {ir['placeholder']}");
    }}""")

    text_code = "\n".join(text_updates) if text_updates else "    // No text layers to update"
    image_code = "\n".join(image_updates) if image_updates else "    // No image layers to update"

    render_code = """
    // Render composition
    if (CONFIG.renderOutput && CONFIG.renderPath) {
        logMessage("Rendering to: " + CONFIG.renderPath);
        // Note: Rendering requires render queue setup
        // This is a placeholder for the actual render logic
        alert("Rendering would output to: " + CONFIG.renderPath);
    }""" if opts['render_output'] else "    // Rendering disabled"

    return f"""// Main Execution
function main() {{
    try {{
        logMessage(repeatString("=", 70));
        logMessage("After Effects Template Automation");
        logMessage(repeatString("=", 70));

        // Check if a project is open
        if (app.project == null || app.project.file == null) {{
            alert("ERROR: No project is open!\\n\\nPlease open your template file first, then run this script.");
            return;
        }}

        logMessage("Working with currently open project");
        logMessage("Project: " + app.project.file.name);
        logMessage("");

        // Find main composition
        var comp = null;
        for (var i = 1; i <= app.project.numItems; i++) {{
            if (app.project.item(i) instanceof CompItem) {{
                if (app.project.item(i).name === CONFIG.compositionName) {{
                    comp = app.project.item(i);
                    break;
                }}
            }}
        }}

        if (!comp) {{
            var errorMsg = "ERROR: Composition '" + CONFIG.compositionName + "' not found!\\n\\n";
            errorMsg += "Available compositions:\\n";
            for (var i = 1; i <= app.project.numItems; i++) {{
                if (app.project.item(i) instanceof CompItem) {{
                    errorMsg += "  - " + app.project.item(i).name + "\\n";
                }}
            }}
            alert(errorMsg);
            return;
        }}

        logMessage("Found composition: " + comp.name);
        logMessage("");

        var layer;

        // Update text layers
        logMessage("Updating text layers...");
{text_code}
        logMessage("");

        // Update image layers
        logMessage("Updating image layers...");
{image_code}
        logMessage("");

        // Save project
        if (CONFIG.outputProject) {{
            logMessage("Saving project to: " + CONFIG.outputProject);
            var saveFile = new File(CONFIG.outputProject);
            app.project.save(saveFile);
        }}
{render_code}

        logMessage("");
        logMessage(repeatString("=", 70));
        logMessage("Automation completed successfully!");
        logMessage(repeatString("=", 70));

        alert("Template automation completed successfully!");

    }} catch (e) {{
        var errorMsg = "ERROR: " + e.toString() + "\\nLine: " + e.line;
        logMessage(errorMsg);
        alert(errorMsg);
    }}
}}"""


def _generate_footer() -> str:
    """Generate script footer."""
    return """
// Execute main function
main();
"""


def _escape_path(path: str) -> str:
    """Escape file path for ExtendScript."""
    # Replace backslashes with forward slashes for cross-platform compatibility
    return path.replace('\\', '/')


def _escape_js_string(text: str) -> str:
    """Escape string for JavaScript."""
    return (text
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))
