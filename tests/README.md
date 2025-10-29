# Test Suite Documentation

Comprehensive test suite for the After Effects Automation project using pytest.

---

## Quick Start

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
./run_tests.sh
```

Or directly with pytest:

```bash
pytest tests/
```

---

## Test Structure

```
tests/
├── unit/                      # Unit tests (individual components)
│   ├── test_psd_service.py    # PSD service tests
│   ├── test_aepx_service.py   # AEPX service tests
│   ├── test_matching_service.py  # Matching service tests
│   └── test_preview_service.py   # Preview service tests
├── integration/               # Integration tests (multiple components)
│   └── test_full_workflow.py # Complete workflow tests
├── fixtures/                  # Test data files (if needed)
└── conftest.py               # Shared fixtures
```

---

## Running Tests

### All Tests with Coverage

```bash
./run_tests.sh
```

or

```bash
pytest tests/ --cov=services --cov=core --cov-report=html
```

### Quick Tests (Unit Only)

```bash
./run_tests.sh quick
```

or

```bash
pytest tests/unit/ -v
```

### Integration Tests Only

```bash
./run_tests.sh integration
```

or

```bash
pytest tests/integration/ -v
```

### Specific Test File

```bash
pytest tests/unit/test_psd_service.py -v
```

### Specific Test Class

```bash
pytest tests/unit/test_psd_service.py::TestPSDServiceParsing -v
```

### Specific Test Method

```bash
pytest tests/unit/test_psd_service.py::TestPSDServiceParsing::test_parse_psd_file_not_found -v
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

---

## Test Markers

Tests are marked with these markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, multiple components)
- `@pytest.mark.slow` - Tests that take a long time
- `@pytest.mark.requires_ae` - Tests that require After Effects installed

View all markers:

```bash
pytest --markers
```

---

## Test Coverage

### View Coverage Report

After running tests with coverage:

```bash
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

### Coverage Goals

- **Overall coverage:** >80%
- **Services:** >90%
- **Critical paths:** 100%

### Check Coverage for Specific Module

```bash
pytest tests/ --cov=services.psd_service --cov-report=term-missing
```

---

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test Structure

```python
import pytest
from services.psd_service import PSDService

@pytest.fixture
def psd_service():
    """Create service instance for testing."""
    return PSDService(logger=None)

class TestPSDServiceFeature:
    """Test specific feature of PSD service."""

    @pytest.mark.unit
    def test_feature_success_case(self, psd_service):
        """Test successful operation."""
        result = psd_service.some_method()

        assert result.is_success()
        data = result.get_data()
        assert data is not None

    @pytest.mark.unit
    def test_feature_error_case(self, psd_service):
        """Test error handling."""
        result = psd_service.some_method(invalid_input)

        assert not result.is_success()
        assert 'error' in result.get_error().lower()
```

### Testing Best Practices

1. **Test both success and failure cases**
   - Happy path: normal operation
   - Error path: invalid inputs, edge cases

2. **Use fixtures for common setup**
   - Defined in `conftest.py`
   - Available to all tests

3. **Keep tests independent**
   - No shared state between tests
   - Each test can run in isolation

4. **Test one thing at a time**
   - Single assertion focus
   - Clear test purpose

5. **Use descriptive names**
   - `test_parse_psd_file_not_found` not `test_1`
   - Names explain what is being tested

6. **Use markers appropriately**
   - Mark slow tests with `@pytest.mark.slow`
   - Mark integration tests with `@pytest.mark.integration`

---

## Available Fixtures

Fixtures are defined in `conftest.py` and available to all tests.

### File Fixtures

- `temp_dir` - Temporary directory for test files
- `sample_psd_path` - Path to sample PSD (no file created)
- `sample_aepx_path` - Path to sample AEPX (no file created)
- `sample_image` - Creates test image file
- `large_image` - Creates large test image
- `invalid_psd_file` - Creates invalid PSD file
- `invalid_aepx_file` - Creates invalid AEPX file
- `valid_aepx_file` - Creates minimal valid AEPX

### Data Fixtures

- `mock_psd_data` - Mock PSD data structure
- `mock_aepx_data` - Mock AEPX data structure
- `mock_mappings` - Mock content mappings
- `mock_preview_options` - Mock preview options
- `empty_psd_data` - Empty PSD data
- `empty_aepx_data` - Empty AEPX data

### Using Fixtures

```python
def test_with_fixture(mock_psd_data):
    """Test using mock data fixture."""
    # mock_psd_data is automatically provided
    assert 'layers' in mock_psd_data
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest tests/ --cov=services --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Troubleshooting

### Tests Not Found

```bash
# Verify pytest can discover tests
pytest --collect-only
```

### Import Errors

```bash
# Ensure you're in the project root
cd /Users/edf/aftereffects-automation

# Run tests from project root
pytest tests/
```

### Fixture Not Found

- Check `conftest.py` for fixture definition
- Verify fixture name matches exactly
- Ensure `conftest.py` is in `tests/` directory

### Coverage Not Working

```bash
# Install coverage plugin
pip install pytest-cov

# Run with explicit coverage
pytest tests/ --cov=services --cov=core
```

---

## Test Output Examples

### Successful Test Run

```
tests/unit/test_psd_service.py::TestPSDServiceParsing::test_parse_psd_file_not_found PASSED
tests/unit/test_psd_service.py::TestPSDServiceParsing::test_parse_psd_invalid_extension PASSED
...

========== 45 passed in 2.31s ==========
```

### Failed Test

```
tests/unit/test_psd_service.py::TestPSDServiceParsing::test_example FAILED

FAILED tests/unit/test_psd_service.py::TestPSDServiceParsing::test_example
AssertionError: assert False
```

### Coverage Report

```
---------- coverage: platform darwin, python 3.9.6 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
services/base_service.py            50      2    96%   45, 67
services/psd_service.py            120      8    93%   112-115, 201-204
services/aepx_service.py           140     12    91%   ...
services/matching_service.py       180     15    92%   ...
---------------------------------------------------------------
TOTAL                              490     37    92%
```

---

## Future Improvements

- [ ] Add performance benchmarks
- [ ] Add tests for web routes
- [ ] Add end-to-end tests with real files
- [ ] Add load testing for concurrent requests
- [ ] Add mutation testing
- [ ] Improve test coverage to >95%

---

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)

---

## Support

For questions or issues with tests:

1. Check test output carefully
2. Run with verbose mode: `pytest -vv`
3. Check fixture definitions in `conftest.py`
4. Review test examples in existing test files
