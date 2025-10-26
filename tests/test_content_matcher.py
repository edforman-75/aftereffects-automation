"""
Test content matcher functionality.

Verifies intelligent mapping between PSD content and AEPX placeholders.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots


def test_content_matcher():
    """Test that content matcher correctly maps PSD layers to AEPX placeholders."""
    
    print("=" * 70)
    print("CONTENT MATCHER TEST")
    print("=" * 70)
    
    # Load PSD data
    print("\n📄 Loading PSD file...")
    psd_data = parse_psd('sample_files/test-photoshop-doc.psd')
    print(f"   Loaded: {psd_data['filename']}")
    print(f"   Total layers: {len(psd_data['layers'])}")
    print(f"   Text layers: {sum(1 for l in psd_data['layers'] if l['type'] == 'text')}")
    print(f"   Image layers: {sum(1 for l in psd_data['layers'] if l['type'] in ('image', 'smartobject'))}")
    
    # Load AEPX data
    print("\n🎬 Loading AEPX template...")
    aepx_data = parse_aepx('sample_files/test-after-effects-project.aepx')
    print(f"   Loaded: {aepx_data['filename']}")
    print(f"   Main composition: {aepx_data['composition_name']}")
    print(f"   Total placeholders: {len(aepx_data['placeholders'])}")
    print(f"   Text placeholders: {sum(1 for p in aepx_data['placeholders'] if p['type'] == 'text')}")
    print(f"   Image placeholders: {sum(1 for p in aepx_data['placeholders'] if p['type'] == 'image')}")
    
    # Run matcher
    print("\n🔗 Running content matcher...")
    result = match_content_to_slots(psd_data, aepx_data)
    
    print(f"\n   Created {len(result['mappings'])} mappings")
    print(f"   Unmapped PSD layers: {len(result['unmapped_psd_layers'])}")
    print(f"   Unfilled placeholders: {len(result['unfilled_placeholders'])}")
    
    # Display mappings
    print("\n" + "=" * 70)
    print("MAPPINGS")
    print("=" * 70)
    
    for i, mapping in enumerate(result['mappings'], 1):
        print(f"\n{i}. {mapping['type'].upper()} MAPPING")
        print(f"   PSD Layer: {mapping['psd_layer']}")
        print(f"   ↓")
        print(f"   AEPX Placeholder: {mapping['aepx_placeholder']}")
        print(f"   Confidence: {mapping['confidence']:.2f} ({mapping['confidence']*100:.0f}%)")
        print(f"   Reason: {mapping['reason']}")
    
    # Display unmapped/unfilled
    if result['unmapped_psd_layers']:
        print("\n" + "=" * 70)
        print("UNMAPPED PSD LAYERS")
        print("=" * 70)
        for layer in result['unmapped_psd_layers']:
            print(f"   - {layer}")
    
    if result['unfilled_placeholders']:
        print("\n" + "=" * 70)
        print("UNFILLED PLACEHOLDERS")
        print("=" * 70)
        for ph in result['unfilled_placeholders']:
            print(f"   - {ph}")
    
    # Verification
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    checks = []
    
    # Check expected mappings exist
    expected_mappings = [
        ("BEN FORMAN", "player1fullname", "text"),
        ("ELOISE GRACE", "player2fullname", "text"),
        ("EMMA LOUISE", "player3fullname", "text"),
        ("cutout", "featuredimage1", "image")
    ]
    
    for psd_layer, aepx_ph, mapping_type in expected_mappings:
        found = any(
            m['psd_layer'] == psd_layer and 
            m['aepx_placeholder'] == aepx_ph and 
            m['type'] == mapping_type
            for m in result['mappings']
        )
        checks.append((found, f"Mapped {psd_layer} → {aepx_ph}"))
    
    # Check confidence scores
    high_confidence_count = sum(1 for m in result['mappings'] if m['confidence'] >= 0.8)
    checks.append(
        (high_confidence_count >= 3, 
         f"At least 3 high-confidence mappings (found {high_confidence_count})")
    )
    
    # Check we have mappings
    checks.append((len(result['mappings']) >= 4, "Created at least 4 mappings"))
    
    # Check all mappings have required fields
    for m in result['mappings']:
        checks.append(
            ('psd_layer' in m and 'aepx_placeholder' in m and 'type' in m and 
             'confidence' in m and 'reason' in m,
             f"Mapping has all required fields")
        )
        break  # Just check one
    
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
    
    print("\n🎉 Content matcher test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_content_matcher()
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
