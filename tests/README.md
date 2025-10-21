# 🧪 Trading Bot Test Suite

Comprehensive testing framework for the Market Adaptive Trading Bot system.

## 📁 Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                    # Pytest configuration
├── requirements.txt               # Test dependencies
├── run_tests.py                   # Test runner script
├── README.md                      # This file
├── unit/                          # Unit tests
│   ├── test_models.py            # Core data models
│   ├── test_technical_analysis_layer.py  # Technical analysis
│   ├── test_risk_manager.py      # Risk management
│   ├── test_data_layer.py        # Data layer
│   └── test_config.py            # Configuration
├── integration/                   # Integration tests
│   ├── test_trading_bot_integration.py  # Complete system flow
│   └── test_api_integration.py   # API interactions
└── edge_cases/                    # Edge case tests
    └── test_edge_cases.py        # Error conditions and edge cases
```

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
# Install test dependencies
python tests/run_tests.py --install-deps

# Or manually
pip install -r tests/requirements.txt
```

### 2. Run Tests

```bash
# Run all tests
python tests/run_tests.py --all

# Run specific test types
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --edge

# Run with coverage
python tests/run_tests.py --all --coverage

# Run specific test file
python tests/run_tests.py --test tests/unit/test_models.py

# Run specific test function
python tests/run_tests.py --test tests/unit/test_models.py::TestCandleData::test_candle_data_creation_success
```

### 3. Generate Reports

```bash
# Generate comprehensive test report
python tests/run_tests.py --report

# Run linting checks
python tests/run_tests.py --lint

# Run type checking
python tests/run_tests.py --type-check
```

## 🧪 Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:

- **`test_models.py`** - Core data models and validation
- **`test_technical_analysis_layer.py`** - Technical analysis algorithms
- **`test_risk_manager.py`** - Risk management logic
- **`test_data_layer.py`** - Data collection and processing
- **`test_config.py`** - Configuration management

### Integration Tests (`tests/integration/`)

Test component interactions:

- **`test_trading_bot_integration.py`** - Complete trading flow
- **`test_api_integration.py`** - OANDA API interactions

### Edge Case Tests (`tests/edge_cases/`)

Test error conditions and boundary cases:

- **`test_edge_cases.py`** - Invalid data, extreme values, error handling

## 🏷️ Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.edge` - Edge case tests
- `@pytest.mark.ai` - AI-related tests
- `@pytest.mark.risk` - Risk management tests
- `@pytest.mark.notification` - Notification tests
- `@pytest.mark.slow` - Slow running tests

## 🔧 Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    edge: Edge case tests
    # ... more markers
```

### Test Dependencies (`requirements.txt`)

Comprehensive testing stack:

- **pytest** - Core testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities
- **hypothesis** - Property-based testing
- **faker** - Test data generation

## 📊 Coverage Requirements

- **Minimum Coverage**: 80%
- **Critical Components**: 90%+
- **Coverage Reports**: HTML and terminal output

## 🚨 Test Execution

### Running Tests

```bash
# Basic test run
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific markers
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "edge"

# Parallel execution
pytest tests/ -n 4

# Verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x
```

### Test Output

Tests provide detailed output including:

- Test execution status
- Coverage reports
- Performance metrics
- Error details
- Test duration

## 🔍 Debugging Tests

### Running Individual Tests

```bash
# Run specific test file
pytest tests/unit/test_models.py

# Run specific test class
pytest tests/unit/test_models.py::TestCandleData

# Run specific test method
pytest tests/unit/test_models.py::TestCandleData::test_candle_data_creation_success

# Run with debug output
pytest tests/unit/test_models.py -v -s
```

### Test Debugging

```python
# Add breakpoints in tests
import pdb; pdb.set_trace()

# Use pytest's built-in debugging
pytest tests/ --pdb

# Print debug information
print(f"Debug: {variable}")
```

## 📈 Performance Testing

### Benchmark Tests

```bash
# Run performance benchmarks
pytest tests/ --benchmark-only

# Compare with previous runs
pytest tests/ --benchmark-compare

# Save benchmark results
pytest tests/ --benchmark-save=my_benchmark
```

### Memory Profiling

```bash
# Run memory profiling
pytest tests/ --profile

# Memory usage analysis
pytest tests/ --memray
```

## 🛠️ Test Development

### Writing New Tests

1. **Follow naming conventions**:
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test methods: `test_*`

2. **Use appropriate markers**:
   ```python
   @pytest.mark.unit
   def test_something():
       pass
   ```

3. **Use fixtures for setup**:
   ```python
   def test_with_fixture(sample_candles):
       assert len(sample_candles) > 0
   ```

4. **Mock external dependencies**:
   ```python
   @patch('module.external_dependency')
   def test_with_mock(mock_dependency):
       mock_dependency.return_value = "mocked"
       # test logic
   ```

### Test Data

- Use `conftest.py` for shared fixtures
- Generate realistic test data
- Test edge cases and error conditions
- Validate input/output formats

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## 🚀 Continuous Integration

### GitHub Actions

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
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r tests/requirements.txt
      - name: Run tests
        run: python tests/run_tests.py --all --coverage
```

### Pre-commit Hooks

```yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: python tests/run_tests.py --unit
        language: system
        pass_filenames: false
```

## 📋 Test Checklist

Before committing code:

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Edge case tests pass
- [ ] Coverage meets requirements (80%+)
- [ ] No linting errors
- [ ] Type checking passes
- [ ] Performance tests pass
- [ ] Documentation updated

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Add src to Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

2. **Async Test Issues**:
   ```python
   # Use pytest-asyncio
   pytest tests/ --asyncio-mode=auto
   ```

3. **Mock Issues**:
   ```python
   # Ensure proper patching
   @patch('module.path.Class.method')
   def test_with_mock(mock_method):
       # test logic
   ```

4. **Coverage Issues**:
   ```bash
   # Check coverage configuration
   pytest tests/ --cov=src --cov-report=term-missing
   ```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Asyncio](https://pytest-asyncio.readthedocs.io/)
- [Pytest-Cov](https://pytest-cov.readthedocs.io/)
- [Hypothesis](https://hypothesis.readthedocs.io/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## 🤝 Contributing

When adding new tests:

1. Follow existing patterns
2. Add appropriate markers
3. Include docstrings
4. Test both success and failure cases
5. Update this README if needed

## 📞 Support

For test-related issues:

1. Check this README
2. Review existing test patterns
3. Check pytest documentation
4. Create an issue with test details

