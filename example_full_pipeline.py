#!/usr/bin/env python3
"""
Complete Pipeline Example

Demonstrates the full automation pipeline with conflict detection:
1. Parse PSD (Module 1.1)
2. Parse AEPX (Module 2.1)
3. Match content (Module 3.1)
4. Detect conflicts (Module 3.2)
"""

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.conflict_detector import detect_conflicts
import json


def main():
    print("=" * 70)
    print("COMPLETE AUTOMATION PIPELINE EXAMPLE")
    print("=" * 70)
    
    # Step 1: Parse PSD
    print("\n📄 Step 1: Parsing PSD file...")
    psd = parse_psd('sample_files/test-photoshop-doc.psd')
    print(f"   ✓ Loaded: {psd['filename']} ({psd['width']}×{psd['height']})")
    print(f"   ✓ Found {len(psd['layers'])} layers")
    
    # Step 2: Parse AEPX
    print("\n🎬 Step 2: Parsing AEPX template...")
    aepx = parse_aepx('sample_files/test-after-effects-project.aepx')
    print(f"   ✓ Loaded: {aepx['filename']}")
    print(f"   ✓ Main composition: {aepx['composition_name']}")
    print(f"   ✓ Found {len(aepx['placeholders'])} placeholders")
    
    # Step 3: Match content
    print("\n🔗 Step 3: Matching content to placeholders...")
    mappings = match_content_to_slots(psd, aepx)
    print(f"   ✓ Created {len(mappings['mappings'])} mappings")
    
    # Display mappings
    print("\n   Mappings created:")
    for i, m in enumerate(mappings['mappings'], 1):
        print(f"   {i}. {m['psd_layer']} → {m['aepx_placeholder']} ({m['confidence']:.0%})")
    
    # Step 4: Detect conflicts
    print("\n🔍 Step 4: Detecting potential conflicts...")
    conflicts = detect_conflicts(psd, aepx, mappings)
    print(f"   ✓ Analyzed mappings")
    print(f"   ✓ Found {conflicts['summary']['total']} potential issues")
    
    # Display conflicts
    if conflicts['summary']['total'] > 0:
        print(f"\n   Conflicts breakdown:")
        print(f"   - 🔴 Critical: {conflicts['summary']['critical']}")
        print(f"   - ⚠️  Warnings: {conflicts['summary']['warning']}")
        print(f"   - ℹ️  Info: {conflicts['summary']['info']}")
        
        print("\n" + "=" * 70)
        print("DETECTED CONFLICTS")
        print("=" * 70)
        
        severity_icons = {'critical': '🔴', 'warning': '⚠️', 'info': 'ℹ️'}
        
        for i, conflict in enumerate(conflicts['conflicts'], 1):
            icon = severity_icons[conflict['severity']]
            print(f"\n{i}. {icon} {conflict['severity'].upper()}: {conflict['type']}")
            print(f"   Issue: {conflict['issue']}")
            print(f"   Suggestion: {conflict['suggestion']}")
    else:
        print("\n   ✅ No conflicts detected! All mappings look good.")
    
    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"\n✅ PSD Content:")
    print(f"   - Source: {psd['filename']}")
    print(f"   - Dimensions: {psd['width']}×{psd['height']} px")
    print(f"   - Layers: {len(psd['layers'])}")
    
    print(f"\n✅ AEPX Template:")
    print(f"   - Template: {aepx['filename']}")
    print(f"   - Composition: {aepx['composition_name']}")
    print(f"   - Placeholders: {len(aepx['placeholders'])}")
    
    print(f"\n✅ Mappings:")
    print(f"   - Total: {len(mappings['mappings'])}")
    print(f"   - High confidence: {sum(1 for m in mappings['mappings'] if m['confidence'] >= 0.9)}")
    print(f"   - Unmapped PSD layers: {len(mappings['unmapped_psd_layers'])}")
    print(f"   - Unfilled placeholders: {len(mappings['unfilled_placeholders'])}")
    
    print(f"\n✅ Quality Check:")
    print(f"   - Total conflicts: {conflicts['summary']['total']}")
    print(f"   - Critical issues: {conflicts['summary']['critical']}")
    print(f"   - Warnings: {conflicts['summary']['warning']}")
    
    # Decision
    print("\n" + "=" * 70)
    if conflicts['summary']['critical'] == 0:
        print("✅ READY FOR RENDERING")
        print("=" * 70)
        print("\nNo critical issues detected. Safe to proceed!")
    else:
        print("⚠️ REVIEW REQUIRED")
        print("=" * 70)
        print(f"\n{conflicts['summary']['critical']} critical issue(s) found.")
        print("Please fix before proceeding with rendering.")
    
    print()


if __name__ == "__main__":
    main()
