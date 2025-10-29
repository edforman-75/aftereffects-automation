#!/usr/bin/env python3
"""
Aspect Ratio Handler Demo

Demonstrates real-world usage of the conservative aspect ratio handling system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.aspect_ratio import AspectRatioHandler, TransformationType
import logging


def print_decision(decision, psd_dims, aepx_dims):
    """Pretty print a decision"""
    print(f"\n{'='*70}")
    print(f"Analyzing: {psd_dims[0]}×{psd_dims[1]} → {aepx_dims[0]}×{aepx_dims[1]}")
    print(f"{'='*70}")
    print(f"PSD Category:  {decision.psd_category.value}")
    print(f"AEPX Category: {decision.aepx_category.value}")
    print(f"Difference:    {decision.ratio_difference:.1%}")
    print(f"Type:          {decision.transformation_type.value}")
    print(f"Auto-apply:    {'✅ Yes' if decision.can_auto_apply else '❌ No'}")
    print(f"Confidence:    {decision.confidence:.1%}")
    print(f"\n📋 Recommendation:")
    print(f"   {decision.recommended_action}")
    print(f"\n💡 Reasoning:")
    print(f"   {decision.reasoning}")


def demo_perfect_match():
    """Demo: Perfect aspect ratio match"""
    print("\n" + "█"*70)
    print("DEMO 1: Perfect Match (HD to 4K)")
    print("█"*70)

    logger = logging.getLogger('demo')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    decision = handler.analyze_mismatch(1920, 1080, 3840, 2160)
    print_decision(decision, (1920, 1080), (3840, 2160))

    if handler.can_auto_transform(decision):
        transform = handler.calculate_transform(1920, 1080, 3840, 2160, method="fit")
        print(f"\n✅ AUTO-APPLY TRANSFORMATION:")
        print(f"   Scale: {transform['scale']:.3f}x")
        print(f"   New size: {transform['new_width']:.0f}×{transform['new_height']:.0f}")
        print(f"   Bars: {transform['bars'] or 'None'}")


def demo_minor_adjustment():
    """Demo: Minor aspect ratio difference"""
    print("\n" + "█"*70)
    print("DEMO 2: Minor Adjustment (7% difference)")
    print("█"*70)

    logger = logging.getLogger('demo')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    decision = handler.analyze_mismatch(1920, 1080, 1920, 1161)
    print_decision(decision, (1920, 1080), (1920, 1161))

    if handler.can_auto_transform(decision):
        transform = handler.calculate_transform(1920, 1080, 1920, 1161, method="fit")
        print(f"\n✅ AUTO-APPLY TRANSFORMATION:")
        print(f"   Scale: {transform['scale']:.3f}x")
        print(f"   New size: {transform['new_width']:.0f}×{transform['new_height']:.0f}")
        print(f"   Offset: ({transform['offset_x']:.1f}, {transform['offset_y']:.1f})")
        print(f"   Bars: {transform['bars'] or 'None'}")


def demo_moderate_difference():
    """Demo: Moderate difference requiring approval"""
    print("\n" + "█"*70)
    print("DEMO 3: Moderate Adjustment (15% difference - Needs Approval)")
    print("█"*70)

    logger = logging.getLogger('demo')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    decision = handler.analyze_mismatch(1920, 1080, 1920, 1280)
    print_decision(decision, (1920, 1080), (1920, 1280))

    if not handler.can_auto_transform(decision):
        print(f"\n⚠️  HUMAN APPROVAL REQUIRED")
        print(f"   This would show a preview dialog to the user")

        # Show what the transform would look like
        transform_fit = handler.calculate_transform(1920, 1080, 1920, 1280, method="fit")
        transform_fill = handler.calculate_transform(1920, 1080, 1920, 1280, method="fill")

        print(f"\n   Option 1 - Fit (letterbox):")
        print(f"      Scale: {transform_fit['scale']:.3f}x")
        print(f"      Bars: {transform_fit['bars']}")

        print(f"\n   Option 2 - Fill (crop):")
        print(f"      Scale: {transform_fill['scale']:.3f}x")
        print(f"      Crop: {abs(transform_fill['offset_y']):.0f}px on edges")

        # Simulate user approval
        print(f"\n   [User approves 'fit' method]")

        handler.record_human_decision(
            (1920, 1080), (1920, 1280),
            decision.transformation_type.value,
            "proceed"
        )
        print(f"   ✓ Decision recorded for learning")


def demo_cross_category():
    """Demo: Cross-category transformation"""
    print("\n" + "█"*70)
    print("DEMO 4: Cross-Category (Landscape to Portrait - BLOCKED)")
    print("█"*70)

    logger = logging.getLogger('demo')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    decision = handler.analyze_mismatch(1920, 1080, 1080, 1920)
    print_decision(decision, (1920, 1080), (1080, 1920))

    if not handler.can_auto_transform(decision):
        print(f"\n🛑 AUTOMATIC TRANSFORMATION BLOCKED")
        print(f"   Cross-category transformations require manual handling")
        print(f"   User options:")
        print(f"   1. Skip this graphic")
        print(f"   2. Choose different AEPX template")
        print(f"   3. Manually recreate in After Effects")

        # Simulate user skipping
        print(f"\n   [User chooses to skip]")

        handler.record_human_decision(
            (1920, 1080), (1080, 1920),
            decision.transformation_type.value,
            "skip"
        )
        print(f"   ✓ Decision recorded for learning")


def demo_landscape_to_square():
    """Demo: Landscape to square transformation"""
    print("\n" + "█"*70)
    print("DEMO 5: Landscape to Square (44% difference)")
    print("█"*70)

    logger = logging.getLogger('demo')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    decision = handler.analyze_mismatch(1920, 1080, 1080, 1080)
    print_decision(decision, (1920, 1080), (1080, 1080))

    if not handler.can_auto_transform(decision):
        print(f"\n⚠️  MANUAL REVIEW REQUIRED")

        # Show transform options
        transform_fit = handler.calculate_transform(1920, 1080, 1080, 1080, method="fit")
        transform_fill = handler.calculate_transform(1920, 1080, 1080, 1080, method="fill")

        print(f"\n   Option 1 - Fit (pillarbox):")
        print(f"      Scale: {transform_fit['scale']:.3f}x")
        print(f"      New size: {transform_fit['new_width']:.0f}×{transform_fit['new_height']:.0f}")
        print(f"      Bars: {transform_fit['bars']} ({abs(transform_fit['offset_x']):.0f}px each side)")

        print(f"\n   Option 2 - Fill (crop sides):")
        print(f"      Scale: {transform_fill['scale']:.3f}x")
        print(f"      New size: {transform_fill['new_width']:.0f}×{transform_fill['new_height']:.0f}")
        print(f"      Crop: {abs(transform_fill['offset_x']):.0f}px on each side")

        print(f"\n   ⚠️ WARNING: Both options result in significant content loss")
        print(f"   Recommendation: Use square-optimized template instead")


def demo_learning_system():
    """Demo: Learning system and statistics"""
    print("\n" + "█"*70)
    print("DEMO 6: Learning System Statistics")
    print("█"*70)

    logger = logging.getLogger('demo')
    logger.setLevel(logging.WARNING)
    handler = AspectRatioHandler(logger)

    # Simulate a series of decisions
    decisions_data = [
        ((1920, 1080), (1920, 1080), "none", "proceed"),
        ((1920, 1080), (3840, 2160), "none", "proceed"),
        ((1920, 1080), (1920, 1161), "minor_scale", "proceed"),
        ((1920, 1080), (1920, 1280), "moderate", "proceed"),
        ((1920, 1080), (1920, 1280), "moderate", "skip"),
        ((1920, 1080), (1920, 1400), "human_review", "manual_fix"),
        ((1920, 1080), (1080, 1920), "human_review", "skip"),
        ((1080, 1080), (1920, 1080), "human_review", "skip"),
    ]

    print(f"\nRecording {len(decisions_data)} human decisions...")

    for psd, aepx, ai_rec, human in decisions_data:
        handler.record_human_decision(psd, aepx, ai_rec, human)
        agreed = "✓" if human == "proceed" else "✗"
        print(f"   {agreed} {psd} → {aepx}: AI={ai_rec:15} Human={human}")

    # Get statistics
    stats = handler.get_learning_stats()

    print(f"\n{'='*70}")
    print("LEARNING STATISTICS")
    print(f"{'='*70}")
    print(f"Total Decisions:       {stats['total_decisions']}")
    print(f"Auto-apply Accuracy:   {stats['auto_apply_accuracy']:.1%}")
    print(f"Overall Agreement:     {stats['agreement_rate']:.1%}")

    print(f"\nBy Category:")
    for category, data in stats['by_category'].items():
        print(f"   {category:10} {data['agreed']:2}/{data['total']:2} agreed ({data['accuracy']:.1%})")

    if stats['common_overrides']:
        print(f"\nCommon Overrides (AI vs Human):")
        for override in stats['common_overrides'][:3]:
            print(f"   {override['psd_category']} → {override['aepx_category']}")
            print(f"   Diff: {override['ratio_difference']:.1%}, "
                  f"AI: {override['ai_recommendation']}, "
                  f"Human: {override['human_choice']}")

    # Export data
    export_path = "/tmp/aspect_ratio_demo_learning.json"
    handler.export_learning_data(export_path)
    print(f"\n✓ Exported learning data to {export_path}")


def main():
    """Run all demos"""
    print("\n" + "▓"*70)
    print("▓" + " "*68 + "▓")
    print("▓" + "  ASPECT RATIO HANDLER - INTERACTIVE DEMO".center(68) + "▓")
    print("▓" + " "*68 + "▓")
    print("▓"*70)

    demos = [
        demo_perfect_match,
        demo_minor_adjustment,
        demo_moderate_difference,
        demo_cross_category,
        demo_landscape_to_square,
        demo_learning_system
    ]

    for demo in demos:
        demo()

    print("\n" + "▓"*70)
    print("▓" + " "*68 + "▓")
    print("▓" + "  DEMO COMPLETE".center(68) + "▓")
    print("▓" + " "*68 + "▓")
    print("▓"*70)

    print("\n📚 For more information, see modules/aspect_ratio/README.md")
    print("🧪 Run tests with: python3 test_aspect_ratio_handler.py\n")


if __name__ == "__main__":
    main()
