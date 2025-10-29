# PSD Parser Fallback Mechanism

## Overview

The PSD parser (`modules/phase1/psd_parser.py`) now includes a fallback mechanism to handle newer Photoshop formats that the `psd-tools` library cannot parse.

## Problem

The `psd-tools` library fails on Photoshop version 8+ files with:
```
AssertionError: Invalid version 8
```

These newer Photoshop formats cannot be read by psd-tools, but Pillow (PIL) can still read them as images and extract basic information.

## Solution

The parser now implements a two-tier approach:

### 1. Primary: psd-tools (Full Parsing)

First, the parser attempts to use `psd-tools` for complete layer parsing:
- Full layer hierarchy
- Layer types (text, image, shape, group, smart object)
- Text content and styling
- Bounding boxes and dimensions
- Visibility information
- Nested layer groups

### 2. Fallback: Pillow (Basic Parsing)

If `psd-tools` fails with a version error or other parsing error, the parser automatically falls back to Pillow:
- Document dimensions (width, height)
- Color mode (RGB, CMYK, etc.)
- Layer names (when available)
- Basic layer structure

## Usage

The parser automatically handles the fallback - no code changes needed:

```python
from modules.phase1.psd_parser import parse_psd

# Works with both old and new Photoshop formats
result = parse_psd('path/to/file.psd')

# Check which parser was used
if result['limited_parse']:
    print("Used Pillow fallback (newer Photoshop format)")
else:
    print("Used psd-tools (full layer information available)")
```

## Return Structure

### Full Parse (psd-tools)

```python
{
    "filename": "example.psd",
    "width": 1920,
    "height": 1080,
    "limited_parse": False,  # Full parsing available
    "layers": [
        {
            "name": "Background",
            "type": "image",
            "visible": True,
            "path": "Background",
            "bbox": {"left": 0, "top": 0, "right": 1920, "bottom": 1080},
            "width": 1920,
            "height": 1080
        },
        {
            "name": "Title Text",
            "type": "text",
            "visible": True,
            "path": "Title Text",
            "text": {
                "content": "Hello World",
                "font_size": 72.0,
                "color": {"r": 255, "g": 255, "b": 255, "a": 255}
            }
        }
        # ... more layers
    ]
}
```

### Limited Parse (Pillow)

```python
{
    "filename": "example.psd",
    "width": 1920,
    "height": 1080,
    "mode": "RGB",
    "limited_parse": True,  # Pillow fallback was used
    "layers": [
        {
            "name": "Background",
            "type": "unknown",  # Type info not available in Pillow
            "visible": True,
            "path": "Background"
        },
        {
            "name": "Title Text",
            "type": "unknown",
            "visible": True,
            "path": "Title Text"
        }
        # ... more layers (names only)
    ]
}
```

## Key Differences

| Feature | psd-tools (Full) | Pillow (Limited) |
|---------|------------------|------------------|
| Layer names | ✅ | ✅ |
| Layer types | ✅ | ❌ (unknown) |
| Layer hierarchy | ✅ | ❌ (flat list) |
| Text content | ✅ | ❌ |
| Text styling | ✅ | ❌ |
| Bounding boxes | ✅ | ❌ |
| Visibility | ✅ | ⚠️ (assumed true) |
| Smart objects | ✅ | ❌ |
| Layer groups | ✅ | ❌ |

## Logging

The parser provides detailed logging to help debug parsing issues:

```
INFO: Attempting to parse PSD with psd-tools: file.psd
INFO: Successfully parsed PSD with psd-tools: 6 layers found
```

Or when fallback is used:

```
INFO: Attempting to parse PSD with psd-tools: file.psd
WARNING: psd-tools failed with version error: Invalid version 8
INFO: Falling back to Pillow for basic parsing: file.psd
INFO: Extracted 6 layer names from Pillow
INFO: Successfully parsed PSD with Pillow: 6 layers, 1920x1080, mode=RGB (LIMITED PARSE)
```

## Testing

Run the test script to verify both parsers work:

```bash
python3 test_psd_fallback.py
```

This will test:
1. Normal parsing with psd-tools
2. Direct Pillow parsing
3. Display which parser was used for each file

## Handling Limited Parse in Your Code

When `limited_parse` is `True`, adapt your code accordingly:

```python
result = parse_psd('file.psd')

if result['limited_parse']:
    # Limited parsing - only layer names available
    print(f"Warning: Limited parse mode. Only basic info available.")

    # Can still use layer names for matching
    layer_names = [layer['name'] for layer in result['layers']]

    # But cannot rely on:
    # - Layer types
    # - Text content
    # - Bounding boxes
    # - Layer hierarchy
else:
    # Full parsing - all information available
    for layer in result['layers']:
        if layer['type'] == 'text':
            print(f"Text layer: {layer['text']['content']}")
```

## Compatibility

- **psd-tools**: Works with Photoshop CS through CC 2015 (versions 1-7)
- **Pillow fallback**: Works with newer Photoshop CC formats (version 8+)

Together, these provide coverage for all Photoshop formats from CS1 through the latest CC versions.

## Error Handling

If both parsers fail, the system raises a descriptive error:

```python
ValueError: Unable to parse PSD file: file.psd.
psd-tools error: [error details], Pillow error: [error details]
```

This helps diagnose files that cannot be read by either parser (e.g., corrupted files).
