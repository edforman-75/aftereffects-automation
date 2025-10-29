#!/usr/bin/env python3
"""Test PNG conversion functionality."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image

# Import the function
from modules.phase5.preview_generator import make_ae_compatible_png

def test_png_conversion():
    """Test that PNG conversion works correctly."""
    
    print("=" * 80)
    print("TEST: PNG Conversion for After Effects Compatibility")
    print("=" * 80)
    print()
    
    # Create a temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create a valid test PNG
        test_png = os.path.join(temp_dir, 'test_input.png')
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_png, 'PNG')
        print(f"Created test PNG: {test_png}")
        print(f"  Size: {os.path.getsize(test_png)} bytes")
        print()
        
        # Convert it
        print("Converting PNG to AE-compatible format...")
        converted_path = make_ae_compatible_png(test_png, temp_dir)
        print()
        
        # Verify conversion
        if converted_path != test_png:
            print(f"✅ Conversion successful!")
            print(f"  Input: {os.path.basename(test_png)}")
            print(f"  Output: {os.path.basename(converted_path)}")
            print(f"  Input size: {os.path.getsize(test_png)} bytes")
            print(f"  Output size: {os.path.getsize(converted_path)} bytes")
            print()
            
            # Verify output is valid PNG
            converted_img = Image.open(converted_path)
            print(f"  Verified output PNG:")
            print(f"    Mode: {converted_img.mode}")
            print(f"    Size: {converted_img.size}")
            print()
            
            return True
        else:
            print("❌ Conversion returned same file (shouldn't happen)")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        print("Cleaned up temp directory")

if __name__ == '__main__':
    success = test_png_conversion()
    sys.exit(0 if success else 1)
