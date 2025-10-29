#!/usr/bin/env python3
"""
Test footage search with multiple locations
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import prepare_temp_project


def test_footage_search_multiple_locations():
    """Test that footage files are found in multiple search locations."""
    print("\n" + "="*70)
    print("TEST: Footage Search with Multiple Locations")
    print("="*70)

    # Use AEPX with relative paths
    aepx_file = 'sample_files/test-correct-fixed.aepx'

    if not os.path.exists(aepx_file):
        print(f"⚠️  Test AEPX not found: {aepx_file}")
        return False

    print(f"\nTesting with: {aepx_file}")
    print("Expected footage references:")
    print("  - footage/cutout.png")
    print("  - footage/green_yellow_bg.png")
    print("  - footage/test-photoshop-doc.psd")
    print("\nThese should be found in: sample_files/footage/\n")

    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix='test_footage_search_')
        print(f"Temp directory: {temp_dir}\n")

        # Prepare temp project (this should copy footage from sample_files/footage/)
        mappings = {'test': 'value'}
        result = prepare_temp_project(aepx_file, mappings, temp_dir)

        print(f"\n✅ Temp project created: {result}")

        # Check what files were created
        print(f"\nFiles in temp directory:")
        all_files = []
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            rel_root = os.path.relpath(root, temp_dir)
            if rel_root == '.':
                print(f"{indent}{os.path.basename(temp_dir)}/")
            else:
                print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                print(f"{subindent}{file} ({file_size:,} bytes)")
                all_files.append(file)

        # Verify expected files
        expected_files = ['cutout.png', 'green_yellow_bg.png', 'test-photoshop-doc.psd']
        found_footage = [f for f in expected_files if f in all_files]

        print(f"\n{'='*70}")
        print("VERIFICATION")
        print(f"{'='*70}")
        print(f"Expected footage files: {len(expected_files)}")
        print(f"Found in temp dir: {len(found_footage)}")

        for filename in expected_files:
            if filename in found_footage:
                print(f"  ✅ {filename}")
            else:
                print(f"  ❌ {filename} (NOT FOUND)")

        # Cleanup
        shutil.rmtree(temp_dir)

        # Success if all footage files found
        success = len(found_footage) == len(expected_files)

        if success:
            print(f"\n✅ Test PASSED: All {len(expected_files)} footage files found")
        else:
            print(f"\n❌ Test FAILED: Only {len(found_footage)}/{len(expected_files)} footage files found")

        return success

    except Exception as e:
        print(f"\n❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "FOOTAGE MULTI-LOCATION SEARCH TEST" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")

    result = test_footage_search_multiple_locations()

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{status}: Footage Multi-Location Search")
    print("="*70)
    print()

    sys.exit(0 if result else 1)
