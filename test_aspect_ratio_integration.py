#!/usr/bin/env python3
"""
Test Aspect Ratio Integration

Verify that the aspect ratio handler is properly integrated into the project service.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.project_service import ProjectService
from modules.aspect_ratio import TransformationType
import logging


def test_aspect_ratio_integration():
    """Test aspect ratio checking integration"""
    print("\n" + "="*70)
    print("TESTING ASPECT RATIO INTEGRATION")
    print("="*70)

    # Setup logger
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger('test')

    # Create settings dict
    settings = {}

    # Initialize project service
    print("\n1. Initializing ProjectService with AspectRatioHandler...")
    project_service = ProjectService(logger, settings)

    # Verify aspect ratio handler was created
    assert hasattr(project_service, 'aspect_ratio_handler'), "AspectRatioHandler not initialized"
    print("   ✓ AspectRatioHandler initialized successfully")

    # Test _check_aspect_ratio_compatibility
    print("\n2. Testing _check_aspect_ratio_compatibility method...")

    # Create test graphic and data
    graphic = {
        'id': 'test_graphic_1',
        'name': 'Test Graphic'
    }

    # Test case 1: Perfect match
    print("\n   Test Case 1: Perfect Match (1920×1080 → 1920×1080)")
    psd_data = {'width': 1920, 'height': 1080}
    aepx_data = {'width': 1920, 'height': 1080}

    result = project_service._check_aspect_ratio_compatibility(
        graphic, psd_data, aepx_data
    )

    assert result.is_success(), "Check should succeed"
    data = result.get_data()
    assert data['can_auto_apply'] is True, "Should auto-apply for perfect match"
    assert data['transform'] is not None, "Should have transform data"
    print(f"   ✓ Perfect match: auto-apply={data['can_auto_apply']}, transform scale={data['transform']['scale']}")

    # Test case 2: Minor difference (7%)
    print("\n   Test Case 2: Minor Difference (1920×1080 → 1920×1161)")
    graphic2 = {'id': 'test_graphic_2', 'name': 'Test Graphic 2'}
    psd_data = {'width': 1920, 'height': 1080}
    aepx_data = {'width': 1920, 'height': 1161}

    result = project_service._check_aspect_ratio_compatibility(
        graphic2, psd_data, aepx_data
    )

    assert result.is_success(), "Check should succeed"
    data = result.get_data()
    assert data['can_auto_apply'] is True, "Should auto-apply for minor difference"
    print(f"   ✓ Minor difference: auto-apply={data['can_auto_apply']}, " +
          f"confidence={graphic2['aspect_ratio_check']['confidence']:.1%}")

    # Test case 3: Moderate difference (15%)
    print("\n   Test Case 3: Moderate Difference (1920×1080 → 1920×1280)")
    graphic3 = {'id': 'test_graphic_3', 'name': 'Test Graphic 3'}
    psd_data = {'width': 1920, 'height': 1080}
    aepx_data = {'width': 1920, 'height': 1280}

    result = project_service._check_aspect_ratio_compatibility(
        graphic3, psd_data, aepx_data
    )

    assert result.is_success(), "Check should succeed"
    data = result.get_data()
    assert data['needs_review'] is True, "Should need review for moderate difference"
    assert data['can_auto_apply'] is False, "Should not auto-apply"
    print(f"   ✓ Moderate difference: needs_review={data['needs_review']}, " +
          f"type={graphic3['aspect_ratio_check']['transformation_type']}")

    # Test case 4: Cross-category (Landscape → Portrait)
    print("\n   Test Case 4: Cross-Category (1920×1080 → 1080×1920)")
    graphic4 = {'id': 'test_graphic_4', 'name': 'Test Graphic 4'}
    psd_data = {'width': 1920, 'height': 1080}
    aepx_data = {'width': 1080, 'height': 1920}

    result = project_service._check_aspect_ratio_compatibility(
        graphic4, psd_data, aepx_data
    )

    assert result.is_success(), "Check should succeed"
    data = result.get_data()
    assert data['needs_review'] is True, "Should need review for cross-category"
    assert graphic4['aspect_ratio_check']['psd_category'] == 'landscape', "Should be landscape"
    assert graphic4['aspect_ratio_check']['aepx_category'] == 'portrait', "Should be portrait"
    print(f"   ✓ Cross-category: {graphic4['aspect_ratio_check']['psd_category']} → " +
          f"{graphic4['aspect_ratio_check']['aepx_category']}, " +
          f"confidence={graphic4['aspect_ratio_check']['confidence']:.1%}")

    # Test learning stats methods
    print("\n3. Testing learning stats methods...")
    stats_result = project_service.get_aspect_ratio_learning_stats()
    assert stats_result.is_success(), "Should get learning stats"
    stats = stats_result.get_data()
    print(f"   ✓ Learning stats retrieved: {stats['total_decisions']} decisions recorded")

    # Test export method
    print("\n4. Testing export learning data method...")
    export_path = "/tmp/test_aspect_ratio_export.json"
    export_result = project_service.export_aspect_ratio_learning_data(export_path)
    assert export_result.is_success(), "Should export successfully"
    assert os.path.exists(export_path), "Export file should exist"
    print(f"   ✓ Learning data exported to {export_path}")

    # Verify aspect_ratio_check metadata
    print("\n5. Verifying aspect_ratio_check metadata storage...")
    assert 'aspect_ratio_check' in graphic, "Should have aspect_ratio_check in graphic"
    check = graphic['aspect_ratio_check']

    required_fields = [
        'psd_category', 'aepx_category', 'psd_dimensions', 'aepx_dimensions',
        'transformation_type', 'ratio_difference', 'confidence', 'reasoning',
        'recommended_action', 'can_auto_apply', 'needs_review'
    ]

    for field in required_fields:
        assert field in check, f"Missing field: {field}"

    print(f"   ✓ All {len(required_fields)} required fields present in metadata")

    # Print summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    print("✓ AspectRatioHandler initialization")
    print("✓ _check_aspect_ratio_compatibility method (4 test cases)")
    print("✓ get_aspect_ratio_learning_stats method")
    print("✓ export_aspect_ratio_learning_data method")
    print("✓ Metadata storage and validation")
    print("\n" + "="*70)
    print("ALL INTEGRATION TESTS PASSED!")
    print("="*70 + "\n")

    return True


def test_decision_workflow():
    """Test human decision workflow"""
    print("\n" + "="*70)
    print("TESTING DECISION WORKFLOW")
    print("="*70)

    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger('test_workflow')
    settings = {}

    project_service = ProjectService(logger, settings)

    # Create a test project
    print("\n1. Creating test project...")
    result = project_service.create_project("Test Aspect Ratio Project", "Test Client")
    assert result.is_success(), "Should create project"
    project = result.get_data()
    project_id = project['id']
    print(f"   ✓ Created project: {project_id}")

    # Create a test graphic
    print("\n2. Creating test graphic...")
    result = project_service.create_graphic(project_id, "Test Graphic")
    assert result.is_success(), "Should create graphic"
    graphic = result.get_data()
    graphic_id = graphic['id']
    print(f"   ✓ Created graphic: {graphic_id}")

    # Simulate aspect ratio check data
    print("\n3. Simulating aspect ratio check...")
    project_obj = project_service.store.get_project(project_id)
    graphic_obj = project_obj.get_graphic(graphic_id)

    # Add aspect ratio check metadata (simulating what would happen during processing)
    graphic_dict = graphic_obj.to_dict()
    graphic_dict['aspect_ratio_check'] = {
        'psd_category': 'landscape',
        'aepx_category': 'landscape',
        'psd_dimensions': (1920, 1080),
        'aepx_dimensions': (1920, 1280),
        'transformation_type': 'moderate',
        'ratio_difference': 0.156,
        'confidence': 0.60,
        'reasoning': 'Moderate aspect ratio difference detected',
        'recommended_action': 'Human approval suggested',
        'can_auto_apply': False,
        'needs_review': True
    }

    # Update the graphic in store
    for key, value in graphic_dict.items():
        if hasattr(graphic_obj, key):
            setattr(graphic_obj, key, value)

    project_service.store.save()
    print("   ✓ Aspect ratio check data added")

    # Test human decision handling - proceed
    print("\n4. Testing 'proceed' decision...")
    result = project_service.handle_aspect_ratio_decision(
        project_id, graphic_id, 'proceed', transform_method='fit'
    )
    assert result.is_success(), "Should handle decision successfully"
    data = result.get_data()
    assert data['status'] == 'approved', "Should be approved"
    assert 'transform' in data, "Should have transform data"
    print(f"   ✓ Proceed decision handled: scale={data['transform']['scale']:.3f}")

    # Test skip decision
    print("\n5. Testing 'skip' decision...")
    # Create another graphic
    result = project_service.create_graphic(project_id, "Test Graphic 2")
    graphic2 = result.get_data()
    graphic2_id = graphic2['id']

    # Add aspect ratio check data
    graphic2_obj = project_obj.get_graphic(graphic2_id)
    graphic2_dict = graphic2_obj.to_dict()
    graphic2_dict['aspect_ratio_check'] = {
        'psd_category': 'landscape',
        'aepx_category': 'portrait',
        'psd_dimensions': (1920, 1080),
        'aepx_dimensions': (1080, 1920),
        'transformation_type': 'human_review',
        'ratio_difference': 0.684,
        'confidence': 0.0,
        'reasoning': 'Cross-category transformation',
        'recommended_action': 'Manual review required',
        'can_auto_apply': False,
        'needs_review': True
    }

    for key, value in graphic2_dict.items():
        if hasattr(graphic2_obj, key):
            setattr(graphic2_obj, key, value)

    project_service.store.save()

    result = project_service.handle_aspect_ratio_decision(
        project_id, graphic2_id, 'skip'
    )
    assert result.is_success(), "Should handle skip"
    data = result.get_data()
    assert data['status'] == 'skipped', "Should be skipped"
    print(f"   ✓ Skip decision handled")

    # Verify learning system recorded decisions
    print("\n6. Verifying learning system...")
    stats_result = project_service.get_aspect_ratio_learning_stats()
    stats = stats_result.get_data()
    assert stats['total_decisions'] >= 2, "Should have recorded decisions"
    print(f"   ✓ {stats['total_decisions']} decisions recorded in learning system")

    print("\n" + "="*70)
    print("DECISION WORKFLOW TEST PASSED!")
    print("="*70 + "\n")

    return True


if __name__ == "__main__":
    try:
        # Run integration test
        test_aspect_ratio_integration()

        # Run decision workflow test
        test_decision_workflow()

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
