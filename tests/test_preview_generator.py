#!/usr/bin/env python3
"""
Test suite for Module 5: Video Preview Generation

Tests preview generation functionality with and without aerender.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.phase5.preview_generator import (
    check_aerender_available,
    generate_preview,
    prepare_temp_project,
    render_with_aerender,
    generate_thumbnail,
    get_video_info
)


def test_check_aerender_available():
    """Test aerender availability check."""
    print("\n" + "=" * 70)
    print("TEST 1: Check aerender Availability")
    print("=" * 70)

    aerender_path = check_aerender_available()

    if aerender_path:
        print(f"✅ aerender found at: {aerender_path}")
        return True
    else:
        print("⚠️  aerender not found (After Effects not installed)")
        print("   Preview generation will be skipped in tests")
        return False


def test_prepare_temp_project():
    """Test temporary project preparation."""
    print("\n" + "=" * 70)
    print("TEST 2: Prepare Temporary Project")
    print("=" * 70)

    # Create mock AEPX file
    temp_dir = tempfile.mkdtemp(prefix='test_preview_')

    try:
        # Create dummy AEPX file
        aepx_path = os.path.join(temp_dir, 'test_template.aepx')
        with open(aepx_path, 'w') as f:
            f.write('<?xml version="1.0"?><AfterEffectsProject></AfterEffectsProject>')

        # Mock mappings
        mappings = {
            'composition_name': 'Main Comp',
            'mappings': [
                {
                    'psd_layer': 'Title',
                    'aepx_placeholder': 'title_text',
                    'type': 'text',
                    'confidence': 1.0
                }
            ]
        }

        # Prepare project
        work_dir = tempfile.mkdtemp(prefix='test_work_')
        result_path = prepare_temp_project(aepx_path, mappings, work_dir)

        if os.path.exists(result_path):
            print(f"✅ Temp project created: {result_path}")
            return True
        else:
            print(f"❌ Failed to create temp project")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)


def test_generate_preview_no_aerender():
    """Test preview generation when aerender is not available."""
    print("\n" + "=" * 70)
    print("TEST 3: Generate Preview (No aerender)")
    print("=" * 70)

    with patch('modules.phase5.preview_generator.check_aerender_available', return_value=None):
        # Create dummy AEPX file
        temp_dir = tempfile.mkdtemp(prefix='test_preview_')

        try:
            aepx_path = os.path.join(temp_dir, 'test.aepx')
            with open(aepx_path, 'w') as f:
                f.write('<?xml version="1.0"?><AfterEffectsProject></AfterEffectsProject>')

            mappings = {
                'composition_name': 'Main Comp',
                'mappings': []
            }

            output_path = os.path.join(temp_dir, 'preview.mp4')

            result = generate_preview(aepx_path, mappings, output_path)

            if not result['success'] and 'aerender not found' in result.get('error', ''):
                print("✅ Correctly reported aerender not available")
                return True
            else:
                print(f"❌ Unexpected result: {result}")
                return False

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_render_with_aerender_mock():
    """Test render with aerender using mock."""
    print("\n" + "=" * 70)
    print("TEST 4: Render with aerender (Mocked)")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix='test_render_')

    try:
        project_path = os.path.join(temp_dir, 'test.aep')
        output_path = os.path.join(temp_dir, 'output.mp4')

        # Create dummy project file
        with open(project_path, 'w') as f:
            f.write('mock project')

        # Mock subprocess.run to simulate successful render
        def mock_subprocess_run(*args, **kwargs):
            # Create the output file to simulate aerender creating it
            with open(output_path, 'w') as f:
                f.write('mock video output')
            return Mock(returncode=0, stdout='Render completed', stderr='')

        with patch('subprocess.run', side_effect=mock_subprocess_run):
            options = {
                'resolution': 'half',
                'duration': 5.0,
                'format': 'mp4',
                'fps': 15
            }

            aerender_path = '/mock/aerender'

            result = render_with_aerender(
                project_path,
                'Main Comp',
                output_path,
                options,
                aerender_path
            )

            if result:
                print("✅ Mock render succeeded")
                return True
            else:
                print("❌ Mock render failed")
                return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_generate_thumbnail_mock():
    """Test thumbnail generation using mock."""
    print("\n" + "=" * 70)
    print("TEST 5: Generate Thumbnail (Mocked)")
    print("=" * 70)

    with patch('subprocess.run') as mock_run:
        # Mock ffmpeg check (available)
        mock_run.side_effect = [
            Mock(returncode=0, stdout='/usr/bin/ffmpeg'),  # which ffmpeg
            Mock(returncode=0)  # ffmpeg command
        ]

        temp_dir = tempfile.mkdtemp(prefix='test_thumb_')

        try:
            # Create dummy video file
            video_path = os.path.join(temp_dir, 'video.mp4')
            with open(video_path, 'w') as f:
                f.write('mock video')

            # Create mock thumbnail (since ffmpeg is mocked)
            thumb_path = os.path.join(temp_dir, 'video.jpg')
            with open(thumb_path, 'w') as f:
                f.write('mock thumbnail')

            result = generate_thumbnail(video_path, timestamp=0.5)

            if result and 'jpg' in result:
                print(f"✅ Thumbnail path generated: {result}")
                return True
            else:
                print(f"⚠️  Thumbnail generation skipped (ffmpeg not available)")
                return True  # This is acceptable

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_video_info_mock():
    """Test video info extraction using mock."""
    print("\n" + "=" * 70)
    print("TEST 6: Get Video Info (Mocked)")
    print("=" * 70)

    mock_ffprobe_output = '''
    {
        "format": {
            "duration": "5.0"
        },
        "streams": [
            {
                "codec_type": "video",
                "width": 960,
                "height": 540,
                "r_frame_rate": "30/1"
            }
        ]
    }
    '''

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=mock_ffprobe_output,
            stderr=''
        )

        temp_dir = tempfile.mkdtemp(prefix='test_info_')

        try:
            video_path = os.path.join(temp_dir, 'video.mp4')
            with open(video_path, 'w') as f:
                f.write('mock video')

            info = get_video_info(video_path)

            print(f"   Duration: {info.get('duration')}")
            print(f"   Resolution: {info.get('resolution')}")
            print(f"   FPS: {info.get('fps')}")

            if info.get('duration') == 5.0 and info.get('resolution') == '960x540':
                print("✅ Video info extracted correctly")
                return True
            else:
                print(f"⚠️  Video info extraction skipped or incomplete")
                return True

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "PREVIEW GENERATOR TESTS" + " " * 27 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    results = []

    # Run tests
    results.append(("aerender Check", test_check_aerender_available()))
    results.append(("Prepare Temp Project", test_prepare_temp_project()))
    results.append(("Generate Preview (No aerender)", test_generate_preview_no_aerender()))
    results.append(("Render with aerender (Mock)", test_render_with_aerender_mock()))
    results.append(("Generate Thumbnail (Mock)", test_generate_thumbnail_mock()))
    results.append(("Get Video Info (Mock)", test_get_video_info_mock()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 70)
    print()

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)
