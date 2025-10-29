"""
Service Layer Usage Example

Demonstrates how to use the new service-based architecture for
processing PSD and AEPX files through the complete workflow.
"""

from config.container import container


def example_complete_workflow(psd_path: str, aepx_path: str, output_video: str):
    """
    Complete workflow example using the service layer.

    This demonstrates:
    1. Parsing PSD and AEPX files
    2. Matching content to placeholders
    3. Generating preview video
    4. Error handling with Result pattern
    """

    print("=" * 70)
    print("SERVICE LAYER WORKFLOW EXAMPLE")
    print("=" * 70)

    # Step 1: Parse PSD file
    print("\n[1/5] Parsing PSD file...")
    psd_result = container.psd_service.parse_psd(psd_path)

    if not psd_result.is_success():
        print(f"❌ PSD parsing failed: {psd_result.get_error()}")
        return False

    psd_data = psd_result.get_data()
    print(f"✅ PSD parsed: {len(psd_data.get('layers', []))} layers")

    # Step 2: Parse AEPX file
    print("\n[2/5] Parsing AEPX file...")
    aepx_result = container.aepx_service.parse_aepx(aepx_path)

    if not aepx_result.is_success():
        print(f"❌ AEPX parsing failed: {aepx_result.get_error()}")
        return False

    aepx_data = aepx_result.get_data()
    print(f"✅ AEPX parsed: {len(aepx_data.get('placeholders', []))} placeholders")

    # Step 3: Match content to placeholders
    print("\n[3/5] Matching content...")
    match_result = container.matching_service.match_content(psd_data, aepx_data)

    if not match_result.is_success():
        print(f"❌ Matching failed: {match_result.get_error()}")
        return False

    mappings = match_result.get_data()
    print(f"✅ Matched: {len(mappings.get('mappings', []))} mappings")

    # Get matching statistics
    stats_result = container.matching_service.get_matching_statistics(mappings)
    if stats_result.is_success():
        stats = stats_result.get_data()
        print(f"   - Text mappings: {stats['text_mappings']}")
        print(f"   - Image mappings: {stats['image_mappings']}")
        print(f"   - Average confidence: {stats['average_confidence']:.2f}")
        print(f"   - Completion rate: {stats['completion_rate']:.0%}")

    # Step 4: Check aerender availability
    print("\n[4/5] Checking After Effects...")
    aerender_result = container.preview_service.check_aerender_available()

    if not aerender_result.is_success():
        print(f"⚠️  {aerender_result.get_error()}")
        print("   (Preview generation will be skipped)")
        return True  # Still successful up to this point

    aerender_path = aerender_result.get_data()
    print(f"✅ After Effects found: {aerender_path}")

    # Step 5: Generate preview
    print("\n[5/5] Generating preview...")
    preview_result = container.preview_service.generate_preview(
        aepx_path=aepx_path,
        mappings=mappings,
        output_path=output_video,
        options={
            'resolution': 'half',
            'duration': 5,
            'format': 'mp4',
            'fps': 15
        }
    )

    if not preview_result.is_success():
        print(f"❌ Preview failed: {preview_result.get_error()}")
        return False

    preview_data = preview_result.get_data()
    print(f"✅ Preview generated: {preview_data['video_path']}")
    print(f"   - Duration: {preview_data['duration']}s")
    print(f"   - Resolution: {preview_data['resolution']}")

    if preview_data.get('thumbnail_path'):
        print(f"   - Thumbnail: {preview_data['thumbnail_path']}")

    print("\n" + "=" * 70)
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 70)

    return True


def example_validation_only(psd_path: str, aepx_path: str):
    """
    Example: Validate files without processing them.

    Demonstrates using validation methods without full processing.
    """

    print("\n" + "=" * 70)
    print("VALIDATION EXAMPLE")
    print("=" * 70)

    # Validate PSD
    print("\nValidating PSD file...")
    psd_valid = container.psd_service.validate_psd_file(psd_path, max_size_mb=50)

    if psd_valid.is_success():
        print("✅ PSD file is valid")
    else:
        print(f"❌ PSD validation failed: {psd_valid.get_error()}")

    # Validate AEPX
    print("\nValidating AEPX file...")
    aepx_valid = container.aepx_service.validate_aepx_file(aepx_path, max_size_mb=10)

    if aepx_valid.is_success():
        print("✅ AEPX file is valid")
    else:
        print(f"❌ AEPX validation failed: {aepx_valid.get_error()}")


def example_extract_fonts(psd_path: str):
    """
    Example: Extract fonts from PSD.

    Demonstrates extracting fonts using the service layer.
    """

    print("\n" + "=" * 70)
    print("FONT EXTRACTION EXAMPLE")
    print("=" * 70)

    # Parse PSD
    print("\nParsing PSD...")
    psd_result = container.psd_service.parse_psd(psd_path)

    if not psd_result.is_success():
        print(f"❌ Failed: {psd_result.get_error()}")
        return

    # Extract fonts
    print("Extracting fonts...")
    fonts_result = container.psd_service.extract_fonts(psd_result.get_data())

    if fonts_result.is_success():
        fonts = fonts_result.get_data()
        print(f"✅ Found {len(fonts)} unique fonts:")
        for font in fonts:
            print(f"   - {font}")
    else:
        print(f"❌ Failed: {fonts_result.get_error()}")


