# Contributing to MrktDly

## Testing Requirements

**All commits MUST pass tests and senior engineer review.**

### Pre-Commit Checklist

Before committing any code changes:

- [ ] **Run tests**: `./run_tests.sh`
- [ ] **All tests pass**: Minimum 4/4 smoke tests
- [ ] **Tests exist** for new Lambda functions
- [ ] **No breaking changes** to existing tests
- [ ] **Code review** completed as senior engineer
- [ ] **Best practices** followed

### Running Tests

```bash
# Run all tests
./run_tests.sh

# Run specific test
python3 -m unittest tests/unit/test_smoke.py -v

# Run with full dependencies
pip install -r requirements-test.txt
./run_tests.sh
```

### Pre-Commit Hook

A pre-commit hook automatically:
1. ✅ Runs test suite
2. ✅ Checks for Lambda changes
3. ✅ Requires senior engineer review confirmation
4. ❌ Blocks commit if tests fail

### Senior Engineer Review

When committing Lambda changes, you must verify:

1. **Tests Exist**: Every Lambda function has corresponding tests
2. **Tests Pass**: All existing tests still pass
3. **Best Practices**:
   - No hardcoded credentials
   - Proper error handling
   - Efficient code
   - Clear documentation
   - Type hints where applicable

### Test Coverage

- **Smoke Tests**: 100% (required)
- **Unit Tests**: 70%+ (recommended)
- **Integration Tests**: Optional but encouraged

### Adding New Tests

When adding a new Lambda function:

1. Create test file: `tests/unit/test_<function_name>.py`
2. Add smoke test for file existence
3. Add unit tests for core functionality
4. Update this documentation

### Example Test

```python
import unittest

class TestMyFunction(unittest.TestCase):
    def test_something(self):
        """Test description"""
        self.assertEqual(1 + 1, 2)
```

### CI/CD Pipeline

GitHub Actions automatically:
- Runs tests on every push
- Checks code coverage
- Runs linting
- Blocks merge if tests fail

### Bypassing Pre-Commit Hook

**Only for emergencies:**
```bash
git commit --no-verify -m "Emergency fix"
```

**Note**: This should be rare and requires post-commit review.

## Code Standards

- Python 3.11+
- PEP 8 style guide
- Type hints encouraged
- Docstrings for all functions
- Max line length: 100 characters

## Questions?

See `tests/README.md` for detailed testing documentation.
