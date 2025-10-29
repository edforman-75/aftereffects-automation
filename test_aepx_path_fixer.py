#!/usr/bin/env python3
"""
Test AEPX Footage Path Fixer
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase2.aepx_path_fixer import (
    find_footage_references,
    fix_footage_paths,
    collect_footage_files
)


def test_find_footage_references():
    """Test finding footage references in AEPX file."""
    print("\n" + "="*70)
    print("TEST 1: Find Footage References")
    print("="*70)

    # Look for test AEPX files
    test_files = [
        'sample_files/test-correct.aepx',
        'uploads/1735246738_aepx_test-correct.aepx',
    ]

    aepx_file = None
    for test_file in test_files:
        if os.path.exists(test_file):
            aepx_file = test_file
            break

    if not aepx_file:
        print("⚠️  No test AEPX file found. Skipping test.")
        print(f"   Looked for: {', '.join(test_files)}")
        return False

    print(f"\nTesting with: {aepx_file}")

    try:
        refs = find_footage_references(aepx_file)

        print(f"\n✅ Found {len(refs)} footage references")

        if refs:
            print("\nFootage files:")
            for i, ref in enumerate(refs, 1):
                status = "✅" if ref['exists'] else "❌"
                print(f"  {i}. {status} [{ref['type']}] {ref['path']}")
                print(f"      Element: <{ref['element']}>")
        else:
            print("  (No footage references found in this AEPX)")

        return True

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fix_footage_paths():
    """Test fixing footage paths."""
    print("\n" + "="*70)
    print("TEST 2: Fix Footage Paths")
    print("="*70)

    # Look for test AEPX files
    test_files = [
        'sample_files/test-correct.aepx',
        'uploads/1735246738_aepx_test-correct.aepx',
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
        # Create footage directory
        footage_dir = 'sample_files/footage'
        os.makedirs(footage_dir, exist_ok=True)

        # Fix paths
        output_file = aepx_file.replace('.aepx', '_fixed.aepx')
        result = fix_footage_paths(aepx_file, output_file, footage_dir)

        if result['success']:
            print(f"\n✅ {result['message']}")
            print(f"\nOutput: {result['output_path']}")

            if result['fixed_paths']:
                print(f"\nFixed {len(result['fixed_paths'])} paths:")
                for old_path, new_path in result['fixed_paths'].items():
                    filename = os.path.basename(old_path)
                    print(f"  {filename}")
                    print(f"    OLD: {old_path}")
                    print(f"    NEW: {new_path}")

            if result['missing_files']:
                print(f"\n⚠️  Missing {len(result['missing_files'])} files:")
                for missing in result['missing_files']:
                    print(f"  ❌ {missing}")

            # Verify output file exists
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"\n✅ Output file created: {file_size:,} bytes")
                return True
            else:
                print(f"\n❌ Output file not created")
                return False

        else:
            print(f"\n❌ FAIL: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_collect_footage_files():
    """Test collecting footage files."""
    print("\n" + "="*70)
    print("TEST 3: Collect Footage Files")
    print("="*70)

    # Look for test AEPX files
    test_files = [
        'sample_files/test-correct.aepx',
        'uploads/1735246738_aepx_test-correct.aepx',
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
        # Collect files
        output_dir = 'test_collected'
        result = collect_footage_files(aepx_file, output_dir)

        if result['success']:
            print(f"\n✅ {result['message']}")
            print(f"\nOutput directory: {output_dir}")
            print(f"Footage directory: {result['footage_dir']}")
            print(f"New AEPX: {result['aepx_path']}")

            if result['collected_files']:
                print(f"\nCollected {len(result['collected_files'])} files:")
                for filepath in result['collected_files']:
                    filename = os.path.basename(filepath)
                    size = os.path.getsize(filepath)
                    print(f"  ✅ {filename} ({size:,} bytes)")

            if result['missing_files']:
                print(f"\n⚠️  Missing {len(result['missing_files'])} files:")
                for missing in result['missing_files']:
                    print(f"  ❌ {missing}")

            return True

        else:
            print(f"\n❌ FAIL: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "AEPX PATH FIXER TESTS" + " " * 29 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []

    # Run tests
    results.append(("Find Footage References", test_find_footage_references()))
    results.append(("Fix Footage Paths", test_fix_footage_paths()))
    results.append(("Collect Footage Files", test_collect_footage_files()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nRESULTS: {passed}/{total} tests passed")
    print("="*70)
    print()

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