def example_result_chaining(psd_path: str):
    """
    Example: Using Result.map() and Result.flat_map() for chaining.

    Demonstrates the power of the Result monad pattern.
    """

    print("\n" + "=" * 70)
    print("RESULT CHAINING EXAMPLE")
    print("=" * 70)

    # Chain operations using map and flat_map
    result = (
        container.psd_service.parse_psd(psd_path)
        .flat_map(lambda psd_data: container.psd_service.extract_fonts(psd_data))
        .map(lambda fonts: sorted(fonts))
        .map(lambda fonts: {"font_count": len(fonts), "fonts": fonts})
    )

    if result.is_success():
        data = result.get_data()
        print(f"✅ Found {data['font_count']} fonts:")
        for font in data['fonts']:
            print(f"   - {font}")
    else:
        print(f"❌ Pipeline failed: {result.get_error()}")


def example_error_handling(invalid_path: str):
    """
    Example: Graceful error handling.

    Demonstrates how the Result pattern handles errors without exceptions.
    """

    print("\n" + "=" * 70)
    print("ERROR HANDLING EXAMPLE")
    print("=" * 70)

    # Try to parse invalid file
    print(f"\nTrying to parse: {invalid_path}")
    result = container.psd_service.parse_psd(invalid_path)

    # No try/catch needed - check result instead
    if result.is_success():
        print("✅ File parsed successfully")
        data = result.get_data()
        print(f"   Layers: {len(data.get('layers', []))}")
    else:
        # Error is captured in Result, not thrown
        print(f"⚠️  Parsing failed (as expected): {result.get_error()}")
        print("   (Application continues gracefully)")


def example_matching_analysis(psd_path: str, aepx_path: str):
    """
    Example: Detailed matching analysis.

    Demonstrates using various matching service methods.
    """

    print("\n" + "=" * 70)
    print("MATCHING ANALYSIS EXAMPLE")
    print("=" * 70)

    # Parse files
    psd_result = container.psd_service.parse_psd(psd_path)
    aepx_result = container.aepx_service.parse_aepx(aepx_path)

    if not (psd_result.is_success() and aepx_result.is_success()):
        print("❌ Failed to parse files")
        return

    # Match content
    match_result = container.matching_service.match_content(
        psd_result.get_data(),
        aepx_result.get_data()
    )

    if not match_result.is_success():
        print(f"❌ Matching failed: {match_result.get_error()}")
        return

    mappings = match_result.get_data()

    # Analyze mappings
    print("\n📊 Matching Analysis:")

    # Get text mappings
    text_result = container.matching_service.get_text_mappings(mappings)
    if text_result.is_success():
        print(f"\n   Text Mappings: {len(text_result.get_data())}")
        for m in text_result.get_data():
            print(f"      {m['psd_layer']} → {m['aepx_placeholder']} "
                  f"(confidence: {m['confidence']:.2f})")

    # Get image mappings
    image_result = container.matching_service.get_image_mappings(mappings)
    if image_result.is_success():
        print(f"\n   Image Mappings: {len(image_result.get_data())}")
        for m in image_result.get_data():
            print(f"      {m['psd_layer']} → {m['aepx_placeholder']} "
                  f"(confidence: {m['confidence']:.2f})")

    # Get low confidence mappings (may need review)
    low_conf_result = container.matching_service.get_low_confidence_mappings(
        mappings,
        max_confidence=0.7
    )
    if low_conf_result.is_success():
        low_conf = low_conf_result.get_data()
        if low_conf:
            print(f"\n   ⚠️  Low Confidence Mappings (need review): {len(low_conf)}")
            for m in low_conf:
                print(f"      {m['psd_layer']} → {m['aepx_placeholder']} "
                      f"(confidence: {m['confidence']:.2f})")

    # Get unmapped layers
    unmapped_result = container.matching_service.get_unmapped_layers(mappings)
    if unmapped_result.is_success():
        unmapped = unmapped_result.get_data()
        if unmapped:
            print(f"\n   Unmapped PSD Layers: {len(unmapped)}")
            for layer in unmapped:
                print(f"      - {layer}")

    # Get unfilled placeholders
    unfilled_result = container.matching_service.get_unfilled_placeholders(mappings)
    if unfilled_result.is_success():
        unfilled = unfilled_result.get_data()
        if unfilled:
            print(f"\n   Unfilled AEPX Placeholders: {len(unfilled)}")
            for ph in unfilled:
                print(f"      - {ph}")

    # Get overall statistics
    stats_result = container.matching_service.get_matching_statistics(mappings)
    if stats_result.is_success():
        stats = stats_result.get_data()
        print(f"\n   Overall Statistics:")
        print(f"      Total mappings: {stats['total_mappings']}")
        print(f"      Average confidence: {stats['average_confidence']:.2f}")
        print(f"      Completion rate: {stats['completion_rate']:.0%}")


if __name__ == "__main__":
    """
    Run examples (requires actual PSD and AEPX files).

    Update these paths to match your test files.
    """

    # Example file paths (update these for your environment)
    PSD_FILE = "sample_files/test.psd"
    AEPX_FILE = "sample_files/test.aepx"
    OUTPUT_VIDEO = "previews/test_preview.mp4"

    # Run examples
    print("\n" + "🚀 SERVICE LAYER EXAMPLES" + "\n")

    # Example 1: Validation only
    example_validation_only(PSD_FILE, AEPX_FILE)

    # Example 2: Extract fonts
    example_extract_fonts(PSD_FILE)

    # Example 3: Error handling
    example_error_handling("nonexistent_file.psd")

    # Example 4: Result chaining
    example_result_chaining(PSD_FILE)

    # Example 5: Matching analysis
    example_matching_analysis(PSD_FILE, AEPX_FILE)

    # Example 6: Complete workflow
    # example_complete_workflow(PSD_FILE, AEPX_FILE, OUTPUT_VIDEO)
