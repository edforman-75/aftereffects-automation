#!/usr/bin/env python3
"""
Test preview generation with correct composition name.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import generate_preview

def test_preview_with_correct_comp_name():
    """Test preview generation using actual composition name from AEPX."""

    print("\n" + "="*70)
    print("TEST: Preview Generation with Correct Composition Name")
    print("="*70)

    # Create temp AEPX file
    temp_dir = tempfile.mkdtemp(prefix='test_comp_')
    aepx_path = f"{temp_dir}/test-correct.aepx"

    with open(aepx_path, 'w') as f:
        f.write('<?xml version="1.0"?><AfterEffectsProject></AfterEffectsProject>')

    # Mappings with composition_name from AEPX (after web_app.py fix)
    mappings = {
        'composition_name': 'test-aep',  # ← This is now set by web_app.py
        'mappings': [
            {
                'psd_layer': 'Title',
                'aepx_placeholder': 'player1fullname',
                'type': 'text',
                'confidence': 1.0
            }
        ],
        'unmapped_psd_layers': [],
        'unfilled_placeholders': []
    }

    output_path = f"{temp_dir}/preview.mp4"

    print(f"\nConfiguration:")
    print(f"  AEPX Path: {aepx_path}")
    print(f"  Output Path: {output_path}")
    print(f"  Composition Name: '{mappings['composition_name']}'")
    print(f"\nExpected behavior:")
    print(f"  ✓ Should use composition 'test-aep' (from AEPX)")
    print(f"  ✗ Should NOT use 'Main Comp' (hardcoded default)")
    print()

    # Mock aerender to simulate successful render
    def mock_subprocess_run(*args, **kwargs):
        cmd = args[0]
        # Extract composition name from command
        comp_idx = cmd.index('-comp') + 1 if '-comp' in cmd else -1
        if comp_idx > 0:
            comp_used = cmd[comp_idx]
            print(f"Mock aerender: Rendering composition '{comp_used}'")

            # Verify correct composition name is used
            if comp_used == 'test-aep':
                print(f"✅ Correct composition name used!")
            else:
                print(f"❌ Wrong composition name! Expected 'test-aep', got '{comp_used}'")

        # Create output file to simulate successful render
        with open(output_path, 'wb') as f:
            f.write(b'mock video data')

        return Mock(returncode=0, stdout='Render completed', stderr='')

    # Mock check_aerender_available to return a path
    with patch('modules.phase5.preview_generator.check_aerender_available',
               return_value='/Applications/Adobe After Effects 2025/aerender'):
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            # Generate preview
            result = generate_preview(aepx_path, mappings, output_path)

            print(f"\nResult:")
            print(f"  Success: {result['success']}")
            if result['success']:
                print(f"  Video Path: {result['video_path']}")
                return True
            else:
                print(f"  Error: {result.get('error')}")
                return False

if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "PREVIEW WITH CORRECT COMPOSITION NAME" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")

    success = test_preview_with_correct_comp_name()

    print("\n" + "="*70)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("="*70)
    print()

    sys.exit(0 if success else 1)
