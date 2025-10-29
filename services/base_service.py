"""
Base Service Class and Result Type

Provides foundational classes for all services in the application.
"""

from typing import Any, Optional, TypeVar, Generic, Dict
import logging
from contextlib import contextmanager
import time
import os


T = TypeVar('T')


class Result(Generic[T]):
    """
    Encapsulates operation results without throwing exceptions.

    This allows for railway-oriented programming where operations
    return success or failure states that can be chained together.

    Example:
        result = some_service.parse_file(path)
        if result.is_success():
            data = result.get_data()
            # Process data
        else:
            error = result.get_error()
            # Handle error
    """

    def __init__(self, success: bool, data: Optional[T] = None, error: Optional[str] = None):
        """
        Create a Result instance.

        Args:
            success: Whether the operation succeeded
            data: The result data if successful
            error: Error message if failed
        """
        self._success = success
        self._data = data
        self._error = error

    @staticmethod
    def success(data: T) -> 'Result[T]':
        """Create a successful result."""
        return Result(True, data=data)

    @staticmethod
    def failure(error: str) -> 'Result[T]':
        """Create a failed result."""
        return Result(False, error=error)

    def is_success(self) -> bool:
        """Check if the operation succeeded."""
        return self._success

    def is_failure(self) -> bool:
        """Check if the operation failed."""
        return not self._success

    def get_data(self) -> Optional[T]:
        """Get the result data (None if failed)."""
        return self._data if self._success else None

    def get_error(self) -> Optional[str]:
        """Get the error message (None if succeeded)."""
        return self._error

    def get_data_or_default(self, default: T) -> T:
        """Get data or return default if failed."""
        return self._data if self._success else default

    def map(self, func):
        """
        Map the data if successful, otherwise propagate failure.

        Example:
            result.map(lambda x: x['layers']).map(len)
        """
        if self._success and self._data is not None:
            try:
                return Result.success(func(self._data))
            except Exception as e:
                return Result.failure(str(e))
        return Result.failure(self._error)

    def flat_map(self, func):
        """
        Flat map - apply a function that returns a Result.

        Example:
            result.flat_map(lambda data: service.process(data))
        """
        if self._success and self._data is not None:
            return func(self._data)
        return Result.failure(self._error)

    def __repr__(self):
        if self._success:
            return f"Result.success({self._data!r})"
        return f"Result.failure({self._error!r})"


