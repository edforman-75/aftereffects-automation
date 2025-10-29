# Production-Grade Architecture Refactoring Guide

## ✅ Infrastructure Complete!

The foundation for a production-grade architecture has been created. This guide shows how to use the new service layer and incrementally refactor existing code.

## What's Been Created

### Directory Structure
```
aftereffects-automation/
├── services/              # NEW - Business logic layer
│   ├── __init__.py
│   ├── base_service.py   # Base class for all services
│   └── psd_service.py    # Example service implementation
├── core/                  # NEW - Core utilities
│   ├── exceptions.py     # Custom exception hierarchy
│   └── logging_config.py # Centralized logging
├── config/                # NEW - Configuration
│   └── container.py      # Dependency injection container
├── logs/                  # NEW - Log files storage
├── tests/                 # NEW - Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── modules/               # EXISTING - Keep unchanged for now
    └── phase1/
        └── psd_parser.py
```

### Key Components

**1. Result Pattern** (`services/base_service.py`)
- Encapsulates success/failure without throwing exceptions
- Enables railway-oriented programming
- Makes error handling explicit and type-safe

**2. Base Service** (`services/base_service.py`)
- Common functionality for all services
- Integrated logging
- Error handling utilities

**3. Custom Exceptions** (`core/exceptions.py`)
- Hierarchy of domain-specific exceptions
- Better error messages and debugging
- Consistent error handling

**4. Logging System** (`core/logging_config.py`)
- Rotating file logs
- Separate error log
- Console output
- Structured logging format

**5. Dependency Injection** (`config/container.py`)
- Centralized service management
- Singleton pattern
- Shared logging configuration

## How to Use

### Using the Service Layer

**Example: Parse a PSD file**

```python
# Old way (direct module call)
from modules.phase1 import psd_parser
psd_data = psd_parser.parse_psd(path)  # May throw exception

# New way (using service)
from config.container import container

result = container.psd_service.parse_psd(path)

if result.is_success():
    psd_data = result.get_data()
    # Process data
    print(f"Loaded {len(psd_data['layers'])} layers")
else:
    error = result.get_error()
    # Handle error gracefully
    print(f"Error: {error}")
    return jsonify({'error': error}), 400
```

**Example: Chaining operations with Result**

```python
# Parse PSD and extract fonts
result = (
    container.psd_service.parse_psd(psd_path)
    .flat_map(lambda data: container.psd_service.extract_fonts(data))
)

if result.is_success():
    fonts = result.get_data()
    print(f"Fonts used: {', '.join(fonts)}")
else:
    print(f"Error: {result.get_error()}")
```

**Example: Using in web routes**

```python
# web_app.py
from config.container import container

@app.route('/upload-psd', methods=['POST'])
def upload_psd():
    try:
        # Save uploaded file
        psd_file = request.files.get('psd')
        psd_path = save_file(psd_file)

        # Validate using service
        validation_result = container.psd_service.validate_psd_file(
            psd_path,
            max_size_mb=50
        )

        if not validation_result.is_success():
            return jsonify({
                'success': False,
                'error': validation_result.get_error()
            }), 400

        # Parse using service
        parse_result = container.psd_service.parse_psd(psd_path)

        if not parse_result.is_success():
            return jsonify({
                'success': False,
                'error': parse_result.get_error()
            }), 500

        psd_data = parse_result.get_data()

        # Extract fonts using service
        fonts_result = container.psd_service.extract_fonts(psd_data)

        return jsonify({
            'success': True,
            'data': {
                'layers': len(psd_data['layers']),
                'fonts': fonts_result.get_data_or_default([])
            }
        })

    except Exception as e:
        container.main_logger.error("Upload failed", exc_info=e)
        return jsonify({'error': 'Internal server error'}), 500
```

## Incremental Refactoring Strategy

### Phase 1: Add New Service (Current)

✅ **Completed:**
- Base infrastructure created
- PSDService as example
- No existing code modified

### Phase 2: Create More Services (Next)

Create services for other modules:

