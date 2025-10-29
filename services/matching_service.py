"""
Matching Service

Handles content-to-slot matching operations, mapping PSD content layers
to AEPX template placeholders.
"""

from typing import Dict, List, Any

from services.base_service import BaseService, Result
from core.exceptions import MatchingError, ValidationError

# Import existing modules (these will remain unchanged)
from modules.phase3 import content_matcher


class MatchingService(BaseService):
    """
    Service for handling content matching operations.

    This service wraps the existing content_matcher module and provides
    a clean API with proper error handling and logging.
    """

    def match_content(
        self,
        psd_data: Dict[str, Any],
        aepx_data: Dict[str, Any]
    ) -> Result[Dict[str, Any]]:
        """
        Match PSD content layers to AEPX template placeholders.

        Args:
            psd_data: Parsed PSD data from PSDService
            aepx_data: Parsed AEPX data from AEPXService

        Returns:
            Result containing mapping dict with:
            - mappings: List of matched pairs
            - unmapped_psd_layers: Unmatched PSD layers
            - unfilled_placeholders: Unfilled AEPX placeholders
        """
        self.log_info("Starting content matching")

        # Validate inputs
        validation = self._validate_matching_inputs(psd_data, aepx_data)
        if not validation.is_success():
            return validation

        try:
            # Call existing matcher module
            mapping_result = content_matcher.match_content_to_slots(
                psd_data,
                aepx_data
            )

            # Validate result structure
            if not isinstance(mapping_result, dict):
                return Result.failure("Invalid mapping result structure")

            if 'mappings' not in mapping_result:
                return Result.failure("Mapping result missing 'mappings' field")

            # Log statistics
            mapping_count = len(mapping_result.get('mappings', []))
            unmapped_count = len(mapping_result.get('unmapped_psd_layers', []))
            unfilled_count = len(mapping_result.get('unfilled_placeholders', []))

            self.log_info(
                f"Matching complete: {mapping_count} mappings, "
                f"{unmapped_count} unmapped layers, "
                f"{unfilled_count} unfilled placeholders"
            )

            return Result.success(mapping_result)

        except Exception as e:
            self.log_error("Content matching failed", exc=e)
            return Result.failure(f"Content matching failed: {str(e)}")

    def get_mappings(self, mapping_result: Dict[str, Any]) -> Result[List[Dict]]:
        """
        Extract just the mappings from a matching result.

        Args:
            mapping_result: Result from match_content

        Returns:
            Result containing list of mappings or error
        """
        try:
            mappings = mapping_result.get('mappings', [])
            return Result.success(mappings)
        except Exception as e:
            self.log_error("Failed to get mappings", exc=e)
            return Result.failure(str(e))

    def get_text_mappings(self, mapping_result: Dict[str, Any]) -> Result[List[Dict]]:
        """
        Get only text layer mappings.

        Args:
            mapping_result: Result from match_content

        Returns:
            Result containing list of text mappings or error
        """
        try:
            mappings = mapping_result.get('mappings', [])
            text_mappings = [
                m for m in mappings
                if m.get('type') == 'text'
            ]

            self.log_info(f"Found {len(text_mappings)} text mappings")
            return Result.success(text_mappings)

        except Exception as e:
            self.log_error("Failed to get text mappings", exc=e)
            return Result.failure(str(e))

    def get_image_mappings(self, mapping_result: Dict[str, Any]) -> Result[List[Dict]]:
        """
        Get only image layer mappings.

        Args:
            mapping_result: Result from match_content

        Returns:
            Result containing list of image mappings or error
        """
        try:
            mappings = mapping_result.get('mappings', [])
            image_mappings = [
                m for m in mappings
                if m.get('type') == 'image'
            ]

            self.log_info(f"Found {len(image_mappings)} image mappings")
            return Result.success(image_mappings)

        except Exception as e:
            self.log_error("Failed to get image mappings", exc=e)
            return Result.failure(str(e))

    def get_high_confidence_mappings(
        self,
        mapping_result: Dict[str, Any],
        min_confidence: float = 0.8
    ) -> Result[List[Dict]]:
        """
        Get mappings above a confidence threshold.

        Args:
            mapping_result: Result from match_content
            min_confidence: Minimum confidence score (0.0-1.0)

        Returns:
            Result containing list of high-confidence mappings or error
        """
        try:
            mappings = mapping_result.get('mappings', [])
            high_conf = [
                m for m in mappings
                if m.get('confidence', 0) >= min_confidence
            ]

            self.log_info(
                f"Found {len(high_conf)} mappings with confidence >= {min_confidence}"
            )
            return Result.success(high_conf)

        except Exception as e:
            self.log_error("Failed to filter by confidence", exc=e)
            return Result.failure(str(e))

    def get_low_confidence_mappings(
        self,
        mapping_result: Dict[str, Any],
        max_confidence: float = 0.5
    ) -> Result[List[Dict]]:
        """
        Get mappings below a confidence threshold (may need review).

        Args:
            mapping_result: Result from match_content
            max_confidence: Maximum confidence score (0.0-1.0)

        Returns:
            Result containing list of low-confidence mappings or error
        """
        try:
            mappings = mapping_result.get('mappings', [])
            low_conf = [
                m for m in mappings
                if m.get('confidence', 1.0) <= max_confidence
            ]

            if low_conf:
                self.log_info(
                    f"Found {len(low_conf)} mappings with confidence <= {max_confidence} "
                    "(may need review)"
                )
            else:
                self.log_info("No low-confidence mappings found")

            return Result.success(low_conf)

        except Exception as e:
            self.log_error("Failed to filter by confidence", exc=e)
            return Result.failure(str(e))

    def get_unmapped_layers(self, mapping_result: Dict[str, Any]) -> Result[List[str]]:
        """
        Get list of PSD layers that were not mapped.

        Args:
            mapping_result: Result from match_content

        Returns:
            Result containing list of unmapped layer names or error
        """
        try:
            unmapped = mapping_result.get('unmapped_psd_layers', [])
            if unmapped:
                self.log_info(f"Found {len(unmapped)} unmapped PSD layers")
            return Result.success(unmapped)
        except Exception as e:
            self.log_error("Failed to get unmapped layers", exc=e)
            return Result.failure(str(e))

    def get_unfilled_placeholders(
        self,
        mapping_result: Dict[str, Any]
    ) -> Result[List[str]]:
        """
        Get list of AEPX placeholders that were not filled.

        Args:
            mapping_result: Result from match_content

        Returns:
            Result containing list of unfilled placeholder names or error
        """
        try:
            unfilled = mapping_result.get('unfilled_placeholders', [])
            if unfilled:
                self.log_info(f"Found {len(unfilled)} unfilled placeholders")
            return Result.success(unfilled)
        except Exception as e:
            self.log_error("Failed to get unfilled placeholders", exc=e)
            return Result.failure(str(e))

    def get_matching_statistics(
        self,
        mapping_result: Dict[str, Any]
    ) -> Result[Dict[str, Any]]:
        """
        Get statistics about the matching results.

        Args:
            mapping_result: Result from match_content

        Returns:
            Result containing statistics dict or error
        """
        try:
            mappings = mapping_result.get('mappings', [])
            unmapped = mapping_result.get('unmapped_psd_layers', [])
            unfilled = mapping_result.get('unfilled_placeholders', [])

            text_mappings = [m for m in mappings if m.get('type') == 'text']
            image_mappings = [m for m in mappings if m.get('type') == 'image']

            # Calculate average confidence
            confidences = [m.get('confidence', 0) for m in mappings]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            stats = {
                'total_mappings': len(mappings),
                'text_mappings': len(text_mappings),
                'image_mappings': len(image_mappings),
                'unmapped_layers': len(unmapped),
                'unfilled_placeholders': len(unfilled),
                'average_confidence': round(avg_confidence, 3),
                'completion_rate': round(
                    len(mappings) / (len(mappings) + len(unfilled))
                    if (len(mappings) + len(unfilled)) > 0 else 0,
                    3
                )
            }

            self.log_info(f"Matching statistics: {stats}")
            return Result.success(stats)

        except Exception as e:
            self.log_error("Failed to calculate statistics", exc=e)
            return Result.failure(str(e))

    def _validate_matching_inputs(
        self,
        psd_data: Dict[str, Any],
        aepx_data: Dict[str, Any]
    ) -> Result[bool]:
        """
        Validate inputs for content matching.

        Args:
            psd_data: PSD data to validate
            aepx_data: AEPX data to validate

        Returns:
            Result with True if valid, or error message
        """
        # Validate PSD data
        if not isinstance(psd_data, dict):
            return Result.failure("Invalid PSD data: expected dict")

        if 'layers' not in psd_data:
            return Result.failure("PSD data missing 'layers' field")

        if not isinstance(psd_data['layers'], list):
            return Result.failure("PSD 'layers' field must be a list")

        # Validate AEPX data
        if not isinstance(aepx_data, dict):
            return Result.failure("Invalid AEPX data: expected dict")

        if 'placeholders' not in aepx_data:
            return Result.failure("AEPX data missing 'placeholders' field")

        if not isinstance(aepx_data['placeholders'], list):
            return Result.failure("AEPX 'placeholders' field must be a list")

        # Check if there's content to match
        layer_count = len(psd_data['layers'])
        placeholder_count = len(aepx_data['placeholders'])

        if layer_count == 0:
            self.log_info("Warning: No layers in PSD data")

        if placeholder_count == 0:
            self.log_info("Warning: No placeholders in AEPX data")

        self.log_info(
            f"Validation passed: {layer_count} PSD layers, "
            f"{placeholder_count} AEPX placeholders"
        )

        return Result.success(True)
