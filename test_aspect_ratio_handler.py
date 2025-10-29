"""
Test suite for Aspect Ratio Handler

Comprehensive tests for all decision paths and edge cases.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.aspect_ratio import (
    AspectRatioCategory,
    TransformationType,
    AspectRatioDecision,
    AspectRatioClassifier,
    AspectRatioHandler
)
import logging


def test_classifier():
    """Test aspect ratio classification"""
    print("\n" + "="*70)
    print("TEST 1: Aspect Ratio Classification")
    print("="*70)

    test_cases = [
        # (width, height, expected_category, description)
        (1080, 1920, AspectRatioCategory.PORTRAIT, "Instagram Story"),
        (1080, 1350, AspectRatioCategory.PORTRAIT, "Instagram Portrait Post"),
        (1080, 1080, AspectRatioCategory.SQUARE, "Instagram Square Post"),
        (1200, 1200, AspectRatioCategory.SQUARE, "Square"),
        (1920, 1080, AspectRatioCategory.LANDSCAPE, "HD Video"),
        (3840, 2160, AspectRatioCategory.LANDSCAPE, "4K Video"),
        (1920, 1920, AspectRatioCategory.SQUARE, "Large Square"),
        (1000, 1050, AspectRatioCategory.SQUARE, "Near Square (0.95 ratio)"),
    ]

    passed = 0
    for width, height, expected, desc in test_cases:
        result = AspectRatioClassifier.classify(width, height)
        ratio = width / height
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1

        print(f"{status} {desc:25} {width}×{height:5} (ratio={ratio:.2f}) → {result.value:10} (expected: {expected.value})")

    print(f"\nClassification Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_ratio_difference():
    """Test ratio difference calculation"""
    print("\n" + "="*70)
    print("TEST 2: Ratio Difference Calculation")
    print("="*70)

    test_cases = [
        # (psd_w, psd_h, aepx_w, aepx_h, expected_diff, description)
        (1920, 1080, 1920, 1080, 0.0, "Perfect match"),
        (1920, 1080, 3840, 2160, 0.0, "Same ratio, different scale"),
        (1920, 1080, 1280, 720, 0.0, "Same ratio (16:9)"),
        (1920, 1080, 1920, 1200, 0.1, "Small difference (~10%)"),
        (1920, 1080, 1080, 1920, 0.688, "Portrait vs Landscape"),
        (1080, 1080, 1920, 1080, 0.438, "Square vs Landscape"),
    ]

    passed = 0
    for psd_w, psd_h, aepx_w, aepx_h, expected, desc in test_cases:
        result = AspectRatioClassifier.get_ratio_difference(
            psd_w, psd_h, aepx_w, aepx_h
        )
        # Allow 1% tolerance in comparison
        match = abs(result - expected) < 0.01
        status = "✓" if match else "✗"
        if match:
            passed += 1

        print(f"{status} {desc:30} {psd_w}×{psd_h} → {aepx_w}×{aepx_h}: "
              f"diff={result:.3f} (expected: {expected:.3f})")

    print(f"\nRatio Difference Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_analyze_mismatch():
    """Test mismatch analysis and decision making"""
    print("\n" + "="*70)
    print("TEST 3: Mismatch Analysis & Decision Making")
    print("="*70)

    # Setup handler
    logger = logging.getLogger('test')
    logger.setLevel(logging.WARNING)  # Quiet for tests
    handler = AspectRatioHandler(logger)

    test_cases = [
        # (psd_w, psd_h, aepx_w, aepx_h, expected_type, expected_auto, description)
        (1920, 1080, 1920, 1080, TransformationType.NONE, True, "Perfect match"),
        (1920, 1080, 3840, 2160, TransformationType.NONE, True, "Same ratio"),
        (1920, 1080, 1920, 1161, TransformationType.MINOR_SCALE, True, "Minor difference (7%)"),
        (1920, 1080, 1920, 1280, TransformationType.MODERATE_ADJUST, False, "Moderate (14%)"),
        (1920, 1080, 1920, 1400, TransformationType.HUMAN_REVIEW, False, "Large diff (23%)"),
        (1920, 1080, 1080, 1920, TransformationType.HUMAN_REVIEW, False, "Cross-category"),
        (1080, 1080, 1920, 1080, TransformationType.HUMAN_REVIEW, False, "Square to Landscape"),
    ]

    passed = 0
    for psd_w, psd_h, aepx_w, aepx_h, expected_type, expected_auto, desc in test_cases:
        decision = handler.analyze_mismatch(psd_w, psd_h, aepx_w, aepx_h)

        type_match = decision.transformation_type == expected_type
        auto_match = decision.can_auto_apply == expected_auto

        if type_match and auto_match:
            passed += 1
            status = "✓"
        else:
            status = "✗"

        print(f"\n{status} {desc}")
        print(f"   {psd_w}×{psd_h} ({decision.psd_category.value}) → "
              f"{aepx_w}×{aepx_h} ({decision.aepx_category.value})")
        print(f"   Difference: {decision.ratio_difference:.1%}")
        print(f"   Type: {decision.transformation_type.value} "
              f"(expected: {expected_type.value}) {'' if type_match else '✗'}")
        print(f"   Auto-apply: {decision.can_auto_apply} "
              f"(expected: {expected_auto}) {'' if auto_match else '✗'}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Action: {decision.recommended_action}")

    print(f"\nAnalysis Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_transform_calculations():
    """Test transformation calculations (fit and fill)"""
    print("\n" + "="*70)
    print("TEST 4: Transformation Calculations")
    print("="*70)

    logger = logging.getLogger('test')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    test_cases = [
        # (psd_w, psd_h, aepx_w, aepx_h, method, description)
        (1920, 1080, 3840, 2160, "fit", "2x scale up (same ratio)"),
        (1920, 1080, 1280, 720, "fit", "Scale down (same ratio)"),
        (1920, 1080, 1920, 1920, "fit", "Landscape to Square (letterbox)"),
        (1080, 1920, 1920, 1920, "fit", "Portrait to Square (pillarbox)"),
        (1920, 1080, 3840, 2160, "fill", "2x scale up (fill)"),
        (1920, 1080, 1920, 1920, "fill", "Landscape to Square (crop)"),
    ]

    passed = 0
    for psd_w, psd_h, aepx_w, aepx_h, method, desc in test_cases:
        transform = handler.calculate_transform(psd_w, psd_h, aepx_w, aepx_h, method)

        # Basic validation
        valid = (
            transform['scale'] > 0 and
            transform['method'] == method and
            transform['new_width'] > 0 and
            transform['new_height'] > 0
        )

        if valid:
            passed += 1
            status = "✓"
        else:
            status = "✗"

        print(f"\n{status} {desc}")
        print(f"   {psd_w}×{psd_h} → {aepx_w}×{aepx_h} ({method})")
        print(f"   Scale: {transform['scale']:.3f}")
        print(f"   New dimensions: {transform['new_width']:.0f}×{transform['new_height']:.0f}")
        print(f"   Offset: ({transform['offset_x']:.1f}, {transform['offset_y']:.1f})")
        if transform['bars']:
            print(f"   Bars: {transform['bars']}")

    print(f"\nTransform Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_learning_system():
    """Test learning system and statistics"""
    print("\n" + "="*70)
    print("TEST 5: Learning System")
    print("="*70)

    logger = logging.getLogger('test')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    # Record some decisions
    decisions = [
        ((1920, 1080), (1920, 1080), "none", "proceed"),
        ((1920, 1080), (1920, 1100), "minor_scale", "proceed"),
        ((1920, 1080), (1920, 1200), "moderate", "skip"),
        ((1920, 1080), (1080, 1920), "human_review", "manual_fix"),
        ((1920, 1080), (1920, 1080), "none", "proceed"),
    ]

    print("Recording decisions...")
    for psd_dims, aepx_dims, ai_rec, human_choice in decisions:
        handler.record_human_decision(psd_dims, aepx_dims, ai_rec, human_choice)
        print(f"  {psd_dims} → {aepx_dims}: AI={ai_rec}, Human={human_choice}")

    # Get statistics
    stats = handler.get_learning_stats()

    print(f"\nLearning Statistics:")
    print(f"  Total decisions: {stats['total_decisions']}")
    print(f"  Auto-apply accuracy: {stats['auto_apply_accuracy']:.1%}")
    print(f"  Overall agreement rate: {stats['agreement_rate']:.1%}")

    if stats['by_category']:
        print(f"\n  By category:")
        for category, data in stats['by_category'].items():
            print(f"    {category}: {data['agreed']}/{data['total']} agreed ({data['accuracy']:.1%})")

    # Test export
    export_path = "/tmp/aspect_ratio_learning.json"
    handler.export_learning_data(export_path)
    print(f"\n✓ Exported learning data to {export_path}")

    # Verify export
    import json
    with open(export_path, 'r') as f:
        exported = json.load(f)
        print(f"  Exported {exported['total_records']} records")

    passed = stats['total_decisions'] == len(decisions)
    print(f"\nLearning Tests: {'PASSED' if passed else 'FAILED'}")
    return passed


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "="*70)
    print("TEST 6: Edge Cases")
    print("="*70)

    logger = logging.getLogger('test')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    passed = 0
    total = 0

    # Test 1: Zero height (should raise error)
    total += 1
    try:
        AspectRatioClassifier.classify(1920, 0)
        print("✗ Should raise ValueError for zero height")
    except ValueError:
        print("✓ Correctly raises ValueError for zero height")
        passed += 1

    # Test 2: Very small dimensions
    total += 1
    try:
        decision = handler.analyze_mismatch(10, 10, 20, 20)
        if decision.transformation_type == TransformationType.NONE:
            print("✓ Handles very small dimensions")
            passed += 1
        else:
            print("✗ Incorrect handling of small dimensions")
    except Exception as e:
        print(f"✗ Error with small dimensions: {e}")

    # Test 3: Very large dimensions
    total += 1
    try:
        decision = handler.analyze_mismatch(7680, 4320, 15360, 8640)
        if decision.transformation_type == TransformationType.NONE:
            print("✓ Handles very large dimensions (8K)")
            passed += 1
        else:
            print("✗ Incorrect handling of large dimensions")
    except Exception as e:
        print(f"✗ Error with large dimensions: {e}")

    # Test 4: Invalid transform method
    total += 1
    try:
        handler.calculate_transform(1920, 1080, 1920, 1080, method="invalid")
        print("✗ Should raise ValueError for invalid method")
    except ValueError:
        print("✓ Correctly raises ValueError for invalid method")
        passed += 1

    # Test 5: Extreme aspect ratios
    total += 1
    try:
        decision = handler.analyze_mismatch(100, 1000, 1000, 100)  # 10:1 vs 1:10
        if decision.transformation_type == TransformationType.HUMAN_REVIEW:
            print("✓ Flags extreme aspect ratio differences for review")
            passed += 1
        else:
            print("✗ Should flag extreme ratios for review")
    except Exception as e:
        print(f"✗ Error with extreme ratios: {e}")

    print(f"\nEdge Case Tests: {passed}/{total} passed")
    return passed == total


def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*70)
    print("ASPECT RATIO HANDLER - COMPREHENSIVE TEST SUITE")
    print("="*70)

    results = {
        "Classification": test_classifier(),
        "Ratio Difference": test_ratio_difference(),
        "Mismatch Analysis": test_analyze_mismatch(),
        "Transform Calculations": test_transform_calculations(),
        "Learning System": test_learning_system(),
        "Edge Cases": test_edge_cases(),
    }

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status:12} {test_name}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print("="*70)
    print(f"OVERALL: {total_passed}/{total_tests} test suites passed")
    print("="*70)

    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
