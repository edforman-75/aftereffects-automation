"""
Unit tests for PSDService.

Tests the PSDService class methods in isolation using mock data.
"""

import pytest
import os
from pathlib import Path

from services.psd_service import PSDService
from core.logging_config import get_service_logger


@pytest.fixture
def psd_service():
    """Create a PSDService instance for testing."""
    logger = get_service_logger('test_psd')
    return PSDService(logger)


class TestPSDServiceParsing:
    """Test PSD parsing functionality."""

    @pytest.mark.unit
    def test_parse_psd_file_not_found(self, psd_service):
        """Test parsing non-existent PSD file."""
        result = psd_service.parse_psd('nonexistent.psd')

        assert not result.is_success()
        assert 'not found' in result.get_error().lower()

    @pytest.mark.unit
    def test_parse_psd_invalid_extension(self, psd_service, temp_dir):
        """Test parsing file with wrong extension."""
        wrong_file = os.path.join(temp_dir, 'test.txt')
        with open(wrong_file, 'w') as f:
            f.write('test')

        result = psd_service.parse_psd(wrong_file)

        assert not result.is_success()
        assert 'extension' in result.get_error().lower()

    @pytest.mark.unit
    def test_parse_psd_invalid_file(self, psd_service, invalid_psd_file):
        """Test parsing invalid PSD file."""
        result = psd_service.parse_psd(invalid_psd_file)

        assert not result.is_success()
        # Should fail during parsing
        assert result.get_error() is not None


class TestPSDServiceValidation:
    """Test PSD file validation."""

    @pytest.mark.unit
    def test_validate_psd_file_not_found(self, psd_service):
        """Test validation of non-existent file."""
        result = psd_service.validate_psd_file('nonexistent.psd')

        assert not result.is_success()
        assert 'not found' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_psd_invalid_extension(self, psd_service, temp_dir):
        """Test validation of file with wrong extension."""
        wrong_file = os.path.join(temp_dir, 'test.txt')
        with open(wrong_file, 'w') as f:
            f.write('test')

        result = psd_service.validate_psd_file(wrong_file)

        assert not result.is_success()
        assert 'extension' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_psd_file_too_large(self, psd_service, temp_dir):
        """Test validation of file exceeding size limit."""
        large_file = os.path.join(temp_dir, 'large.psd')
        # Create a file larger than 1MB (test with 1MB limit)
        with open(large_file, 'wb') as f:
            f.write(b'0' * (2 * 1024 * 1024))  # 2MB

        result = psd_service.validate_psd_file(large_file, max_size_mb=1)

        assert not result.is_success()
        assert 'large' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_psd_invalid_signature(self, psd_service, invalid_psd_file):
        """Test validation of file with invalid PSD signature."""
        result = psd_service.validate_psd_file(invalid_psd_file)

        assert not result.is_success()
        assert 'signature' in result.get_error().lower() or 'invalid' in result.get_error().lower()


class TestPSDServiceFonts:
    """Test font extraction functionality."""

    @pytest.mark.unit
    def test_extract_fonts_success(self, psd_service, mock_psd_data):
        """Test successful font extraction."""
        result = psd_service.extract_fonts(mock_psd_data)

        assert result.is_success()
        fonts = result.get_data()
        assert isinstance(fonts, list)
        assert 'Arial' in fonts
        assert 'Helvetica' in fonts

    @pytest.mark.unit
    def test_extract_fonts_empty_data(self, psd_service, empty_psd_data):
        """Test font extraction with no layers."""
        result = psd_service.extract_fonts(empty_psd_data)

        assert result.is_success()
        fonts = result.get_data()
        assert isinstance(fonts, list)
        assert len(fonts) == 0

    @pytest.mark.unit
    def test_extract_fonts_no_text_layers(self, psd_service):
        """Test font extraction with no text layers."""
        psd_data = {
            'layers': [
                {'name': 'Image1', 'type': 'image'},
                {'name': 'Image2', 'type': 'image'}
            ]
        }
        result = psd_service.extract_fonts(psd_data)

        assert result.is_success()
        fonts = result.get_data()
        assert len(fonts) == 0

    @pytest.mark.unit
    def test_extract_fonts_invalid_data(self, psd_service):
        """Test font extraction with invalid data structure."""
        invalid_data = {'wrong_key': 'wrong_value'}
        result = psd_service.extract_fonts(invalid_data)

        assert not result.is_success()

    @pytest.mark.unit
    def test_extract_fonts_duplicate_fonts(self, psd_service):
        """Test that duplicate fonts are deduplicated."""
        psd_data = {
            'layers': [
                {
                    'type': 'text',
                    'text': {'font': 'Arial'}
                },
                {
                    'type': 'text',
                    'text': {'font': 'Arial'}
                },
                {
                    'type': 'text',
                    'text': {'font': 'Helvetica'}
                }
            ]
        }
        result = psd_service.extract_fonts(psd_data)

        assert result.is_success()
        fonts = result.get_data()
        # Should have 2 unique fonts, not 3
        assert len(fonts) == 2
        assert 'Arial' in fonts
        assert 'Helvetica' in fonts


class TestPSDServiceLayers:
    """Test layer extraction functionality."""

    @pytest.mark.unit
    def test_get_layer_count(self, psd_service, mock_psd_data):
        """Test getting total layer count."""
        result = psd_service.get_layer_count(mock_psd_data)

        assert result.is_success()
        count = result.get_data()
        assert count == 4  # Based on mock_psd_data fixture

    @pytest.mark.unit
    def test_get_text_layers(self, psd_service, mock_psd_data):
        """Test getting only text layers."""
        result = psd_service.get_text_layers(mock_psd_data)

        assert result.is_success()
        text_layers = result.get_data()
        assert len(text_layers) == 2
        assert all(layer['type'] == 'text' for layer in text_layers)

    @pytest.mark.unit
    def test_get_image_layers(self, psd_service, mock_psd_data):
        """Test getting only image layers."""
        result = psd_service.get_image_layers(mock_psd_data)

        assert result.is_success()
        image_layers = result.get_data()
        # Should get both 'image' and 'smartobject' types
        assert len(image_layers) == 2
        assert all(layer['type'] in ('image', 'smartobject') for layer in image_layers)

    @pytest.mark.unit
    def test_get_layers_empty_data(self, psd_service, empty_psd_data):
        """Test layer extraction with empty PSD."""
        text_result = psd_service.get_text_layers(empty_psd_data)
        image_result = psd_service.get_image_layers(empty_psd_data)

        assert text_result.is_success()
        assert len(text_result.get_data()) == 0

        assert image_result.is_success()
        assert len(image_result.get_data()) == 0
