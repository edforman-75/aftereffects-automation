"""
Custom Exception Hierarchy

Defines application-specific exceptions for better error handling and debugging.
"""


class AEAutomationError(Exception):
    """Base exception for all application-specific errors."""

    def __init__(self, message: str, details: dict = None):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error context (dict)
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# File Processing Errors

class FileProcessingError(AEAutomationError):
    """Base class for file processing errors."""
    pass


class FileNotFoundError(FileProcessingError):
    """Raised when a required file is not found."""
    pass


class FileFormatError(FileProcessingError):
    """Raised when a file has an invalid format."""
    pass


class FileSizeError(FileProcessingError):
    """Raised when a file exceeds size limits."""
    pass


# PSD-specific Errors

class PSDError(FileProcessingError):
    """Base class for PSD-related errors."""
    pass


class PSDParsingError(PSDError):
    """Raised when PSD parsing fails."""
    pass


class PSDLayerError(PSDError):
    """Raised when there's an issue with PSD layers."""
    pass


class PSDFontError(PSDError):
    """Raised when there's an issue extracting fonts from PSD."""
    pass


# AEPX-specific Errors

class AEPXError(FileProcessingError):
    """Base class for AEPX-related errors."""
    pass


class AEPXParsingError(AEPXError):
    """Raised when AEPX parsing fails."""
    pass


class AEPXPlaceholderError(AEPXError):
    """Raised when there's an issue with AEPX placeholders."""
    pass


# Matching and Mapping Errors

class MatchingError(AEAutomationError):
    """Raised when content matching fails."""
    pass


class MappingError(AEAutomationError):
    """Raised when there's an issue with content mapping."""
    pass


class ConflictError(AEAutomationError):
    """Raised when conflicts are detected in mappings."""
    pass


# Preview and Rendering Errors

class PreviewError(AEAutomationError):
    """Base class for preview-related errors."""
    pass


class PreviewGenerationError(PreviewError):
    """Raised when preview generation fails."""
    pass


class AERenderError(PreviewError):
    """Raised when After Effects rendering fails."""
    pass


# Font Errors

class FontError(AEAutomationError):
    """Base class for font-related errors."""
    pass


class FontMissingError(FontError):
    """Raised when required fonts are missing."""
    pass


class FontInstallationError(FontError):
    """Raised when font installation fails."""
    pass


# Configuration Errors

class ConfigurationError(AEAutomationError):
    """Raised when there's a configuration issue."""
    pass


class ValidationError(AEAutomationError):
    """Raised when validation fails."""
    pass


# Project Management Errors

class ProjectError(AEAutomationError):
    """Base class for project management errors."""
    pass


class ProjectNotFoundError(ProjectError):
    """Raised when a project is not found."""
    pass


class GraphicError(ProjectError):
    """Raised when there's an issue with a graphic in a project."""
    pass


# Helper Functions

def raise_file_not_found(file_path: str):
    """Convenience function to raise FileNotFoundError."""
    raise FileNotFoundError(
        f"File not found",
        details={"path": file_path}
    )


def raise_parsing_error(file_type: str, file_path: str, reason: str):
    """Convenience function to raise parsing errors."""
    if file_type.upper() == 'PSD':
        raise PSDParsingError(
            f"Failed to parse PSD file",
            details={"path": file_path, "reason": reason}
        )
    elif file_type.upper() == 'AEPX':
        raise AEPXParsingError(
            f"Failed to parse AEPX file",
            details={"path": file_path, "reason": reason}
        )
    else:
        raise FileFormatError(
            f"Failed to parse {file_type} file",
            details={"path": file_path, "reason": reason}
        )
