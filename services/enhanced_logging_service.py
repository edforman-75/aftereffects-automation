"""
Enhanced Logging Service

Provides comprehensive logging with advanced debugging capabilities including:
- Structured JSON logging
- Configurable log levels
- Debug mode toggle
- Performance profiling with percentiles
- Memory tracking
- Call stack capture
- Timeline visualization
"""

import logging
import json
import time
import os
import tracemalloc
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from collections import defaultdict


class EnhancedLoggingService:
    """
    Comprehensive logging service with advanced debugging features

    Features:
    - Structured JSON logging
    - Configurable log levels
    - Debug mode toggle
    - Performance profiling
    - Memory tracking
    - Call stack capture
    - Log filtering
    - Timeline visualization
    """

    def __init__(
        self,
        logger: logging.Logger,
        debug_mode: bool = None,
        log_format: str = None,
        log_level: str = None,
        enable_profiling: bool = None,
        enable_memory_tracking: bool = None
    ):
        """
        Initialize enhanced logging service

        Args:
            logger: Base logger instance
            debug_mode: Enable debug mode (default: from DEBUG_MODE env var)
            log_format: 'json' or 'text' (default: from LOG_FORMAT env var or 'text')
            log_level: 'DEBUG', 'INFO', 'WARNING', 'ERROR' (default: from LOG_LEVEL env var or 'INFO')
            enable_profiling: Enable performance profiling (default: from ENABLE_PROFILING env var)
            enable_memory_tracking: Enable memory tracking (default: from TRACK_MEMORY env var)
        """
        self.logger = logger

        # Configuration from environment or parameters
        self.debug_mode = debug_mode if debug_mode is not None else os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.log_format = log_format or os.getenv('LOG_FORMAT', 'text')
        self.enable_profiling = enable_profiling if enable_profiling is not None else os.getenv('ENABLE_PROFILING', 'true').lower() == 'true'
        self.enable_memory_tracking = enable_memory_tracking if enable_memory_tracking is not None else os.getenv('TRACK_MEMORY', 'false').lower() == 'true'

        # Set log level
        level_str = log_level or os.getenv('LOG_LEVEL', 'INFO')
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        self.logger.setLevel(level_map.get(level_str.upper(), logging.INFO))

        # Performance tracking
        self.performance_data = defaultdict(list)  # operation -> [durations]
        self.timeline_events = []  # List of timeline events for visualization
        self.call_stack = []  # Current operation call stack

        # Memory tracking
        if self.enable_memory_tracking:
            tracemalloc.start()

    def log_event(
        self,
        event_type: str,
        message: str,
        level: str = 'info',
        **context
    ):
        """
        Log an event with structured context

        Args:
            event_type: Type of event (e.g., 'step', 'timing', 'error')
            message: Event message
            level: Log level ('debug', 'info', 'warning', 'error')
            **context: Additional context data
        """
        # Build log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'message': message,
            'level': level.upper()
        }

        # Add context
        if context:
            log_entry['context'] = context

        # Add call stack if available
        if self.call_stack:
            log_entry['call_stack'] = list(self.call_stack)

        # Add memory info if tracking enabled
        if self.enable_memory_tracking:
            current, peak = tracemalloc.get_traced_memory()
            log_entry['memory'] = {
                'current_mb': current / 1024 / 1024,
                'peak_mb': peak / 1024 / 1024
            }

        # Format output
        if self.log_format == 'json':
            output = json.dumps(log_entry)
        else:
            # Text format
            context_str = ' '.join([f"{k}={v}" for k, v in context.items()])
            output = f"[{event_type.upper()}] {message}"
            if context_str:
                output += f" {context_str}"

        # Log at appropriate level
        log_level = level.lower()
        if log_level == 'debug':
            self.logger.debug(output)
        elif log_level == 'warning':
            self.logger.warning(output)
        elif log_level == 'error':
            self.logger.error(output)
        else:
            self.logger.info(output)

    @contextmanager
    def operation_context(
        self,
        operation: str,
        **context
    ):
        """
        Context manager for tracking operations with automatic profiling

        Usage:
            with enhanced_logging.operation_context('psd_parsing', graphic_id='g1'):
                # do work
                result = parse_psd(path)

        Automatically:
        - Times the operation
        - Tracks call stack
        - Logs timing information
        - Records timeline event
        - Tracks memory if enabled

        Args:
            operation: Operation name
            **context: Additional context
        """
        # Add to call stack
        self.call_stack.append(operation)

        # Record start
        start_time = time.time()
        start_memory = None

        if self.enable_memory_tracking:
            start_memory = tracemalloc.get_traced_memory()[0]

        # Log operation start in debug mode
        if self.debug_mode:
            self.log_event('operation_start', f"Starting {operation}", level='debug', **context)

        try:
            yield
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Calculate memory delta if tracking
            memory_delta_mb = None
            if self.enable_memory_tracking and start_memory is not None:
                current_memory = tracemalloc.get_traced_memory()[0]
                memory_delta_mb = (current_memory - start_memory) / 1024 / 1024

            # Remove from call stack
            self.call_stack.pop()

            # Record performance data
            if self.enable_profiling:
                self.performance_data[operation].append(duration_ms)

            # Build timing context
            timing_context = dict(context)
            timing_context['duration_ms'] = round(duration_ms, 2)

            if memory_delta_mb is not None:
                timing_context['memory_delta_mb'] = round(memory_delta_mb, 2)

            # Log timing
            self.log_event('timing', f"{operation}: {duration_ms:.1f}ms", level='info', **timing_context)

            # Record timeline event
            self.timeline_events.append({
                'name': operation,
                'cat': 'operation',
                'ph': 'X',  # Complete event
                'ts': int((start_time - self.timeline_events[0]['ts'] / 1000000) * 1000000) if self.timeline_events else 0,
                'dur': int(duration_ms * 1000),  # microseconds
                'args': context
            })

    def log_data_structure(
        self,
        label: str,
        data: Any,
        max_length: int = 1000
    ):
        """
        Log data structure for debugging (only in debug mode)

        Args:
            label: Label for the data
            data: Data to log (will be JSON serialized)
            max_length: Maximum length before truncation
        """
        if not self.debug_mode:
            return

        try:
            # Serialize data
            data_str = json.dumps(data, indent=2 if self.log_format == 'text' else None, default=str)

            # Truncate if too long
            if len(data_str) > max_length:
                data_str = data_str[:max_length] + f"... (truncated, {len(data_str)} total chars)"

            # Log
            if self.log_format == 'json':
                self.log_event('data_dump', label, level='debug', data=data_str)
            else:
                self.logger.debug(f"[DATA] {label}:\n{data_str}")

        except Exception as e:
            self.logger.debug(f"[DATA] {label}: <could not serialize: {e}>")

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary with percentiles

        Returns:
            Dictionary with performance statistics for each operation:
            {
                'operation_name': {
                    'count': 45,
                    'avg_ms': 123.4,
                    'min_ms': 89.2,
                    'max_ms': 234.5,
                    'p50_ms': 120.1,
                    'p95_ms': 189.3,
                    'p99_ms': 220.7,
                    'total_ms': 5553.0
                }
            }
        """
        summary = {}

        for operation, durations in self.performance_data.items():
            if not durations:
                continue

            # Sort for percentile calculation
            sorted_durations = sorted(durations)
            count = len(sorted_durations)

            # Calculate statistics
            summary[operation] = {
                'count': count,
                'avg_ms': round(sum(sorted_durations) / count, 2),
                'min_ms': round(min(sorted_durations), 2),
                'max_ms': round(max(sorted_durations), 2),
                'total_ms': round(sum(sorted_durations), 2)
            }

            # Calculate percentiles
            def percentile(p):
                k = (count - 1) * p / 100
                f = int(k)
                c = f + 1 if f + 1 < count else f
                return sorted_durations[f] + (k - f) * (sorted_durations[c] - sorted_durations[f])

            summary[operation]['p50_ms'] = round(percentile(50), 2)
            summary[operation]['p95_ms'] = round(percentile(95), 2)
            summary[operation]['p99_ms'] = round(percentile(99), 2)

        return summary

    def log_performance_summary(self):
        """Log current performance summary"""
        summary = self.get_performance_summary()

        if not summary:
            self.logger.info("No performance data collected")
            return

        if self.log_format == 'json':
            self.logger.info(json.dumps({
                'event_type': 'performance_summary',
                'summary': summary
            }))
        else:
            # Text format
            self.logger.info("\n=== PERFORMANCE SUMMARY ===")
            self.logger.info(
                f"{'Operation':<25s} {'Count':>7s} {'Avg':>10s} {'Min':>10s} "
                f"{'Max':>10s} {'p50':>10s} {'p95':>10s} {'p99':>10s}"
            )
            self.logger.info("-" * 100)

            for operation, stats in sorted(summary.items()):
                self.logger.info(
                    f"{operation:<25s} {stats['count']:>7d} "
                    f"{stats['avg_ms']:>9.1f}ms {stats['min_ms']:>9.1f}ms "
                    f"{stats['max_ms']:>9.1f}ms {stats['p50_ms']:>9.1f}ms "
                    f"{stats['p95_ms']:>9.1f}ms {stats['p99_ms']:>9.1f}ms"
                )

    def export_timeline(self, output_path: str):
        """
        Export timeline in Chrome Trace Format for visualization

        Args:
            output_path: Path to save timeline JSON

        Usage:
            # After running operations
            enhanced_logging.export_timeline('timeline.json')

            # View in Chrome:
            # 1. Open chrome://tracing
            # 2. Click "Load" and select timeline.json
        """
        with open(output_path, 'w') as f:
            json.dump(self.timeline_events, f, indent=2)

        self.logger.info(f"Timeline exported to {output_path}")
        self.logger.info("View in Chrome: chrome://tracing")

    def log_step(self, step_name: str, level: str = 'info', **context):
        """Log a processing step (backward compatible with BaseService)"""
        self.log_event('step', step_name, level=level, **context)

    def log_timing(self, operation: str, duration_ms: float, **context):
        """Log timing information (backward compatible with BaseService)"""
        timing_context = dict(context)
        timing_context['duration_ms'] = round(duration_ms, 2)
        self.log_event('timing', f"{operation}: {duration_ms:.1f}ms", level='info', **timing_context)

        # Record in performance data
        if self.enable_profiling:
            self.performance_data[operation].append(duration_ms)

    def log_error_with_context(self, error_msg: str, exception: Optional[Exception] = None, **context):
        """Log error with context (backward compatible with BaseService)"""
        self.log_event('error', error_msg, level='error', **context)

        if exception and self.logger.isEnabledFor(logging.ERROR):
            self.logger.error(f"Exception details:", exc_info=exception)

    @contextmanager
    def timer(self, operation: str, **context):
        """
        Simple timer context manager (backward compatible with BaseService)

        For advanced features, use operation_context() instead.
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.log_timing(operation, duration_ms, **context)
