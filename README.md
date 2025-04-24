poetry build

- PyPI 토큰 구성 (처음 한번만)
  poetry config pypi-token.pypi your-token-here

- 배포
  poetry publish

---

# MacWinUA

> A library for generating realistic browser headers for macOS and Windows platforms — always the freshest Chrome headers.

[![PyPI version](https://badge.fury.io/py/MacWinUA.svg)](https://badge.fury.io/py/MacWinUA)
[![Python Versions](https://img.shields.io/pypi/pyversions/MacWinUA.svg)](https://pypi.org/project/MacWinUA/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

# Get any Chrome User-Agent string
chrome_ua = ua.chrome

# Get a macOS Chrome User-Agent
mac_ua = ua.mac

# Get a Windows Chrome User-Agent
win_ua = ua.windows

# Get the latest version Chrome User-Agent
latest_ua = ua.latest

# Get a random Chrome User-Agent (alias for chrome)
random_ua = ua.random
```

### Complete Browser Headers

```python
from macwinua import ua

# Get random Chrome headers
headers = ua.get_headers()

# Get macOS Chrome headers
mac_headers = ua.get_headers(platform="mac")

# Get Windows Chrome headers
win_headers = ua.get_headers(platform="win")

# Get specific Chrome version headers
chrome137_headers = ua.get_headers(chrome_version="137")

# Specify both platform and version
mac_chrome136 = ua.get_headers(platform="mac", chrome_version="136")

# Use with requests
import requests
response = requests.get("https://example.com", headers=ua.get_headers())
```

### Compatibility Function

For even more concise code:

```python
from macwinua import get_chrome_headers

# Get random headers
headers = get_chrome_headers()

# Get macOS headers
mac_headers = get_chrome_headers(platform="mac")
```

### Custom Instances

```python
from macwinua import ChromeUA

# Create your own instance
my_ua = ChromeUA()

# Update with new User-Agents (for future auto-update functionality)
my_ua.update(agents=[...new_agents_list...], sec_ua={...new_sec_ch_ua_values...})
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
git clone https://github.com/yourusername/MacWinUA.git
cd MacWinUA

# Setup Python 3.13 with pyenv (if you have pyenv installed)
pyenv install 3.13.0
pyenv local 3.13.0

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell

# Run tests
pytest

# Install pre-commit hooks
pre-commit install
```

#### Pre-commit hooks

This project uses pre-commit to ensure code quality. The following checks run automatically before each commit:

1. Ruff linting and formatting
2. Mypy type checking
3. Pytest tests

**_These are the same checks that run in our CI pipeline, ensuring consistency between local development and automated testing environments._**

## Comparison with other libraries

Unlike `fake-useragent` which tries to cover all browsers and platforms, MacWinUA focuses specifically on:

1. Chrome browser only
2. macOS and Windows platforms
3. Always up-to-date headers (including sec-ch-ua values)
4. Realistic header combinations

## License

MIT
