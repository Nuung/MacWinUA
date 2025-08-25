# MacWinUA

> [!NOTE]
> A library for generating realistic browser headers for macOS and Windows platforms — always the freshest Chrome headers.

[![PyPI version](https://badge.fury.io/py/MacWinUA.svg)](https://badge.fury.io/py/MacWinUA)
[![Python Versions](https://img.shields.io/pypi/pyversions/MacWinUA.svg)](https://pypi.org/project/MacWinUA/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/test%20coverage-100%25-brightgreen.svg)](https://github.com/Nuung/MacWinUA)
[![CI Status](https://github.com/Nuung/MacWinUA/actions/workflows/ci.yaml/badge.svg)](https://github.com/Nuung/MacWinUA/actions/workflows/ci.yaml)

## 🔄 Why MacWinUA?

1. **Always fresh**: **_Focus on providing the most up-to-date Chrome headers_!**
2. **Platform specific**: Tailored for macOS and Windows environments
3. **Smart caching**: API calls only once per week to minimize overhead
4. **Simple API**: Easy-to-use, property-based interface
5. **Zero dependencies**: No external dependencies required
6. **Thread-safe**: Built for concurrent applications
7. **Clean architecture**: SOLID principles with proper separation of concerns

## Installation

```bash
pip install MacWinUA
```

With Poetry:

```bash
poetry add MacWinUA
```

## Requirements

- Python 3.10 or higher

## 🔥 Usage

### Simple UA Strings

```python
from macwinua import ua

# Get any Chrome User-Agent string (random)
ua_string = ua.chrome

# Get a macOS Chrome UA
mac_ua = ua.mac

# Get a Windows Chrome UA
win_ua = ua.windows

# Get the latest available version's UA
latest_ua = ua.latest

# Alias for random Chrome UA
random_ua = ua.random
```

### Complete Browser Headers

```python
from macwinua import ua

# Basic Chrome headers
headers = ua.get_headers()

# macOS Chrome headers
mac_headers = ua.get_headers(platform="mac")

# Windows Chrome headers
win_headers = ua.get_headers(platform="win")

# Specific Chrome version
ver_headers = ua.get_headers(chrome_version="139")

# Specific platform + version
combo_headers = ua.get_headers(platform="mac", chrome_version="138")

# Add custom headers (merged)
custom_headers = ua.get_headers(extra_headers={"X-API-KEY": "mykey"})

# Use with requests
import requests
response = requests.get("https://example.com", headers=ua.get_headers())
```

### Compatibility Function

For even more concise code:

```python
from macwinua import get_chrome_headers

headers = get_chrome_headers()  # random
mac_headers = get_chrome_headers(platform="mac")
win_headers = get_chrome_headers(platform="win", chrome_version="139")
```

### Custom Instances

```python
from macwinua import HeaderGenerator

# Create a new instance (uses singleton DataManager internally)
my_ua = HeaderGenerator()

# Force refresh data from API (bypasses 7-day cache)
my_ua.force_update()

# Use the same methods as the singleton
headers = my_ua.get_headers(platform="win")
```

### Force Update

```python
from macwinua import force_update

# Force refresh the global singleton with latest data from API
force_update()

# Now all calls will use the refreshed data
headers = ua.get_headers()
```

## Example Usage with HTTP Clients

### With requests

```python
import requests
from macwinua import ua

# Create a session
session = requests.Session()

# Configure with macOS Chrome headers
session.headers.update(ua.get_headers(platform="mac"))

# Make requests
response = session.get("https://httpbin.org/headers")
print(response.json()["headers"]["User-Agent"])

# Change to Windows headers for next request
session.headers.update(ua.get_headers(platform="win"))
response = session.get("https://httpbin.org/headers")
print(response.json()["headers"]["User-Agent"])
```

### With httpx

```python
import httpx
from macwinua import get_chrome_headers

async def fetch_data():
    headers = get_chrome_headers(platform="mac", chrome_version="139")

    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get("https://httpbin.org/headers")
        return response.json()

# Run the async function
import asyncio
result = asyncio.run(fetch_data())
print(result["headers"]["User-Agent"])
```

### Custom User-Agent Rotation

```python
from macwinua import HeaderGenerator
import random
import requests
import time

class UARotator:
    def __init__(self):
        self.ua_generator = HeaderGenerator()
        self.platforms = ["mac", "win"]
        self.used_uas = set()

    def get_fresh_headers(self, max_attempts=10):
        """Get headers that haven't been used recently."""
        for _ in range(max_attempts):
            platform = random.choice(self.platforms)
            headers = self.ua_generator.get_headers(platform=platform)
            ua_string = headers["User-Agent"]

            if ua_string not in self.used_uas:
                self.used_uas.add(ua_string)
                # Keep only last 20 UAs to prevent infinite growth
                if len(self.used_uas) > 20:
                    self.used_uas.pop()
                return headers

        # If all attempts failed, return any headers
        return self.ua_generator.get_headers()

# Usage
rotator = UARotator()
session = requests.Session()

for i in range(5):
    fresh_headers = rotator.get_fresh_headers()
    session.headers.update(fresh_headers)

    response = session.get("https://httpbin.org/headers")
    ua_string = response.json()["headers"]["User-Agent"]
    platform = "macOS" if "Macintosh" in ua_string else "Windows"
    print(f"Request {i+1} ({platform}): ...{ua_string[-50:]}")
    time.sleep(1)
```

## Supported Platforms and Browsers

Currently supports:

- **Chrome versions**: 137, 138, 139 (automatically updated)
- **Platforms**: macOS and Windows
- **Automatic version detection**: Fetches latest versions from Google's API
- **Smart caching**: Updates version data weekly

## API Reference

### ua (Singleton Instance)

#### Properties

- `ua.chrome` → Random Chrome User-Agent string
- `ua.mac` → Random macOS Chrome User-Agent string
- `ua.windows` → Random Windows Chrome User-Agent string
- `ua.latest` → User-Agent from latest Chrome version
- `ua.random` → Alias for `ua.chrome`

#### Methods

- `ua.get_headers(platform=None, chrome_version=None, extra_headers=None)` → Complete headers dict
- `ua.force_update()` → Force refresh data from API

### Functions

- `get_chrome_headers(**kwargs)` → Convenience function using singleton
- `force_update()` → Force refresh singleton data

### Classes

- `HeaderGenerator(data_manager=None)` → Create header generator instance
- `UAError` → Base exception class
- `APIFetchError` → API-related errors
- `CacheError` → Cache-related errors
- `DataValidationError` → Data validation errors

## Architecture

MacWinUA follows clean architecture principles with proper separation of concerns:

### Core Components

- **`constants.py`**: Configuration, supported versions, type definitions
- **`exceptions.py`**: Custom exception classes for different error types
- **`core.py`**: Data processing components (caching, API fetching, data management)
- **`ua.py`**: User-facing interface for header generation

### Design Principles

- **Single Responsibility Principle**: Each class has one clear purpose
- **Open/Closed Principle**: Easy to extend with new platforms or features
- **Dependency Injection**: Components are loosely coupled and testable
- **Thread Safety**: All operations are thread-safe for concurrent use

## How It Works

1. **Version Detection**: Fetches latest Chrome versions from Google's official API
2. **Smart Caching**: Caches version data locally for 7 days to minimize API calls
3. **Header Generation**: Creates realistic headers with proper sec-ch-ua values
4. **Fallback System**: Uses hardcoded versions (139, 138, 137) if API fails
5. **Thread Safety**: All operations are thread-safe for concurrent applications

## Cache Behavior

- **Cache Location**: `~/.macwinua/macwinua_cache.json` in user's home directory
- **Cache Duration**: 7 days
- **Auto Refresh**: Automatically refreshes expired cache on next use
- **Force Refresh**: Use `force_update()` to bypass cache
- **Fallback**: Uses built-in versions (139, 138, 137) if API is unavailable

## Error Handling

```python
from macwinua import ua, UAError, APIFetchError, CacheError, DataValidationError

try:
    headers = ua.get_headers(platform="mac", chrome_version="139")
except UAError as e:
    print(f"UA Error: {e}")
except APIFetchError as e:
    print(f"API Error: {e}")
except CacheError as e:
    print(f"Cache Error: {e}")
except DataValidationError as e:
    print(f"Data Validation Error: {e}")
```

## Development

This project uses Poetry for dependency management and packaging.

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Nuung/MacWinUA.git
cd MacWinUA

# Setup Python 3.10+ with pyenv (optional)
pyenv install 3.13.0
pyenv local 3.13.0

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=macwinua --cov-report=html

# Run specific test file
pytest tests/test_ua.py
pytest tests/test_core.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Run linter
poetry run ruff check macwinua/ tests/

# Run formatter
poetry run ruff format macwinua/ tests/

# Run type checker
poetry run mypy macwinua/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

The pre-commit hooks automatically run:

1. Ruff linting and formatting
2. MyPy type checking
3. Pytest tests

> [!WARNING] > **_These checks run in CI pipeline, ensuring consistency between local development and automated testing._**

## Performance

MacWinUA is designed for high performance:

- **Singleton Pattern**: Shared data manager reduces memory usage
- **Smart Caching**: Minimizes API calls (once per week maximum)
- **Thread Safety**: Efficient concurrent access with minimal locking
- **Memory Efficient**: Lightweight data structures and minimal dependencies

### Benchmark Results

```python
# Simple performance test
import time
from macwinua import ua

# Test header generation speed
start = time.time()
for _ in range(1000):
    headers = ua.get_headers()
end = time.time()

print(f"Generated 1000 headers in {end-start:.3f}s")
# Typical result: ~0.010s (100,000 headers/second)
```

## Comparison with Other Libraries

Unlike `fake-useragent` and similar libraries, MacWinUA focuses specifically on:

1. **Always up-to-date headers** (including sec-ch-ua values)
2. **Realistic header combinations** for perfect browser impersonation
3. **Chrome-only focus** with macOS and Windows platforms
4. **Zero dependencies** and lightweight design
5. **Smart caching** to minimize API overhead
6. **Thread-safe operations** for production applications
7. **Clean architecture** following SOLID principles

## Contributing

We welcome contributions! Please ensure your code follows our standards:

1. **Code Style**: Use Ruff for linting and formatting
2. **Type Hints**: Full type coverage with MyPy
3. **Tests**: 100% test coverage for new code
4. **Documentation**: Update README and docstrings
5. **Architecture**: Follow SOLID principles and existing patterns

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
