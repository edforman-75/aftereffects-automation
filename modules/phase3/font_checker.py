"""
Module 3.3: Font Checker

Checks if fonts used in PSD are commonly available in After Effects.
"""

from typing import Dict, List, Any, Set


# Common fonts typically available on most systems
COMMON_FONTS = {
    'arial', 'helvetica', 'times', 'times new roman', 'courier', 'courier new',
    'georgia', 'verdana', 'trebuchet', 'impact', 'comic sans', 'lucida',
    'palatino', 'garamond', 'bookman', 'avant garde', 'myriad', 'minion'
}

# Adobe fonts often available with Creative Cloud
ADOBE_FONTS = {
    'myriad pro', 'minion pro', 'adobe caslon', 'adobe garamond',
    'proxima nova', 'source sans', 'source serif', 'neue haas grotesk',
    'futura', 'din', 'freight', 'acumin'
}


def check_fonts(psd_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check fonts used in PSD and assess availability.

    Args:
        psd_data: Parsed PSD data from Module 1.1

    Returns:
        Dictionary with:
            - fonts_used: Set of font names found
            - common_fonts: List of fonts likely available
            - uncommon_fonts: List of fonts that may be missing
            - warnings: List of warning messages
    """
    fonts_used = set()
    font_details = []
    text_layers_found = 0

    # Extract fonts from text layers
    for layer in psd_data['layers']:
        if layer['type'] == 'text' and 'text' in layer:
            text_layers_found += 1

            # Check for font or font_name (supports both psd-tools and Photoshop data)
            if 'font' in layer['text']:
                font_name = layer['text']['font']
                fonts_used.add(font_name)
                font_details.append({
                    'layer': layer['name'],
                    'font': font_name,
                    'size': layer['text'].get('font_size', 'unknown')
                })
            elif 'font_name' in layer['text']:
                font_name = layer['text']['font_name']
                fonts_used.add(font_name)
                font_details.append({
                    'layer': layer['name'],
                    'font': font_name,
                    'size': layer['text'].get('font_size', 'unknown')
                })
            # Fallback to font_index
            elif 'font_index' in layer['text']:
                font_index = layer['text']['font_index']
                font_details.append({
                    'layer': layer['name'],
                    'font': f'Font Index {font_index}',
                    'size': layer['text'].get('font_size', 'unknown')
                })

    # Categorize fonts
    common_fonts = []
    adobe_fonts_found = []
    uncommon_fonts = []

    for font in fonts_used:
        font_lower = font.lower()

        # Check if it's a common system font
        is_common = any(common in font_lower for common in COMMON_FONTS)
        is_adobe = any(adobe in font_lower for adobe in ADOBE_FONTS)

        if is_common:
            common_fonts.append(font)
        elif is_adobe:
            adobe_fonts_found.append(font)
        else:
            uncommon_fonts.append(font)

    # Generate warnings
    warnings = []

    # If no font names extracted, warn user to check manually
    if text_layers_found > 0 and not fonts_used:
        warnings.append({
            'severity': 'info',
            'type': 'FONT_CHECK_LIMITED',
            'message': f"Found {text_layers_found} text layer(s) but could not extract font names",
            'fonts': [],
            'suggestion': 'Manually verify fonts are available in After Effects before rendering'
        })

    if uncommon_fonts:
        warnings.append({
            'severity': 'warning',
            'type': 'UNCOMMON_FONTS',
            'message': f"Found {len(uncommon_fonts)} font(s) that may not be available in After Effects",
            'fonts': uncommon_fonts,
            'suggestion': 'Ensure these fonts are installed on the system running After Effects'
        })

    if adobe_fonts_found:
        warnings.append({
            'severity': 'info',
            'type': 'ADOBE_FONTS',
            'message': f"Found {len(adobe_fonts_found)} Adobe font(s) (usually available with Creative Cloud)",
            'fonts': adobe_fonts_found,
            'suggestion': 'Verify Creative Cloud fonts are synced'
        })

    return {
        'fonts_used': sorted(list(fonts_used)),
        'font_details': font_details,
        'common_fonts': common_fonts,
        'adobe_fonts': adobe_fonts_found,
        'uncommon_fonts': uncommon_fonts,
        'warnings': warnings,
        'summary': {
            'total': len(fonts_used),
            'common': len(common_fonts),
            'adobe': len(adobe_fonts_found),
            'uncommon': len(uncommon_fonts)
        }
    }


def get_font_substitution_suggestions(font_name: str) -> List[str]:
    """
    Suggest alternative fonts if a font is not available.

    Args:
        font_name: Name of the font to find alternatives for

    Returns:
        List of suggested alternative font names
    """
    font_lower = font_name.lower()

    # Sans-serif fonts
    if any(word in font_lower for word in ['helvetica', 'arial', 'swiss', 'gothic']):
        return ['Arial', 'Helvetica', 'Helvetica Neue', 'Verdana']

    # Serif fonts
    if any(word in font_lower for word in ['times', 'garamond', 'baskerville', 'georgia']):
        return ['Times New Roman', 'Georgia', 'Palatino']

    # Monospace fonts
    if any(word in font_lower for word in ['courier', 'mono', 'console']):
        return ['Courier New', 'Consolas', 'Monaco']

    # Default fallback
    return ['Arial', 'Helvetica', 'Times New Roman']
