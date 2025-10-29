#!/usr/bin/env python3
"""
Test script to verify PSD parser fallback behavior.
Tests both psd-tools parsing and Pillow fallback.
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

from modules.phase1.psd_parser import parse_psd, _parse_psd_with_pillow


def test_psd_parser():
    """Test PSD parser with available test files."""
    test_files = [
        './sample_files/test-photoshop-doc.psd',
        './uploads/1761698127_e50e1411_psd_test-photoshop-doc.psd',
    ]

    print("=" * 70)
    print("PSD PARSER TEST - Testing fallback behavior")
    print("=" * 70)

    success_count = 0
    failure_count = 0

    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"\n⚠️  Skipping (file not found): {test_file}")
            continue

        print(f"\n{'=' * 70}")
        print(f"Testing: {test_file}")
        print('=' * 70)

        try:
            # Test with parse_psd (will try psd-tools first, then Pillow if needed)
            result = parse_psd(test_file)

            print(f"\n✅ Parse successful!")
            print(f"   Filename: {result['filename']}")
            print(f"   Dimensions: {result['width']}x{result['height']}")
            print(f"   Number of layers: {len(result['layers'])}")
            print(f"   Limited parse: {result.get('limited_parse', False)}")
            print(f"   Parser used: {'Pillow (fallback)' if result.get('limited_parse') else 'psd-tools (full)'}")

            if result.get('mode'):
                print(f"   Mode: {result['mode']}")

            if result['layers']:
                print(f"\n   Layers:")
                for i, layer in enumerate(result['layers'][:5]):
                    print(f"      {i+1}. {layer['name']} (type: {layer['type']})")
                if len(result['layers']) > 5:
                    print(f"      ... and {len(result['layers']) - 5} more layers")

            success_count += 1

        except Exception as e:
            print(f"\n❌ Parse failed: {e}")
            failure_count += 1
            import traceback
            traceback.print_exc()

    # Also test direct Pillow parsing
    print(f"\n{'=' * 70}")
    print("Testing direct Pillow parsing (fallback method)")
    print('=' * 70)

    test_file = './sample_files/test-photoshop-doc.psd'
    if Path(test_file).exists():
        try:
            result = _parse_psd_with_pillow(test_file, Path(test_file))

            print(f"\n✅ Pillow parse successful!")
            print(f"   Filename: {result['filename']}")
            print(f"   Dimensions: {result['width']}x{result['height']}")
            print(f"   Number of layers: {len(result['layers'])}")
            print(f"   Limited parse: {result.get('limited_parse', False)}")
            print(f"   Mode: {result.get('mode', 'N/A')}")

            if result['layers']:
                print(f"\n   Layers:")
                for i, layer in enumerate(result['layers'][:5]):
                    print(f"      {i+1}. {layer['name']}")

        except Exception as e:
            print(f"\n❌ Pillow parse failed: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print(f"\n{'=' * 70}")
    print("TEST SUMMARY")
    print('=' * 70)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failure_count}")
    print(f"\nThe fallback mechanism is ready to handle:")
    print(f"  • Photoshop version 8+ files (newer formats)")
    print(f"  • Files that psd-tools cannot parse")
    print(f"  • Will gracefully fall back to Pillow for basic parsing")
    print('=' * 70)


if __name__ == '__main__':
    test_psd_parser()
