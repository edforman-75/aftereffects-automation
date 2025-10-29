"""
Module 1.2: Font Metrics Calculator

Calculate actual rendered text width using font files for accurate overflow detection.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

# Font cache for performance
_FONT_CACHE: Dict[str, TTFont] = {}


def calculate_text_width(text: str, font_name: str, font_size: float,
                         font_path: Optional[str] = None) -> float:
    """
    Calculate actual rendered text width in pixels.

    Args:
        text: Text string to measure
        font_name: Name of the font
        font_size: Font size in points
        font_path: Optional path to font file. If None, will search system fonts.

    Returns:
        Width in pixels as float

    Example:
        >>> width = calculate_text_width("HELLO", "Arial", 48)
        >>> print(f"Text width: {width}px")
    """
    try:
        # Find font file if path not provided
        if not font_path:
            font_path = find_system_font(font_name)

        # If font file found, use accurate calculation
        if font_path and os.path.exists(font_path):
            font = load_font(font_path)
            if font:
                return get_text_width_from_font(text, font, font_size)

        # Fallback to estimation
        return estimate_width_without_font(text, font_size)

    except Exception as e:
        # On any error, fall back to estimation
        return estimate_width_without_font(text, font_size)


def load_font(font_path: str) -> Optional[TTFont]:
    """
    Load font file and cache it.

    Args:
        font_path: Path to TTF or OTF file

    Returns:
        TTFont object or None if loading fails
    """
    try:
        # Check cache first
        if font_path in _FONT_CACHE:
            return _FONT_CACHE[font_path]

        # Load font
        font = TTFont(font_path)

        # Verify required tables exist
        required_tables = ['head', 'hhea', 'hmtx', 'cmap']
        for table in required_tables:
            if table not in font:
                return None

        # Cache for future use
        _FONT_CACHE[font_path] = font
        return font

    except Exception:
        return None


def get_text_width_from_font(text: str, font: TTFont, font_size: float) -> float:
    """
    Calculate text width using actual font metrics.

    Args:
        text: Text string to measure
        font: Loaded TTFont object
        font_size: Font size in points

    Returns:
        Width in pixels
    """
    try:
        # Get units per em (typically 1000 or 2048)
        units_per_em = font['head'].unitsPerEm

        # Get character map
        cmap = font.getBestCmap()
        if not cmap:
            return estimate_width_without_font(text, font_size)

        # Get horizontal metrics table
        hmtx = font['hmtx']

        # Calculate total width
        total_width = 0.0

        for char in text:
            # Get glyph name for character
            glyph_name = cmap.get(ord(char))

            if not glyph_name:
                # Character not in font, estimate
                total_width += font_size * 0.6
                continue

            # Get advance width for this glyph
            if glyph_name in hmtx.metrics:
                advance_width, lsb = hmtx.metrics[glyph_name]
                # Convert from font units to pixels
                total_width += (advance_width / units_per_em) * font_size
            else:
                # Glyph not in metrics, estimate
                total_width += font_size * 0.6

        # Apply kerning if available
        if 'kern' in font:
            total_width += apply_kerning(text, font, font_size, cmap)

        return total_width

    except Exception:
        return estimate_width_without_font(text, font_size)


def apply_kerning(text: str, font: TTFont, font_size: float, cmap: dict) -> float:
    """
    Apply kerning adjustments to text width.

    Args:
        text: Text string
        font: Loaded font object
        font_size: Font size in points
        cmap: Character to glyph name mapping

    Returns:
        Additional width adjustment from kerning (can be negative)
    """
    try:
        if 'kern' not in font or len(text) < 2:
            return 0.0

        kern_table = font['kern']
        units_per_em = font['head'].unitsPerEm
        total_kerning = 0.0

        # Check each pair of characters
        for i in range(len(text) - 1):
            char1 = text[i]
            char2 = text[i + 1]

            glyph1 = cmap.get(ord(char1))
            glyph2 = cmap.get(ord(char2))

            if not glyph1 or not glyph2:
                continue

            # Look up kerning value for this pair
            for table in kern_table.kernTables:
                if hasattr(table, 'kernTable'):
                    pair = (glyph1, glyph2)
                    if pair in table.kernTable:
                        kern_value = table.kernTable[pair]
                        total_kerning += (kern_value / units_per_em) * font_size

        return total_kerning

    except Exception:
        return 0.0


def find_system_font(font_name: str) -> Optional[str]:
    """
    Search for font file on system.

    Args:
        font_name: Name of font to find

    Returns:
        Path to font file or None if not found

    Search locations (in order):
        1. fonts/ directory (uploaded fonts)
        2. /Library/Fonts (system fonts)
        3. ~/Library/Fonts (user fonts)
        4. /System/Library/Fonts (OS fonts)
    """
    # Normalize font name for comparison
    font_name_lower = font_name.lower().replace(' ', '')

    # Search directories in order
    search_dirs = [
        Path('fonts'),  # Uploaded fonts
        Path('/Library/Fonts'),
        Path.home() / 'Library' / 'Fonts',
        Path('/System/Library/Fonts'),
    ]

    # Common font file extensions
    extensions = ['.ttf', '.otf', '.TTF', '.OTF']

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        try:
            # Search for font files
            for font_file in search_dir.rglob('*'):
                if not font_file.is_file():
                    continue

                # Check if extension matches
                if font_file.suffix not in extensions:
                    continue

                # Check if filename matches
                file_name_lower = font_file.stem.lower().replace(' ', '').replace('-', '')

                # Try exact match first
                if font_name_lower == file_name_lower:
                    return str(font_file)

                # Try partial match (e.g., "Arial Bold" matches "ArialBold.ttf")
                if font_name_lower in file_name_lower or file_name_lower in font_name_lower:
                    return str(font_file)

        except (PermissionError, OSError):
            # Skip directories we can't read
            continue

    return None


def estimate_width_without_font(text: str, font_size: float) -> float:
    """
    Estimate text width when font file is not available.

    Args:
        text: Text string
        font_size: Font size in points

    Returns:
        Estimated width in pixels

    This uses a simple heuristic:
    - Average character width ≈ 0.6 * font_size
    - This works reasonably well for most fonts
    """
    # Character count * average width per character
    # 0.6 is a reasonable approximation for most fonts
    return len(text) * font_size * 0.6


def get_font_info(font_path: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a font file.

    Args:
        font_path: Path to font file

    Returns:
        Dictionary with font info or None if can't load

    Example:
        {
            'family': 'Arial',
            'style': 'Bold',
            'units_per_em': 2048,
            'has_kerning': True
        }
    """
    try:
        font = load_font(font_path)
        if not font:
            return None

        info = {
            'units_per_em': font['head'].unitsPerEm,
            'has_kerning': 'kern' in font,
        }

        # Try to get font name
        if 'name' in font:
            name_table = font['name']
            for record in name_table.names:
                # Font family name
                if record.nameID == 1:
                    info['family'] = record.toUnicode()
                # Font style
                elif record.nameID == 2:
                    info['style'] = record.toUnicode()

        return info

    except Exception:
        return None


def clear_font_cache():
    """Clear the font cache to free memory."""
    global _FONT_CACHE
    _FONT_CACHE.clear()
