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
3. **Simple API**: Easy-to-use, property-based interface
4. **Lightweight**: No external dependencies
5. **Fast**: Built-in memoization for performance

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
ver_headers = ua.get_headers(chrome_version="137")

# Specific platform + version
combo_headers = ua.get_headers(platform="mac", chrome_version="136")

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
```

### Custom Instances

```python
from macwinua import ChromeUA

# Create a new instance
my_ua = ChromeUA()

# Update internal data manually
my_ua.update(
    agents=[
        ("mac", "Mac OS X 15_0", "138", "Mozilla/5.0 (...)"),
        ...
    ],
    sec_ua={
        "138": '"Google Chrome";v="138", "Chromium";v="138", "Not.A/Brand";v="99"',
        ...
    },
)
```

---

## Supported Platforms and Browsers

Currently supports:

- Chrome versions: 135, 136, 137
- Platforms: macOS and Windows

## Example

A complete example with requests:

```python
import requests
from macwinua import ua

# Create a session
session = requests.Session()

# Configure with macOS Chrome headers
session.headers.update(ua.get_headers(platform="mac"))

# Make a request
response = session.get("https://httpbin.org/headers")
print(response.json())
```

## Development

This project uses Poetry for dependency management and packaging. To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/Nuung/MacWinUA.git
cd MacWinUA

# Setup Python 3.13 with pyenv (if you have pyenv installed)
pyenv install 3.13.0
pyenv local 3.13.0

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell

# Run tests
pytest  # or pytest --cov=macwinua --cov-report=html

# Install pre-commit hooks
pre-commit install
```

#### Pre-commit hooks

This project uses pre-commit to ensure code quality. The following checks run automatically before each commit:

1. Ruff linting and formatting
2. Mypy type checking
3. Pytest tests

> [!WARNING] > **_These are the same checks that run in our CI pipeline, ensuring consistency between local development and automated testing environments._**

## Comparison with other libraries

Unlike `fake-useragent` which tries to cover all browsers and platforms, MacWinUA focuses specifically on:

1. Always up-to-date headers (including sec-ch-ua values)
2. Realistic header combinations, enabling perfect browser impersonation with authentic UA strings!
3. Chrome browser only and macOS and Windows platforms
4. More Simple, More Fast, More Easy to Custom, No external dependencies
