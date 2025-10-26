"""
Real-world test for PSD Parser with actual PSD file.

This test uses the uploaded test-photoshop-doc.psd file.
"""

import sys
import json
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules' / 'phase1'))

from psd_parser import parse_psd


def test_with_uploaded_psd():
    """Test parser with the uploaded PSD file."""

    # Try multiple possible locations for the uploaded file
    possible_paths = [
        "/mnt/user-data/uploads/test-photoshop-doc.psd",
        "/tmp/uploads/test-photoshop-doc.psd",
        "sample_files/test-photoshop-doc.psd",
        "../sample_files/test-photoshop-doc.psd",
    ]

    psd_file = None
    for path in possible_paths:
        if Path(path).exists():
            psd_file = path
            break

    if not psd_file:
        print("❌ PSD file not found. Tried:")
        for path in possible_paths:
            print(f"   - {path}")
        print("\nPlease place test-photoshop-doc.psd in sample_files/")
        return False

    print(f"✓ Found PSD file: {psd_file}\n")
    print("=" * 70)
    print("PARSING PSD FILE")
    print("=" * 70)

    try:
        # Parse the PSD
        result = parse_psd(psd_file)

        # Display results in readable format
        print(f"\n📄 Filename: {result['filename']}")
        print(f"📐 Dimensions: {result['width']} x {result['height']} pixels")
        print(f"🎨 Total Layers: {len(result['layers'])}")

        print("\n" + "=" * 70)
        print("LAYER STRUCTURE")
        print("=" * 70)

        # Print layer hierarchy
        _print_layers(result['layers'], indent=0)

        print("\n" + "=" * 70)
        print("FULL JSON OUTPUT")
        print("=" * 70)

        # Print full JSON
        print(json.dumps(result, indent=2))

        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        # Verify expected keys
        checks = [
            ("filename" in result, "Has 'filename' key"),
            ("width" in result, "Has 'width' key"),
            ("height" in result, "Has 'height' key"),
            ("layers" in result, "Has 'layers' key"),
            (isinstance(result["layers"], list), "Layers is a list"),
            (result["width"] > 0, "Width is positive"),
            (result["height"] > 0, "Height is positive"),
        ]

        all_passed = True
        for check, description in checks:
            status = "✓" if check else "✗"
            print(f"{status} {description}")
            if not check:
                all_passed = False

        if all_passed:
            print("\n🎉 ALL CHECKS PASSED!")
        else:
            print("\n⚠️  Some checks failed")

        return all_passed

    except Exception as e:
        print(f"\n❌ Error parsing PSD: {e}")
        import traceback
        traceback.print_exc()
        return False


def _print_layers(layers, indent=0):
    """Recursively print layer hierarchy."""
    prefix = "  " * indent

    icons = {
        'text': '📝',
        'image': '🖼️ ',
        'shape': '⬜',
        'group': '📁',
        'smartobject': '🔷',
        'unknown': '❓'
    }

    for layer in layers:
        icon = icons.get(layer['type'], '❓')
        visibility = '👁️ ' if layer['visible'] else '🚫'

        # Format dimensions
        if 'width' in layer and 'height' in layer:
            dims = f"[{layer['width']}x{layer['height']}]"
        else:
            dims = "[no dims]"

        print(f"{prefix}{icon} {layer['name']} ({layer['type']}) {visibility} {dims}")

        # Print bounding box if available
        if 'bbox' in layer:
            bbox = layer['bbox']
            print(f"{prefix}   ↳ Position: ({bbox['left']}, {bbox['top']}) → ({bbox['right']}, {bbox['bottom']})")

        # Recursively print children
        if 'children' in layer:
            _print_layers(layer['children'], indent + 1)


if __name__ == "__main__":
    success = test_with_uploaded_psd()
    sys.exit(0 if success else 1)
