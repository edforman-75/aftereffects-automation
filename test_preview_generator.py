#!/usr/bin/env python3
"""
Test Aspect Ratio Preview Generator

Tests the visual preview generation for aspect ratio transformations.
"""

import sys
import os
import logging
from PIL import Image
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import BaseService directly to avoid circular dependency
spec = importlib.util.spec_from_file_location("base_service", "services/base_service.py")
base_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_service)

# Import AspectRatioPreviewGenerator directly
spec2 = importlib.util.spec_from_file_location("preview_generator", "modules/aspect_ratio/preview_generator.py")
preview_module = importlib.util.module_from_spec(spec2)
sys.modules['services.base_service'] = base_service  # Make it available for preview_generator
spec2.loader.exec_module(preview_module)

AspectRatioPreviewGenerator = preview_module.AspectRatioPreviewGenerator


def create_test_psd(path: str, width: int, height: int):
    """Create a test PSD/image file with color gradient"""
    # Create a gradient image for testing
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            # Create a gradient from blue to green
            r = int((x / width) * 255)
            g = int((y / height) * 255)
            b = 128
            pixels[x, y] = (r, g, b)

    # Add a red border so we can see cropping
    border_width = 10
    for x in range(width):
        for y in range(border_width):
            pixels[x, y] = (255, 0, 0)
            if y < height:
                pixels[x, height - 1 - y] = (255, 0, 0)

    for y in range(height):
        for x in range(border_width):
            pixels[x, y] = (255, 0, 0)
            if x < width:
                pixels[width - 1 - x, y] = (255, 0, 0)

    img.save(path)
    print(f"   ✓ Created test image: {width}×{height}")
    return path


def test_preview_generation():
    """Test basic preview generation"""
    print("\n" + "="*70)
    print("TESTING ASPECT RATIO PREVIEW GENERATOR")
    print("="*70)

    # Setup logger
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger('test')

    # Create preview generator
    print("\n1. Initializing AspectRatioPreviewGenerator...")
    generator = AspectRatioPreviewGenerator(logger)
    print("   ✓ Generator initialized successfully")

    # Create test directory
    test_dir = "/tmp/aspect_ratio_preview_test"
    os.makedirs(test_dir, exist_ok=True)

    # Test Case 1: Landscape to Square (letterbox)
    print("\n2. Test Case 1: Landscape (1920×1080) → Square (1920×1920)")
    psd_path_1 = os.path.join(test_dir, "test_landscape.png")
    create_test_psd(psd_path_1, 1920, 1080)

    output_dir_1 = os.path.join(test_dir, "case1_landscape_to_square")
    result = generator.generate_transformation_previews(
        psd_path=psd_path_1,
        aepx_width=1920,
        aepx_height=1920,
        output_dir=output_dir_1
    )

    assert result.is_success(), f"Preview generation failed: {result.get_error()}"
    data = result.get_data()

    assert 'previews' in data, "Missing previews in result"
    assert 'fit' in data['previews'], "Missing fit preview"
    assert 'fill' in data['previews'], "Missing fill preview"
    assert 'original' in data['previews'], "Missing original preview"

    # Verify files exist
    assert os.path.exists(data['previews']['fit']), "Fit preview file not created"
    assert os.path.exists(data['previews']['fill']), "Fill preview file not created"
    assert os.path.exists(data['previews']['original']), "Original preview file not created"

    # Check transform info
    fit_info = data['transform_info']['fit']
    assert fit_info['method'] == 'fit', "Incorrect transform method"
    assert fit_info['bars'] == 'horizontal', "Should have horizontal letterbox"
    assert fit_info['offset_y'] > 0, "Should have vertical offset for letterbox"

    fill_info = data['transform_info']['fill']
    assert fill_info['method'] == 'fill', "Incorrect fill method"
    assert fill_info['crop_left'] > 0 or fill_info['crop_top'] > 0, "Should have cropping"

    print(f"   ✓ Generated 3 previews in {output_dir_1}")
    print(f"   ✓ Fit: {fit_info['bars']} bars, scale={fit_info['scale']:.3f}")
    print(f"   ✓ Fill: cropped {fill_info['crop_left']}px left, {fill_info['crop_top']}px top")

    # Test Case 2: Portrait to Landscape (pillarbox)
    print("\n3. Test Case 2: Portrait (1080×1920) → Landscape (1920×1080)")
    psd_path_2 = os.path.join(test_dir, "test_portrait.png")
    create_test_psd(psd_path_2, 1080, 1920)

    output_dir_2 = os.path.join(test_dir, "case2_portrait_to_landscape")
    result = generator.generate_transformation_previews(
        psd_path=psd_path_2,
        aepx_width=1920,
        aepx_height=1080,
        output_dir=output_dir_2
    )

    assert result.is_success(), "Preview generation should succeed"
    data = result.get_data()

    fit_info = data['transform_info']['fit']
    assert fit_info['bars'] == 'vertical', "Should have vertical pillarbox"
    assert fit_info['offset_x'] > 0, "Should have horizontal offset for pillarbox"

    print(f"   ✓ Generated 3 previews in {output_dir_2}")
    print(f"   ✓ Fit: {fit_info['bars']} bars, scale={fit_info['scale']:.3f}")

    # Test Case 3: Perfect match (no bars, minimal crop)
    print("\n4. Test Case 3: Perfect Match (1920×1080) → (1920×1080)")
    psd_path_3 = os.path.join(test_dir, "test_match.png")
    create_test_psd(psd_path_3, 1920, 1080)

    output_dir_3 = os.path.join(test_dir, "case3_perfect_match")
    result = generator.generate_transformation_previews(
        psd_path=psd_path_3,
        aepx_width=1920,
        aepx_height=1080,
        output_dir=output_dir_3
    )

    assert result.is_success(), "Preview generation should succeed"
    data = result.get_data()

    fit_info = data['transform_info']['fit']
    assert fit_info['bars'] is None, "Should have no bars for perfect match"
    assert fit_info['scale'] == 1.0, "Should have 1.0 scale for perfect match"

    print(f"   ✓ Generated 3 previews in {output_dir_3}")
    print(f"   ✓ Perfect match: no bars, scale=1.0")

    print("\n" + "="*70)
    print("BASIC PREVIEW GENERATION TESTS PASSED!")
    print("="*70)

    return test_dir


