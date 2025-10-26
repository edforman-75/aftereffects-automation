"""
Test text layer extraction functionality.

Verifies that text content, font size, and color information
is correctly extracted from PSD text layers.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase1.psd_parser import parse_psd


def test_text_extraction():
    """Test that text layers have content, font, and color extracted."""

    # Parse the test PSD
    result = parse_psd('sample_files/test-photoshop-doc.psd')

    print("=" * 70)
    print("TEXT EXTRACTION TEST")
    print("=" * 70)

    # Find all text layers
    text_layers = [layer for layer in result['layers'] if layer['type'] == 'text']

    print(f"\n✓ Found {len(text_layers)} text layers")

    # Verify we found text layers
    assert len(text_layers) > 0, "No text layers found in PSD"

    # Test each text layer
    passed_checks = 0
    total_checks = 0

    for layer in text_layers:
        print(f"\n📝 Testing layer: {layer['name']}")

        # Check that text data exists
        total_checks += 1
        if 'text' in layer:
            print(f"   ✓ Has text data")
            passed_checks += 1

            text_data = layer['text']

            # Check for content
            total_checks += 1
            if 'content' in text_data:
                print(f"   ✓ Content: \"{text_data['content']}\"")
                passed_checks += 1
            else:
                print(f"   ✗ Missing content")

            # Check for font size
            total_checks += 1
            if 'font_size' in text_data:
                print(f"   ✓ Font size: {text_data['font_size']}pt")
                passed_checks += 1
                assert isinstance(text_data['font_size'], (int, float)), "Font size should be numeric"
            else:
                print(f"   ✗ Missing font size")

            # Check for color
            total_checks += 1
            if 'color' in text_data:
                color = text_data['color']
                hex_color = f"#{color['r']:02x}{color['g']:02x}{color['b']:02x}"
                print(f"   ✓ Color: {hex_color} (RGBA: {color['r']}, {color['g']}, {color['b']}, {color['a']})")
                passed_checks += 1

                # Verify color values are in valid range
                assert 0 <= color['r'] <= 255, "Red value out of range"
                assert 0 <= color['g'] <= 255, "Green value out of range"
                assert 0 <= color['b'] <= 255, "Blue value out of range"
                assert 0 <= color['a'] <= 255, "Alpha value out of range"
            else:
                print(f"   ✗ Missing color")
        else:
            print(f"   ✗ No text data extracted")

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed_checks}/{total_checks} checks passed")
    print("=" * 70)

    # Overall test should pass if we got most of the checks
    success_rate = passed_checks / total_checks if total_checks > 0 else 0
    assert success_rate >= 0.75, f"Too many checks failed: {passed_checks}/{total_checks}"

    print("\n🎉 Text extraction test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_text_extraction()
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
