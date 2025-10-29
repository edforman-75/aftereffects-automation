"""
Unit tests for AEPXService.

Tests the AEPXService class methods in isolation using mock data.
"""

import pytest
import os

from services.aepx_service import AEPXService
from core.logging_config import get_service_logger


@pytest.fixture
def aepx_service():
    """Create an AEPXService instance for testing."""
    logger = get_service_logger('test_aepx')
    return AEPXService(logger)


class TestAEPXServiceParsing:
    """Test AEPX parsing functionality."""

    @pytest.mark.unit
    def test_parse_aepx_file_not_found(self, aepx_service):
        """Test parsing non-existent AEPX file."""
        result = aepx_service.parse_aepx('nonexistent.aepx')

        assert not result.is_success()
        assert 'not found' in result.get_error().lower()

    @pytest.mark.unit
    def test_parse_aepx_invalid_extension(self, aepx_service, temp_dir):
        """Test parsing file with wrong extension."""
        wrong_file = os.path.join(temp_dir, 'test.txt')
        with open(wrong_file, 'w') as f:
            f.write('test')

        result = aepx_service.parse_aepx(wrong_file)

        assert not result.is_success()
        assert 'extension' in result.get_error().lower()

    @pytest.mark.unit
    def test_parse_aepx_invalid_file(self, aepx_service, invalid_aepx_file):
        """Test parsing invalid AEPX file."""
        result = aepx_service.parse_aepx(invalid_aepx_file)

        assert not result.is_success()
        # Should fail during XML parsing
        assert result.get_error() is not None

    @pytest.mark.unit
    def test_parse_aepx_valid_file(self, aepx_service, valid_aepx_file):
        """Test parsing valid AEPX file."""
        result = aepx_service.parse_aepx(valid_aepx_file)

        assert result.is_success()
        aepx_data = result.get_data()
        assert 'compositions' in aepx_data
        assert 'placeholders' in aepx_data


class TestAEPXServiceValidation:
    """Test AEPX file validation."""

    @pytest.mark.unit
    def test_validate_aepx_file_not_found(self, aepx_service):
        """Test validation of non-existent file."""
        result = aepx_service.validate_aepx_file('nonexistent.aepx')

        assert not result.is_success()
        assert 'not found' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_aepx_invalid_extension(self, aepx_service, temp_dir):
        """Test validation of file with wrong extension."""
        wrong_file = os.path.join(temp_dir, 'test.txt')
        with open(wrong_file, 'w') as f:
            f.write('test')

        result = aepx_service.validate_aepx_file(wrong_file)

        assert not result.is_success()
        assert 'extension' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_aepx_file_too_large(self, aepx_service, temp_dir):
        """Test validation of file exceeding size limit."""
        large_file = os.path.join(temp_dir, 'large.aepx')
        # Create a file larger than 1MB
        with open(large_file, 'wb') as f:
            f.write(b'0' * (2 * 1024 * 1024))  # 2MB

        result = aepx_service.validate_aepx_file(large_file, max_size_mb=1)

        assert not result.is_success()
        assert 'large' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_aepx_invalid_xml(self, aepx_service, invalid_aepx_file):
        """Test validation of file with invalid XML."""
        result = aepx_service.validate_aepx_file(invalid_aepx_file)

        assert not result.is_success()
        assert 'xml' in result.get_error().lower() or 'format' in result.get_error().lower()

    @pytest.mark.unit
    def test_validate_aepx_valid_file(self, aepx_service, valid_aepx_file):
        """Test validation of valid AEPX file."""
        result = aepx_service.validate_aepx_file(valid_aepx_file)

        assert result.is_success()


class TestAEPXServicePlaceholders:
    """Test placeholder extraction functionality."""

    @pytest.mark.unit
    def test_get_placeholders_success(self, aepx_service, mock_aepx_data):
        """Test successful placeholder extraction."""
        result = aepx_service.get_placeholders(mock_aepx_data)

        assert result.is_success()
        placeholders = result.get_data()
        assert isinstance(placeholders, list)
        assert len(placeholders) == 3
        assert all('name' in ph for ph in placeholders)

    @pytest.mark.unit
    def test_get_placeholders_empty(self, aepx_service, empty_aepx_data):
        """Test placeholder extraction with no placeholders."""
        result = aepx_service.get_placeholders(empty_aepx_data)

        assert result.is_success()
        placeholders = result.get_data()
        assert len(placeholders) == 0

    @pytest.mark.unit
    def test_get_placeholders_invalid_data(self, aepx_service):
        """Test placeholder extraction with invalid data."""
        invalid_data = {'wrong_key': 'wrong_value'}
        result = aepx_service.get_placeholders(invalid_data)

        # Service handles invalid data gracefully by returning empty list
        assert result.is_success()
        placeholders = result.get_data()
        assert len(placeholders) == 0

    @pytest.mark.unit
    def test_get_text_placeholders(self, aepx_service, mock_aepx_data):
        """Test getting only text placeholders."""
        result = aepx_service.get_text_placeholders(mock_aepx_data)

        assert result.is_success()
        text_placeholders = result.get_data()
        assert len(text_placeholders) == 2
        assert all(ph['type'] == 'text' for ph in text_placeholders)

    @pytest.mark.unit
    def test_get_image_placeholders(self, aepx_service, mock_aepx_data):
        """Test getting only image placeholders."""
        result = aepx_service.get_image_placeholders(mock_aepx_data)

        assert result.is_success()
        image_placeholders = result.get_data()
        assert len(image_placeholders) == 1
        assert all(ph['type'] == 'image' for ph in image_placeholders)

    @pytest.mark.unit
    def test_get_placeholder_count(self, aepx_service, mock_aepx_data):
        """Test getting placeholder count."""
        result = aepx_service.get_placeholder_count(mock_aepx_data)

        assert result.is_success()
        count = result.get_data()
        assert count == 3


class TestAEPXServiceCompositions:
    """Test composition extraction functionality."""

    @pytest.mark.unit
    def test_get_compositions(self, aepx_service, mock_aepx_data):
        """Test getting all compositions."""
        result = aepx_service.get_compositions(mock_aepx_data)

        assert result.is_success()
        compositions = result.get_data()
        assert len(compositions) == 1
        assert compositions[0]['name'] == 'Main Comp'

    @pytest.mark.unit
    def test_get_main_composition(self, aepx_service, mock_aepx_data):
        """Test getting main composition."""
        result = aepx_service.get_main_composition(mock_aepx_data)

        assert result.is_success()
        comp = result.get_data()
        assert comp['name'] == 'Main Comp'

    @pytest.mark.unit
    def test_get_main_composition_no_compositions(self, aepx_service):
        """Test getting main composition when none exist."""
        aepx_data = {
            'composition_name': 'Test',
            'compositions': [],
            'placeholders': []
        }
        result = aepx_service.get_main_composition(aepx_data)

        assert not result.is_success()
        assert 'no compositions' in result.get_error().lower()
