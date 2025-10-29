"""
Unit tests for MatchingService.

Tests the MatchingService class methods in isolation using mock data.
"""

import pytest

from services.matching_service import MatchingService
from core.logging_config import get_service_logger


@pytest.fixture
def matching_service():
    """Create a MatchingService instance for testing."""
    logger = get_service_logger('test_matching')
    return MatchingService(logger)


class TestMatchingServiceContentMatching:
    """Test content matching functionality."""

    @pytest.mark.unit
    def test_match_content_success(self, matching_service, mock_psd_data, mock_aepx_data):
        """Test successful content matching."""
        result = matching_service.match_content(mock_psd_data, mock_aepx_data)

        assert result.is_success()
        mappings = result.get_data()
        assert 'mappings' in mappings
        assert 'unmapped_psd_layers' in mappings
        assert 'unfilled_placeholders' in mappings
        assert len(mappings['mappings']) > 0

    @pytest.mark.unit
    def test_match_content_empty_psd(self, matching_service, empty_psd_data, mock_aepx_data):
        """Test matching with empty PSD data."""
        result = matching_service.match_content(empty_psd_data, mock_aepx_data)

        assert result.is_success()
        mappings = result.get_data()
        assert len(mappings['mappings']) == 0
        assert len(mappings['unfilled_placeholders']) == len(mock_aepx_data['placeholders'])

    @pytest.mark.unit
    def test_match_content_empty_aepx(self, matching_service, mock_psd_data, empty_aepx_data):
        """Test matching with empty AEPX data."""
        result = matching_service.match_content(mock_psd_data, empty_aepx_data)

        assert result.is_success()
        mappings = result.get_data()
        assert len(mappings['mappings']) == 0
        assert len(mappings['unmapped_psd_layers']) > 0

    @pytest.mark.unit
    def test_match_content_both_empty(self, matching_service, empty_psd_data, empty_aepx_data):
        """Test matching with both datasets empty."""
        result = matching_service.match_content(empty_psd_data, empty_aepx_data)

        assert result.is_success()
        mappings = result.get_data()
        assert len(mappings['mappings']) == 0
        assert len(mappings['unmapped_psd_layers']) == 0
        assert len(mappings['unfilled_placeholders']) == 0

    @pytest.mark.unit
    def test_match_content_invalid_psd_data(self, matching_service, mock_aepx_data):
        """Test matching with invalid PSD data."""
        invalid_psd = {'wrong_key': 'wrong_value'}
        result = matching_service.match_content(invalid_psd, mock_aepx_data)

        assert not result.is_success()

    @pytest.mark.unit
    def test_match_content_invalid_aepx_data(self, matching_service, mock_psd_data):
        """Test matching with invalid AEPX data."""
        invalid_aepx = {'wrong_key': 'wrong_value'}
        result = matching_service.match_content(mock_psd_data, invalid_aepx)

        assert not result.is_success()


class TestMatchingServiceMappingExtraction:
    """Test mapping extraction functionality."""

    @pytest.mark.unit
    def test_get_mappings(self, matching_service, mock_mappings):
        """Test getting mappings from result."""
        result = matching_service.get_mappings(mock_mappings)

        assert result.is_success()
        mappings = result.get_data()
        assert len(mappings) == 3

    @pytest.mark.unit
    def test_get_text_mappings(self, matching_service, mock_mappings):
        """Test getting only text mappings."""
        result = matching_service.get_text_mappings(mock_mappings)

        assert result.is_success()
        text_mappings = result.get_data()
        assert len(text_mappings) == 2
        assert all(m['type'] == 'text' for m in text_mappings)

    @pytest.mark.unit
    def test_get_image_mappings(self, matching_service, mock_mappings):
        """Test getting only image mappings."""
        result = matching_service.get_image_mappings(mock_mappings)

        assert result.is_success()
        image_mappings = result.get_data()
        assert len(image_mappings) == 1
        assert all(m['type'] == 'image' for m in image_mappings)


