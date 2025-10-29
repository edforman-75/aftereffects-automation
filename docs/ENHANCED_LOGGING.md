# Enhanced Logging System Documentation

## Overview

The Enhanced Logging System provides comprehensive debugging and performance analysis capabilities for the After Effects Automation application. It builds upon the minimal structured logging (see [LOGGING.md](LOGGING.md)) with advanced features including:

- **JSON Logging**: Machine-readable log format for log aggregation tools
- **Performance Profiling**: Automatic operation timing with percentile calculations (p50, p95, p99)
- **Memory Tracking**: Optional memory usage tracking per operation
- **Call Stack Tracking**: Maintains operation call stack for debugging
- **Debug Mode**: Toggleable verbose logging with data dumps
- **Timeline Export**: Chrome Trace Format for performance visualization
- **Performance Summary API**: HTTP endpoint for real-time performance data

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [Using Enhanced Logging](#using-enhanced-logging)
4. [Performance Analysis](#performance-analysis)
5. [Log Analysis](#log-analysis)
6. [API Endpoints](#api-endpoints)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Enable Enhanced Logging

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit .env
USE_ENHANCED_LOGGING=true
LOG_FORMAT=text
LOG_LEVEL=INFO
ENABLE_PROFILING=true
```

### 2. Start the Application

```bash
python3 web_app.py
```

The server will start with enhanced logging enabled.

### 3. View Performance Summary

While the application is running, visit:

```
GET http://localhost:5001/api/performance-summary
```

## Configuration

### Environment Variables

All configuration is done via environment variables in your `.env` file:

#### USE_ENHANCED_LOGGING

- **Type**: boolean (`true` or `false`)
- **Default**: `false`
- **Description**: Master switch for enhanced logging. When `false`, falls back to minimal structured logging.

```bash
USE_ENHANCED_LOGGING=true
```

#### DEBUG_MODE

- **Type**: boolean (`true` or `false`)
- **Default**: `false`
- **Description**: Enables verbose logging and data structure dumps. Only use in development.

```bash
DEBUG_MODE=true  # Development only!
```

#### LOG_FORMAT

- **Type**: string (`text` or `json`)
- **Default**: `text`
- **Description**: Output format for logs.
  - `text`: Human-readable format (default)
  - `json`: Machine-parseable JSON format (recommended for production with log aggregation)

```bash
LOG_FORMAT=json
```

#### LOG_LEVEL

- **Type**: string (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- **Default**: `INFO`
- **Description**: Minimum log level to output.

```bash
LOG_LEVEL=DEBUG  # Very verbose
LOG_LEVEL=INFO   # Recommended for production
```

#### ENABLE_PROFILING

- **Type**: boolean (`true` or `false`)
- **Default**: `true` (when enhanced logging is enabled)
- **Description**: Enables performance profiling with timing data collection.

```bash
ENABLE_PROFILING=true
```

#### TRACK_MEMORY

- **Type**: boolean (`true` or `false`)
- **Default**: `false`
- **Description**: Enables memory usage tracking. Has small performance overhead.

```bash
TRACK_MEMORY=true
```

### Configuration Presets

#### Development Debugging

```bash
USE_ENHANCED_LOGGING=true
DEBUG_MODE=true
LOG_FORMAT=text
LOG_LEVEL=DEBUG
ENABLE_PROFILING=true
TRACK_MEMORY=false
```

#### Production (Text Logs)

```bash
USE_ENHANCED_LOGGING=true
DEBUG_MODE=false
LOG_FORMAT=text
LOG_LEVEL=INFO
ENABLE_PROFILING=true
TRACK_MEMORY=false
```

#### Production (JSON + Log Aggregation)

```bash
USE_ENHANCED_LOGGING=true
DEBUG_MODE=false
LOG_FORMAT=json
LOG_LEVEL=INFO
ENABLE_PROFILING=true
TRACK_MEMORY=false
```

#### Performance Analysis

```bash
USE_ENHANCED_LOGGING=true
DEBUG_MODE=false
LOG_FORMAT=json
LOG_LEVEL=INFO
ENABLE_PROFILING=true
TRACK_MEMORY=true
```

## Using Enhanced Logging

Enhanced logging is automatically used by all services when `USE_ENHANCED_LOGGING=true`. No code changes are required.

### Automatic Features

When enhanced logging is enabled, all services automatically get:

1. **operation_context()** - Available via `self.enhanced_logging.operation_context()`
2. **Performance tracking** - Automatic timing collection
3. **Memory tracking** - Optional memory usage tracking
4. **Call stack tracking** - Maintains operation hierarchy

### In Service Methods

Services can use enhanced logging directly:

```python
class MyService(BaseService):
    def process_data(self, graphic_id, data):
        # Option 1: Use operation_context for full profiling
        if self.enhanced_logging:
            with self.enhanced_logging.operation_context('process_data', graphic_id=graphic_id):
                result = self._do_heavy_work(data)
                return Result.success(result)

        # Option 2: Use timer for simple timing (backward compatible)
        with self.timer('process_data', graphic_id=graphic_id):
            result = self._do_heavy_work(data)
            return Result.success(result)
```

### operation_context() vs timer()

**operation_context()** (Enhanced):
- Full performance profiling
- Memory tracking (if enabled)
- Call stack tracking
- Timeline event recording
- Percentile calculations (p50, p95, p99)

**timer()** (Minimal):
- Simple timing only
- Backward compatible
- Lower overhead

Use `operation_context()` for critical operations you want to analyze deeply.
Use `timer()` for quick timing without extra features.

### Logging Methods

All logging methods from BaseService work with enhanced logging:

```python
# Log processing steps
self.log_step('parsing_complete',
    graphic_id=graphic_id,
    status='success',
    items_count=42)

# Log timing manually
self.log_timing('database_query', 123.4,
    graphic_id=graphic_id,
    query_type='select')

# Log errors with context
self.log_error_with_context(
    'Processing failed',
    exception=e,
    graphic_id=graphic_id,
    step='matching')

# Dump data structures (debug mode only)
self.log_data_dump('psd_layers', psd_data)
```

## Performance Analysis

### Real-Time Performance Summary

Get current performance statistics via the API:

```bash
curl http://localhost:5001/api/performance-summary
```

Response:

```json
{
  "success": true,
  "data": {
    "summary": {
      "psd_parse": {
        "count": 45,
        "avg_ms": 1234.5,
        "min_ms": 890.2,
        "max_ms": 2134.7,
        "p50_ms": 1200.1,
        "p95_ms": 1895.3,
        "p99_ms": 2050.7,
        "total_ms": 55552.5
      },
      "aepx_parse": {
        "count": 45,
        "avg_ms": 456.3,
        "min_ms": 234.1,
        "max_ms": 890.5,
        "p50_ms": 450.2,
        "p95_ms": 678.9,
        "p99_ms": 820.4,
        "total_ms": 20533.5
      }
    },
    "total_operations": 2,
    "note": "Performance data collected since server start"
  }
}
```

### Understanding Percentiles

- **p50 (median)**: 50% of operations completed faster than this
- **p95**: 95% of operations completed faster than this
- **p99**: 99% of operations completed faster than this

Use p95 and p99 to identify performance outliers and worst-case scenarios.

### Log Analysis Script

Analyze logs with the enhanced analysis script:

```bash
# Show timing summary (works with both text and JSON logs)
python scripts/analyze_logs.py app.log --timing

# Filter by graphic and show timing
python scripts/analyze_logs.py app.log --graphic g1 --timing

# Force JSON parsing mode
python scripts/analyze_logs.py app.log --json --timing

# Show only errors
python scripts/analyze_logs.py app.log --errors

# Track specific request by correlation ID
python scripts/analyze_logs.py app.log --correlation abc-123-def
```

### Timeline Visualization

Export timeline for Chrome tracing:

```python
# In your code
container.enhanced_logging.export_timeline('timeline.json')
```

Then view in Chrome:
1. Open `chrome://tracing`
2. Click "Load"
3. Select `timeline.json`
4. Use W/A/S/D to navigate the timeline

## Log Analysis

### Text Format Logs

```bash
# View live logs
tail -f app.log

# Search for specific graphic
grep "graphic_id=g1" app.log

# Find timing entries
grep "\[TIMING\]" app.log

# Find errors
grep "\[ERROR\]" app.log

# Track request by correlation ID
grep "correlation_id=abc-123" app.log
```

### JSON Format Logs

```bash
# View live logs with jq
tail -f app.log | jq

# Filter by event type
jq 'select(.event_type=="timing")' app.log

# Filter by graphic ID
jq 'select(.context.graphic_id=="g1")' app.log

# Extract timing data
jq 'select(.event_type=="timing") | {operation: .message, duration: .context.duration_ms}' app.log

# Find errors
jq 'select(.event_type=="error" or .level=="ERROR")' app.log
```

### Using the Analysis Script

```bash
# Basic usage
python scripts/analyze_logs.py app.log

# Show timing summary
python scripts/analyze_logs.py app.log --timing

# Filter by graphic
python scripts/analyze_logs.py app.log --graphic g1

# Show errors for specific step
python scripts/analyze_logs.py app.log --step psd_parse --errors

# Track correlation ID
python scripts/analyze_logs.py app.log --correlation abc-123-def

# Combine filters
python scripts/analyze_logs.py app.log --graphic g1 --timing --json
```

## API Endpoints

### GET /api/performance-summary

Get performance summary with percentiles.

**Request:**
```
GET /api/performance-summary
```

**Response** (success):
```json
{
  "success": true,
  "data": {
    "summary": {
      "operation_name": {
        "count": 100,
        "avg_ms": 123.4,
        "min_ms": 50.0,
        "max_ms": 500.0,
        "p50_ms": 120.0,
        "p95_ms": 250.0,
        "p99_ms": 450.0,
        "total_ms": 12340.0
      }
    },
    "total_operations": 5
  }
}
```

**Response** (enhanced logging not enabled):
```json
{
  "success": false,
  "error": "Enhanced logging is not enabled. Set USE_ENHANCED_LOGGING=true to enable."
}
```

## Best Practices

### 1. Use Appropriate Log Levels

```python
# DEBUG - Detailed diagnostic information
self.log_step('parsing_layer', level='debug',
    layer_id='layer_1',
    layer_type='text')

# INFO - General informational messages (default)
self.log_step('parsing_complete',
    graphic_id='g1',
    status='success')

# WARNING - Warning messages for recoverable issues
self.log_step('aspect_ratio_mismatch', level='warning',
    expected='16:9',
    actual='4:3')

# ERROR - Error messages for failures
self.log_step('parsing_failed', level='error',
    graphic_id='g1',
    error='file_not_found')
```

### 2. Include Relevant Context

Always include identifying information in log context:

```python
# Good - Includes graphic_id for tracking
self.log_step('psd_parse_complete',
    graphic_id=graphic_id,
    project_id=project_id,
    layers_count=42)

# Bad - Missing context
self.log_step('parse_complete')
```

### 3. Use operation_context for Critical Operations

```python
# Critical operations - use operation_context
with self.enhanced_logging.operation_context('database_migration',
    migration_id='20250126_001'):
    migrate_database()

# Simple operations - use timer
with self.timer('cache_lookup', key=cache_key):
    result = cache.get(key)
```

### 4. Debug Mode Only in Development

**Never enable DEBUG_MODE in production!**

```bash
# Development
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Production
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### 5. Monitor Performance Regularly

Set up regular performance checks:

```bash
# Daily performance report
curl http://localhost:5001/api/performance-summary > perf-$(date +%Y%m%d).json

# Alert on high p99 times
python scripts/check_performance.py --threshold-p99 5000
```

## Troubleshooting

### Enhanced Logging Not Working

**Symptom**: Logs show text format even with `LOG_FORMAT=json`

**Solution**:
1. Verify `.env` file exists in project root
2. Check `USE_ENHANCED_LOGGING=true` is set
3. Restart the application
4. Check logs for "Enhanced logging enabled" message

### No Performance Data

**Symptom**: `/api/performance-summary` returns empty summary

**Solution**:
1. Verify `ENABLE_PROFILING=true`
2. Trigger some operations (upload PSD, process graphics)
3. Check that operations are using `timer()` or `operation_context()`

### Memory Tracking Issues

**Symptom**: Memory data not appearing in logs

**Solution**:
1. Verify `TRACK_MEMORY=true`
2. Ensure Python's `tracemalloc` module is available
3. Check that operations are using `operation_context()` (not `timer()`)

### High Memory Usage

**Symptom**: Application memory grows over time

**Solution**:
1. Disable memory tracking: `TRACK_MEMORY=false`
2. Reduce log retention
3. Use JSON format with external log rotation

### Slow Performance

**Symptom**: Application slower with enhanced logging

**Cause**: Debug mode and memory tracking have overhead

**Solution**:
```bash
# Production settings
DEBUG_MODE=false
LOG_FORMAT=json
LOG_LEVEL=INFO
TRACK_MEMORY=false
```

### JSON Parsing Errors

**Symptom**: Log analysis script fails to parse JSON logs

**Solution**:
1. Verify logs are actually in JSON format: `head -1 app.log`
2. Use `--json` flag: `python scripts/analyze_logs.py app.log --json`
3. Check for mixed text/JSON logs (shouldn't happen, but verify `LOG_FORMAT` hasn't changed)

## Summary

The Enhanced Logging System provides powerful debugging and performance analysis capabilities:

- **Zero code changes required** - Enable via environment variables
- **Backward compatible** - Falls back to minimal structured logging
- **Production ready** - JSON format for log aggregation
- **Performance profiling** - Percentiles, call stacks, timeline export
- **HTTP API** - Real-time performance summary endpoint
- **Flexible** - Text or JSON, debug or production mode

For basic usage, see [LOGGING.md](LOGGING.md).

For enhanced features, enable via `.env` and use the configuration presets above.

---

**Created**: 2025-01-28
**Status**: Production Ready
**Version**: 1.0
