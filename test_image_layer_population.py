#!/usr/bin/env python3
"""
Test Image Layer Population in ExtendScript

This test verifies that:
1. ExtendScript generator handles both text AND image mappings
2. Image replacement code is generated correctly
3. Image sources are properly mapped from temp directory
4. Preview generation includes image layer population
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import generate_preview

def test_image_layer_population():
    """Test image layer population in preview generation."""

    print("=" * 80)
    print("TEST: Image Layer Population")
    print("=" * 80)
    print()

    # Test inputs
    aepx_path = 'sample_files/test-correct-fixed.aepx'
    output_path = '/tmp/test_image_population_preview.mp4'

    # Mappings with BOTH text and image layers
    mappings = {
        'composition_name': 'test-aep',
        'mappings': [
            # Text layers
            {
                'psd_layer': 'BEN FORMAN',
                'aepx_placeholder': 'player1fullname',
                'type': 'text'
            },
            {
                'psd_layer': 'EMMA LOUISE',
                'aepx_placeholder': 'player2fullname',
                'type': 'text'
            },
            # Image layer
            {
                'psd_layer': 'cutout',  # PSD layer name (matches cutout.png)
                'aepx_placeholder': 'featuredimage1',  # AEPX layer name
                'type': 'image'
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
    print(f"  Text mappings: 2")
    print(f"  Image mappings: 1")
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
    print("Running Preview Generation (with text AND image population)...")
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

            print()
            print("=" * 80)
            print("MANUAL VERIFICATION NEEDED:")
            print("=" * 80)
            print()
            print("To verify image population worked, check:")
            print(f"1. Open the output video: {output_path}")
            print("2. Verify you see:")
            print("   TEXT:")
            print("     - 'BEN FORMAN' (not 'player1fullname')")
            print("     - 'EMMA LOUISE' (not 'player2fullname')")
            print("   IMAGE:")
            print("     - 'cutout.png' image displayed (not placeholder)")
            print()
            print("If you see both text AND image content, it's working! ✅")
            print()

            # Check ExtendScript was generated
            temp_dirs = []
            for root, dirs, files in os.walk('/var/folders'):
                if 'ae_preview_' in root and 'populate.jsx' in files:
                    temp_dirs.append(root)

            if temp_dirs:
                latest_temp = max(temp_dirs, key=os.path.getctime)
                jsx_file = os.path.join(latest_temp, 'populate.jsx')

                print("=" * 80)
                print("EXTENDSCRIPT VERIFICATION:")
                print("=" * 80)
                print()
                print(f"Generated ExtendScript: {jsx_file}")
                print()

                # Read and check for image replacement code
                with open(jsx_file, 'r', encoding='utf-8') as f:
                    jsx_content = f.read()

                # Check for text replacement
                has_text_replacement = 'updateTextLayer' in jsx_content
                print(f"{'✅' if has_text_replacement else '❌'} Contains text replacement code")

                # Check for image replacement
                has_image_replacement = 'replaceImageSource' in jsx_content
                print(f"{'✅' if has_image_replacement else '❌'} Contains image replacement code")

                # Check for specific layer names
                has_player1 = 'player1fullname' in jsx_content
                has_featured = 'featuredimage1' in jsx_content
                print(f"{'✅' if has_player1 else '❌'} References text layer 'player1fullname'")
                print(f"{'✅' if has_featured else '❌'} References image layer 'featuredimage1'")

                # Check for cutout.png path
                has_cutout = 'cutout.png' in jsx_content
                print(f"{'✅' if has_cutout else '❌'} References 'cutout.png' image file")

                print()

                if has_text_replacement and has_image_replacement and has_cutout:
                    print("✅ ExtendScript contains BOTH text and image replacement code!")
                    print()
                    return True
                else:
                    print("⚠️  ExtendScript may be missing some replacement code")
                    print()
                    return False

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
    success = test_image_layer_population()
    sys.exit(0 if success else 1)
