#!/usr/bin/env python3
"""
Test Aspect Ratio Integration with Preview Generation

Verify that aspect ratio checking generates visual previews when needed.
"""

import sys
import os
import logging
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly to avoid circular dependencies
import importlib.util

spec = importlib.util.spec_from_file_location("base_service", "services/base_service.py")
base_service = importlib.util.module_from_spec(spec)
sys.modules['services.base_service'] = base_service
spec.loader.exec_module(base_service)

spec2 = importlib.util.spec_from_file_location("project_service", "services/project_service.py")
project_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(project_module)

ProjectService = project_module.ProjectService


def create_test_psd(path: str, width: int, height: int):
    """Create a test PSD/image file"""
    # Create a simple gradient image
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            r = int((x / width) * 255)
            g = int((y / height) * 255)
            b = 128
            pixels[x, y] = (r, g, b)

    # Add red border
    border = 10
    for x in range(width):
        for y in range(border):
            pixels[x, y] = (255, 0, 0)
            if y < height:
                pixels[x, height - 1 - y] = (255, 0, 0)

    for y in range(height):
        for x in range(border):
            pixels[x, y] = (255, 0, 0)
            if x < width:
                pixels[width - 1 - x, y] = (255, 0, 0)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return path


def test_preview_integration():
    """Test aspect ratio checking with preview generation"""
    print("\n" + "="*70)
    print("TESTING ASPECT RATIO WITH PREVIEW GENERATION")
    print("="*70)

    # Setup
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger('test')

    settings = {'base_dir': '/tmp/aspect_ratio_test'}
    project_service = ProjectService(logger, settings)

    print("\n1. Initializing ProjectService with preview generator...")
    assert hasattr(project_service, 'aspect_ratio_handler'), "Missing aspect_ratio_handler"
    assert hasattr(project_service, 'preview_generator'), "Missing preview_generator"
    print("   ✓ Both handlers initialized")

    # Create test project
    project_id = 'test_project_123'

    # Test Case 1: Auto-apply scenario (no previews needed)
    print("\n2. Test Case 1: Auto-apply (1920×1080 → 1920×1161, 7% diff)")
    print("   Should NOT generate previews")

    graphic1 = {
        'id': 'graphic_1',
        'name': 'Test Graphic 1',
        'psd_path': '/tmp/test_landscape.png'
    }

    psd_data1 = {'width': 1920, 'height': 1080}
    aepx_data1 = {'width': 1920, 'height': 1161}

    result = project_service._check_aspect_ratio_compatibility(
        project_id=project_id,
        graphic=graphic1,
        psd_data=psd_data1,
        aepx_data=aepx_data1
    )

    assert result.is_success(), "Check should succeed"
    data = result.get_data()
    assert data['can_auto_apply'] is True, "Should auto-apply for minor difference"
    assert data['transform'] is not None, "Should have transform"
    assert data['previews'] is None, "Should NOT generate previews for auto-apply"
    print(f"   ✓ Auto-apply: scale={data['transform']['scale']:.3f}, no previews")

    # Test Case 2: Needs review scenario (previews required)
    print("\n3. Test Case 2: Needs Review (1920×1080 → 1920×1920, 44% diff)")
    print("   SHOULD generate 3 previews + 3 thumbnails")

    # Create actual test PSD (use PNG since PIL can't write PSD)
    test_psd_path = '/tmp/aspect_ratio_test/test_landscape.png'
    create_test_psd(test_psd_path, 1920, 1080)

    graphic2 = {
        'id': 'graphic_2',
        'name': 'Test Graphic 2',
        'psd_path': test_psd_path
    }

    psd_data2 = {'width': 1920, 'height': 1080}
    aepx_data2 = {'width': 1920, 'height': 1920}

    result = project_service._check_aspect_ratio_compatibility(
        project_id=project_id,
        graphic=graphic2,
        psd_data=psd_data2,
        aepx_data=aepx_data2
    )

    assert result.is_success(), f"Check should succeed: {result.get_error()}"
    data = result.get_data()
    assert data['needs_review'] is True, "Should need review"
    assert data['can_auto_apply'] is False, "Should not auto-apply"
    assert data['previews'] is not None, "Should have previews"

    previews = data['previews']
    assert 'fit' in previews, "Should have fit preview"
    assert 'fill' in previews, "Should have fill preview"
    assert 'original' in previews, "Should have original preview"
    assert 'thumbnails' in previews, "Should have thumbnails"

    # Verify files exist
    assert os.path.exists(previews['fit']), f"Fit preview missing: {previews['fit']}"
    assert os.path.exists(previews['fill']), f"Fill preview missing: {previews['fill']}"
    assert os.path.exists(previews['original']), f"Original preview missing: {previews['original']}"

    print(f"   ✓ Generated 3 previews:")
    print(f"     - Fit: {previews['fit']}")
    print(f"     - Fill: {previews['fill']}")
    print(f"     - Original: {previews['original']}")

    # Verify thumbnails
    thumbnails = previews['thumbnails']
    assert len(thumbnails) == 3, f"Should have 3 thumbnails, got {len(thumbnails)}"

    for method in ['fit', 'fill', 'original']:
        assert method in thumbnails, f"Missing {method} thumbnail"
        assert os.path.exists(thumbnails[method]), f"Thumbnail file missing: {thumbnails[method]}"

    print(f"   ✓ Generated 3 thumbnails (400px max)")

    # Verify preview images
    fit_img = Image.open(previews['fit'])
    fill_img = Image.open(previews['fill'])

    assert fit_img.size == (1920, 1920), "Fit preview wrong size"
    assert fill_img.size == (1920, 1920), "Fill preview wrong size"

    print(f"   ✓ Preview dimensions correct: 1920×1920")

    # Verify metadata stored in graphic
    assert 'aspect_ratio_check' in graphic2, "Missing aspect_ratio_check in graphic"
    check = graphic2['aspect_ratio_check']
    assert check['needs_review'] is True, "Should need review in metadata"
    assert check['previews'] is not None, "Should have previews in metadata"

    print(f"   ✓ Metadata stored in graphic")

    # Test Case 3: Cross-category (also needs previews)
    print("\n4. Test Case 3: Cross-Category (1920×1080 → 1080×1920)")
    print("   SHOULD generate previews (cross-category)")

    test_psd_path_3 = '/tmp/aspect_ratio_test/test_landscape_3.png'
    create_test_psd(test_psd_path_3, 1920, 1080)

    graphic3 = {
        'id': 'graphic_3',
        'name': 'Test Graphic 3',
        'psd_path': test_psd_path_3
    }

    psd_data3 = {'width': 1920, 'height': 1080}
    aepx_data3 = {'width': 1080, 'height': 1920}

    result = project_service._check_aspect_ratio_compatibility(
        project_id=project_id,
        graphic=graphic3,
        psd_data=psd_data3,
        aepx_data=aepx_data3
    )

    assert result.is_success(), "Check should succeed"
    data = result.get_data()
    assert data['needs_review'] is True, "Should need review for cross-category"
    assert data['previews'] is not None, "Should have previews for cross-category"

    print(f"   ✓ Cross-category previews generated")

    print("\n" + "="*70)
    print("ASPECT RATIO WITH PREVIEW INTEGRATION TEST SUMMARY")
    print("="*70)
    print("✓ ProjectService initialization with both handlers")
    print("✓ Auto-apply case (no previews)")
    print("✓ Needs review case (3 previews + 3 thumbnails)")
    print("✓ Cross-category case (previews generated)")
    print("✓ Metadata storage verified")
    print("✓ File creation verified")
    print("\n" + "="*70)
    print("ALL PREVIEW INTEGRATION TESTS PASSED!")
    print("="*70 + "\n")

    return True


if __name__ == "__main__":
    try:
        test_preview_integration()

        print("\n🎉 ALL TESTS PASSED!\n")
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
