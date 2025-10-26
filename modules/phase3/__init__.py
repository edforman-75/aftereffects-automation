"""
Phase 3: Content Mapping and Automation

Modules for mapping content to templates and generating automation scripts.
"""

from .content_matcher import match_content_to_slots
from .conflict_detector import detect_conflicts

__all__ = ['match_content_to_slots', 'detect_conflicts']
