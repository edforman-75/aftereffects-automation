"""
PSD Service

Handles all PSD-related operations including parsing, validation,
font extraction, and preview generation.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from services.base_service import BaseService, Result
from core.exceptions import (
    PSDParsingError,
    PSDLayerError,
    PSDFontError,
    raise_file_not_found,
    raise_parsing_error
)

# Import existing modules (these will remain unchanged)
from modules.phase1 import psd_parser


class PSDService(BaseService):
    """
    Service for handling PSD file operations.

    This service wraps the existing psd_parser module and provides
    a clean API with proper error handling and logging.
    """

    def parse_psd(self, psd_path: str) -> Result[Dict]:
        """
        Parse a PSD file and extract its structure.

        Args:
            psd_path: Path to the PSD file

        Returns:
            Result containing PSD data dict or error message
        """
        self.log_info(f"Parsing PSD file: {psd_path}")

        # Validate file exists
        if not os.path.exists(psd_path):
            self.log_error(f"PSD file not found: {psd_path}")
            return Result.failure(f"PSD file not found: {psd_path}")

        # Validate file extension
        if not psd_path.lower().endswith('.psd'):
            self.log_error(f"Invalid file extension: {psd_path}")
            return Result.failure(f"File must have .psd extension")

        try:
            # Call existing parser module
            psd_data = psd_parser.parse_psd(psd_path)

            # Validate parsed data has expected structure
            if not isinstance(psd_data, dict):
                return Result.failure("Invalid PSD data structure returned")

            if 'layers' not in psd_data:
                return Result.failure("PSD data missing 'layers' field")

            layer_count = len(psd_data.get('layers', []))
            self.log_info(f"Successfully parsed PSD with {layer_count} layers")

            return Result.success(psd_data)

        except Exception as e:
            self.log_error(f"Failed to parse PSD: {psd_path}", exc=e)
            return Result.failure(f"PSD parsing failed: {str(e)}")

    def extract_fonts(self, psd_data: Dict) -> Result[List[str]]:
        """
        Extract list of fonts used in the PSD.

        Args:
            psd_data: Parsed PSD data dictionary

        Returns:
            Result containing list of font names or error
        """
        self.log_info("Extracting fonts from PSD data")

        try:
            # Validate input
            if not isinstance(psd_data, dict):
                return Result.failure("Invalid PSD data: expected dict")

            if 'layers' not in psd_data:
                return Result.failure("PSD data missing 'layers' field")

            # Extract fonts from text layers
            fonts = set()
            layers = psd_data.get('layers', [])

            for layer in layers:
                if layer.get('type') == 'text':
                    font_name = layer.get('text', {}).get('font')
                    if font_name:
                        fonts.add(font_name)

            font_list = sorted(list(fonts))
            self.log_info(f"Extracted {len(font_list)} unique fonts")

            return Result.success(font_list)

        except Exception as e:
            self.log_error("Font extraction failed", exc=e)
            return Result.failure(f"Font extraction failed: {str(e)}")

    def get_layer_count(self, psd_data: Dict) -> Result[int]:
        """
        Get the number of layers in the PSD.

        Args:
            psd_data: Parsed PSD data

        Returns:
            Result containing layer count or error
        """
        try:
            layers = psd_data.get('layers', [])
            count = len(layers)
            return Result.success(count)
        except Exception as e:
            self.log_error("Failed to get layer count", exc=e)
            return Result.failure(str(e))

    def get_text_layers(self, psd_data: Dict) -> Result[List[Dict]]:
        """
        Get all text layers from the PSD.

        Args:
            psd_data: Parsed PSD data

        Returns:
            Result containing list of text layer dicts or error
        """
        self.log_info("Extracting text layers from PSD")

        try:
            layers = psd_data.get('layers', [])
            text_layers = [
                layer for layer in layers
                if layer.get('type') == 'text'
            ]

            self.log_info(f"Found {len(text_layers)} text layers")
            return Result.success(text_layers)

        except Exception as e:
            self.log_error("Failed to extract text layers", exc=e)
            return Result.failure(str(e))

    def get_image_layers(self, psd_data: Dict) -> Result[List[Dict]]:
        """
        Get all image layers from the PSD.

        Includes both 'image' and 'smartobject' type layers.

        Args:
            psd_data: Parsed PSD data

        Returns:
            Result containing list of image layer dicts or error
        """
        self.log_info("Extracting image layers from PSD")

        try:
            layers = psd_data.get('layers', [])
            image_layers = [
                layer for layer in layers
                if layer.get('type') in ('image', 'smartobject')
            ]

            self.log_info(f"Found {len(image_layers)} image layers")
            return Result.success(image_layers)

        except Exception as e:
            self.log_error("Failed to extract image layers", exc=e)
            return Result.failure(str(e))

    def validate_psd_file(self, psd_path: str, max_size_mb: int = 50) -> Result[bool]:
        """
        Validate a PSD file before processing.

        Args:
            psd_path: Path to PSD file
            max_size_mb: Maximum allowed file size in MB

        Returns:
            Result containing True if valid, or error message
        """
        self.log_info(f"Validating PSD file: {psd_path}")

        # Check existence
        if not os.path.exists(psd_path):
            return Result.failure(f"File not found: {psd_path}")

        # Check extension
        if not psd_path.lower().endswith('.psd'):
            return Result.failure("File must have .psd extension")

        # Check file size
        file_size = os.path.getsize(psd_path)
        size_mb = file_size / (1024 * 1024)

        if size_mb > max_size_mb:
            return Result.failure(
                f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"
            )

        # Check if file is readable
        try:
            with open(psd_path, 'rb') as f:
                # Read first few bytes to verify it's a PSD
                header = f.read(4)
                if header != b'8BPS':
                    return Result.failure("Invalid PSD file signature")
        except Exception as e:
            return Result.failure(f"Cannot read file: {str(e)}")

        self.log_info(f"PSD file validation passed ({size_mb:.1f}MB)")
        return Result.success(True)