class BaseService:
    """
    Base class for all services.

    Provides common functionality like logging and error handling.
    Services encapsulate business logic and coordinate between modules.
    """

    def __init__(self, logger: Optional[logging.Logger] = None, enhanced_logging=None):
        """
        Initialize the service.

        Args:
            logger: Logger instance to use. If None, creates a default logger.
            enhanced_logging: EnhancedLoggingService instance. If None and enhanced logging
                            is enabled via environment, creates one automatically.
        """
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger

        # Check if enhanced logging should be used
        use_enhanced = os.getenv('USE_ENHANCED_LOGGING', 'false').lower() == 'true'

        if enhanced_logging is not None:
            # Use provided enhanced logging service
            self.enhanced_logging = enhanced_logging
        elif use_enhanced:
            # Auto-create enhanced logging service
            from services.enhanced_logging_service import EnhancedLoggingService
            self.enhanced_logging = EnhancedLoggingService(logger)
        else:
            # No enhanced logging
            self.enhanced_logging = None

    def log_info(self, message: str, **kwargs):
        """Log an info message."""
        self.logger.info(message, extra=kwargs)

    def log_warning(self, message: str, **kwargs):
        """Log a warning message."""
        self.logger.warning(message, extra=kwargs)

    def log_error(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """
        Log an error message.

        Args:
            message: Error message
            exc: Exception instance if available
            **kwargs: Additional context to log
        """
        self.logger.error(message, exc_info=exc, extra=kwargs)

    def log_debug(self, message: str, **kwargs):
        """Log a debug message."""
        self.logger.debug(message, extra=kwargs)

    def wrap_result(self, func, *args, **kwargs) -> Result:
        """
        Wrap a function call in a Result.

        Catches exceptions and converts them to Result.failure.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result containing the function's return value or error
        """
        try:
            result = func(*args, **kwargs)
            return Result.success(result)
        except Exception as e:
            self.log_error(f"Error in {func.__name__}", exc=e)
            return Result.failure(str(e))

    def log_step(
        self,
        step_name: str,
        level: str = 'info',
        **context
    ):
        """
        Log a processing step with structured context

        Creates searchable, parseable log entries with context data.

        Args:
            step_name: Name of the step (e.g., 'psd_parsing', 'matching')
            level: Log level ('info', 'warning', 'error', 'debug')
            **context: Key-value pairs of context data

        Example:
            self.log_step('psd_parsing',
                graphic_id='g1',
                file_size=1234567,
                elapsed_ms=245,
                status='success')

        Output:
            [INFO] [step:psd_parsing] graphic_id=g1 file_size=1234567 elapsed_ms=245 status=success
        """
        # Delegate to enhanced logging if available
        if self.enhanced_logging:
            self.enhanced_logging.log_step(step_name, level, **context)
            return

        # Build context string
        context_str = ' '.join([f"{k}={v}" for k, v in context.items()])

        # Build message
        msg = f"[step:{step_name}] {context_str}"

        # Log at appropriate level
        if level == 'debug':
            self.logger.debug(msg)
        elif level == 'warning':
            self.logger.warning(msg)
        elif level == 'error':
            self.logger.error(msg)
        else:
            self.logger.info(msg)

    def log_timing(
        self,
        operation: str,
        duration_ms: float,
        **context
    ):
        """
        Log operation timing for performance analysis

        Args:
            operation: Name of operation
            duration_ms: Duration in milliseconds
            **context: Additional context

        Example:
            self.log_timing('psd_parse', 1234.5,
                graphic_id='g1',
                file_size=5000000)

        Output:
            [TIMING] psd_parse: 1234.5ms graphic_id=g1 file_size=5000000
        """
        # Delegate to enhanced logging if available
        if self.enhanced_logging:
            self.enhanced_logging.log_timing(operation, duration_ms, **context)
            return

        context_str = ' '.join([f"{k}={v}" for k, v in context.items()])
        msg = f"[TIMING] {operation}: {duration_ms:.1f}ms {context_str}"
        self.logger.info(msg)

    def log_data_dump(
        self,
        label: str,
        data: Dict,
        max_length: int = 500
    ):
        """
        Dump data structure for debugging

        Only logs in debug mode to avoid cluttering production logs.

        Args:
            label: Label for the data dump
            data: Dictionary to dump
            max_length: Maximum string length (truncate if longer)

        Example:
            self.log_data_dump('psd_data', psd_result.get_data())

        Output:
            [DATA] psd_data: {"width": 1920, "height": 1080, ...}
        """
        # Delegate to enhanced logging if available
        if self.enhanced_logging:
            self.enhanced_logging.log_data_structure(label, data, max_length)
            return

        import json

        try:
            # Convert to JSON string
            json_str = json.dumps(data, indent=None, default=str)

            # Truncate if too long
            if len(json_str) > max_length:
                json_str = json_str[:max_length] + f"... (truncated, {len(json_str)} total chars)"

            msg = f"[DATA] {label}: {json_str}"
            self.logger.debug(msg)

        except Exception as e:
            self.logger.debug(f"[DATA] {label}: <could not serialize: {e}>")

    def log_error_with_context(
        self,
        error_msg: str,
        exception: Optional[Exception] = None,
        **context
    ):
        """
        Log error with structured context

        Args:
            error_msg: Error message
            exception: Optional exception object
            **context: Additional context (graphic_id, step, etc.)

        Example:
            self.log_error_with_context(
                'PSD parsing failed',
                exception=e,
                graphic_id='g1',
                file_path='/path/to/file.psd',
                step='psd_parse'
            )
        """
        # Delegate to enhanced logging if available
        if self.enhanced_logging:
            self.enhanced_logging.log_error_with_context(error_msg, exception, **context)
            return

        context_str = ' '.join([f"{k}={v}" for k, v in context.items()])
        msg = f"[ERROR] {error_msg} {context_str}"

        if exception:
            self.logger.error(msg, exc_info=exception)
        else:
            self.logger.error(msg)

    @contextmanager
    def timer(self, operation: str, **context):
        """
        Context manager for timing operations

        Usage:
            with self.timer('psd_parsing', graphic_id='g1'):
                # do parsing work
                psd_result = parse_psd(path)

        Automatically logs timing when block completes.
        """
        # Delegate to enhanced logging if available
        if self.enhanced_logging:
            with self.enhanced_logging.timer(operation, **context):
                yield
            return

        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.log_timing(operation, duration_ms, **context)
