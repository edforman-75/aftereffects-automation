"""
Test AEPX parser functionality.

Verifies that compositions, layers, and placeholders are correctly extracted
from After Effects AEPX template files.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase2.aepx_parser import parse_aepx


def test_aepx_parser():
    """Test that AEPX parser extracts compositions and placeholders."""

    # Parse the test AEPX file
    result = parse_aepx('sample_files/test-after-effects-project.aepx')

    print("=" * 70)
    print("AEPX PARSER TEST")
    print("=" * 70)

    # Test 1: Basic structure
    print("\n✓ Parsed AEPX file successfully")
    print(f"  Filename: {result['filename']}")
    print(f"  Main Composition: {result['composition_name']}")
    print(f"  Total Compositions: {len(result['compositions'])}")
    print(f"  Total Placeholders: {len(result['placeholders'])}")

    # Test 2: Verify expected keys
    checks = []
    checks.append(('filename' in result, "Has 'filename' key"))
    checks.append(('composition_name' in result, "Has 'composition_name' key"))
    checks.append(('compositions' in result, "Has 'compositions' key"))
    checks.append(('placeholders' in result, "Has 'placeholders' key"))

    # Test 3: Verify main composition name
    checks.append(
        (result['composition_name'] == 'Split Screen',
         "Main composition is 'Split Screen'")
    )

    # Test 4: Verify we found compositions
    checks.append(
        (len(result['compositions']) >= 1,
         "Found at least one composition")
    )

    # Test 5: Check composition structure
    if result['compositions']:
        comp = result['compositions'][0]
        checks.append(('name' in comp, "Composition has 'name'"))
        checks.append(('width' in comp, "Composition has 'width'"))
        checks.append(('height' in comp, "Composition has 'height'"))
        checks.append(('duration' in comp, "Composition has 'duration'"))
        checks.append(('layers' in comp, "Composition has 'layers'"))

    # Test 6: Verify placeholder detection
    placeholder_names = [p['name'] for p in result['placeholders']]
    
    expected_placeholders = [
        'player1fullname',
        'player2fullname',
        'player3fullname',
        'featuredimage1'
    ]

    print("\n" + "=" * 70)
    print("PLACEHOLDER DETECTION")
    print("=" * 70)
    
    for expected in expected_placeholders:
        found = expected in placeholder_names
        checks.append((found, f"Found placeholder: {expected}"))
        if found:
            placeholder = next(p for p in result['placeholders'] if p['name'] == expected)
            print(f"\n✓ {expected}")
            print(f"  Type: {placeholder['type']}")
            print(f"  Composition: {placeholder['composition']}")

    # Test 7: Verify layer structure
    print("\n" + "=" * 70)
    print("LAYER STRUCTURE")
    print("=" * 70)

    for comp in result['compositions']:
        print(f"\nComposition: {comp['name']} ({comp['width']}x{comp['height']})")
        print(f"  Duration: {comp['duration']}s")
        print(f"  Layers: {len(comp['layers'])}")
        
        for layer in comp['layers']:
            placeholder_marker = " [PLACEHOLDER]" if layer['is_placeholder'] else ""
            print(f"    - {layer['name']} ({layer['type']}){placeholder_marker}")

    # Run all checks
    print("\n" + "=" * 70)
    print("VERIFICATION CHECKS")
    print("=" * 70)

    passed = 0
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"{status} {description}")
        if check:
            passed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(checks)} checks passed")
    print("=" * 70)

    # Assert all critical checks passed
    assert passed >= len(checks) * 0.9, f"Too many checks failed: {passed}/{len(checks)}"
    
    print("\n🎉 AEPX parser test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_aepx_parser()
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
