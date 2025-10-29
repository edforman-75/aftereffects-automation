"""
Module 3.2: Conflict Detection Configuration

Manages configuration for conflict detection thresholds.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


# Default configuration
DEFAULT_CONFLICT_CONFIG = {
    "text_length_warning": 50,       # chars - warn if text is longer
    "text_length_critical": 100,     # chars - critical if text is longer
    "aspect_ratio_tolerance": 0.2,   # 20% difference is acceptable
    "upscale_warning_factor": 2.0,   # warn if upscaling more than 2x
    "downscale_info_factor": 0.5,    # info if downscaling more than 50%
    "font_size_large": 72,           # pt - warn if font is larger
    "font_size_small": 12,           # pt - info if font is smaller
    "dimension_tolerance": 0.1       # 10% aspect ratio difference for dimension check
}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load conflict detection configuration.
    
    Args:
        config_path: Path to JSON config file, or None for defaults
    
    Returns:
        Configuration dictionary with validated values
    """
    if config_path is None:
        return DEFAULT_CONFLICT_CONFIG.copy()
    
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r') as f:
        config = json.load(f)
    
    # Validate and merge with defaults
    validated = DEFAULT_CONFLICT_CONFIG.copy()
    validated.update(config)
    
    # Validate values are reasonable
    if validated['text_length_warning'] < 10 or validated['text_length_warning'] > 200:
        raise ValueError(f"text_length_warning must be between 10 and 200")
    
    if validated['text_length_critical'] <= validated['text_length_warning']:
        raise ValueError(f"text_length_critical must be > text_length_warning")
    
    if validated['aspect_ratio_tolerance'] < 0 or validated['aspect_ratio_tolerance'] > 1:
        raise ValueError(f"aspect_ratio_tolerance must be between 0 and 1")
    
    return validated


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to JSON file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save to
    """
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def get_config_template() -> str:
    """
    Get configuration template with explanations.
    
    Returns:
        JSON string with comments (as a dict with descriptions)
    """
    template = {
        "_comment": "Conflict Detection Configuration",
        "text_length_warning": {
            "value": 50,
            "description": "Warn if text is longer than this many characters"
        },
        "text_length_critical": {
            "value": 100,
            "description": "Critical alert if text exceeds this length (likely overflow)"
        },
        "aspect_ratio_tolerance": {
            "value": 0.2,
            "description": "Acceptable aspect ratio difference (0.2 = 20%)"
        },
        "upscale_warning_factor": {
            "value": 2.0,
            "description": "Warn if image will be upscaled more than this factor"
        },
        "downscale_info_factor": {
            "value": 0.5,
            "description": "Info if image will be downscaled more than this factor"
        },
        "font_size_large": {
            "value": 72,
            "description": "Warn if font size (in points) is larger than this"
        },
        "font_size_small": {
            "value": 12,
            "description": "Info if font size is smaller than this (readability concern)"
        },
        "dimension_tolerance": {
            "value": 0.1,
            "description": "Aspect ratio tolerance for dimension mismatch (0.1 = 10%)"
        }
    }
    
    return json.dumps(template, indent=2)
