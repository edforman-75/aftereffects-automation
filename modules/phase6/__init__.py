"""
Phase 6: Plainly Validation Module

Final quality control step to ensure AEP files are compatible with Plainly's requirements.
Includes auto-fix capabilities for common compatibility issues.
"""

from .plainly_validator import (
    ValidationSeverity,
    ValidationIssue,
    ValidationReport,
    PlainlyValidator
)

from .plainly_auto_fixer import (
    PlainlyAutoFixer,
    FixResult
)

__all__ = [
    'ValidationSeverity',
    'ValidationIssue',
    'ValidationReport',
    'PlainlyValidator',
    'PlainlyAutoFixer',
    'FixResult'
]
