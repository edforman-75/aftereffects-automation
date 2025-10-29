/*
 * Extract PSD Layer Data - ExtendScript for Adobe Photoshop
 *
 * Extracts complete layer information from the active Photoshop document
 * and outputs it as JSON to a temporary file.
 *
 * Returns: Path to the JSON output file
 */

// JSON polyfill for ExtendScript (some versions don't have native JSON)
if (typeof JSON === 'undefined') {
    JSON = {
        stringify: function(obj, replacer, space) {
            return _jsonStringify(obj, replacer, space || '');
        }
    };

    function _jsonStringify(obj, replacer, space) {
        var indent = typeof space === 'number' ? Array(space + 1).join(' ') : space;
        return _stringify(obj, replacer, indent, '');
    }

    function _stringify(obj, replacer, indent, currentIndent) {
        var type = typeof obj;

        if (obj === null) return 'null';
        if (type === 'undefined') return undefined;
        if (type === 'number' || type === 'boolean') return String(obj);
        if (type === 'string') return '"' + obj.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t') + '"';

        if (obj instanceof Array) {
            var items = [];
            for (var i = 0; i < obj.length; i++) {
                var val = _stringify(obj[i], replacer, indent, currentIndent + indent);
                items.push(val !== undefined ? val : 'null');
            }
            if (items.length === 0) return '[]';
            if (!indent) return '[' + items.join(',') + ']';
            return '[\n' + currentIndent + indent + items.join(',\n' + currentIndent + indent) + '\n' + currentIndent + ']';
        }

        if (type === 'object') {
            var pairs = [];
            for (var key in obj) {
                if (obj.hasOwnProperty(key)) {
                    var val = _stringify(obj[key], replacer, indent, currentIndent + indent);
                    if (val !== undefined) {
                        pairs.push('"' + key + '":' + (indent ? ' ' : '') + val);
                    }
                }
            }
            if (pairs.length === 0) return '{}';
            if (!indent) return '{' + pairs.join(',') + '}';
            return '{\n' + currentIndent + indent + pairs.join(',\n' + currentIndent + indent) + '\n' + currentIndent + '}';
        }

        return undefined;
    }
}

// Main extraction function
function extractLayerData() {
    try {
        // Get active document
        if (app.documents.length === 0) {
            throw new Error("No document is open");
        }

        var doc = app.activeDocument;

        // Build layer data structure
        var data = {
            filename: doc.name,
            width: doc.width.as("px"),
            height: doc.height.as("px"),
            mode: doc.mode.toString(),
            layers: [],
            parse_method: "photoshop"
        };

        // Extract all layers recursively
        data.layers = extractLayers(doc, "");

        // Write to temporary JSON file
        var outputPath = Folder.temp + "/psd_extract_" + new Date().getTime() + ".json";
        var outputFile = new File(outputPath);

        outputFile.encoding = "UTF-8";
        outputFile.open("w");
        outputFile.write(JSON.stringify(data, null, 2));
        outputFile.close();

        return outputPath;

    } catch (e) {
        return "ERROR: " + e.toString();
    }
}

// Recursively extract layers from document or layer set
function extractLayers(layerParent, parentPath) {
    var layers = [];
    var layerCount = layerParent.layers ? layerParent.layers.length : 0;

    // Iterate through layers (in reverse to maintain top-to-bottom order)
    for (var i = layerCount - 1; i >= 0; i--) {
        var layer = layerParent.layers[i];

        try {
            var layerPath = parentPath ? (parentPath + "/" + layer.name) : layer.name;

            // Build layer info object
            var layerInfo = {
                name: layer.name,
                type: getLayerType(layer),
                visible: layer.visible,
                path: layerPath
            };

            // Get layer bounds
            try {
                var bounds = layer.bounds;
                layerInfo.bbox = {
                    left: parseInt(bounds[0].as("px")),
                    top: parseInt(bounds[1].as("px")),
                    right: parseInt(bounds[2].as("px")),
                    bottom: parseInt(bounds[3].as("px"))
                };
                layerInfo.width = layerInfo.bbox.right - layerInfo.bbox.left;
                layerInfo.height = layerInfo.bbox.bottom - layerInfo.bbox.top;
            } catch (boundsError) {
                // Some layers don't have bounds (empty layers, etc.)
            }

            // Extract text layer information
            if (layer.kind === LayerKind.TEXT) {
                try {
                    layerInfo.text = extractTextInfo(layer);
                } catch (textError) {
                    // Text extraction failed, skip text info
                }
            }

            // Extract group/layer set children
            if (layer.typename === "LayerSet") {
                layerInfo.children = extractLayers(layer, layerPath);
            }

            layers.push(layerInfo);

        } catch (layerError) {
            // Skip layers that cause errors
            layers.push({
                name: layer.name || "Unknown Layer",
                type: "unknown",
                visible: false,
                path: parentPath ? (parentPath + "/Unknown") : "Unknown",
                error: layerError.toString()
            });
        }
    }

    return layers;
}

// Determine layer type
function getLayerType(layer) {
    try {
        var kind = layer.kind;

        if (kind === LayerKind.TEXT) {
            return "text";
        } else if (kind === LayerKind.NORMAL) {
            // Check if it's a smart object
            try {
                if (layer.kind === LayerKind.SMARTOBJECT) {
                    return "smartobject";
                }
            } catch (e) {}
            return "image";
        } else if (kind === LayerKind.SOLIDFILL) {
            return "shape";
        } else if (kind === LayerKind.GRADIENTFILL) {
            return "shape";
        } else if (kind === LayerKind.PATTERNFILL) {
            return "shape";
        } else if (kind === LayerKind.BRIGHTNESSCONTRAST) {
            return "adjustment";
        } else if (kind === LayerKind.LEVELS) {
            return "adjustment";
        } else if (kind === LayerKind.CURVES) {
            return "adjustment";
        } else if (kind === LayerKind.COLORBALANCE) {
            return "adjustment";
        } else if (kind === LayerKind.HUESATURATION) {
            return "adjustment";
        }

        // Check if it's a group/layer set
        if (layer.typename === "LayerSet") {
            return "group";
        }

        return "image";

    } catch (e) {
        return "unknown";
    }
}

// Extract text layer information
function extractTextInfo(textLayer) {
    var textInfo = {};

    try {
        var textItem = textLayer.textItem;

        // Text content
        textInfo.content = textItem.contents;

        // Font name
        try {
            textInfo.font = textItem.font;
        } catch (e) {}

        // Font size
        try {
            textInfo.font_size = parseFloat(textItem.size.as("px"));
        } catch (e) {}

        // Text color
        try {
            var color = textItem.color;
            textInfo.color = {
                r: Math.round(color.rgb.red),
                g: Math.round(color.rgb.green),
                b: Math.round(color.rgb.blue),
                a: 255
            };
        } catch (e) {}

        // Justification
        try {
            var just = textItem.justification;
            if (just === Justification.LEFT) {
                textInfo.justification = "left";
            } else if (just === Justification.CENTER) {
                textInfo.justification = "center";
            } else if (just === Justification.RIGHT) {
                textInfo.justification = "right";
            }
        } catch (e) {}

    } catch (e) {
        // Return empty text info on error
    }

    return textInfo;
}

// Execute and return result
extractLayerData();
