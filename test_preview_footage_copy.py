#!/usr/bin/env python3
"""
Test preview generator with footage copying
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import prepare_temp_project


def test_footage_copying():
    """Test that footage files are copied to temp directory."""
    print("\n" + "="*70)
    print("TEST: Footage Copying in Preview Generation")
    print("="*70)

    # Look for test AEPX with footage
    test_files = [
        'sample_files/test-correct.aepx',
        'sample_files/test-correct_fixed.aepx',
    ]

    aepx_file = None
    for test_file in test_files:
        if os.path.exists(test_file):
            aepx_file = test_file
            break

    if not aepx_file:
        print("⚠️  No test AEPX file found. Skipping test.")
        return False

    print(f"\nTesting with: {aepx_file}")

    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix='test_preview_footage_')
        print(f"Temp directory: {temp_dir}\n")

        # Prepare temp project (this should copy footage)
        mappings = {'test': 'value'}
        result = prepare_temp_project(aepx_file, mappings, temp_dir)

        print(f"\n✅ Temp project created: {result}")

        # Check what files were created
        print(f"\nFiles in temp directory:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                print(f"{subindent}{file} ({file_size:,} bytes)")

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\n✅ Test completed successfully")

        return True

    except Exception as e:
        print(f"\n❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PREVIEW FOOTAGE COPY TEST" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")

    result = test_footage_copying()

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{status}: Footage Copying")
    print("="*70)
    print()

    sys.exit(0 if result else 1)