**AEPXService** (`services/aepx_service.py`):
```python
from services.base_service import BaseService, Result
from modules.phase2 import aepx_parser

class AEPXService(BaseService):
    def parse_aepx(self, aepx_path: str) -> Result[Dict]:
        self.log_info(f"Parsing AEPX: {aepx_path}")
        try:
            # Validate
            if not os.path.exists(aepx_path):
                return Result.failure(f"File not found: {aepx_path}")

            # Call existing module
            aepx_data = aepx_parser.parse_aepx(aepx_path)

            self.log_info("AEPX parsed successfully")
            return Result.success(aepx_data)

        except Exception as e:
            self.log_error("AEPX parsing failed", exc=e)
            return Result.failure(str(e))

    def find_placeholders(self, aepx_data: Dict) -> Result[List[str]]:
        # Implementation...
        pass
```

**MatchingService** (`services/matching_service.py`):
```python
from services.base_service import BaseService, Result
from modules.phase3 import content_matcher

class MatchingService(BaseService):
    def match_content(
        self,
        psd_data: Dict,
        aepx_data: Dict,
        confidence_threshold: float = 0.7
    ) -> Result[Dict]:
        self.log_info("Matching PSD content to AEPX placeholders")
        try:
            # Call existing module
            mappings = content_matcher.match_content_to_slots(
                psd_data,
                aepx_data,
                threshold=confidence_threshold
            )

            self.log_info(f"Created {len(mappings)} mappings")
            return Result.success(mappings)

        except Exception as e:
            self.log_error("Matching failed", exc=e)
            return Result.failure(str(e))
```

**PreviewService** (`services/preview_service.py`):
```python
from services.base_service import BaseService, Result
from modules.phase5 import preview_generator

class PreviewService(BaseService):
    def generate_preview(
        self,
        aepx_path: str,
        mappings: Dict,
        output_path: str,
        options: Dict = None
    ) -> Result[Dict]:
        self.log_info(f"Generating preview: {output_path}")
        try:
            # Validate inputs
            if not os.path.exists(aepx_path):
                return Result.failure(f"AEPX not found: {aepx_path}")

            # Call existing module
            result = preview_generator.generate_preview(
                aepx_path,
                mappings,
                output_path,
                options or {}
            )

            if result.get('success'):
                self.log_info("Preview generated successfully")
                return Result.success(result)
            else:
                return Result.failure(result.get('error', 'Unknown error'))

        except Exception as e:
            self.log_error("Preview generation failed", exc=e)
            return Result.failure(str(e))
```

**Add to container** (`config/container.py`):
```python
def _initialize_services(self):
    self.psd_service = PSDService(logger=get_service_logger('psd'))
    self.aepx_service = AEPXService(logger=get_service_logger('aepx'))
    self.matching_service = MatchingService(logger=get_service_logger('matching'))
    self.preview_service = PreviewService(logger=get_service_logger('preview'))
```

### Phase 3: Refactor Web Routes

Gradually refactor routes to use services:

**Before:**
```python
@app.route('/upload', methods=['POST'])
def upload():
    psd_data = psd_parser.parse_psd(psd_path)  # Direct call
    aepx_data = aepx_parser.parse_aepx(aepx_path)
    # ...
```

**After:**
```python
@app.route('/upload', methods=['POST'])
def upload():
    psd_result = container.psd_service.parse_psd(psd_path)
    if not psd_result.is_success():
        return jsonify({'error': psd_result.get_error()}), 400

    aepx_result = container.aepx_service.parse_aepx(aepx_path)
    if not aepx_result.is_success():
        return jsonify({'error': aepx_result.get_error()}), 400

    psd_data = psd_result.get_data()
    aepx_data = aepx_result.get_data()
    # ...
```

### Phase 4: Add Tests

Create unit tests for services:

