"""
Demo: Using the PSD Parser

This script demonstrates how to use the PSD parser to extract
layer information from Photoshop files.
"""

import sys
import json
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase1.psd_parser import parse_psd


def demo_parse_psd(psd_file_path: str):
    """
    Demonstrate parsing a PSD file and displaying the results.

    Args:
        psd_file_path: Path to the PSD file to parse
    """
    print(f"\n{'='*60}")
    print(f"Parsing PSD File: {psd_file_path}")
    print(f"{'='*60}\n")

    try:
        # Parse the PSD file
        result = parse_psd(psd_file_path)

        # Display document information
        print(f"📄 Document: {result['filename']}")
        print(f"📐 Dimensions: {result['width']} x {result['height']} pixels")
        print(f"🎨 Total Layers: {len(result['layers'])}")
        print()

        # Display layer hierarchy
        print("📂 Layer Structure:")
        print("-" * 60)
        _print_layers(result['layers'], indent=0)

        # Save to JSON file
        output_file = Path(psd_file_path).stem + "_parsed.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n✓ Parsed data saved to: {output_file}")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except ValueError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def _print_layers(layers, indent=0):
    """Recursively print layer hierarchy with indentation."""
    prefix = "  " * indent

    for layer in layers:
        # Layer icon based on type
        icons = {
            'text': '📝',
            'image': '🖼️',
            'shape': '⬜',
            'group': '📁',
            'smartobject': '🔷',
            'unknown': '❓'
        }
        icon = icons.get(layer['type'], '❓')

        # Layer visibility
        visibility = '👁️' if layer['visible'] else '🚫'

        # Print layer info
        dims = f"{layer.get('width', '?')}x{layer.get('height', '?')}"
        print(f"{prefix}{icon} {layer['name']} ({layer['type']}) {visibility} [{dims}]")

        # Print children if it's a group
        if 'children' in layer and layer['children']:
            _print_layers(layer['children'], indent + 1)


if __name__ == "__main__":
    # Check if PSD file path was provided
    if len(sys.argv) < 2:
        print("Usage: python demo_psd_parser.py <path_to_psd_file>")
        print("\nExample:")
        print("  python demo_psd_parser.py sample_files/my_design.psd")
        sys.exit(1)

    # Parse the provided PSD file
    psd_file = sys.argv[1]
    demo_parse_psd(psd_file)
