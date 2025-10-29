"""
Module 5: Video Preview Generation

Generate low-resolution video previews of populated After Effects templates.
"""

from .preview_generator import (
    generate_preview,
    prepare_temp_project,
    render_with_aerender,
    generate_thumbnail,
    check_aerender_available
)

__all__ = [
    'generate_preview',
    'prepare_temp_project',
    'render_with_aerender',
    'generate_thumbnail',
    'check_aerender_available'
]