**Example: Test PSDService** (`tests/unit/test_psd_service.py`):
```python
import pytest
import logging
from pathlib import Path
from services.psd_service import PSDService

@pytest.fixture
def psd_service():
    """Create a PSDService instance for testing."""
    logger = logging.getLogger('test_psd')
    return PSDService(logger)

@pytest.fixture
def sample_psd_path():
    """Path to sample PSD file for testing."""
    return Path('tests/fixtures/sample.psd')

def test_parse_psd_success(psd_service, sample_psd_path):
    """Test successful PSD parsing."""
    result = psd_service.parse_psd(str(sample_psd_path))

    assert result.is_success()
    assert result.get_data() is not None

    data = result.get_data()
    assert 'layers' in data
    assert isinstance(data['layers'], list)

def test_parse_psd_file_not_found(psd_service):
    """Test PSD parsing with non-existent file."""
    result = psd_service.parse_psd('nonexistent.psd')

    assert result.is_failure()
    assert 'not found' in result.get_error().lower()

def test_parse_psd_invalid_extension(psd_service):
    """Test PSD parsing with wrong file extension."""
    result = psd_service.parse_psd('file.txt')

    assert result.is_failure()
    assert 'extension' in result.get_error().lower()

def test_extract_fonts_success(psd_service):
    """Test font extraction from PSD data."""
    psd_data = {
        'layers': [
            {
                'type': 'text',
                'text': {'font': 'Arial'}
            },
            {
                'type': 'text',
                'text': {'font': 'Helvetica'}
            },
            {
                'type': 'image'  # Should be ignored
            }
        ]
    }

    result = psd_service.extract_fonts(psd_data)

    assert result.is_success()
    fonts = result.get_data()
    assert 'Arial' in fonts
    assert 'Helvetica' in fonts
    assert len(fonts) == 2

def test_extract_fonts_empty(psd_service):
    """Test font extraction with no text layers."""
    psd_data = {
        'layers': [
            {'type': 'image'}
        ]
    }

    result = psd_service.extract_fonts(psd_data)

    assert result.is_success()
    assert result.get_data() == []

def test_validate_psd_file_too_large(psd_service, tmp_path):
    """Test validation fails for oversized file."""
    # Create a file that's too large
    large_file = tmp_path / "large.psd"
    large_file.write_bytes(b'8BPS' + b'x' * (51 * 1024 * 1024))

    result = psd_service.validate_psd_file(str(large_file), max_size_mb=50)

    assert result.is_failure()
    assert 'too large' in result.get_error().lower()
```

**Test configuration** (`tests/conftest.py`):
```python
import pytest
from pathlib import Path

@pytest.fixture(scope='session')
def fixtures_dir():
    """Get the fixtures directory."""
    return Path(__file__).parent / 'fixtures'

@pytest.fixture(scope='session')
def sample_psd(fixtures_dir):
    """Path to sample PSD file."""
    return fixtures_dir / 'sample.psd'

@pytest.fixture(scope='session')
def sample_aepx(fixtures_dir):
    """Path to sample AEPX file."""
    return fixtures_dir / 'sample.aepx'
```

**Run tests:**
```bash
# Install pytest
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov-report=html

# Run specific test file
pytest tests/unit/test_psd_service.py

# Run specific test
pytest tests/unit/test_psd_service.py::test_parse_psd_success
```

## Benefits of This Architecture

### 1. Testability
✅ **Before:** Direct module calls, hard to test
✅ **After:** Services can be tested in isolation with mocks

### 2. Error Handling
✅ **Before:** Exceptions everywhere, inconsistent handling
✅ **After:** Explicit Result types, consistent error management

### 3. Logging
✅ **Before:** Ad-hoc print statements
✅ **After:** Structured logging throughout, separate log files

### 4. Maintainability
✅ **Before:** Business logic mixed with web layer
✅ **After:** Clear separation of concerns

### 5. Upgradability
✅ **Before:** Changing implementations breaks everything
✅ **After:** Swap service implementations without breaking callers

### 6. Type Safety
✅ **Before:** No type hints, runtime errors
✅ **After:** Type-hinted Results, IDE support

### 7. Observable
✅ **Before:** Hard to debug production issues
✅ **After:** Comprehensive logging, error tracking

## Best Practices