def test_thumbnail_generation(test_dir: str):
    """Test thumbnail generation"""
    print("\n" + "="*70)
    print("TESTING THUMBNAIL GENERATION")
    print("="*70)

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test_thumbnail')

    generator = AspectRatioPreviewGenerator(logger)

    # Use a preview from previous test
    preview_path = os.path.join(test_dir, "case1_landscape_to_square", "fit_preview.jpg")
    thumbnail_path = os.path.join(test_dir, "fit_thumbnail.jpg")

    print("\n1. Generating thumbnail from preview...")
    result = generator.generate_thumbnail(
        preview_path=preview_path,
        output_path=thumbnail_path,
        max_size=400
    )

    assert result.is_success(), f"Thumbnail generation failed: {result.get_error()}"
    data = result.get_data()

    assert os.path.exists(thumbnail_path), "Thumbnail file not created"

    # Verify dimensions
    thumb = Image.open(thumbnail_path)
    width, height = thumb.size
    assert max(width, height) <= 400, "Thumbnail exceeds max size"

    print(f"   ✓ Thumbnail created: {width}×{height}")
    print(f"   ✓ Path: {thumbnail_path}")

    print("\n" + "="*70)
    print("THUMBNAIL GENERATION TEST PASSED!")
    print("="*70)


def test_side_by_side_comparison(test_dir: str):
    """Test side-by-side comparison generation"""
    print("\n" + "="*70)
    print("TESTING SIDE-BY-SIDE COMPARISON")
    print("="*70)

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test_comparison')

    generator = AspectRatioPreviewGenerator(logger)

    # Use previews from case 1
    preview_dir = os.path.join(test_dir, "case1_landscape_to_square")
    original_path = os.path.join(preview_dir, "original_preview.jpg")
    fit_path = os.path.join(preview_dir, "fit_preview.jpg")
    fill_path = os.path.join(preview_dir, "fill_preview.jpg")

    comparison_path = os.path.join(test_dir, "comparison.jpg")

    print("\n1. Generating side-by-side comparison...")
    result = generator.generate_side_by_side_comparison(
        original_path=original_path,
        fit_path=fit_path,
        fill_path=fill_path,
        output_path=comparison_path
    )

    assert result.is_success(), f"Comparison generation failed: {result.get_error()}"
    data = result.get_data()

    assert os.path.exists(comparison_path), "Comparison file not created"

    # Verify dimensions
    comparison = Image.open(comparison_path)
    comp_width, comp_height = comparison.size

    # Should be 3 images wide plus spacing
    original = Image.open(original_path)
    expected_width_approx = original.width * 3 + 80  # 4 * spacing (20px each)

    assert comp_width > original.width * 3, "Comparison should be 3+ images wide"

    print(f"   ✓ Comparison created: {comp_width}×{comp_height}")
    print(f"   ✓ Path: {comparison_path}")

    print("\n" + "="*70)
    print("SIDE-BY-SIDE COMPARISON TEST PASSED!")
    print("="*70)


def test_error_handling():
    """Test error handling"""
    print("\n" + "="*70)
    print("TESTING ERROR HANDLING")
    print("="*70)

    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger('test_errors')

    generator = AspectRatioPreviewGenerator(logger)

    # Test 1: Non-existent PSD file
    print("\n1. Testing non-existent PSD file...")
    result = generator.generate_transformation_previews(
        psd_path="/tmp/nonexistent.psd",
        aepx_width=1920,
        aepx_height=1080,
        output_dir="/tmp/test_output"
    )

    assert not result.is_success(), "Should fail for non-existent file"
    print(f"   ✓ Correctly failed: {result.get_error()}")

    # Test 2: Non-existent preview for thumbnail
    print("\n2. Testing non-existent preview for thumbnail...")
    result = generator.generate_thumbnail(
        preview_path="/tmp/nonexistent.jpg",
        output_path="/tmp/thumb.jpg"
    )

    assert not result.is_success(), "Should fail for non-existent preview"
    print(f"   ✓ Correctly failed: {result.get_error()}")

    # Test 3: Non-existent previews for comparison
    print("\n3. Testing non-existent previews for comparison...")
    result = generator.generate_side_by_side_comparison(
        original_path="/tmp/nonexistent1.jpg",
        fit_path="/tmp/nonexistent2.jpg",
        fill_path="/tmp/nonexistent3.jpg",
        output_path="/tmp/comparison.jpg"
    )

    assert not result.is_success(), "Should fail for non-existent previews"
    print(f"   ✓ Correctly failed: {result.get_error()}")

    print("\n" + "="*70)
    print("ERROR HANDLING TESTS PASSED!")
    print("="*70)


if __name__ == "__main__":
    try:
        # Run all tests
        test_dir = test_preview_generation()
        test_thumbnail_generation(test_dir)
        test_side_by_side_comparison(test_dir)
        test_error_handling()

        print("\n" + "="*70)
        print("🎉 ALL PREVIEW GENERATOR TESTS PASSED!")
        print("="*70)
        print(f"\nTest outputs saved to: {test_dir}")
        print("You can view the generated preview images to verify quality.\n")

        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
