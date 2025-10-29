"""
Phase 3: Content Mapping and Automation

Modules for mapping content to templates and generating automation scripts.
"""

from .content_matcher import match_content_to_slots
from .ml_content_matcher import match_content_to_slots_ml
from .conflict_detector import detect_conflicts
from .conflict_config import load_config, save_config, get_config_template, DEFAULT_CONFLICT_CONFIG
from .font_checker import check_fonts, get_font_substitution_suggestions

__all__ = [
    'match_content_to_slots',
    'match_content_to_slots_ml',
    'detect_conflicts',
    'load_config',
    'save_config',
    'get_config_template',
    'DEFAULT_CONFLICT_CONFIG',
    'check_fonts',
    'get_font_substitution_suggestions'
]
