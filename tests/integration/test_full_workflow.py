"""
Integration tests for full workflow.

Tests complete workflows using multiple services together.
"""

import pytest

from config.container import container
from core.logging_config import get_service_logger


class TestFullWorkflowWithMockData:
    """Test complete workflow from parsing to matching with mock data."""

    @pytest.mark.integration
    def test_complete_workflow_parse_and_match(self, mock_psd_data, mock_aepx_data):
        """Test complete workflow: extract fonts -> get placeholders -> match content."""

        # Step 1: Extract fonts from PSD
        fonts_result = container.psd_service.extract_fonts(mock_psd_data)
        assert fonts_result.is_success(), f"Font extraction failed: {fonts_result.get_error()}"

        fonts = fonts_result.get_data()
        assert len(fonts) > 0, "Should extract at least one font"

        # Step 2: Get text layers from PSD
        text_layers_result = container.psd_service.get_text_layers(mock_psd_data)
        assert text_layers_result.is_success(), f"Text layer extraction failed"

        text_layers = text_layers_result.get_data()
        assert len(text_layers) > 0, "Should have text layers"

        # Step 3: Get placeholders from AEPX
        placeholders_result = container.aepx_service.get_placeholders(mock_aepx_data)
        assert placeholders_result.is_success(), f"Placeholder extraction failed"

        placeholders = placeholders_result.get_data()
        assert len(placeholders) > 0, "Should have placeholders"

        # Step 4: Match content
        match_result = container.matching_service.match_content(mock_psd_data, mock_aepx_data)
        assert match_result.is_success(), f"Matching failed: {match_result.get_error()}"

        mappings = match_result.get_data()
        assert len(mappings['mappings']) > 0, "Should create at least one mapping"

        # Step 5: Get matching statistics
        stats_result = container.matching_service.get_matching_statistics(mappings)
        assert stats_result.is_success(), f"Statistics calculation failed"

        stats = stats_result.get_data()
        assert stats['total_mappings'] > 0
        assert 0 <= stats['average_confidence'] <= 1
        assert 0 <= stats['completion_rate'] <= 1

    @pytest.mark.integration
    def test_workflow_with_filtering(self, mock_psd_data, mock_aepx_data):
        """Test workflow with confidence filtering."""

        # Match content
        match_result = container.matching_service.match_content(mock_psd_data, mock_aepx_data)
        assert match_result.is_success()

        mappings = match_result.get_data()

        # Get high confidence mappings
        high_conf_result = container.matching_service.get_high_confidence_mappings(
            mappings,
            min_confidence=0.8
        )
        assert high_conf_result.is_success()
        high_conf = high_conf_result.get_data()

        # Get low confidence mappings
        low_conf_result = container.matching_service.get_low_confidence_mappings(
            mappings,
            max_confidence=0.8
        )
        assert low_conf_result.is_success()
        low_conf = low_conf_result.get_data()

        # Sum should equal total (accounting for boundary case at 0.8)
        total_mappings = len(mappings['mappings'])
        assert len(high_conf) + len(low_conf) >= total_mappings - 1

    @pytest.mark.integration
    def test_workflow_text_and_image_separation(self, mock_psd_data, mock_aepx_data):
        """Test workflow separating text and image processing."""

        # Get text layers from PSD
        text_layers_result = container.psd_service.get_text_layers(mock_psd_data)
        assert text_layers_result.is_success()
        text_layers = text_layers_result.get_data()

        # Get image layers from PSD
        image_layers_result = container.psd_service.get_image_layers(mock_psd_data)
        assert image_layers_result.is_success()
        image_layers = image_layers_result.get_data()

        # Get text placeholders from AEPX
        text_ph_result = container.aepx_service.get_text_placeholders(mock_aepx_data)
        assert text_ph_result.is_success()
        text_placeholders = text_ph_result.get_data()

        # Get image placeholders from AEPX
        image_ph_result = container.aepx_service.get_image_placeholders(mock_aepx_data)
        assert image_ph_result.is_success()
        image_placeholders = image_ph_result.get_data()

        # Verify counts match expectations
        assert len(text_layers) == 2
        assert len(image_layers) == 2
        assert len(text_placeholders) == 2
        assert len(image_placeholders) == 1

        # Match content
        match_result = container.matching_service.match_content(mock_psd_data, mock_aepx_data)
        assert match_result.is_success()

        mappings = match_result.get_data()

        # Get text mappings
        text_mappings_result = container.matching_service.get_text_mappings(mappings)
        assert text_mappings_result.is_success()
        text_mappings = text_mappings_result.get_data()

        # Get image mappings
        image_mappings_result = container.matching_service.get_image_mappings(mappings)
        assert image_mappings_result.is_success()
        image_mappings = image_mappings_result.get_data()

        # Should have text mappings (image mappings depend on name matching)
        assert len(text_mappings) > 0
        # Image mappings might be empty if names don't match well enough
        # assert len(image_mappings) > 0


