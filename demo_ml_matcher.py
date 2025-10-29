#!/usr/bin/env python3
"""
ML-Enhanced Matcher Demonstration

Shows the difference between rule-based and ML-enhanced content matching.
"""

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.ml_content_matcher import match_content_to_slots_ml, _ML_AVAILABLE


def main():
    print("=" * 70)
    print("ML-ENHANCED CONTENT MATCHER DEMONSTRATION")
    print("=" * 70)

    # Check ML availability
    if _ML_AVAILABLE:
        print("\n✅ Machine Learning: ACTIVE")
        print("   Using sentence-transformers with 'all-MiniLM-L6-v2' model")
    else:
        print("\n⚠️  Machine Learning: NOT AVAILABLE")
        print("   Using rule-based matching only")

    # Load sample files
    print("\n📄 Loading sample files...")
    psd = parse_psd('sample_files/test-photoshop-doc.psd')
    aepx = parse_aepx('sample_files/test-after-effects-project.aepx')

    print(f"   Source: {psd['filename']} ({psd['width']}×{psd['height']})")
    print(f"   Template: {aepx['filename']}")
    print(f"   Composition: {aepx['composition_name']}")

    # Run rule-based matcher
    print("\n" + "=" * 70)
    print("METHOD 1: RULE-BASED MATCHER")
    print("=" * 70)
    print("\nAlgorithm:")
    print("  • Text: Sequential matching (top to bottom)")
    print("  • Images: Keyword + name similarity + size heuristics")

    rule_result = match_content_to_slots(psd, aepx)

    print(f"\n✓ Created {len(rule_result['mappings'])} mappings:\n")
    for i, m in enumerate(rule_result['mappings'], 1):
        confidence_bar = "█" * int(m['confidence'] * 20)
        print(f"  {i}. {m['psd_layer']:20s} → {m['aepx_placeholder']:20s}")
        print(f"     Confidence: {confidence_bar} {m['confidence']:.0%}")
        print(f"     Type: {m['type']}")
        print()

    # Run ML-enhanced matcher
    print("=" * 70)
    print("METHOD 2: ML-ENHANCED MATCHER")
    print("=" * 70)

    if _ML_AVAILABLE:
        print("\nAlgorithm:")
        print("  • Text: Sequential + semantic validation")
        print("  • Images: Semantic embeddings + keyword boost + size heuristics")
        print("  • Scoring: (Semantic 40%) + (Keywords 40%) + (Size 20%)")

        ml_result = match_content_to_slots_ml(psd, aepx, use_ml=True)

        print(f"\n✓ Created {len(ml_result['mappings'])} mappings:\n")
        for i, m in enumerate(ml_result['mappings'], 1):
            confidence_bar = "█" * int(m['confidence'] * 20)
            print(f"  {i}. {m['psd_layer']:20s} → {m['aepx_placeholder']:20s}")
            print(f"     Confidence: {confidence_bar} {m['confidence']:.0%}")
            print(f"     Type: {m['type']}")
            print()

        # Show comparison
        print("=" * 70)
        print("COMPARISON")
        print("=" * 70)

        print("\nConfidence Levels:")
        print(f"{'Layer':<20s} {'Placeholder':<20s} {'Rule-Based':<12s} {'ML-Enhanced':<12s}")
        print("-" * 70)

        for rule_m in rule_result['mappings']:
            # Find corresponding ML mapping
            ml_m = next((m for m in ml_result['mappings']
                        if m['psd_layer'] == rule_m['psd_layer']), None)

            if ml_m:
                rule_conf = f"{rule_m['confidence']:.0%}"
                ml_conf = f"{ml_m['confidence']:.0%}"

                # Highlight differences
                diff_marker = ""
                if abs(rule_m['confidence'] - ml_m['confidence']) > 0.05:
                    diff_marker = " ⚡"

                print(f"{rule_m['psd_layer']:<20s} {rule_m['aepx_placeholder']:<20s} "
                      f"{rule_conf:<12s} {ml_conf:<12s}{diff_marker}")

        print("\n💡 Key Insights:")
        print("   • ML matcher uses semantic understanding of layer/placeholder names")
        print("   • Content keywords (cutout, photo, portrait) are boosted")
        print("   • Decorative keywords (background, texture) are de-prioritized")
        print("   • Text matching confidence slightly adjusted based on semantic similarity")

    else:
        print("\n⚠️  ML matching not available")
        print("   Install: pip install sentence-transformers")
        print("   Falls back to rule-based matcher automatically")

    # Show unmapped/unfilled
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\nPSD Layers: {len(psd['layers'])} total")
    print(f"  • Mapped: {len(rule_result['mappings'])}")
    print(f"  • Unmapped: {len(rule_result['unmapped_psd_layers'])}")
    if rule_result['unmapped_psd_layers']:
        for layer in rule_result['unmapped_psd_layers']:
            print(f"    - {layer}")

    print(f"\nAEPX Placeholders: {len(aepx['placeholders'])} total")
    print(f"  • Filled: {len(rule_result['mappings'])}")
    print(f"  • Unfilled: {len(rule_result['unfilled_placeholders'])}")
    if rule_result['unfilled_placeholders']:
        for placeholder in rule_result['unfilled_placeholders']:
            print(f"    - {placeholder}")

    print()


if __name__ == "__main__":
    main()
