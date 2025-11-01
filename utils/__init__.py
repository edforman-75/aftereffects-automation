"""
Utilities Package

Provides utility functions and classes for error handling and other common operations.
"""

from .errors import (
    AppError,
    JobNotFoundError,
    BatchNotFoundError,
    ValidationError,
    FileProcessingError,
    StageTransitionError,
    handle_error
)

__all__ = [
    'AppError',
    'JobNotFoundError',
    'BatchNotFoundError',
    'ValidationError',
    'FileProcessingError',
    'StageTransitionError',
    'handle_error'
]
