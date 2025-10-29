"""
Test ExtendScript Generator functionality.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from modules.phase4.extendscript_generator import generate_extendscript


def test_extendscript_generator():
    """Test ExtendScript generation with sample files."""

    print("=" * 70)
    print("EXTENDSCRIPT GENERATOR TEST")
    print("=" * 70)

    # Load data
    print("\n📄 Loading sample files...")
    psd = parse_psd('sample_files/test-photoshop-doc.psd')
    aepx = parse_aepx('sample_files/test-after-effects-project.aepx')
    mappings = match_content_to_slots(psd, aepx)

    print(f"   ✓ Loaded {psd['filename']}")
    print(f"   ✓ Loaded {aepx['filename']}")
    print(f"   ✓ Created {len(mappings['mappings'])} mappings")

    # Configure options with actual absolute paths
    psd_abs_path = os.path.abspath('sample_files/test-photoshop-doc.psd')
    aepx_abs_path = os.path.abspath('sample_files/test-after-effects-project.aepx')
    output_abs_path = os.path.abspath('output/populated_template.aep')

    options = {
        "psd_file_path": psd_abs_path,
        "aepx_file_path": aepx_abs_path,
        "output_project_path": output_abs_path,
        "render_output": False,
        "render_path": ""
    }

    # Generate ExtendScript
    print("\n🔨 Generating ExtendScript...")
    output_path = "output/automation_script.jsx"
    result_path = generate_extendscript(psd, aepx, mappings, output_path, options)

    print(f"   ✓ Script generated: {result_path}")

    # Read and validate generated script
    print("\n🔍 Validating generated script...")
    with open(result_path, 'r', encoding='utf-8') as f:
        script_content = f.read()

    # Run checks
    checks = []

    # Basic structure checks
    checks.append((len(script_content) > 0, "Script is not empty"))
    checks.append(("CONFIG" in script_content, "Contains CONFIG object"))
    checks.append(("function main()" in script_content, "Contains main function"))
    checks.append(("findLayerByName" in script_content, "Contains findLayerByName helper"))
    checks.append(("updateTextLayer" in script_content, "Contains updateTextLayer helper"))

    # Metadata checks
    checks.append((psd['filename'] in script_content, "Contains PSD filename"))
    checks.append((aepx['filename'] in script_content, "Contains AEPX filename"))
    checks.append((aepx['composition_name'] in script_content, "Contains composition name"))

    # Mapping checks - verify placeholder names appear
    text_mappings = [m for m in mappings['mappings'] if m['type'] == 'text']
    if text_mappings:
        first_text = text_mappings[0]['aepx_placeholder']
        checks.append((first_text in script_content, f"Contains text placeholder: {first_text}"))

    image_mappings = [m for m in mappings['mappings'] if m['type'] == 'image']
    if image_mappings:
        first_image = image_mappings[0]['aepx_placeholder']
        checks.append((first_image in script_content, f"Contains image placeholder: {first_image}"))

    # Content checks - verify PSD text content appears
    for psd_layer in psd['layers']:
        if psd_layer['type'] == 'text' and 'text' in psd_layer:
            content = psd_layer['text']['content']
            # Check if content or escaped version appears
            checks.append((content in script_content or content.replace('"', '\\"') in script_content,
                          f"Contains text content: {content[:20]}..."))
            break  # Just check first one

    # Syntax checks
    checks.append(("try {" in script_content, "Contains try-catch block"))
    checks.append(("alert(" in script_content, "Contains alert statements"))
    checks.append(("logMessage(" in script_content, "Contains logging"))

    # File path checks
    checks.append((options['aepx_file_path'].replace('\\', '/') in script_content,
                  "Contains AEPX file path"))
    checks.append((options['output_project_path'].replace('\\', '/') in script_content,
                  "Contains output project path"))

    # Print validation results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    passed = 0
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"{status} {description}")
        if check:
            passed += 1

    # Show script preview
    print("\n" + "=" * 70)
    print("SCRIPT PREVIEW (first 30 lines)")
    print("=" * 70)
    lines = script_content.split('\n')
    for i, line in enumerate(lines[:30], 1):
        print(f"{i:3d}: {line}")

    if len(lines) > 30:
        print(f"... ({len(lines) - 30} more lines)")

    # Statistics
    print("\n" + "=" * 70)
    print("SCRIPT STATISTICS")
    print("=" * 70)
    print(f"Total lines: {len(lines)}")
    print(f"Total characters: {len(script_content)}")
    print(f"Text mappings: {len(text_mappings)}")
    print(f"Image mappings: {len(image_mappings)}")

    # Final results
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(checks)} checks passed")
    print("=" * 70)

    assert passed >= len(checks) * 0.85, f"Too many checks failed: {passed}/{len(checks)}"

    print("\n🎉 ExtendScript generator test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_extendscript_generator()
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
