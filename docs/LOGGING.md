# Structured Logging Guide

## Overview

The application now includes minimal structured logging enhancements to improve debugging and tracing without major refactoring. This guide explains how to use the new logging methods.

## Features

- **Structured Logging**: Log entries with key-value pairs for easy searching
- **Timing Information**: Automatic operation timing with the `timer()` context manager
- **Correlation IDs**: Track requests through the entire pipeline
- **Searchable Logs**: Filter and analyze logs by graphic, step, correlation ID, etc.
- **Log Analysis Tool**: Helper script to analyze and summarize logs

## Structured Logging Methods

All services that inherit from `BaseService` have access to these methods:

### 1. log_step()

Log a processing step with structured context:

```python
self.log_step('psd_parsing',
    graphic_id='g1',
    file_size=1234567,
    status='success')
```

**Output:**
```
[INFO] [step:psd_parsing] graphic_id=g1 file_size=1234567 status=success
```

**Parameters:**
- `step_name` (str): Name of the step (e.g., 'psd_parsing', 'matching')
- `level` (str): Log level ('info', 'warning', 'error', 'debug') - default: 'info'
- `**context`: Key-value pairs of context data

**Common Usage:**
```python
# Log start of processing
self.log_step('process_graphic_start',
    project_id=project_id,
    graphic_id=graphic_id,
    graphic_name=graphic.get('name'))

# Log completion
self.log_step('psd_parse_complete',
    graphic_id=graphic_id,
    status='success',
    width=1920,
    height=1080)

# Log with warning level
self.log_step('aspect_ratio_check',
    level='warning',
    graphic_id='g1',
    issue='dimensions_mismatch')
```

### 2. log_timing()

Log operation timing for performance analysis:

```python
self.log_timing('psd_parse', 1234.5,
    graphic_id='g1',
    file_size=5000000)
```

**Output:**
```
[TIMING] psd_parse: 1234.5ms graphic_id=g1 file_size=5000000
```

**Parameters:**
- `operation` (str): Name of operation
- `duration_ms` (float): Duration in milliseconds
- `**context`: Additional context

**Note:** Usually you'll use the `timer()` context manager instead of calling this directly.

### 3. timer() Context Manager

Automatic timing - the recommended way to time operations:

```python
with self.timer('psd_parsing', graphic_id='g1', project_id='proj_123'):
    psd_result = parse_psd(path)
    # ... do work ...
```

**Output (automatically logged when block completes):**
```
[TIMING] psd_parsing: 1234.5ms graphic_id=g1 project_id=proj_123
```

**Usage Examples:**
```python
# Time PSD parsing
with self.timer('psd_parse', graphic_id=graphic_id, project_id=project_id):
    psd_result = self.psd_service.parse_psd(graphic['psd_path'])

# Time matching
with self.timer('matching', graphic_id=graphic_id):
    match_result = self.matching_service.match_content(psd_data, aepx_data)

# Time database operations
with self.timer('db_save', project_id=project_id):
    self.store.save()
```

### 4. log_error_with_context()

Log errors with structured context:

```python
self.log_error_with_context(
    'PSD parsing failed',
    exception=e,
    graphic_id='g1',
    file_path='/path/to/file.psd',
    step='psd_parse')
```

**Output:**
```
[ERROR] PSD parsing failed graphic_id=g1 file_path=/path/to/file.psd step=psd_parse
<exception traceback if provided>
```

**Parameters:**
- `error_msg` (str): Error message
- `exception` (Exception, optional): Exception object for traceback
- `**context`: Additional context (graphic_id, step, etc.)

**Usage Examples:**
```python
try:
    psd_result = self.psd_service.parse_psd(path)
except Exception as e:
    self.log_error_with_context(
        'PSD parsing failed',
        exception=e,
        graphic_id=graphic_id,
        project_id=project_id,
        step='psd_parse',
        file_path=path
    )
    return Result.failure(str(e))
```

### 5. log_data_dump()

Dump data structures for debugging (debug level only):

```python
self.log_data_dump('psd_data', psd_result.get_data())
```

**Output (only when logger is in DEBUG mode):**
```
[DATA] psd_data: {"width": 1920, "height": 1080, "layers": [...]}
```

**Parameters:**
- `label` (str): Label for the data dump
- `data` (dict): Dictionary to dump
- `max_length` (int): Maximum string length (default: 500)

**Note:** This only logs when the logger is at DEBUG level to avoid cluttering production logs.

## Correlation IDs

Every HTTP request automatically gets a correlation ID that's propagated through the entire request:

**Request Headers:**
```
X-Correlation-ID: abc-123-def-456
```

**Response Headers:**
```
X-Correlation-ID: abc-123-def-456
```

**Log Entries:**
```
[REQUEST] POST /api/projects/proj1/graphics/g1/process correlation_id=abc-123-def-456
[step:psd_parsing] graphic_id=g1 correlation_id=abc-123-def-456
[TIMING] psd_parse: 1234.5ms graphic_id=g1 correlation_id=abc-123-def-456
[RESPONSE] /api/projects/proj1/graphics/g1/process status=200 correlation_id=abc-123-def-456
```

**Benefits:**
- Track a request through the entire pipeline
- Search logs for all entries related to a specific request
- Debug issues by following the complete request flow

## Searching Logs

### Using grep

Find all log entries for a specific graphic:
```bash
grep "graphic_id=g1" app.log
```

Find timing information for a specific operation:
```bash
grep "[TIMING] psd_parse" app.log
```

Find all errors:
```bash
grep "\[ERROR\]" app.log
```

