"""
Test conflict detector functionality with configurable thresholds.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.conflict_detector import detect_conflicts
from modules.phase3.conflict_config import DEFAULT_CONFLICT_CONFIG


def test_conflict_detector():
    """Test conflict detector with default and custom configurations."""
    
    print("=" * 70)
    print("CONFLICT DETECTOR TEST (with Configuration)")
    print("=" * 70)
    
    # Load data
    print("\n📄 Loading files...")
    psd = parse_psd('sample_files/test-photoshop-doc.psd')
    aepx = parse_aepx('sample_files/test-after-effects-project.aepx')
    mappings = match_content_to_slots(psd, aepx)
    
    print(f"   ✓ Loaded {psd['filename']}")
    print(f"   ✓ Loaded {aepx['filename']}")
    print(f"   ✓ Created {len(mappings['mappings'])} mappings")
    
    # Test with default config
    print("\n🔍 Test 1: Default Configuration")
    result1 = detect_conflicts(psd, aepx, mappings)
    
    print(f"   Found {result1['summary']['total']} conflicts")
    print(f"   - Critical: {result1['summary']['critical']}")
    print(f"   - Warning: {result1['summary']['warning']}")
    print(f"   - Info: {result1['summary']['info']}")
    
    # Test with strict config
    print("\n🔍 Test 2: Strict Configuration")
    strict_config = DEFAULT_CONFLICT_CONFIG.copy()
    strict_config['text_length_warning'] = 20  # Very strict
    strict_config['aspect_ratio_tolerance'] = 0.1  # Very strict
    
    result2 = detect_conflicts(psd, aepx, mappings, strict_config)
    
    print(f"   Found {result2['summary']['total']} conflicts")
    print(f"   - Critical: {result2['summary']['critical']}")
    print(f"   - Warning: {result2['summary']['warning']}")
    print(f"   - Info: {result2['summary']['info']}")
    
    # Display conflicts
    print("\n" + "=" * 70)
    print("DETECTED CONFLICTS (Default Config)")
    print("=" * 70)
    
    for i, conflict in enumerate(result1['conflicts'], 1):
        severity_icons = {'critical': '🔴', 'warning': '⚠️', 'info': 'ℹ️'}
        icon = severity_icons[conflict['severity']]
        
        print(f"\n{i}. {icon} {conflict['id']}: {conflict['type']}")
        print(f"   Severity: {conflict['severity']}")
        print(f"   Issue: {conflict['issue']}")
        print(f"   Auto-fixable: {conflict['auto_fixable']}")
    
    # Verification
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    checks = []
    
    # Structure checks
    checks.append(('summary' in result1, "Has summary"))
    checks.append(('conflicts' in result1, "Has conflicts list"))
    checks.append(('total' in result1['summary'], "Summary has total"))
    checks.append(('critical' in result1['summary'], "Summary has critical"))
    checks.append(('warning' in result1['summary'], "Summary has warning"))
    checks.append(('info' in result1['summary'], "Summary has info"))
    
    # Conflict structure
    if result1['conflicts']:
        first = result1['conflicts'][0]
        checks.append(('id' in first, "Conflict has ID"))
        checks.append(('type' in first, "Conflict has type"))
        checks.append(('severity' in first, "Conflict has severity"))
        checks.append(('issue' in first, "Conflict has issue"))
        checks.append(('suggestion' in first, "Conflict has suggestion"))
        checks.append(('auto_fixable' in first, "Conflict has auto_fixable flag"))
    
    # Check that strict config found more conflicts
    checks.append((result2['summary']['total'] >= result1['summary']['total'],
                  "Strict config finds >= conflicts than default"))
    
    # Check dimension mismatch detected
    dim_conflicts = [c for c in result1['conflicts'] if c['type'] == 'DIMENSION_INFO']
    checks.append((len(dim_conflicts) > 0, "Detected dimension mismatch"))
    
    # Print results
    passed = 0
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"{status} {description}")
        if check:
            passed += 1
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{len(checks)} checks passed")
    print(f"{'=' * 70}")
    
    assert passed >= len(checks) * 0.85, f"Too many checks failed: {passed}/{len(checks)}"
    
    print("\n🎉 Conflict detector test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_conflict_detector()
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
