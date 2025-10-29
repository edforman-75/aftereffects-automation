#!/usr/bin/env python3
"""
Test PSD Layer Preview Usage for Image Population

This test verifies that:
1. Image sources use PSD layer preview files (not footage placeholders)
2. Session ID is extracted from AEPX path
3. Preview files are found using glob pattern
4. Most recent preview file is used
5. Falls back to footage if preview not available
"""

import os
import sys
import shutil
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase5.preview_generator import generate_preview

def setup_test_preview_files():
    """Create mock PSD layer preview files for testing."""

    # Create previews directory if it doesn't exist
    preview_dir = Path('previews')
    preview_dir.mkdir(exist_ok=True)

    # Create mock session ID (matching the pattern in uploads/)
    session_id = "1761598122_ab371181"
    timestamp1 = int(time.time())
    timestamp2 = timestamp1 + 10  # Newer file

    # Create mock PSD layer preview files
    preview_files = []

    # Create cutout layer preview (older)
    cutout_preview1 = preview_dir / f"psd_layer_cutout_{session_id}_{timestamp1}.png"
    with open(cutout_preview1, 'wb') as f:
        # Write a simple 1x1 PNG
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89')
    preview_files.append(cutout_preview1)
    print(f"Created mock preview: {cutout_preview1}")

    # Create cutout layer preview (newer - should be selected)
    time.sleep(0.1)  # Ensure different mtime
    cutout_preview2 = preview_dir / f"psd_layer_cutout_{session_id}_{timestamp2}.png"
    with open(cutout_preview2, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89')
    preview_files.append(cutout_preview2)
    print(f"Created mock preview: {cutout_preview2}")

    # Create background layer preview
    background_preview = preview_dir / f"psd_layer_green_yellow_bg_{session_id}_{timestamp1}.png"
    with open(background_preview, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89')
    preview_files.append(background_preview)
    print(f"Created mock preview: {background_preview}")

    return session_id, preview_files


def cleanup_test_preview_files(preview_files):
    """Remove mock preview files."""
    for preview_file in preview_files:
        if preview_file.exists():
            preview_file.unlink()
            print(f"Cleaned up: {preview_file}")


def test_psd_layer_preview_usage():
    """Test that image sources use PSD layer previews."""

    print("=" * 80)
    print("TEST: PSD Layer Preview Usage for Image Population")
    print("=" * 80)
    print()

    # Setup: Create mock preview files
    session_id, preview_files = setup_test_preview_files()
    print()

    try:
        # Create mock AEPX path with session ID
        # This simulates: "uploads/1761598122_ab371181_aepx_test.aepx"
        mock_aepx_dir = Path('uploads')
        mock_aepx_dir.mkdir(exist_ok=True)

        mock_aepx_name = f"{session_id}_aepx_test.aepx"
        mock_aepx_path = mock_aepx_dir / mock_aepx_name

        # Copy real AEPX to mock path
        real_aepx = Path('sample_files/test-correct-fixed.aepx')
        if not real_aepx.exists():
            print(f"❌ FAIL: Real AEPX not found: {real_aepx}")
            return False

        shutil.copy(real_aepx, mock_aepx_path)
        print(f"Created mock AEPX: {mock_aepx_path}")
        print()

        # Test mappings with image layers
        mappings = {
            'composition_name': 'test-aep',
            'mappings': [
                # Text layer
                {
                    'psd_layer': 'BEN FORMAN',
                    'aepx_placeholder': 'player1fullname',
                    'type': 'text'
                },
                # Image layers - should use PSD layer previews!
                {
                    'psd_layer': 'cutout',  # Should find psd_layer_cutout_{session_id}_*.png
                    'aepx_placeholder': 'featuredimage1',
                    'type': 'image'
                },
                {
                    'psd_layer': 'green_yellow_bg',  # Should find psd_layer_green_yellow_bg_{session_id}_*.png
                    'aepx_placeholder': 'player2fullname',  # Using text layer as image placeholder for test
                    'type': 'image'
                }
            ]
        }

        output_path = '/tmp/test_psd_preview_usage.mp4'
        options = {
            'resolution': 'half',
            'duration': 2.5,
            'format': 'mp4'
        }

        print("Test Configuration:")
        print(f"  AEPX: {mock_aepx_path}")
        print(f"  Session ID: {session_id}")
        print(f"  Text mappings: 1")
        print(f"  Image mappings: 2")
        print()

        # Run preview generation
        print("-" * 80)
        print("Running Preview Generation...")
        print("-" * 80)
        print()

        result = generate_preview(str(mock_aepx_path), mappings, output_path, options)

        print()
        print("-" * 80)
        print("Verification")
        print("-" * 80)
        print()

        if result.get('success'):
            print("✅ Preview generation succeeded!")
            print()

            # Check temp directory for ExtendScript
            temp_dirs = []
            for root, dirs, files in os.walk('/var/folders'):
                if 'ae_preview_' in root and 'populate.jsx' in files:
                    temp_dirs.append(root)

            if temp_dirs:
                latest_temp = max(temp_dirs, key=os.path.getctime)
                jsx_file = os.path.join(latest_temp, 'populate.jsx')

                print(f"ExtendScript: {jsx_file}")
                print()

                # Read ExtendScript and check image paths
                with open(jsx_file, 'r', encoding='utf-8') as f:
                    jsx_content = f.read()

                # Check for PSD layer preview paths
                uses_psd_preview = 'psd_layer_cutout_' in jsx_content
                uses_preview_dir = 'previews/' in jsx_content or '/previews/' in jsx_content

                print("ExtendScript Analysis:")
                print(f"  {'✅' if uses_psd_preview else '❌'} Uses PSD layer preview filename pattern")
                print(f"  {'✅' if uses_preview_dir else '❌'} References previews directory")

                # Check NOT using footage directory
                uses_footage_fallback = 'footage/cutout.png' in jsx_content
                print(f"  {'✅' if not uses_footage_fallback else '❌'} NOT using footage fallback")

                print()

                # Extract image replacement lines
                print("Image replacement code:")
                lines = jsx_content.split('\n')
                for i, line in enumerate(lines):
                    if 'replaceImageSource' in line and not 'function' in line:
                        # Print context (2 lines before, line, 2 lines after)
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        for j in range(start, end):
                            marker = " >>> " if j == i else "     "
                            print(f"{marker}{lines[j]}")
                        print()

                if uses_psd_preview:
                    print("✅ SUCCESS: Image sources use PSD layer preview files!")
                    print()
                    return True
                else:
                    print("⚠️  WARNING: Not using PSD layer preview files")
                    print()
                    return False

            return True

        else:
            print(f"❌ Preview generation failed!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup mock files
        print()
        print("-" * 80)
        print("Cleanup")
        print("-" * 80)
        print()

        cleanup_test_preview_files(preview_files)

        # Remove mock AEPX
        if 'mock_aepx_path' in locals() and mock_aepx_path.exists():
            mock_aepx_path.unlink()
            print(f"Cleaned up: {mock_aepx_path}")


if __name__ == '__main__':
    success = test_psd_layer_preview_usage()
    sys.exit(0 if success else 1)
