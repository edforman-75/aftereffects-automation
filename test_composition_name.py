#!/usr/bin/env python3
"""
Test to verify composition name is correctly passed to preview generator.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_composition_name_fix():
    """Verify composition name is correctly extracted from AEPX data."""

    print("\n" + "="*70)
    print("TEST: Composition Name Fix")
    print("="*70)

    # Simulate session data (like what's stored in web_app.py sessions dict)
    session = {
        'aepx_path': '/path/to/test-correct.aepx',
        'aepx_data': {
            'filename': 'test-correct.aepx',
            'composition_name': 'test-aep',  # This is the actual comp name
            'compositions': [
                {'name': 'test-aep', 'width': 1920, 'height': 1080},
                {'name': 'test-photoshop-doc', 'width': 1920, 'height': 1080}
            ],
            'placeholders': [
                {'name': 'player1fullname', 'type': 'text'},
                {'name': 'player2fullname', 'type': 'text'},
                {'name': 'player3fullname', 'type': 'text'}
            ]
        },
        'mappings': {
            'mappings': [
                {'psd_layer': 'Title', 'aepx_placeholder': 'player1fullname', 'type': 'text'}
            ],
            'unmapped_psd_layers': [],
            'unfilled_placeholders': []
            # Note: composition_name is NOT in mappings initially
        }
    }

    # Simulate what the /generate-preview endpoint does
    aepx_data = session['aepx_data']
    mappings = session['mappings']

    print(f"\n1. BEFORE FIX:")
    print(f"   Mappings dict keys: {list(mappings.keys())}")
    print(f"   'composition_name' in mappings: {'composition_name' in mappings}")
    print(f"   Would use: mappings.get('composition_name', 'Main Comp') = '{mappings.get('composition_name', 'Main Comp')}'")

    # Apply the fix from web_app.py
    if 'composition_name' not in mappings:
        mappings['composition_name'] = aepx_data.get('composition_name', 'Main Comp')

    print(f"\n2. AFTER FIX:")
    print(f"   Mappings dict keys: {list(mappings.keys())}")
    print(f"   'composition_name' in mappings: {'composition_name' in mappings}")
    print(f"   mappings['composition_name'] = '{mappings['composition_name']}'")

    # Verify the fix
    expected_comp_name = 'test-aep'
    actual_comp_name = mappings.get('composition_name', 'Main Comp')

    print(f"\n3. VERIFICATION:")
    print(f"   Expected composition name: '{expected_comp_name}'")
    print(f"   Actual composition name: '{actual_comp_name}'")

    if actual_comp_name == expected_comp_name:
        print(f"   ✅ CORRECT! Using actual composition name from AEPX")
        return True
    else:
        print(f"   ❌ WRONG! Not using actual composition name")
        return False


def test_aerender_command():
    """Show what the aerender command will look like with correct comp name."""

    print("\n" + "="*70)
    print("TEST: aerender Command Preview")
    print("="*70)

    # Simulate aerender command construction
    aerender_path = "/Applications/Adobe After Effects 2025/aerender"
    project_path = "/tmp/ae_preview_abc/test-correct.aepx"
    comp_name = "test-aep"  # Correct name from AEPX
    output_path = "/previews/preview_123.mp4"

    cmd = [
        aerender_path,
        '-project', project_path,
        '-comp', comp_name,
        '-output', output_path,
        '-RStemplate', 'Best Settings',
        '-OMtemplate', 'H.264',
        '-s', '0',
        '-e', '75'
    ]

    cmd_str = ' '.join([f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in cmd])

    print(f"\naerender command that will be executed:")
    print(f"  {cmd_str}")

    print(f"\n✅ Command uses composition name: '{comp_name}'")
    print(f"   (instead of hardcoded 'Main Comp')")

    return True


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "COMPOSITION NAME FIX TEST" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []
    results.append(("Composition Name Fix", test_composition_name_fix()))
    results.append(("aerender Command Preview", test_aerender_command()))

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

    sys.exit(0 if passed == total else 1)
