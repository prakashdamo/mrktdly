# MrktDly Test Suite

## Overview
This directory contains unit and integration tests for the MrktDly project.

## Test Structure
```
tests/
├── unit/               # Unit tests for individual Lambda functions
│   ├── test_data_fetch.py
│   ├── test_ticker_analysis.py
│   └── test_ticker_precache.py
├── integration/        # End-to-end integration tests
│   └── test_end_to_end.py
└── README.md
```

## Running Tests

### Install Dependencies
```bash
pip install -r requirements-test.txt
```

### Run All Tests
```bash
./run_tests.sh
```

### Run Unit Tests Only
```bash
python3 -m unittest discover -s tests/unit -p "test_*.py" -v
```

### Run Integration Tests
```bash
RUN_INTEGRATION=true ./run_tests.sh
```

### Run Specific Test File
```bash
python3 -m unittest tests/unit/test_ticker_analysis.py -v
```

## Pre-Commit Hook

A pre-commit hook is installed that:
1. ✅ Runs all unit tests
2. ✅ Checks for Lambda changes without tests
3. ✅ Requires senior engineer review confirmation
4. ✅ Blocks commits if tests fail

## Writing Tests

### Unit Test Template
```python
import unittest
from unittest.mock import patch, MagicMock

class TestMyFunction(unittest.TestCase):
    
    def test_something(self):
        """Test description"""
        # Arrange
        expected = "result"
        
        # Act
        actual = my_function()
        
        # Assert
        self.assertEqual(actual, expected)
```

### Integration Test Template
```python
import unittest
import boto3

class TestIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.client = boto3.client('lambda')
    
    def test_end_to_end(self):
        """Test full workflow"""
        # Test actual AWS resources
        pass
```

## Test Coverage Requirements

- **Minimum Coverage**: 70%
- **Critical Functions**: 90%+
- **Lambda Handlers**: 100%

## Senior Engineer Review Checklist

Before committing Lambda changes, verify:
- [ ] Tests exist for new functionality
- [ ] All existing tests pass
- [ ] Edge cases are covered
- [ ] Error handling is tested
- [ ] Mocks are used appropriately
- [ ] Integration tests updated if needed
- [ ] Code follows best practices
- [ ] No hardcoded credentials or secrets