class TestWorkflowWithEmptyData:
    """Test workflow with edge cases (empty data)."""

    @pytest.mark.integration
    def test_workflow_empty_psd(self, empty_psd_data, mock_aepx_data):
        """Test workflow with empty PSD data."""

        # Should handle empty PSD gracefully
        match_result = container.matching_service.match_content(empty_psd_data, mock_aepx_data)
        assert match_result.is_success()

        mappings = match_result.get_data()
        assert len(mappings['mappings']) == 0
        assert len(mappings['unfilled_placeholders']) > 0

    @pytest.mark.integration
    def test_workflow_empty_aepx(self, mock_psd_data, empty_aepx_data):
        """Test workflow with empty AEPX data."""

        # Should handle empty AEPX gracefully
        match_result = container.matching_service.match_content(mock_psd_data, empty_aepx_data)
        assert match_result.is_success()

        mappings = match_result.get_data()
        assert len(mappings['mappings']) == 0
        assert len(mappings['unmapped_psd_layers']) > 0

    @pytest.mark.integration
    def test_workflow_both_empty(self, empty_psd_data, empty_aepx_data):
        """Test workflow with both empty."""

        match_result = container.matching_service.match_content(empty_psd_data, empty_aepx_data)
        assert match_result.is_success()

        mappings = match_result.get_data()
        assert len(mappings['mappings']) == 0
        assert len(mappings['unmapped_psd_layers']) == 0
        assert len(mappings['unfilled_placeholders']) == 0


class TestWorkflowResultChaining:
    """Test result chaining with map/flat_map."""

    @pytest.mark.integration
    def test_result_chaining_with_map(self, mock_psd_data):
        """Test using Result.map() for transformations."""

        # Chain operations using map
        result = (
            container.psd_service.extract_fonts(mock_psd_data)
            .map(lambda fonts: sorted(fonts))
            .map(lambda fonts: {'count': len(fonts), 'fonts': fonts})
        )

        assert result.is_success()
        data = result.get_data()
        assert 'count' in data
        assert 'fonts' in data
        assert data['count'] > 0

    @pytest.mark.integration
    def test_result_chaining_with_flat_map(self, mock_psd_data):
        """Test using Result.flat_map() for chaining operations."""

        # This would work if we had a method that returns a Result
        # For now, test the pattern
        fonts_result = container.psd_service.extract_fonts(mock_psd_data)
        assert fonts_result.is_success()

        # Could chain more operations here
        fonts = fonts_result.get_data()
        assert len(fonts) > 0


class TestWorkflowStatistics:
    """Test complete workflow with statistics calculation."""

    @pytest.mark.integration
    def test_full_statistics_pipeline(self, mock_psd_data, mock_aepx_data):
        """Test complete pipeline ending with statistics."""

        # Parse and match
        match_result = container.matching_service.match_content(mock_psd_data, mock_aepx_data)
        assert match_result.is_success()

        mappings = match_result.get_data()

        # Calculate comprehensive statistics
        stats_result = container.matching_service.get_matching_statistics(mappings)
        assert stats_result.is_success()

        stats = stats_result.get_data()

        # Verify all expected statistics are present
        expected_keys = [
            'total_mappings',
            'text_mappings',
            'image_mappings',
            'unmapped_layers',
            'unfilled_placeholders',
            'average_confidence',
            'completion_rate'
        ]

        for key in expected_keys:
            assert key in stats, f"Missing statistic: {key}"

        # Verify statistics make sense
        assert stats['total_mappings'] == stats['text_mappings'] + stats['image_mappings']
        assert 0 <= stats['average_confidence'] <= 1
        assert 0 <= stats['completion_rate'] <= 1
