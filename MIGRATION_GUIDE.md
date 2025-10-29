# Migration Guide: Moving to Service Layer Architecture

This guide shows how to migrate existing code to use the new service-based architecture.

## Table of Contents

1. [Overview](#overview)
2. [Before and After Examples](#before-and-after-examples)
3. [Step-by-Step Migration](#step-by-step-migration)
4. [Benefits of Migration](#benefits-of-migration)
5. [Common Patterns](#common-patterns)

---

## Overview

The new service layer provides:
- **Consistent error handling** with the Result pattern
- **Better logging** with structured service loggers
- **Centralized configuration** via dependency injection
- **Easier testing** with mockable services
- **Cleaner code** with separation of concerns

**Important:** The service layer WRAPS existing modules without modifying them. Existing code continues to work unchanged.

---

## Before and After Examples

### Example 1: Parsing a PSD File

**Before (direct module usage):**
```python
from modules.phase1 import psd_parser

try:
    psd_data = psd_parser.parse_psd(psd_path)
    print(f"Parsed {len(psd_data['layers'])} layers")
except Exception as e:
    print(f"Error: {e}")
    # Error handling is manual, inconsistent
```

**After (service layer):**
```python
from config.container import container

result = container.psd_service.parse_psd(psd_path)

if result.is_success():
    psd_data = result.get_data()
    print(f"Parsed {len(psd_data['layers'])} layers")
else:
    # Error is automatically logged
    print(f"Error: {result.get_error()}")
```

**Benefits:**
- ✅ No try/catch needed
- ✅ Automatic logging of errors
- ✅ Consistent error messages
- ✅ Validation included (file exists, correct format, etc.)

---

### Example 2: Complete Workflow

**Before (direct module usage):**
```python
from modules.phase1 import psd_parser
from modules.phase2 import aepx_parser
from modules.phase3 import content_matcher
from modules.phase5 import preview_generator

try:
    # Parse files
    psd_data = psd_parser.parse_psd(psd_path)
    aepx_data = aepx_parser.parse_aepx(aepx_path)

    # Match content
    mappings = content_matcher.match_content_to_slots(psd_data, aepx_data)

    # Generate preview
    preview_result = preview_generator.generate_preview(
        aepx_path, mappings, output_path
    )

    if preview_result['success']:
        print(f"Preview: {preview_result['video_path']}")
    else:
        print(f"Failed: {preview_result['error']}")

except FileNotFoundError as e:
    print(f"File not found: {e}")
except ValueError as e:
    print(f"Invalid file: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

**After (service layer):**
```python
from config.container import container

# Parse files (errors automatically handled)
psd_result = container.psd_service.parse_psd(psd_path)
aepx_result = container.aepx_service.parse_aepx(aepx_path)

if psd_result.is_success() and aepx_result.is_success():
    # Match content
    match_result = container.matching_service.match_content(
        psd_result.get_data(),
        aepx_result.get_data()
    )

    if match_result.is_success():
        # Generate preview
        preview_result = container.preview_service.generate_preview(
            aepx_path,
            match_result.get_data(),
            output_path
        )

        if preview_result.is_success():
            data = preview_result.get_data()
            print(f"Preview: {data['video_path']}")
        else:
            print(f"Failed: {preview_result.get_error()}")
else:
    # Errors are already logged
    if not psd_result.is_success():
        print(f"PSD error: {psd_result.get_error()}")
    if not aepx_result.is_success():
        print(f"AEPX error: {aepx_result.get_error()}")
```

**Benefits:**
- ✅ No try/catch blocks
- ✅ Automatic logging at every step
- ✅ Consistent error handling
- ✅ Easier to test (mock services)
- ✅ Built-in validation

---

### Example 3: Flask Web Route

**Before (direct module usage):**
```python
@app.route('/api/process', methods=['POST'])
def process_files():
    try:
        psd_path = request.json['psd_path']
        aepx_path = request.json['aepx_path']

        # No validation
        psd_data = psd_parser.parse_psd(psd_path)
        aepx_data = aepx_parser.parse_aepx(aepx_path)

        mappings = content_matcher.match_content_to_slots(psd_data, aepx_data)

        return jsonify({
            'success': True,
            'mappings': mappings['mappings']
        })

    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'File not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        # Uncaught errors crash the server or return 500
        return jsonify({'success': False, 'error': 'Internal error'}), 500
```

**After (service layer):**
```python
@app.route('/api/process', methods=['POST'])
def process_files():
    psd_path = request.json['psd_path']
    aepx_path = request.json['aepx_path']

    # Validate files first
    psd_valid = container.psd_service.validate_psd_file(psd_path)
    aepx_valid = container.aepx_service.validate_aepx_file(aepx_path)

    if not psd_valid.is_success():
        return jsonify({'success': False, 'error': psd_valid.get_error()}), 400

    if not aepx_valid.is_success():
        return jsonify({'success': False, 'error': aepx_valid.get_error()}), 400

    # Parse files
    psd_result = container.psd_service.parse_psd(psd_path)
    aepx_result = container.aepx_service.parse_aepx(aepx_path)

    if not psd_result.is_success():
        return jsonify({'success': False, 'error': psd_result.get_error()}), 400

    if not aepx_result.is_success():
        return jsonify({'success': False, 'error': aepx_result.get_error()}), 400

    # Match content
    match_result = container.matching_service.match_content(
        psd_result.get_data(),
        aepx_result.get_data()
    )

    if not match_result.is_success():
        return jsonify({'success': False, 'error': match_result.get_error()}), 500

    # Return mappings
    mappings = match_result.get_data()
    return jsonify({
        'success': True,
        'mappings': mappings['mappings'],
        'unmapped': mappings['unmapped_psd_layers'],
        'unfilled': mappings['unfilled_placeholders']
    })
```

**Benefits:**
- ✅ Explicit validation before processing
- ✅ No try/catch needed
- ✅ Automatic logging of all operations
- ✅ Better error messages for users
- ✅ No crashes from uncaught exceptions

---

## Step-by-Step Migration

### Step 1: Add Import

**Old:**
```python
from modules.phase1 import psd_parser
from modules.phase2 import aepx_parser
from modules.phase3 import content_matcher
from modules.phase5 import preview_generator
```

**New:**
```python
from config.container import container

# That's it! Container provides access to all services
```

### Step 2: Replace Module Calls with Service Calls

**Pattern:**
```python
# OLD: module_name.function_name(args)
# NEW: container.service_name.method_name(args)
```

**Examples:**
```python
# OLD: psd_parser.parse_psd(path)
# NEW: container.psd_service.parse_psd(path)

# OLD: aepx_parser.parse_aepx(path)
# NEW: container.aepx_service.parse_aepx(path)

# OLD: content_matcher.match_content_to_slots(psd, aepx)
# NEW: container.matching_service.match_content(psd, aepx)

# OLD: preview_generator.generate_preview(aepx, mappings, output)
# NEW: container.preview_service.generate_preview(aepx, mappings, output)
```

### Step 3: Replace Try/Catch with Result Checking

**Old:**
```python
try:
    data = module.function(args)
    # use data
except FileNotFoundError:
    # handle error
except ValueError:
    # handle error
except Exception:
    # handle error
```

**New:**
```python
result = container.service.method(args)

if result.is_success():
    data = result.get_data()
    # use data
else:
    error = result.get_error()
    # handle error (already logged)
```

### Step 4: Add Validation (Optional but Recommended)

**New code can use validation methods:**
```python
# Validate before processing
valid = container.psd_service.validate_psd_file(path, max_size_mb=50)

if valid.is_success():
    # proceed with parsing
    result = container.psd_service.parse_psd(path)
else:
    # show validation error
    print(f"Invalid file: {valid.get_error()}")
```

---

## Benefits of Migration

### 1. Consistent Error Handling

**Before:** Different exceptions, different error formats
```python
try:
    data = psd_parser.parse_psd(path)
except FileNotFoundError as e:
    error = f"File not found: {e}"
except ValueError as e:
    error = f"Invalid PSD: {e}"
except Exception as e:
    error = f"Unknown error: {e}"
```

**After:** Uniform Result pattern
```python
result = container.psd_service.parse_psd(path)
if not result.is_success():
    error = result.get_error()  # Always a string, always clear
```

### 2. Automatic Logging

**Before:** Manual logging
```python
logger.info(f"Parsing {path}...")
try:
    data = psd_parser.parse_psd(path)
    logger.info(f"Parsed {len(data['layers'])} layers")
except Exception as e:
    logger.error(f"Failed to parse: {e}")
```

**After:** Automatic logging
```python
# Logging happens automatically in the service
result = container.psd_service.parse_psd(path)
# Logs: "Parsing PSD file: /path/to/file.psd"
# Logs: "Successfully parsed PSD with 15 layers"
# OR Logs: "Failed to parse PSD: /path/to/file.psd" with exception details
```

### 3. Built-in Validation

**Before:** Manual validation
```python
if not os.path.exists(path):
    raise FileNotFoundError(f"File not found: {path}")

if not path.endswith('.psd'):
    raise ValueError("Must be a PSD file")

file_size = os.path.getsize(path)
if file_size > 50 * 1024 * 1024:
    raise ValueError("File too large")

# Finally parse
data = psd_parser.parse_psd(path)
```

**After:** Validation included
```python
# All validation happens inside parse_psd
result = container.psd_service.parse_psd(path)
# Checks: file exists, correct extension, readable, valid format
```

### 4. Easier Testing

**Before:** Hard to test
```python
# Hard to mock direct module imports
def my_function():
    data = psd_parser.parse_psd(path)  # Calls real module
    return process(data)

# Tests require actual PSD files
```

**After:** Easy to mock
```python
def my_function():
    result = container.psd_service.parse_psd(path)
    if result.is_success():
        return process(result.get_data())

# Tests can mock the service
def test_my_function(mocker):
    mock_service = mocker.Mock()
    mock_service.parse_psd.return_value = Result.success({'layers': []})
    container.psd_service = mock_service

    # Now test without real files
    result = my_function()
```

---

## Common Patterns

### Pattern 1: Railway-Oriented Programming

Chain operations using `map()` and `flat_map()`:

```python
result = (
    container.psd_service.parse_psd(path)
    .flat_map(lambda data: container.psd_service.extract_fonts(data))
    .map(lambda fonts: sorted(fonts))
    .map(lambda fonts: {'count': len(fonts), 'fonts': fonts})
)

if result.is_success():
    data = result.get_data()
    print(f"Found {data['count']} fonts: {data['fonts']}")
else:
    print(f"Error: {result.get_error()}")
```

### Pattern 2: Early Return

Check results and return early on failure:

```python
def process_files(psd_path, aepx_path):
    # Parse PSD
    psd_result = container.psd_service.parse_psd(psd_path)
    if not psd_result.is_success():
        return {'error': psd_result.get_error()}

    # Parse AEPX
    aepx_result = container.aepx_service.parse_aepx(aepx_path)
    if not aepx_result.is_success():
        return {'error': aepx_result.get_error()}

    # Match content
    match_result = container.matching_service.match_content(
        psd_result.get_data(),
        aepx_result.get_data()
    )
    if not match_result.is_success():
        return {'error': match_result.get_error()}

    return {'success': True, 'data': match_result.get_data()}
```

### Pattern 3: Collect Multiple Results

Process multiple items and collect results:

```python
def process_multiple_psds(psd_paths):
    results = []

    for path in psd_paths:
        result = container.psd_service.parse_psd(path)

        if result.is_success():
            data = result.get_data()
            results.append({
                'path': path,
                'success': True,
                'layers': len(data['layers'])
            })
        else:
            results.append({
                'path': path,
                'success': False,
                'error': result.get_error()
            })

    return results
```

### Pattern 4: Validation Before Processing

Validate inputs before expensive operations:

```python
def generate_preview(psd_path, aepx_path, output_path):
    # Validate all inputs first (fast)
    psd_valid = container.psd_service.validate_psd_file(psd_path)
    aepx_valid = container.aepx_service.validate_aepx_file(aepx_path)

    if not (psd_valid.is_success() and aepx_valid.is_success()):
        errors = []
        if not psd_valid.is_success():
            errors.append(f"PSD: {psd_valid.get_error()}")
        if not aepx_valid.is_success():
            errors.append(f"AEPX: {aepx_valid.get_error()}")
        return {'success': False, 'errors': errors}

    # Now do expensive operations (parsing, matching, rendering)
    # ...
```

---

## Migration Checklist

When migrating a file:

- [ ] Replace module imports with `from config.container import container`
- [ ] Replace `module.function()` with `container.service.method()`
- [ ] Replace try/catch with Result pattern (`is_success()` / `get_error()`)
- [ ] Remove manual logging (services log automatically)
- [ ] Remove manual validation (services validate automatically)
- [ ] Add validation calls where needed (`validate_psd_file()`, etc.)
- [ ] Update tests to mock services instead of modules
- [ ] Update documentation/comments to reference services

---

## Need Help?

- See `REFACTORING_GUIDE.md` for detailed service architecture documentation
- See `examples/service_layer_example.py` for working code examples
- Check `services/` directory for available services and methods
- Look at existing service code for patterns

---

## Summary

**The service layer makes code:**
- ✅ More consistent (uniform error handling)
- ✅ More robust (built-in validation and logging)
- ✅ Easier to test (mockable services)
- ✅ Easier to maintain (separation of concerns)
- ✅ Safer to modify (existing modules untouched)

**Migration is incremental:**
- Old code continues to work
- Migrate file by file
- No breaking changes
- Service layer wraps existing modules
