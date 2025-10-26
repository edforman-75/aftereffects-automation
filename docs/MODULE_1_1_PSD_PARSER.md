# Module 1.1: Photoshop File Parser

## Overview

The PSD Parser module extracts structured layer information from Adobe Photoshop (PSD) files into Python dictionaries. This data forms the foundation for mapping PSD layers to After Effects templates.

**Location:** `modules/phase1/psd_parser.py`

---

## Features

✅ **Document Metadata** - Extracts filename, width, and height
✅ **Layer Hierarchy** - Preserves nested groups and folder structure
✅ **Layer Types** - Identifies text, image, shape, group, and smart object layers
✅ **Bounding Boxes** - Captures position and dimensions for each layer
✅ **Visibility State** - Tracks which layers are visible/hidden
✅ **Path Tracking** - Maintains full path for nested layers (e.g., "Group1/SubGroup/Layer")

---

## Installation

The module requires `psd-tools` library:

```bash
pip install psd-tools
```

Already installed in the project's virtual environment.

---

## Usage

### Basic Usage

```python
from modules.phase1.psd_parser import parse_psd

# Parse a PSD file
result = parse_psd("path/to/design.psd")

# Access document info
print(f"File: {result['filename']}")
print(f"Size: {result['width']} x {result['height']}")
print(f"Layers: {len(result['layers'])}")
```

### Output Structure

The `parse_psd()` function returns a dictionary with this structure:

```python
{
    "filename": "design.psd",
    "width": 1920,
    "height": 1080,
    "layers": [
        {
            "name": "Background",
            "type": "image",
            "visible": True,
            "path": "Background",
            "bbox": {
                "left": 0,
                "top": 0,
                "right": 1920,
                "bottom": 1080
            },
            "width": 1920,
            "height": 1080
        },
        {
            "name": "Text Group",
            "type": "group",
            "visible": True,
            "path": "Text Group",
            "children": [
                {
                    "name": "Title",
                    "type": "text",
                    "visible": True,
                    "path": "Text Group/Title",
                    "bbox": {...},
                    "width": 500,
                    "height": 60
                }
            ]
        }
    ]
}
```

---

## Layer Types

The parser identifies the following layer types:

| Type | Description | Example |
|------|-------------|---------|
| `text` | Text layers with font information | Titles, body text, labels |
| `image` | Pixel/raster layers | Photos, illustrations |
| `shape` | Vector shape layers | Rectangles, circles, custom paths |
| `group` | Folder/group containing other layers | Organizational structure |
| `smartobject` | Embedded or linked smart objects | External PSDs, vectors |
| `unknown` | Unidentified layer type | Edge cases |

---

## API Reference

### `parse_psd(file_path: str) -> Dict[str, Any]`

Parses a PSD file and returns structured layer data.

**Parameters:**
- `file_path` (str): Path to the PSD file

**Returns:**
- `dict`: Dictionary with keys `filename`, `width`, `height`, `layers`

**Raises:**
- `FileNotFoundError`: If the PSD file doesn't exist
- `ValueError`: If the file is not a valid PSD format

**Example:**
```python
result = parse_psd("designs/homepage.psd")
```

---

## Demo Script

A demonstration script is provided to show the parser in action:

```bash
python examples/demo_psd_parser.py path/to/design.psd
```

This will:
1. Parse the PSD file
2. Display document info and layer hierarchy
3. Save the parsed data to JSON

**Output Example:**
```
============================================================
Parsing PSD File: designs/sample.psd
============================================================

📄 Document: sample.psd
📐 Dimensions: 1920 x 1080 pixels
🎨 Total Layers: 5

📂 Layer Structure:
------------------------------------------------------------
🖼️ Background (image) 👁️ [1920x1080]
📁 Content (group) 👁️ [1200x800]
  📝 Headline (text) 👁️ [500x60]
  📝 Subtitle (text) 👁️ [400x30]
🔷 Logo (smartobject) 👁️ [200x100]

✓ Parsed data saved to: sample_parsed.json
```

---

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/test_psd_parser.py -v

# Run specific test
pytest tests/test_psd_parser.py::TestPSDParser::test_parse_psd_file_not_found -v
```

**Note:** Most tests are placeholders waiting for sample PSD files. Add sample files to `sample_files/` directory to enable full testing.

---

## Next Steps

The current implementation provides:
- ✅ Basic layer extraction
- ✅ Type identification
- ✅ Hierarchy preservation
- ✅ Bounding box data

**Future Enhancements:**
- 📝 Text layer content extraction (fonts, size, color)
- 🎨 Layer effects extraction (shadows, glows, etc.)
- 🖼️ Image data extraction (actual pixel data)
- 🔗 Smart object contents parsing
- 📊 Layer style information
- 🎯 More detailed shape data

---

## Troubleshooting

### Common Issues

**"No module named psd_tools"**
```bash
source venv/bin/activate
pip install psd-tools
```

**"FileNotFoundError"**
- Check that the PSD file path is correct
- Use absolute paths or relative to script location

**"Invalid PSD file"**
- Ensure file is a valid Photoshop document
- Try opening in Photoshop to verify it's not corrupted

---

## Architecture

```
PSD File → psd_parser.py → Structured Dictionary
                 ↓
           JSON Export
                 ↓
    (Next Phase: AE Template Mapping)
```

The parser is designed to be:
- **Modular**: Can be used standalone or as part of larger pipeline
- **Testable**: Clear interfaces for unit testing
- **Extensible**: Easy to add new layer property extraction
- **Error-Resilient**: Handles malformed files gracefully

---

## Dependencies

- **psd-tools** (v1.10.13): Core PSD parsing library
- **pathlib**: Path handling (standard library)
- **typing**: Type hints (standard library)

---

## Version

**Current Version:** 1.0.0
**Status:** ✅ Core functionality complete
**Last Updated:** October 26, 2025

---

## Contact & Contribution

For questions or improvements, update the module and tests following the modular development approach established in this project.