class TestMatchingServiceConfidenceFiltering:
    """Test confidence-based filtering."""

    @pytest.mark.unit
    def test_get_high_confidence_mappings(self, matching_service, mock_mappings):
        """Test filtering for high confidence mappings."""
        result = matching_service.get_high_confidence_mappings(
            mock_mappings,
            min_confidence=0.9
        )

        assert result.is_success()
        high_conf = result.get_data()
        assert len(high_conf) == 2  # 0.95 and 0.90
        assert all(m['confidence'] >= 0.9 for m in high_conf)

    @pytest.mark.unit
    def test_get_low_confidence_mappings(self, matching_service, mock_mappings):
        """Test filtering for low confidence mappings."""
        result = matching_service.get_low_confidence_mappings(
            mock_mappings,
            max_confidence=0.9
        )

        assert result.is_success()
        low_conf = result.get_data()
        assert len(low_conf) == 2  # 0.90 and 0.85
        assert all(m['confidence'] <= 0.9 for m in low_conf)

    @pytest.mark.unit
    def test_get_high_confidence_very_strict(self, matching_service, mock_mappings):
        """Test filtering with very high confidence threshold."""
        result = matching_service.get_high_confidence_mappings(
            mock_mappings,
            min_confidence=0.99
        )

        assert result.is_success()
        high_conf = result.get_data()
        # None should meet this threshold
        assert len(high_conf) == 0


class TestMatchingServiceUnmapped:
    """Test unmapped/unfilled functionality."""

    @pytest.mark.unit
    def test_get_unmapped_layers(self, matching_service, mock_mappings):
        """Test getting unmapped PSD layers."""
        result = matching_service.get_unmapped_layers(mock_mappings)

        assert result.is_success()
        unmapped = result.get_data()
        assert 'Image Layer 1' in unmapped

    @pytest.mark.unit
    def test_get_unfilled_placeholders(self, matching_service, mock_mappings):
        """Test getting unfilled placeholders."""
        result = matching_service.get_unfilled_placeholders(mock_mappings)

        assert result.is_success()
        unfilled = result.get_data()
        assert len(unfilled) == 0  # All filled in mock_mappings


class TestMatchingServiceStatistics:
    """Test statistics calculation."""

    @pytest.mark.unit
    def test_get_matching_statistics(self, matching_service, mock_mappings):
        """Test calculating matching statistics."""
        result = matching_service.get_matching_statistics(mock_mappings)

        assert result.is_success()
        stats = result.get_data()

        assert 'total_mappings' in stats
        assert 'text_mappings' in stats
        assert 'image_mappings' in stats
        assert 'unmapped_layers' in stats
        assert 'unfilled_placeholders' in stats
        assert 'average_confidence' in stats
        assert 'completion_rate' in stats

        assert stats['total_mappings'] == 3
        assert stats['text_mappings'] == 2
        assert stats['image_mappings'] == 1
        assert stats['unmapped_layers'] == 1
        assert 0 <= stats['average_confidence'] <= 1
        assert 0 <= stats['completion_rate'] <= 1

    @pytest.mark.unit
    def test_get_statistics_empty_mappings(self, matching_service):
        """Test statistics with no mappings."""
        empty_mappings = {
            'mappings': [],
            'unmapped_psd_layers': [],
            'unfilled_placeholders': []
        }
        result = matching_service.get_matching_statistics(empty_mappings)

        assert result.is_success()
        stats = result.get_data()
        assert stats['total_mappings'] == 0
        assert stats['average_confidence'] == 0

    @pytest.mark.unit
    def test_get_statistics_invalid_data(self, matching_service):
        """Test statistics with invalid data."""
        invalid_data = {'wrong_key': 'wrong_value'}
        result = matching_service.get_matching_statistics(invalid_data)

        # Service handles invalid data gracefully by returning zero statistics
        assert result.is_success()
        stats = result.get_data()
        assert stats['total_mappings'] == 0
        assert stats['average_confidence'] == 0
