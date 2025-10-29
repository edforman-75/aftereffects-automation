#!/usr/bin/env python3
"""
Test Step 3.7: ExtendScript Population Before Rendering

This test runs the complete preview generation workflow to verify that:
1. ExtendScript is generated correctly
2. AppleScript/osascript successfully opens After Effects
3. ExtendScript runs and populates template content
4. Project is saved with populated content
5. aerender renders the populated (not placeholder) content
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import generate_preview

def test_population_workflow():
    """Test complete preview generation with Step 3.7 population."""

    print("=" * 80)
    print("TEST: Step 3.7 ExtendScript Population")
    print("=" * 80)
    print()

    # Test inputs
    aepx_path = 'sample_files/test-correct-fixed.aepx'
    output_path = '/tmp/test_populated_preview.mp4'

    # Mappings with actual content (not placeholders)
    # Note: aepx_placeholder must match the actual layer name in the AEPX (case-sensitive)
    mappings = {
        'composition_name': 'test-aep',
        'mappings': [
            {
                'psd_layer': 'BEN FORMAN',
                'aepx_placeholder': 'player1fullname',  # Actual layer name (lowercase)
                'type': 'text'
            },
            {
                'psd_layer': 'EMMA LOUISE',
                'aepx_placeholder': 'player2fullname',  # Actual layer name (lowercase)
                'type': 'text'
            },
            {
                'psd_layer': 'ELOISE GRACE',
                'aepx_placeholder': 'player3fullname',  # Actual layer name (lowercase)
                'type': 'text'
            }
        ]
    }

    # Options for preview
    options = {
        'resolution': 'half',
        'duration': 2.5,
        'format': 'mp4'
    }

    print("Test Configuration:")
    print(f"  AEPX: {aepx_path}")
    print(f"  Output: {output_path}")
    print(f"  Mappings: {len(mappings.get('mappings', []))} items")
    print(f"  Options: {options}")
    print()

    # Verify AEPX exists
    if not os.path.exists(aepx_path):
        print(f"❌ FAIL: AEPX file not found: {aepx_path}")
        return False

    print("✅ AEPX file exists")
    print()

    # Run preview generation
    print("-" * 80)
    print("Running Preview Generation (with Step 3.7 population)...")
    print("-" * 80)
    print()

    try:
        result = generate_preview(aepx_path, mappings, output_path, options)

        print()
        print("-" * 80)
        print("Preview Generation Complete")
        print("-" * 80)
        print()

        # Check results
        if result.get('success'):
            print("✅ Preview generation succeeded!")
            print()

            # Verify output file
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✅ Output video exists: {output_path}")
                print(f"   Size: {file_size:,} bytes")
            else:
                print(f"❌ Output video not found: {output_path}")
                return False

            # Verify thumbnail
            if result.get('thumbnail_path') and os.path.exists(result['thumbnail_path']):
                print(f"✅ Thumbnail exists: {result['thumbnail_path']}")

            # Show metadata
            if result.get('duration'):
                print(f"✅ Duration: {result['duration']} seconds")

            if result.get('resolution'):
                print(f"✅ Resolution: {result['resolution']}")

            if result.get('fps'):
                print(f"✅ FPS: {result['fps']}")

            print()
            print("=" * 80)
            print("MANUAL VERIFICATION NEEDED:")
            print("=" * 80)
            print()
            print("To verify Step 3.7 worked correctly, please:")
            print(f"1. Open the output video: {output_path}")
            print("2. Check if you see actual content:")
            print("   - 'BEN FORMAN' (instead of 'player1fullname')")
            print("   - 'EMMA LOUISE' (instead of 'player2fullname')")
            print("   - 'ELOISE GRACE' (instead of 'player3fullname')")
            print()
            print("If you see the actual content, Step 3.7 is working! ✅")
            print("If you see placeholders, Step 3.7 needs debugging. ❌")
            print()

            return True

        else:
            print(f"❌ Preview generation failed!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Exception during preview generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_population_workflow()
    sys.exit(0 if success else 1)
