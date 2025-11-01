#!/usr/bin/env python3
"""
Test script for headless thumbnail generation
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.thumbnail_service import ThumbnailService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_headless_thumbnails():
    """Test headless thumbnail generation"""

    print("=" * 70)
    print("TESTING HEADLESS THUMBNAIL GENERATION")
    print("=" * 70)

    # Use the most recent PSD file
    psd_path = "/Users/edf/aftereffects-automation/uploads/1761806737_deca9643_psd_test-photoshop-doc.psd"
    output_folder = "/Users/edf/aftereffects-automation/uploads"
    session_id = "test_headless"

    print(f"\nPSD File: {psd_path}")
    print(f"Output Folder: {output_folder}")
    print(f"Session ID: {session_id}")
    print("\n⚠️  WATCH FOR PHOTOSHOP WINDOWS - They should NOT appear!")
    print("\nStarting thumbnail generation in 3 seconds...")

    import time
    time.sleep(3)

    # Initialize service
    service = ThumbnailService(logger)

    print("\n🎬 Generating thumbnails...")
    result = service.generate_layer_thumbnails(psd_path, output_folder, session_id)

    if result.success:
        print("\n✅ SUCCESS!")
        thumbnails = result.get_data()
        print(f"\n📊 Generated {len(thumbnails)} thumbnails:")
        for layer_name, thumb_file in thumbnails.items():
            print(f"   - {layer_name}: {thumb_file}")

        # Check if thumbnails exist
        thumb_folder = f"{output_folder}/thumbnails/{session_id}"
        print(f"\n📁 Checking thumbnail folder: {thumb_folder}")

        import os
        if os.path.exists(thumb_folder):
            files = os.listdir(thumb_folder)
            print(f"   Found {len(files)} files:")
            for f in files:
                file_path = os.path.join(thumb_folder, f)
                size = os.path.getsize(file_path)
                print(f"   - {f} ({size:,} bytes)")

        print("\n" + "=" * 70)
        print("DID PHOTOSHOP WINDOWS APPEAR?")
        print("=" * 70)
        print("\nIf NO windows appeared, headless mode is working! ✅")
        print("If windows appeared, there's still an issue. ❌")

    else:
        print(f"\n❌ FAILED: {result.message}")
        return False

    return True

if __name__ == "__main__":
    success = test_headless_thumbnails()
    sys.exit(0 if success else 1)
