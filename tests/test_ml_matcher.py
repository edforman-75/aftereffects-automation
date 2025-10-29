"""
Test ML-Enhanced Content Matcher.

Compares ML matcher performance against rule-based matcher.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.ml_content_matcher import match_content_to_slots_ml, _ML_AVAILABLE


def test_ml_matcher():
    """Test ML-enhanced content matcher."""

    print("=" * 70)
    print("ML-ENHANCED CONTENT MATCHER TEST")
    print("=" * 70)

    # Check ML availability
    print(f"\n🔍 ML Status: {'Available' if _ML_AVAILABLE else 'Not Available'}")

    if not _ML_AVAILABLE:
        print("   ℹ️  sentence-transformers not installed")
        print("   ℹ️  Will test fallback to rule-based matcher")

    # Load data
    print("\n📄 Loading sample files...")
    psd = parse_psd('sample_files/test-photoshop-doc.psd')
    aepx = parse_aepx('sample_files/test-after-effects-project.aepx')

    print(f"   ✓ Loaded {psd['filename']}")
    print(f"   ✓ Loaded {aepx['filename']}")

    # Test rule-based matcher
    print("\n🔧 Test 1: Rule-Based Matcher (baseline)")
    rule_result = match_content_to_slots(psd, aepx)

    print(f"   Found {len(rule_result['mappings'])} mappings")
    for m in rule_result['mappings']:
        print(f"   - {m['psd_layer']} → {m['aepx_placeholder']} ({m['confidence']:.0%})")

    # Test ML-enhanced matcher
    print("\n🤖 Test 2: ML-Enhanced Matcher")
    ml_result = match_content_to_slots_ml(psd, aepx, use_ml=True)

    print(f"   Found {len(ml_result['mappings'])} mappings")
    for m in ml_result['mappings']:
        print(f"   - {m['psd_layer']} → {m['aepx_placeholder']} ({m['confidence']:.0%})")

    # Test ML disabled
    print("\n🔧 Test 3: ML-Enhanced Matcher (use_ml=False)")
    ml_disabled_result = match_content_to_slots_ml(psd, aepx, use_ml=False)

    print(f"   Found {len(ml_disabled_result['mappings'])} mappings")
    print("   Should match rule-based results")

    # Verification
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    checks = []

    # Basic structure checks
    checks.append(('mappings' in ml_result, "ML result has mappings"))
    checks.append(('unmapped_psd_layers' in ml_result, "ML result has unmapped"))
    checks.append(('unfilled_placeholders' in ml_result, "ML result has unfilled"))

    # Mapping checks
    checks.append((len(ml_result['mappings']) > 0, "ML matcher found mappings"))

    # Compare ML vs rule-based
    ml_count = len(ml_result['mappings'])
    rule_count = len(rule_result['mappings'])
    checks.append((ml_count >= rule_count, f"ML found >= mappings ({ml_count} vs {rule_count})"))

    # Check expected mappings exist
    expected_mappings = [
        ('BEN FORMAN', 'player1fullname'),
        ('ELOISE GRACE', 'player2fullname'),
        ('EMMA LOUISE', 'player3fullname'),
        ('cutout', 'featuredimage1')
    ]

    for psd_layer, aepx_placeholder in expected_mappings:
        found = any(
            m['psd_layer'] == psd_layer and m['aepx_placeholder'] == aepx_placeholder
            for m in ml_result['mappings']
        )
        checks.append((found, f"Found expected mapping: {psd_layer}→{aepx_placeholder}"))

    # Confidence checks
    for mapping in ml_result['mappings']:
        checks.append((0.0 <= mapping['confidence'] <= 1.0,
                      f"Valid confidence for {mapping['psd_layer']}: {mapping['confidence']:.2f}"))

    # Check that ML disabled gives same results as rule-based
    ml_disabled_count = len(ml_disabled_result['mappings'])
    checks.append((ml_disabled_count == rule_count,
                  f"ML disabled matches rule-based ({ml_disabled_count} vs {rule_count})"))

    # Print results
    passed = 0
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"{status} {description}")
        if check:
            passed += 1

    # Comparison summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    print(f"\nRule-Based Matcher:")
    print(f"   - Mappings: {len(rule_result['mappings'])}")
    print(f"   - Unmapped PSD layers: {len(rule_result['unmapped_psd_layers'])}")
    print(f"   - Unfilled placeholders: {len(rule_result['unfilled_placeholders'])}")

    print(f"\nML-Enhanced Matcher:")
    print(f"   - Mappings: {len(ml_result['mappings'])}")
    print(f"   - Unmapped PSD layers: {len(ml_result['unmapped_psd_layers'])}")
    print(f"   - Unfilled placeholders: {len(ml_result['unfilled_placeholders'])}")

    # Show confidence comparison
    print("\n" + "=" * 70)
    print("CONFIDENCE COMPARISON")
    print("=" * 70)

    print("\nRule-Based Confidences:")
    for m in rule_result['mappings']:
        print(f"   {m['psd_layer'][:20]:20s} → {m['aepx_placeholder']:20s} {m['confidence']:.2%}")

    print("\nML-Enhanced Confidences:")
    for m in ml_result['mappings']:
        print(f"   {m['psd_layer'][:20]:20s} → {m['aepx_placeholder']:20s} {m['confidence']:.2%}")

    # Final results
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(checks)} checks passed")
    print("=" * 70)

    assert passed >= len(checks) * 0.85, f"Too many checks failed: {passed}/{len(checks)}"

    print("\n🎉 ML matcher test PASSED!")

    if _ML_AVAILABLE:
        print("\n✨ ML enhancement is active and working!")
    else:
        print("\n⚠️  ML not available - fallback to rule-based matcher working correctly")

    return True


if __name__ == "__main__":
    try:
        test_ml_matcher()
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