Find all entries for a correlation ID:
```bash
grep "correlation_id=abc-123" app.log
```

Find all steps:
```bash
grep "\[step:" app.log
```

### Combining Filters

Find PSD parsing steps for graphic g1:
```bash
grep "graphic_id=g1" app.log | grep "\[step:psd_parse"
```

Find all errors for a specific project:
```bash
grep "project_id=proj_123" app.log | grep "\[ERROR\]"
```

## Log Analysis Script

The `scripts/analyze_logs.py` helper script provides convenient log analysis:

### Basic Usage

```bash
# Analyze specific graphic
python scripts/analyze_logs.py app.log --graphic g1

# Show timing summary
python scripts/analyze_logs.py app.log --timing

# Show only errors
python scripts/analyze_logs.py app.log --errors

# Filter by step
python scripts/analyze_logs.py app.log --step psd_parse

# Filter by correlation ID
python scripts/analyze_logs.py app.log --correlation abc-123-def
```

### Timing Summary Example

```bash
python scripts/analyze_logs.py app.log --timing
```

**Output:**
```
=== TIMING SUMMARY ===
Operation                  Avg (ms)   Min (ms)   Max (ms)    Count
----------------------------------------------------------------------
psd_parse                    1234.5      890.2     2134.7       45
aepx_parse                    456.3      234.1      890.5       45
matching                      789.2      456.7     1234.8       45
expression_gen                234.5      123.4      456.7       45
```

### Combining Filters

```bash
# Show timing for specific graphic
python scripts/analyze_logs.py app.log --graphic g1 --timing

# Show errors for specific step
python scripts/analyze_logs.py app.log --step psd_parse --errors
```

## Example Usage in Services

### In a Service Method

```python
from services.base_service import BaseService, Result

class MyService(BaseService):
    def process_data(self, graphic_id, data):
        """Process data with structured logging"""

        # Log start
        self.log_step('process_data_start',
            graphic_id=graphic_id,
            data_size=len(data))

        try:
            # Time the operation
            with self.timer('data_processing', graphic_id=graphic_id):
                # Do work
                result = self._do_processing(data)

            # Log success
            self.log_step('process_data_complete',
                graphic_id=graphic_id,
                status='success',
                result_count=len(result))

            return Result.success(result)

        except Exception as e:
            # Log error with context
            self.log_error_with_context(
                'Data processing failed',
                exception=e,
                graphic_id=graphic_id,
                step='process_data'
            )
            return Result.failure(str(e))
```

### In a Web Route

```python
@app.route('/api/process', methods=['POST'])
def process_route():
    # Correlation ID is automatically available in g.correlation_id
    correlation_id = getattr(g, 'correlation_id', 'unknown')

    container.logger.info(
        f"[API] Processing request correlation_id={correlation_id} "
        f"graphic_id={graphic_id}"
    )

    # Your processing logic...
    result = container.service.process(data)

    # Response automatically includes X-Correlation-ID header
    return jsonify(result.get_data())
```

## Best Practices

### 1. Always Include Relevant Context

```python
# Good
self.log_step('psd_parsing',
    graphic_id=graphic_id,
    project_id=project_id,
    file_size=file_size,
    status='success')

# Bad
self.log_info("Parsed PSD file")
```

### 2. Use timer() for Performance Critical Operations

```python
# Good
with self.timer('database_query', graphic_id=graphic_id):
    results = self.db.query(...)

# Bad (manual timing)
start = time.time()
results = self.db.query(...)
duration = (time.time() - start) * 1000
self.log_timing('database_query', duration, graphic_id=graphic_id)
```

### 3. Include Step Name in Errors

```python
self.log_error_with_context(
    'Operation failed',
    exception=e,
    graphic_id=graphic_id,
    step='psd_parse',  # ← Include the step
    file_path=path
)
```

### 4. Use Consistent Naming

Use consistent names for operations and steps:
- `psd_parse` (not `psd_parsing`, `parse_psd`, etc.)
- `aepx_parse`
- `matching`
- `aspect_ratio_check`
- `expression_gen`

### 5. Log at Key Points

Log at these key points in processing:
- **Start**: When processing begins
- **Major steps**: Each significant operation
- **Errors**: Any failures with full context
- **Completion**: When processing finishes

## Performance Impact

The structured logging methods have minimal overhead:
- **log_step()**: < 0.1ms per call
- **log_timing()**: < 0.1ms per call
- **timer()**: < 0.2ms (includes timing overhead)
- **log_error_with_context()**: < 0.1ms per call
- **log_data_dump()**: Only runs at DEBUG level

Total impact on a typical request: < 2ms

## Backward Compatibility

All existing logging methods still work:
- `log_info()`
- `log_warning()`
- `log_error()`
- `log_debug()`

You can mix old and new logging styles as needed.

## Summary

**Key Logging Methods:**
- `log_step()` - Log processing steps with context
- `timer()` - Automatic operation timing
- `log_error_with_context()` - Errors with full context
- `log_data_dump()` - Debug data dumps

**Key Features:**
- Correlation IDs track requests end-to-end
- Structured key=value format for easy searching
- Log analysis script for summaries and filtering
- Minimal performance overhead
- Backward compatible

**Quick Start:**
```python
# In your service method
self.log_step('operation_start', graphic_id=graphic_id)

with self.timer('operation', graphic_id=graphic_id):
    result = do_work()

self.log_step('operation_complete', graphic_id=graphic_id, status='success')
```

---

For more examples, see the test files and service implementations.
