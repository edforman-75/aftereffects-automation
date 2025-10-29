"""
Font Service

Checks system fonts and validates PSD font requirements.
"""

import os
import glob
import shutil
from pathlib import Path
from typing import List, Dict, Set
from services.base_service import BaseService, Result


class FontService(BaseService):
    """Service for font detection and validation."""

    def _normalize_font_name(self, name: str) -> str:
        """
        Normalize font name for comparison (remove spaces, underscores, hyphens, lowercase).

        This allows matching:
        - RUSHFLOW → RUSH FLOW
        - RUSHFLOW → RUSH_FLOW
        - rushflow → RUSH FLOW

        Args:
            name: Font name to normalize

        Returns:
            Normalized font name (no spaces/underscores/hyphens, lowercase)
        """
        return name.replace(' ', '').replace('_', '').replace('-', '').lower()

    def get_system_fonts(self) -> Result[List[str]]:
        """
        Get list of installed fonts on macOS.

        Searches:
        - /Library/Fonts (system fonts)
        - ~/Library/Fonts (user fonts)
        - /System/Library/Fonts (macOS fonts)
        - /System/Library/Fonts/Supplemental (additional macOS fonts)

        Returns:
            Result containing list of font family names
        """
        self.log_info("Scanning system fonts...")

        font_paths = [
            '/Library/Fonts',
            os.path.expanduser('~/Library/Fonts'),
            '/System/Library/Fonts',
            '/System/Library/Fonts/Supplemental'
        ]

        installed_fonts = set()

        for font_dir in font_paths:
            if not os.path.exists(font_dir):
                self.log_debug(f"Font directory not found: {font_dir}")
                continue

            # Find all font files (.ttf, .otf, .ttc, .dfont)
            for ext in ['*.ttf', '*.otf', '*.ttc', '*.dfont']:
                pattern = os.path.join(font_dir, '**', ext)
                for font_file in glob.glob(pattern, recursive=True):
                    # Extract font family name from filename
                    font_name = Path(font_file).stem

                    # Remove common suffixes to get base font name
                    for suffix in ['-Regular', '-Bold', '-Italic', '-Light', '-Medium',
                                   '-SemiBold', '-Black', '-Thin', '-Heavy',
                                   'Regular', 'Bold', 'Italic', 'Light', 'Medium']:
                        if font_name.endswith(suffix):
                            font_name = font_name[:-len(suffix)]

                    # Clean up
                    font_name = font_name.strip().strip('-').strip()

                    if font_name:
                        installed_fonts.add(font_name)

        font_list = sorted(list(installed_fonts))
        self.log_info(f"Found {len(font_list)} installed fonts")

        return Result.success(font_list)

    def check_required_fonts(self, required_fonts: List[str]) -> Result[Dict[str, bool]]:
        """
        Check if required fonts are installed.

        Args:
            required_fonts: List of font names from PSD

        Returns:
            Result containing dict mapping font name to installed status
            Example: {"RUSHFLOW": True, "Arial": True, "CustomFont": False}
        """
        if not required_fonts:
            self.log_info("No fonts to check")
            return Result.success({})

        self.log_info(f"Checking {len(required_fonts)} required fonts...")

        system_fonts_result = self.get_system_fonts()
        if not system_fonts_result.is_success():
            return Result.failure("Could not retrieve system fonts")

        system_fonts = system_fonts_result.get_data()

        # Create normalized lookup for fuzzy matching
        # Maps normalized name to original name
        normalized_fonts = {
            self._normalize_font_name(f): f for f in system_fonts
        }

        font_status = {}
        for required_font in required_fonts:
            normalized_required = self._normalize_font_name(required_font)

            # Try exact normalized match first (handles spaces, underscores, case)
            if normalized_required in normalized_fonts:
                matched_font = normalized_fonts[normalized_required]
                font_status[required_font] = True
                self.log_info(f"Font matched: '{required_font}' → '{matched_font}'")
            else:
                # Try partial fuzzy match
                is_installed = False
                for normalized_sys, original_sys in normalized_fonts.items():
                    # Check if one is substring of the other (fuzzy partial match)
                    if (normalized_required in normalized_sys or
                        normalized_sys in normalized_required) and len(normalized_sys) > 3:
                        font_status[required_font] = True
                        is_installed = True
                        self.log_info(f"Font fuzzy matched: '{required_font}' → '{original_sys}'")
                        break

                if not is_installed:
                    font_status[required_font] = False
                    self.log_debug(f"Font NOT found: {required_font}")

        installed_count = sum(font_status.values())
        total_count = len(required_fonts)
        self.log_info(f"Font check complete: {installed_count}/{total_count} fonts installed")

        return Result.success(font_status)

    def extract_fonts_from_psd_data(self, psd_data: Dict) -> Result[List[str]]:
        """
        Extract unique font names from parsed PSD data.

        Args:
            psd_data: Parsed PSD data dictionary with layers

        Returns:
            Result containing list of unique font names
        """
        self.log_info("Extracting fonts from PSD data...")

        fonts = set()

        def extract_from_layers(layers):
            """Recursively extract fonts from layers."""
            for layer in layers:
                # Check if layer has text information
                if layer.get('type') == 'text' and 'text' in layer:
                    text_data = layer['text']

                    # Extract font name
                    if 'font' in text_data:
                        font_name = text_data['font']
                        if font_name:
                            fonts.add(font_name)
                            self.log_debug(f"Found font: {font_name} in layer '{layer['name']}'")

                # Recursively process child layers
                if 'children' in layer and layer['children']:
                    extract_from_layers(layer['children'])

        # Process all layers
        if 'layers' in psd_data:
            extract_from_layers(psd_data['layers'])

        font_list = sorted(list(fonts))
        self.log_info(f"Extracted {len(font_list)} unique fonts from PSD")

        return Result.success(font_list)

    def get_font_summary(self, font_status: Dict[str, bool]) -> Dict[str, any]:
        """
        Get summary statistics for font status.

        Args:
            font_status: Dict mapping font names to installed status

        Returns:
            Dict with summary stats:
            {
                "total": 5,
                "installed": 3,
                "missing": 2,
                "percentage": 60.0,
                "all_installed": False
            }
        """
        total = len(font_status)
        installed = sum(font_status.values())
        missing = total - installed
        percentage = (installed / total * 100) if total > 0 else 100.0

        return {
            "total": total,
            "installed": installed,
            "missing": missing,
            "percentage": round(percentage, 1),
            "all_installed": missing == 0
        }

    def install_font(self, font_file_path: str, font_name: str) -> Result[str]:
        """
        Install font to ~/Library/Fonts (no admin required).

        Args:
            font_file_path: Path to font file to install
            font_name: Name of the font

        Returns:
            Result containing success message or error
        """
        self.log_info(f"Installing font: {font_name}")

        # Validate file exists
        if not os.path.exists(font_file_path):
            return Result.failure(f"Font file not found: {font_file_path}")

        # Validate file extension
        valid_extensions = ['.ttf', '.otf', '.ttc', '.dfont']
        file_ext = Path(font_file_path).suffix.lower()
        if file_ext not in valid_extensions:
            return Result.failure(f"Invalid font file type: {file_ext}")

        # Target directory (user fonts, no admin required)
        target_dir = os.path.expanduser('~/Library/Fonts')
        os.makedirs(target_dir, exist_ok=True)

        # Target path - use font_name parameter as the target filename
        # font_name should be the original filename (e.g., "RUSH FLOW.ttf")
        if not font_name.endswith(('.ttf', '.otf', '.ttc', '.dfont')):
            # font_name doesn't have extension, add it from source file
            file_ext = Path(font_file_path).suffix
            target_filename = f"{font_name}{file_ext}"
        else:
            # font_name already has extension
            target_filename = font_name

        target_path = os.path.join(target_dir, target_filename)

        # Check if already exists
        if os.path.exists(target_path):
            self.log_info(f"Font already installed: {font_name}")
            return Result.success(f"Font '{font_name}' is already installed")

        # Copy font file
        try:
            shutil.copy2(font_file_path, target_path)
            self.log_info(f"Font installed successfully: {target_path}")
            return Result.success(f"Font '{font_name}' installed successfully")
        except Exception as e:
            self.log_error(f"Failed to install font: {font_name}", exc=e)
            return Result.failure(f"Failed to install font: {str(e)}")

    def copy_existing_font(self, font_name: str) -> Result[str]:
        """
        Copy an existing system font to ~/Library/Fonts for AE access.

        Args:
            font_name: Name of the font to copy

        Returns:
            Result containing success message or error
        """
        self.log_info(f"Copying existing font: {font_name}")

        # Get system fonts
        system_fonts_result = self.get_system_fonts()
        if not system_fonts_result.is_success():
            return Result.failure("Could not retrieve system fonts")

        system_fonts = system_fonts_result.get_data()

        # Check if font exists
        font_found = False
        for sf in system_fonts:
            if font_name.lower() in sf.lower() or sf.lower() in font_name.lower():
                font_found = True
                break

        if not font_found:
            return Result.failure(f"Font '{font_name}' not found in system")

        # Find font file path
        font_file_path = None
        for font_dir in ['/Library/Fonts', os.path.expanduser('~/Library/Fonts'),
                        '/System/Library/Fonts', '/System/Library/Fonts/Supplemental']:
            if not os.path.exists(font_dir):
                continue

            for ext in ['*.ttf', '*.otf', '*.ttc', '*.dfont']:
                pattern = os.path.join(font_dir, '**', ext)
                for font_file in glob.glob(pattern, recursive=True):
                    file_font_name = Path(font_file).stem
                    if font_name.lower() in file_font_name.lower() or file_font_name.lower() in font_name.lower():
                        font_file_path = font_file
                        break
                if font_file_path:
                    break
            if font_file_path:
                break

        if not font_file_path:
            return Result.failure(f"Could not locate font file for '{font_name}'")

        # Check if already in user fonts
        target_dir = os.path.expanduser('~/Library/Fonts')
        filename = Path(font_file_path).name
        target_path = os.path.join(target_dir, filename)

        if os.path.exists(target_path):
            self.log_info(f"Font already in user fonts: {font_name}")
            return Result.success(f"Font '{font_name}' is already accessible to After Effects")

        # Copy to user fonts
        try:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(font_file_path, target_path)
            self.log_info(f"Font copied successfully: {target_path}")
            return Result.success(f"Font '{font_name}' copied successfully")
        except Exception as e:
            self.log_error(f"Failed to copy font: {font_name}", exc=e)
            return Result.failure(f"Failed to copy font: {str(e)}")


# Test function
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    font_service = FontService(logging.getLogger('font_service'))

    # Test 1: Get system fonts
    print("Test 1: Getting system fonts...")
    result = font_service.get_system_fonts()
    if result.is_success():
        fonts = result.get_data()
        print(f"✅ Found {len(fonts)} fonts")
        print(f"Sample fonts: {fonts[:10]}")
    else:
        print(f"❌ Error: {result.get_error()}")

    # Test 2: Check specific fonts
    print("\nTest 2: Checking specific fonts...")
    test_fonts = ['Arial', 'Helvetica', 'RUSHFLOW', 'NonExistentFont']
    result = font_service.check_required_fonts(test_fonts)
    if result.is_success():
        status = result.get_data()
        print("Font status:")
        for font, installed in status.items():
            status_icon = "✅" if installed else "❌"
            print(f"  {status_icon} {font}: {'Installed' if installed else 'Not Found'}")

        # Get summary
        summary = font_service.get_font_summary(status)
        print(f"\nSummary: {summary['installed']}/{summary['total']} installed ({summary['percentage']}%)")
    else:
        print(f"❌ Error: {result.get_error()}")
