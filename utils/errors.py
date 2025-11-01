"""
Error Handling Utilities

Provides custom exception classes and error handlers for consistent error responses.
"""

from flask import jsonify
from config.container import container


class AppError(Exception):
    """
    Base application error.

    All custom exceptions should inherit from this class.
    """
    status_code = 500

    def __init__(self, message: str, status_code: int = None):
        """
        Initialize application error.

        Args:
            message: Error message
            status_code: HTTP status code (overrides class default)
        """
        super().__init__(message)
        if status_code:
            self.status_code = status_code
        self.message = message


class JobNotFoundError(AppError):
    """Job not found in database."""
    status_code = 404

    def __init__(self, job_id: str):
        super().__init__(f"Job not found: {job_id}")
        self.job_id = job_id


class BatchNotFoundError(AppError):
    """Batch not found in database."""
    status_code = 404

    def __init__(self, batch_id: str):
        super().__init__(f"Batch not found: {batch_id}")
        self.batch_id = batch_id


class ValidationError(AppError):
    """Validation failed."""
    status_code = 400

    def __init__(self, message: str, validation_errors: dict = None):
        super().__init__(message)
        self.validation_errors = validation_errors or {}


class FileProcessingError(AppError):
    """File processing failed."""
    status_code = 500

    def __init__(self, message: str, file_path: str = None):
        super().__init__(message)
        self.file_path = file_path


class StageTransitionError(AppError):
    """Invalid stage transition."""
    status_code = 400

    def __init__(self, job_id: str, current_stage: int, target_stage: int, reason: str = None):
        message = f"Cannot transition job {job_id} from stage {current_stage} to stage {target_stage}"
        if reason:
            message += f": {reason}"
        super().__init__(message)
        self.job_id = job_id
        self.current_stage = current_stage
        self.target_stage = target_stage


def handle_error(error: Exception):
    """
    Global error handler for all exceptions.

    Provides consistent JSON error responses with appropriate logging.

    Args:
        error: Exception instance

    Returns:
        tuple: (JSON response, HTTP status code)
    """
    # Handle known application errors
    if isinstance(error, AppError):
        container.main_logger.warning(
            f"Application error: {error.message}",
            extra={'error_type': error.__class__.__name__}
        )

        response = {
            'success': False,
            'error': error.message
        }

        # Add validation errors if present
        if isinstance(error, ValidationError) and error.validation_errors:
            response['validation_errors'] = error.validation_errors

        return jsonify(response), error.status_code

    # Handle unexpected errors
    container.main_logger.error(
        f"Unexpected error: {str(error)}",
        exc_info=True,
        extra={'error_type': error.__class__.__name__}
    )

    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500
