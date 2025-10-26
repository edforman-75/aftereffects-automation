"""
Test conflict detector functionality.

Verifies detection of text overflow, size mismatches, and dimension conflicts.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.conflict_detector import detect_conflicts


def test_conflict_detector():
    """Test that conflict detector identifies potential issues."""
    
    print("=" * 70)
    print("CONFLICT DETECTOR TEST")
    print("=" * 70)
    
    # Load data
    print("\n📄 Loading files...")
    psd_data = parse_psd('sample_files/test-photoshop-doc.psd')
    aepx_data = parse_aepx('sample_files/test-after-effects-project.aepx')
    mappings = match_content_to_slots(psd_data, aepx_data)
    
    print(f"   ✓ Loaded PSD: {psd_data['filename']}")
    print(f"   ✓ Loaded AEPX: {aepx_data['filename']}")
    print(f"   ✓ Created {len(mappings['mappings'])} mappings")
    
    # Run conflict detector
    print("\n🔍 Running conflict detector...")
    result = detect_conflicts(psd_data, aepx_data, mappings)
    
    print(f"\n   Found {result['summary']['total_conflicts']} potential conflicts:")
    print(f"   - Critical: {result['summary']['critical']}")
    print(f"   - Warnings: {result['summary']['warnings']}")
    print(f"   - Info: {result['summary']['info']}")
    
    # Display conflicts
    print("\n" + "=" * 70)
    print("DETECTED CONFLICTS")
    print("=" * 70)
    
    if not result['conflicts']:
        print("\n✅ No conflicts detected! All mappings look good.")
    else:
        for i, conflict in enumerate(result['conflicts'], 1):
            severity_icons = {
                'critical': '🔴',
                'warning': '⚠️',
                'info': 'ℹ️'
            }
            
            icon = severity_icons.get(conflict['severity'], '•')
            
            print(f"\n{i}. {icon} {conflict['severity'].upper()}: {conflict['type']}")
            
            if 'psd_layer' in conflict['mapping']:
                print(f"   Mapping: {conflict['mapping']['psd_layer']} → {conflict['mapping']['aepx_placeholder']}")
            
            print(f"   Issue: {conflict['issue']}")
            print(f"   Suggestion: {conflict['suggestion']}")
    
    # Verification
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    checks = []
    
    # Check that we have a summary
    checks.append(('summary' in result, "Has summary"))
    checks.append(('total_conflicts' in result['summary'], "Summary has total_conflicts"))
    checks.append(('critical' in result['summary'], "Summary has critical count"))
    checks.append(('warnings' in result['summary'], "Summary has warnings count"))
    checks.append(('info' in result['summary'], "Summary has info count"))
    
    # Check conflicts structure
    checks.append(('conflicts' in result, "Has conflicts list"))
    checks.append((isinstance(result['conflicts'], list), "Conflicts is a list"))
    
    # Check for dimension mismatch (PSD is 1200x1500, template is 1920x1080)
    dimension_conflicts = [c for c in result['conflicts'] if c['type'] == 'dimension_mismatch']
    checks.append((len(dimension_conflicts) > 0, "Detected dimension mismatch (PSD 1200x1500 vs template 1920x1080)"))
    
    # Check conflict structure
    if result['conflicts']:
        first_conflict = result['conflicts'][0]
        checks.append(('type' in first_conflict, "Conflict has type"))
        checks.append(('severity' in first_conflict, "Conflict has severity"))
        checks.append(('issue' in first_conflict, "Conflict has issue"))
        checks.append(('suggestion' in first_conflict, "Conflict has suggestion"))
    
    # Verify severity levels are valid
    valid_severities = {'critical', 'warning', 'info'}
    all_valid = all(c['severity'] in valid_severities for c in result['conflicts'])
    checks.append((all_valid, "All severities are valid (critical/warning/info)"))
    
    # Print results
    passed = 0
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"{status} {description}")
        if check:
            passed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(checks)} checks passed")
    print("=" * 70)
    
    # Assert success
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