### 1. Always Use Result Types

```python
# ❌ Don't throw exceptions
def parse_psd(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    # ...

# ✅ Return Result
def parse_psd(path) -> Result[Dict]:
    if not os.path.exists(path):
        return Result.failure(f"File not found: {path}")
    # ...
```

### 2. Log Important Operations

```python
def parse_psd(path) -> Result[Dict]:
    self.log_info(f"Parsing PSD: {path}")
    # ... do work
    self.log_info("PSD parsed successfully")
    return Result.success(data)
```

### 3. Validate Inputs

```python
def parse_psd(path) -> Result[Dict]:
    # Validate existence
    if not os.path.exists(path):
        return Result.failure("File not found")

    # Validate extension
    if not path.endswith('.psd'):
        return Result.failure("Invalid file extension")

    # Validate size
    if os.path.getsize(path) > MAX_SIZE:
        return Result.failure("File too large")

    # ... proceed with parsing
```

### 4. Keep Services Focused

Each service should have a single responsibility:
- PSDService: PSD operations only
- AEPXService: AEPX operations only
- MatchingService: Matching logic only

### 5. Use Dependency Injection

```python
# ❌ Don't create dependencies directly
class MatchingService:
    def __init__(self):
        self.psd_service = PSDService()  # Hard dependency

# ✅ Inject dependencies
class MatchingService:
    def __init__(self, psd_service: PSDService):
        self.psd_service = psd_service  # Injected, easy to mock
```

## Migration Checklist

- [x] Create service layer infrastructure
- [x] Create base service class with Result pattern
- [x] Create custom exception hierarchy
- [x] Setup logging system
- [x] Create dependency injection container
- [x] Create example PSDService
- [ ] Create AEPXService
- [ ] Create MatchingService
- [ ] Create PreviewService
- [ ] Create ProjectService
- [ ] Refactor web routes to use services
- [ ] Add comprehensive test suite
- [ ] Add integration tests
- [ ] Update configuration to use services
- [ ] Add API documentation
- [ ] Deploy and monitor

## Example: Complete Workflow with Services

```python
from config.container import container

def process_graphics(psd_path: str, aepx_path: str):
    """Process graphics using service layer."""

    # 1. Validate and parse PSD
    psd_result = (
        container.psd_service.validate_psd_file(psd_path)
        .flat_map(lambda _: container.psd_service.parse_psd(psd_path))
    )

    if not psd_result.is_success():
        print(f"PSD Error: {psd_result.get_error()}")
        return

    # 2. Validate and parse AEPX
    aepx_result = container.aepx_service.parse_aepx(aepx_path)

    if not aepx_result.is_success():
        print(f"AEPX Error: {aepx_result.get_error()}")
        return

    # 3. Match content
    matching_result = container.matching_service.match_content(
        psd_result.get_data(),
        aepx_result.get_data()
    )

    if not matching_result.is_success():
        print(f"Matching Error: {matching_result.get_error()}")
        return

    # 4. Generate preview
    preview_result = container.preview_service.generate_preview(
        aepx_path,
        matching_result.get_data(),
        'output/preview.mp4'
    )

    if preview_result.is_success():
        print("✅ Preview generated successfully!")
    else:
        print(f"Preview Error: {preview_result.get_error()}")
```

## Summary

✅ **Infrastructure Created:**
- Service layer with Result pattern
- Custom exception hierarchy
- Centralized logging
- Dependency injection container
- Example PSDService
- Test suite structure

✅ **Ready for Incremental Migration:**
- Existing code unchanged
- New services wrap existing modules
- Can migrate route-by-route
- Full backward compatibility

✅ **Production-Grade Features:**
- Testable architecture
- Comprehensive error handling
- Structured logging
- Type safety
- Clear separation of concerns

**Next Steps:**
1. Create remaining services (AEPX, Matching, Preview)
2. Start migrating web routes to use services
3. Add comprehensive test coverage
4. Monitor logs and refine error handling

This architecture provides a solid foundation for building a maintainable, testable, production-grade application! 🎉
