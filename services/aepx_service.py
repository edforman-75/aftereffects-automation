"""
AEPX Service

Handles all AEPX-related operations including parsing, validation,
placeholder extraction, and composition management.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from services.base_service import BaseService, Result
from core.exceptions import (
    AEPXParsingError,
    raise_file_not_found,
    raise_parsing_error
)

# Import existing modules (these will remain unchanged)
from modules.phase2 import aepx_parser


class AEPXService(BaseService):
    """
    Service for handling AEPX file operations.

    This service wraps the existing aepx_parser module and provides
    a clean API with proper error handling and logging.
    """

    def parse_aepx(self, aepx_path: str) -> Result[Dict]:
        """
        Parse an AEPX file and extract its structure.

        Args:
            aepx_path: Path to the AEPX file

        Returns:
            Result containing AEPX data dict or error message
        """
        self.log_info(f"Parsing AEPX file: {aepx_path}")

        # Validate file exists
        if not os.path.exists(aepx_path):
            self.log_error(f"AEPX file not found: {aepx_path}")
            return Result.failure(f"AEPX file not found: {aepx_path}")

        # Validate file extension
        if not aepx_path.lower().endswith('.aepx'):
            self.log_error(f"Invalid file extension: {aepx_path}")
            return Result.failure(f"File must have .aepx extension")

        try:
            # Call existing parser module
            aepx_data = aepx_parser.parse_aepx(aepx_path)

            # Validate parsed data has expected structure
            if not isinstance(aepx_data, dict):
                return Result.failure("Invalid AEPX data structure returned")

            if 'compositions' not in aepx_data:
                return Result.failure("AEPX data missing 'compositions' field")

            comp_count = len(aepx_data.get('compositions', []))
            placeholder_count = len(aepx_data.get('placeholders', []))
            self.log_info(
                f"Successfully parsed AEPX with {comp_count} compositions "
                f"and {placeholder_count} placeholders"
            )

            return Result.success(aepx_data)

        except FileNotFoundError as e:
            self.log_error(f"AEPX file not found: {aepx_path}", exc=e)
            return Result.failure(str(e))
        except ValueError as e:
            self.log_error(f"Invalid AEPX file: {aepx_path}", exc=e)
            return Result.failure(str(e))
        except Exception as e:
            self.log_error(f"Failed to parse AEPX: {aepx_path}", exc=e)
            return Result.failure(f"AEPX parsing failed: {str(e)}")

    def get_placeholders(self, aepx_data: Dict) -> Result[List[Dict]]:
        """
        Extract placeholder layers from parsed AEPX data.

        Args:
            aepx_data: Parsed AEPX data dictionary

        Returns:
            Result containing list of placeholder dicts or error
        """
        self.log_info("Extracting placeholders from AEPX data")

        try:
            # Validate input
            if not isinstance(aepx_data, dict):
                return Result.failure("Invalid AEPX data: expected dict")

            placeholders = aepx_data.get('placeholders', [])

            if not isinstance(placeholders, list):
                return Result.failure("Invalid placeholders field: expected list")

            self.log_info(f"Found {len(placeholders)} placeholders")
            return Result.success(placeholders)

        except Exception as e:
            self.log_error("Placeholder extraction failed", exc=e)
            return Result.failure(f"Placeholder extraction failed: {str(e)}")

    def get_text_placeholders(self, aepx_data: Dict) -> Result[List[Dict]]:
        """
        Get all text placeholders from the AEPX.

        Args:
            aepx_data: Parsed AEPX data

        Returns:
            Result containing list of text placeholder dicts or error
        """
        self.log_info("Extracting text placeholders from AEPX")

        try:
            placeholders = aepx_data.get('placeholders', [])
            text_placeholders = [
                ph for ph in placeholders
                if ph.get('type') == 'text'
            ]

            self.log_info(f"Found {len(text_placeholders)} text placeholders")
            return Result.success(text_placeholders)

        except Exception as e:
            self.log_error("Failed to extract text placeholders", exc=e)
            return Result.failure(str(e))

    def get_image_placeholders(self, aepx_data: Dict) -> Result[List[Dict]]:
        """
        Get all image placeholders from the AEPX.

        Args:
            aepx_data: Parsed AEPX data

        Returns:
            Result containing list of image placeholder dicts or error
        """
        self.log_info("Extracting image placeholders from AEPX")

        try:
            placeholders = aepx_data.get('placeholders', [])
            image_placeholders = [
                ph for ph in placeholders
                if ph.get('type') == 'image'
            ]

            self.log_info(f"Found {len(image_placeholders)} image placeholders")
            return Result.success(image_placeholders)

        except Exception as e:
            self.log_error("Failed to extract image placeholders", exc=e)
            return Result.failure(str(e))

    def get_compositions(self, aepx_data: Dict) -> Result[List[Dict]]:
        """
        Get all compositions from the AEPX.

        Args:
            aepx_data: Parsed AEPX data

        Returns:
            Result containing list of composition dicts or error
        """
        try:
            compositions = aepx_data.get('compositions', [])
            return Result.success(compositions)
        except Exception as e:
            self.log_error("Failed to get compositions", exc=e)
            return Result.failure(str(e))

    def get_main_composition(self, aepx_data: Dict) -> Result[Dict]:
        """
        Get the main composition from the AEPX.

        Args:
            aepx_data: Parsed AEPX data

        Returns:
            Result containing main composition dict or error
        """
        try:
            compositions = aepx_data.get('compositions', [])
            if not compositions:
                return Result.failure("No compositions found in AEPX")

            comp_name = aepx_data.get('composition_name')

            # Find composition by name
            for comp in compositions:
                if comp.get('name') == comp_name:
                    return Result.success(comp)

            # Fallback to first composition
            self.log_info("Main composition not found by name, using first composition")
            return Result.success(compositions[0])

        except Exception as e:
            self.log_error("Failed to get main composition", exc=e)
            return Result.failure(str(e))

    def validate_aepx_file(self, aepx_path: str, max_size_mb: int = 10) -> Result[bool]:
        """
        Validate an AEPX file before processing.

        Args:
            aepx_path: Path to AEPX file
            max_size_mb: Maximum allowed file size in MB

        Returns:
            Result containing True if valid, or error message
        """
        self.log_info(f"Validating AEPX file: {aepx_path}")

        # Check existence
        if not os.path.exists(aepx_path):
            return Result.failure(f"File not found: {aepx_path}")

        # Check extension
        if not aepx_path.lower().endswith('.aepx'):
            return Result.failure("File must have .aepx extension")

        # Check file size
        file_size = os.path.getsize(aepx_path)
        size_mb = file_size / (1024 * 1024)

        if size_mb > max_size_mb:
            return Result.failure(
                f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"
            )

        # Check if file is readable and appears to be XML
        try:
            with open(aepx_path, 'r', encoding='utf-8') as f:
                # Read first few bytes to verify it's XML
                header = f.read(100)
                if '<?xml' not in header and '<AfterEffectsProject' not in header:
                    return Result.failure("Invalid AEPX file format (not XML)")
        except Exception as e:
            return Result.failure(f"Cannot read file: {str(e)}")

        self.log_info(f"AEPX file validation passed ({size_mb:.1f}MB)")
        return Result.success(True)

    def get_placeholder_count(self, aepx_data: Dict) -> Result[int]:
        """
        Get the number of placeholders in the AEPX.

        Args:
            aepx_data: Parsed AEPX data

        Returns:
            Result containing placeholder count or error
        """
        try:
            placeholders = aepx_data.get('placeholders', [])
            count = len(placeholders)
            return Result.success(count)
        except Exception as e:
            self.log_error("Failed to get placeholder count", exc=e)
            return Result.failure(str(e))
