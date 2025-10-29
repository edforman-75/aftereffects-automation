"""
Unit tests for PreviewService.

Tests the PreviewService class methods in isolation using mock data.
"""

import pytest
import os

from services.preview_service import PreviewService
from core.logging_config import get_service_logger


@pytest.fixture
def preview_service():
    """Create a PreviewService instance for testing."""
    logger = get_service_logger('test_preview')
    return PreviewService(logger)


class TestPreviewServiceOptionsValidation:
    """Test preview options validation."""

    @pytest.mark.unit
    def test_validate_options_valid(self, preview_service, mock_preview_options):
        """Test validation with valid options."""
        result = preview_service.validate_options(mock_preview_options)

        assert result.is_success()

    @pytest.mark.unit
    def test_validate_options_invalid_resolution(self, preview_service):
        """Test validation with invalid resolution."""
        options = {
            'resolution': 'invalid_resolution',
            'duration': 5,
            'format': 'mp4'
        }
        result = preview_service.validate_options(options)

        assert not result.is_success()
        assert 'resolution' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_options_invalid_format(self, preview_service):
        """Test validation with invalid format."""
        options = {
            'resolution': 'half',
            'duration': 5,
            'format': 'invalid_format'
        }
        result = preview_service.validate_options(options)

        assert not result.is_success()
        assert 'format' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_options_invalid_quality(self, preview_service):
        """Test validation with invalid quality."""
        options = {
            'resolution': 'half',
            'duration': 5,
            'format': 'mp4',
            'quality': 'invalid_quality'
        }
        result = preview_service.validate_options(options)

        assert not result.is_success()
        assert 'quality' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_options_negative_duration(self, preview_service):
        """Test validation with negative duration."""
        options = {
            'resolution': 'half',
            'duration': -5,
            'format': 'mp4'
        }
        result = preview_service.validate_options(options)

        assert not result.is_success()
        assert 'duration' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_options_invalid_fps(self, preview_service):
        """Test validation with invalid FPS."""
        options = {
            'resolution': 'half',
            'duration': 5,
            'format': 'mp4',
            'fps': 500  # Too high
        }
        result = preview_service.validate_options(options)

        assert not result.is_success()
        assert 'fps' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_options_full_duration(self, preview_service):
        """Test validation with 'full' duration."""
        options = {
            'resolution': 'half',
            'duration': 'full',
            'format': 'mp4'
        }
        result = preview_service.validate_options(options)

        assert result.is_success()


class TestPreviewServiceDefaults:
    """Test default options."""

    @pytest.mark.unit
    def test_get_default_options(self, preview_service):
        """Test getting default options."""
        defaults = preview_service.get_default_options()

        assert isinstance(defaults, dict)
        assert 'resolution' in defaults
        assert 'duration' in defaults
        assert 'format' in defaults
        assert 'quality' in defaults
        assert 'fps' in defaults


class TestPreviewServiceVideoInfo:
    """Test video metadata extraction."""

    @pytest.mark.unit
    def test_get_video_info_file_not_found(self, preview_service):
        """Test getting info from non-existent video."""
        result = preview_service.get_video_info('nonexistent.mp4')

        assert not result.is_success()
        assert 'not found' in result.get_error().lower()


class TestPreviewServiceValidation:
    """Test preview validation."""

    @pytest.mark.unit
    def test_validate_preview_output_not_found(self, preview_service):
        """Test validation of non-existent preview."""
        result = preview_service.validate_preview_output('nonexistent.mp4')

        assert not result.is_success()
        assert 'not found' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_preview_output_empty_file(self, preview_service, temp_dir):
        """Test validation of empty preview file."""
        empty_file = os.path.join(temp_dir, 'empty.mp4')
        with open(empty_file, 'w') as f:
            pass  # Create empty file

        result = preview_service.validate_preview_output(empty_file)

        assert not result.is_success()
        assert 'empty' in result.get_error().lower()


class TestPreviewServiceThumbnail:
    """Test thumbnail generation."""

    @pytest.mark.unit
    def test_generate_thumbnail_file_not_found(self, preview_service):
        """Test thumbnail generation from non-existent video."""
        result = preview_service.generate_thumbnail('nonexistent.mp4')

        assert not result.is_success()
        assert 'not found' in result.get_error().lower()


class TestPreviewServiceInputValidation:
    """Test preview input validation."""

    @pytest.mark.unit
    def test_validate_inputs_aepx_not_found(self, preview_service, mock_mappings, temp_dir):
        """Test validation with non-existent AEPX."""
        output_path = os.path.join(temp_dir, 'output.mp4')
        # Using internal validation method if exposed, or test through generate_preview
        # For now, this is a placeholder for the pattern

    @pytest.mark.unit
    def test_validate_inputs_invalid_output_format(self, preview_service, temp_dir, mock_mappings):
        """Test validation with invalid output format."""
        aepx_path = os.path.join(temp_dir, 'valid.aepx')
        output_path = os.path.join(temp_dir, 'output.invalid')

        # Create minimal valid AEPX
        with open(aepx_path, 'w') as f:
            f.write('<?xml version="1.0"?><AfterEffectsProject />')

        # This would be tested through _validate_preview_inputs if it's exposed
        # For now, documenting the test pattern
