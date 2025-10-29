"""
Aspect Ratio Handling Module

Conservative aspect ratio handling system with human oversight and learning capabilities.
"""

from .aspect_ratio_handler import (
    AspectRatioCategory,
    TransformationType,
    AspectRatioDecision,
    AspectRatioClassifier,
    AspectRatioHandler
)
from .preview_generator import AspectRatioPreviewGenerator
from .transform_applier import TransformApplier

__all__ = [
    'AspectRatioCategory',
    'TransformationType',
    'AspectRatioDecision',
    'AspectRatioClassifier',
    'AspectRatioHandler',
    'AspectRatioPreviewGenerator',
    'TransformApplier'
]
