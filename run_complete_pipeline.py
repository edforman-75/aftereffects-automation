#!/usr/bin/env python3
"""
Complete Automation Pipeline

Runs all phases: PSD parsing, AEPX parsing, content matching,
conflict detection, and ExtendScript generation.

Usage: python run_complete_pipeline.py [--ml] [psd] [aepx] [output_jsx]
"""

import sys
import argparse
from pathlib import Path

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase3.ml_content_matcher import match_content_to_slots_ml, _ML_AVAILABLE
from modules.phase3.conflict_detector import detect_conflicts
from modules.phase3.font_checker import check_fonts
from modules.phase4.extendscript_generator import generate_extendscript


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_section(title):
    """Print a formatted section."""
    print(f"\n{title}")


def display_conflicts(conflicts):
    """Display conflicts in a formatted way."""
    if conflicts['summary']['total'] == 0:
        print("   ✅ No conflicts detected!")
        return True

    print(f"\n   Found {conflicts['summary']['total']} potential issue(s):")
    print(f"   - 🔴 Critical: {conflicts['summary']['critical']}")
    print(f"   - ⚠️  Warnings: {conflicts['summary']['warning']}")
    print(f"   - ℹ️  Info: {conflicts['summary']['info']}")

    severity_icons = {'critical': '🔴', 'warning': '⚠️', 'info': 'ℹ️'}

    print("\n   Details:")
    for i, conflict in enumerate(conflicts['conflicts'][:5], 1):
        icon = severity_icons[conflict['severity']]
        print(f"   {i}. {icon} {conflict['type']}: {conflict['issue'][:60]}...")

    if len(conflicts['conflicts']) > 5:
        print(f"   ... and {len(conflicts['conflicts']) - 5} more")

    return conflicts['summary']['critical'] == 0


def get_user_approval(conflicts):
    """Ask user whether to proceed despite conflicts."""
    if conflicts['summary']['total'] == 0:
        return True

    print_section("⚠️  REVIEW REQUIRED")

    if conflicts['summary']['critical'] > 0:
        print(f"\n   {conflicts['summary']['critical']} CRITICAL issue(s) detected.")
        print("   It's recommended to fix these before proceeding.")
        choice = input("\n   Proceed anyway? [y/N]: ").strip().lower()
        return choice == 'y'
    else:
        print(f"\n   {conflicts['summary']['warning']} warning(s) and {conflicts['summary']['info']} info message(s).")
        print("   Usually safe to proceed, but review recommended.")
        choice = input("\n   Proceed? [Y/n]: ").strip().lower()
        return choice != 'n'


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='After Effects Automation Pipeline')
    parser.add_argument('--ml', '--use-ml', action='store_true', dest='use_ml',
                       help='Use ML-enhanced semantic matcher')
    parser.add_argument('--comp-name', '--composition-name', dest='comp_name',
                       help='Composition name to update (for AEP files, or to override AEPX detection)')
    parser.add_argument('psd_file', nargs='?', default='sample_files/test-photoshop-doc.psd',
                       help='Path to PSD file')
    parser.add_argument('aepx_file', nargs='?', default='sample_files/test-after-effects-project.aepx',
                       help='Path to After Effects template (.aepx or .aep)')
    parser.add_argument('output_jsx', nargs='?', default='output/automation_script.jsx',
                       help='Path for output JSX file')
    return parser.parse_args()


