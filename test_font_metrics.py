#!/usr/bin/env python3
"""
Test script for font metrics calculation.

Tests:
1. Font finding functionality
2. Text width calculation
3. Fallback estimation
4. Integration with conflict detector
"""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.phase1.font_metrics import (
    calculate_text_width,
    find_system_font,
    estimate_width_without_font,
    get_font_info
)

def test_font_finding():
    """Test font finding in system directories."""
    print("=" * 70)
    print("TEST 1: Font Finding")
    print("=" * 70)

    # Test common fonts
    test_fonts = ['Arial', 'Helvetica', 'Times New Roman', 'RUSH FLOW']

    for font_name in test_fonts:
        font_path = find_system_font(font_name)
        if font_path:
            print(f"✅ Found '{font_name}': {font_path}")

            # Get font info
            info = get_font_info(font_path)
            if info:
                print(f"   Family: {info.get('family', 'N/A')}")
                print(f"   Style: {info.get('style', 'N/A')}")
                print(f"   Units per EM: {info.get('units_per_em', 'N/A')}")
                print(f"   Has Kerning: {info.get('has_kerning', 'N/A')}")
        else:
            print(f"❌ Not found: '{font_name}'")
        print()


def test_text_width_calculation():
    """Test text width calculation with different scenarios."""
    print("=" * 70)
    print("TEST 2: Text Width Calculation")
    print("=" * 70)

    # Test cases
    test_cases = [
        ("BEN FORMAN", "RUSH FLOW", 48),
        ("HELLO WORLD", "Arial", 48),
        ("Short", "Arial", 24),
        ("This is a very long text that should definitely overflow", "Arial", 48),
    ]

    placeholder_width = 400.0  # Default placeholder width

    for text, font_name, font_size in test_cases:
        print(f"\nText: '{text}'")
        print(f"Font: {font_name} at {font_size}pt")

        # Calculate width
        width = calculate_text_width(text, font_name, font_size)

        # Compare to placeholder
        overflow = width - placeholder_width
        overflow_percent = (overflow / placeholder_width) * 100

        print(f"Calculated Width: {width:.1f}px")
        print(f"Placeholder Width: {placeholder_width:.0f}px")

        if overflow > 0:
            if overflow_percent > 20:
                print(f"🔴 CRITICAL OVERFLOW: +{overflow:.1f}px ({overflow_percent:.1f}%)")
            elif overflow_percent > 5:
                print(f"⚠️  WARNING: +{overflow:.1f}px ({overflow_percent:.1f}%)")
            else:
                print(f"✅ Fits with minor overflow: +{overflow:.1f}px ({overflow_percent:.1f}%)")
        else:
            print(f"✅ Fits comfortably: {abs(overflow):.1f}px remaining")


def test_fallback_estimation():
    """Test fallback estimation when font is unavailable."""
    print("\n" + "=" * 70)
    print("TEST 3: Fallback Estimation")
    print("=" * 70)

    text = "SAMPLE TEXT"
    font_size = 48

    # Calculate with estimation
    estimated_width = estimate_width_without_font(text, font_size)

    print(f"\nText: '{text}'")
    print(f"Font Size: {font_size}pt")
    print(f"Estimated Width: {estimated_width:.1f}px")
    print(f"Formula: len({len(text)}) * {font_size} * 0.6 = {estimated_width:.1f}px")

    # Compare with actual if Arial available
    actual_width = calculate_text_width(text, "Arial", font_size)
    print(f"Actual Width (Arial): {actual_width:.1f}px")

    diff = abs(actual_width - estimated_width)
    accuracy = (1 - (diff / actual_width)) * 100
    print(f"Estimation Accuracy: {accuracy:.1f}%")


def test_conflict_detection_integration():
    """Test integration with conflict detector."""
    print("\n" + "=" * 70)
    print("TEST 4: Conflict Detection Integration")
    print("=" * 70)

    # Create mock PSD data
    psd_data = {
        'filename': 'test.psd',
        'width': 1920,
        'height': 1080,
        'layers': [
            {
                'name': 'player1fullname',
                'type': 'text',
                'text': {
                    'content': 'BEN FORMAN',
                    'font_name': 'RUSH FLOW',
                    'font_size': 48.0
                }
            },
            {
                'name': 'short_text',
                'type': 'text',
                'text': {
                    'content': 'OK',
                    'font_name': 'Arial',
                    'font_size': 48.0
                }
            }
        ]
    }

    # Create mock AEPX data
    aepx_data = {
        'filename': 'test.aepx',
        'composition_name': 'Main Comp',
        'compositions': [
            {
                'name': 'Main Comp',
                'width': 1920,
                'height': 1080
            }
        ],
        'placeholders': [
            {
                'name': 'player1fullname',
                'type': 'text'
            },
            {
                'name': 'short_text',
                'type': 'text'
            }
        ]
    }

    # Create mock mappings
    mappings = {
        'mappings': [
            {
                'psd_layer': 'player1fullname',
                'aepx_placeholder': 'player1fullname',
                'type': 'text',
                'confidence': 1.0
            },
            {
                'psd_layer': 'short_text',
                'aepx_placeholder': 'short_text',
                'type': 'text',
                'confidence': 1.0
            }
        ],
        'unmapped_psd_layers': [],
        'unfilled_placeholders': []
    }

    # Import conflict detector
    from modules.phase3.conflict_detector import detect_conflicts

    print("\nRunning conflict detection with font metrics...")
    conflicts = detect_conflicts(psd_data, aepx_data, mappings)

    print(f"\nConflict Summary:")
    print(f"  Total: {conflicts['summary']['total']}")
    print(f"  Critical: {conflicts['summary']['critical']}")
    print(f"  Warning: {conflicts['summary']['warning']}")
    print(f"  Info: {conflicts['summary']['info']}")

    print("\nDetailed Conflicts:")
    for conflict in conflicts['conflicts']:
        severity_icon = {
            'critical': '🔴',
            'warning': '⚠️',
            'info': 'ℹ️'
        }.get(conflict['severity'], '•')

        print(f"\n{severity_icon} {conflict['type']} ({conflict['severity'].upper()})")
        print(f"   Issue: {conflict['issue']}")
        if 'suggestion' in conflict:
            print(f"   Suggestion: {conflict['suggestion']}")
        if 'details' in conflict:
            details = conflict['details']
            if 'text_width' in details:
                print(f"   Details:")
                print(f"     - Text Width: {details['text_width']}px")
                print(f"     - Placeholder Width: {details['placeholder_width']}px")
                print(f"     - Overflow: {details['overflow_pixels']}px ({details['overflow_percent']}%)")
                print(f"     - Font: {details['font_name']} at {details['font_size']}pt")
                print(f"     - Font Found: {details['font_found']}")


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "FONT METRICS CALCULATION TEST" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        # Run all tests
        test_font_finding()
        test_text_width_calculation()
        test_fallback_estimation()
        test_conflict_detection_integration()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 70)
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