def main():
    """Main pipeline execution."""
    args = parse_args()

    print_header("AFTER EFFECTS AUTOMATION - COMPLETE PIPELINE")

    # Show matcher type
    if args.use_ml:
        if _ML_AVAILABLE:
            print("\n🤖 Matcher: ML-Enhanced (sentence-transformers)")
            matcher_func = match_content_to_slots_ml
        else:
            print("\n⚠️  Matcher: Rule-based (ML not available)")
            print("   Install with: pip install sentence-transformers")
            matcher_func = match_content_to_slots
            args.use_ml = False  # Update flag for summary
    else:
        print("\n🔧 Matcher: Rule-based")
        matcher_func = match_content_to_slots

    print(f"\n📁 Input Files:")
    print(f"   PSD:  {args.psd_file}")
    print(f"   AEPX: {args.aepx_file}")
    print(f"   Output: {args.output_jsx}")

    # Validate input files exist
    if not Path(args.psd_file).exists():
        print(f"\n❌ ERROR: PSD file not found: {args.psd_file}")
        sys.exit(1)

    if not Path(args.aepx_file).exists():
        print(f"\n❌ ERROR: AEPX file not found: {args.aepx_file}")
        sys.exit(1)

    # Phase 1: Parse PSD
    print_section("📄 Phase 1: Parsing PSD...")
    try:
        psd = parse_psd(args.psd_file)
        print(f"   ✓ Loaded: {psd['filename']} ({psd['width']}×{psd['height']})")
        print(f"   ✓ Found {len(psd['layers'])} layers")
    except Exception as e:
        print(f"   ❌ ERROR: Failed to parse PSD: {e}")
        sys.exit(1)

    # Phase 1.5: Check fonts
    print_section("🔤 Checking fonts...")
    try:
        font_check = check_fonts(psd)
        text_layer_count = sum(1 for l in psd['layers'] if l['type'] == 'text')

        if font_check['fonts_used']:
            print(f"   ✓ Found {font_check['summary']['total']} font(s) in {text_layer_count} text layer(s)")
            if font_check['summary']['common'] > 0:
                print(f"   ✓ {font_check['summary']['common']} common font(s)")
            if font_check['summary']['uncommon'] > 0:
                print(f"   ⚠️  {font_check['summary']['uncommon']} uncommon font(s) may need installation")
                for font in font_check['uncommon_fonts']:
                    print(f"      - {font}")
        elif text_layer_count > 0:
            print(f"   ⚠️  Found {text_layer_count} text layer(s) but could not extract font names")
            print(f"   ℹ️  Manually verify fonts in After Effects")
        else:
            print(f"   ℹ️  No text layers found")
    except Exception as e:
        print(f"   ⚠️  Warning: Font check failed: {e}")

    # Phase 2: Parse After Effects template
    template_ext = Path(args.aepx_file).suffix.lower()

    if template_ext == '.aep':
        print_section("🎬 Phase 2: Working with AEP template...")
        print(f"   ℹ️  AEP files are binary format (cannot be parsed)")
        print(f"   ✓ Template: {Path(args.aepx_file).name}")

        # Determine composition name
        if args.comp_name:
            comp_name = args.comp_name
            print(f"   ✓ Using composition name from command line: {comp_name}")
        else:
            # Ask for composition name
            print(f"\n   Enter the composition name to update")
            print(f"   (Press Enter to use default: 'Main Comp')")
            comp_name = input("   Composition name: ").strip()
            if not comp_name:
                comp_name = "Main Comp"

        # Create minimal structure for AEP
        aepx = {
            'filename': Path(args.aepx_file).name,
            'composition_name': comp_name,
            'compositions': [{'name': comp_name, 'width': 1920, 'height': 1080}],
            'placeholders': []  # Can't parse AEP, so no placeholders
        }
        print(f"   ✓ Will update composition: {comp_name}")
        print(f"   ℹ️  No placeholders detected (AEP binary format)")

    else:  # .aepx
        print_section("🎬 Phase 2: Parsing AEPX template...")
        try:
            aepx = parse_aepx(args.aepx_file)
            print(f"   ✓ Loaded: {aepx['filename']}")

            # Allow command line to override detected composition name
            if args.comp_name:
                aepx['composition_name'] = args.comp_name
                print(f"   ✓ Main composition (overridden): {aepx['composition_name']}")
            else:
                print(f"   ✓ Main composition: {aepx['composition_name']}")

            print(f"   ✓ Found {len(aepx['placeholders'])} placeholders")
        except Exception as e:
            print(f"   ❌ ERROR: Failed to parse AEPX: {e}")
            sys.exit(1)

    # Phase 3: Match content
    print_section("🔗 Phase 3: Matching content to placeholders...")
    try:
        mappings = matcher_func(psd, aepx)
        print(f"   ✓ Created {len(mappings['mappings'])} mappings")

        # Show mappings
        for i, m in enumerate(mappings['mappings'][:5], 1):
            confidence_icon = "🟢" if m['confidence'] >= 0.9 else "🟡" if m['confidence'] >= 0.6 else "🔴"
            print(f"   {i}. {confidence_icon} {m['psd_layer']} → {m['aepx_placeholder']} ({m['confidence']:.0%})")

        if len(mappings['mappings']) > 5:
            print(f"   ... and {len(mappings['mappings']) - 5} more")

        if mappings['unmapped_psd_layers']:
            print(f"   ℹ️  {len(mappings['unmapped_psd_layers'])} PSD layer(s) unmapped")

        if mappings['unfilled_placeholders']:
            print(f"   ℹ️  {len(mappings['unfilled_placeholders'])} placeholder(s) unfilled")

    except Exception as e:
        print(f"   ❌ ERROR: Failed to match content: {e}")
        sys.exit(1)

    # Phase 3.2: Detect conflicts
    print_section("🔍 Phase 3.2: Detecting potential conflicts...")
    try:
        conflicts = detect_conflicts(psd, aepx, mappings)
        display_conflicts(conflicts)
    except Exception as e:
        print(f"   ❌ ERROR: Failed to detect conflicts: {e}")
        sys.exit(1)

    # Check if user approval needed
    if conflicts['summary']['total'] > 0:
        if not get_user_approval(conflicts):
            print("\n🛑 Pipeline aborted by user.")
            print("\nTo review conflicts interactively, run:")
            print(f"   python conflict_review_tool.py {args.psd_file} {args.aepx_file}")
            sys.exit(0)

    # Phase 4: Generate ExtendScript
    print_section("🔨 Phase 4: Generating ExtendScript...")
    try:
        # Prepare options with absolute paths
        psd_path = Path(args.psd_file).absolute()
        aepx_path = Path(args.aepx_file).absolute()
        output_aep = Path(args.output_jsx).parent / "output_project.aep"

        options = {
            "psd_file_path": str(psd_path),
            "aepx_file_path": str(aepx_path),
            "output_project_path": str(output_aep.absolute()),
            "render_output": False,
            "render_path": ""
        }

        jsx_path = generate_extendscript(psd, aepx, mappings, args.output_jsx, options)
        print(f"   ✓ ExtendScript generated: {jsx_path}")

        # Read and show preview
        with open(jsx_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"   ✓ Script contains {len(lines)} lines")

    except Exception as e:
        print(f"   ❌ ERROR: Failed to generate ExtendScript: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Success summary
    print_header("✅ PIPELINE COMPLETED SUCCESSFULLY")

    print("\n📊 Summary:")
    print(f"   - PSD layers: {len(psd['layers'])}")
    print(f"   - AEPX placeholders: {len(aepx['placeholders'])}")
    print(f"   - Mappings created: {len(mappings['mappings'])}")
    print(f"   - Conflicts detected: {conflicts['summary']['total']}")
    print(f"   - Script generated: {jsx_path}")
    if args.use_ml:
        print(f"   - ML matcher: USED ✨")

    print("\n📝 Next Steps:")
    print("   1. Open After Effects")
    print(f"   2. Open your template file: {args.aepx_file}")
    print(f"   3. Run the generated script: File → Scripts → Run Script File")
    print(f"   4. Select: {jsx_path}")
    print("   5. The script will update your open project!")

    if conflicts['summary']['total'] > 0:
        print("\n⚠️  Note: Review the detected conflicts before final rendering:")
        print(f"   python conflict_review_tool.py {args.psd_file} {args.aepx_file}")

    print()


if __name__ == "__main__":
    main()
