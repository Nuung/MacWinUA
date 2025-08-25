"""
MacWinUA Usage Examples
======================

Comprehensive examples demonstrating various usage patterns of the MacWinUA library.
Run this script to see all examples in action.
"""

import asyncio
import random
import time
import threading

# Basic imports
from macwinua import ua, get_chrome_headers, force_update, HeaderGenerator
from macwinua.exceptions import UAError, APIFetchError, CacheError, DataValidationError


def basic_usage_examples():
    """Demonstrates basic usage patterns."""
    print("=== Basic Usage Examples ===")

    # Simple User-Agent strings
    print(f"Random Chrome UA: {ua.chrome}")
    print(f"macOS Chrome UA: {ua.mac}")
    print(f"Windows Chrome UA: {ua.windows}")
    print(f"Latest version UA: {ua.latest}")
    print(f"Random alias: {ua.random}")
    print()

    # Basic headers
    headers = ua.get_headers()
    print("Basic headers:")
    for key, value in list(headers.items())[:5]:  # Show first 5
        print(f"  {key}: {value}")
    print(f"  ... and {len(headers) - 5} more headers")
    print()


def platform_specific_examples():
    """Demonstrates platform-specific header generation."""
    print("=== Platform-Specific Examples ===")

    # macOS headers
    mac_headers = ua.get_headers(platform="mac")
    print(f"macOS UA: {mac_headers['User-Agent']}")
    print(f"Platform header: {mac_headers['sec-ch-ua-platform']}")
    print()

    # Windows headers
    win_headers = ua.get_headers(platform="win")
    print(f"Windows UA: {win_headers['User-Agent']}")
    print(f"Platform header: {win_headers['sec-ch-ua-platform']}")
    print()


def version_specific_examples():
    """Demonstrates version-specific header generation."""
    print("=== Version-Specific Examples ===")

    try:
        # Specific Chrome version
        v139_headers = ua.get_headers(chrome_version="139")
        print(f"Chrome 139 UA: {v139_headers['User-Agent']}")
        print(f"sec-ch-ua: {v139_headers['sec-ch-ua']}")
        print()

        # Combined platform and version
        mac_v138_headers = ua.get_headers(platform="mac", chrome_version="138")
        print(f"macOS Chrome 138 UA: {mac_v138_headers['User-Agent']}")
        print()

    except UAError as e:
        print(f"Version error: {e}")


def custom_headers_examples():
    """Demonstrates custom header merging."""
    print("=== Custom Headers Examples ===")

    # Add custom headers
    custom_headers = ua.get_headers(
        platform="mac",
        extra_headers={
            "X-API-Key": "your-api-key-here",
            "X-Client-Version": "1.0.0",
            "Authorization": "Bearer token123",
            "X-Request-ID": "req-12345",
        },
    )

    print("Headers with custom additions:")
    custom_keys = [
        k for k in custom_headers.keys() if k.startswith("X-") or k == "Authorization"
    ]
    for key in custom_keys:
        print(f"  {key}: {custom_headers[key]}")
    print()


def requests_example():
    """Example using requests library (if available)."""
    print("=== Requests Library Example ===")

    try:
        import requests

        # Create session with Chrome headers
        session = requests.Session()
        headers = ua.get_headers(platform="mac", chrome_version="139")
        session.headers.update(headers)

        # Make a request
        print("Making request to httpbin.org...")
        response = session.get("https://httpbin.org/headers", timeout=10)

        if response.status_code == 200:
            user_agent = response.json()["headers"]["User-Agent"]
            print(f"✓ Request successful! Sent UA: ...{user_agent[-60:]}")
        else:
            print(f"✗ Request failed with status: {response.status_code}")

    except ImportError:
        print("requests library not available - install with: pip install requests")
    except Exception as e:
        print(f"Request failed: {e}")

    print()


async def httpx_example():
    """Example using httpx library (if available)."""
    print("=== HTTPX Async Library Example ===")

    try:
        import httpx

        headers = get_chrome_headers(platform="win", chrome_version="138")

        print("Making async request to httpbin.org...")
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            response = await client.get("https://httpbin.org/headers")

            if response.status_code == 200:
                user_agent = response.json()["headers"]["User-Agent"]
                print(f"✓ Async request successful! Sent UA: ...{user_agent[-60:]}")
            else:
                print(f"✗ Async request failed with status: {response.status_code}")

    except ImportError:
        print("httpx library not available - install with: pip install httpx")
    except Exception as e:
        print(f"Async request failed: {e}")

    print()


class AdvancedUARotator:
    """Advanced User-Agent rotation with multiple strategies."""

    def __init__(self):
        self.ua_generator = HeaderGenerator()
        self.platforms = ["mac", "win"]
        self.versions = ["137", "138", "139"]
        self.used_combinations = set()
        self.request_count = 0

    def get_fresh_headers(self, strategy="random"):
        """Get headers with different rotation strategies."""
        self.request_count += 1

        if strategy == "random":
            return self._random_strategy()
        elif strategy == "round_robin":
            return self._round_robin_strategy()
        elif strategy == "avoid_duplicates":
            return self._avoid_duplicates_strategy()
        else:
            return self.ua_generator.get_headers()

    def _random_strategy(self):
        """Completely random selection."""
        platform = random.choice(self.platforms)
        version = random.choice(self.versions)
        return self.ua_generator.get_headers(platform=platform, chrome_version=version)

    def _round_robin_strategy(self):
        """Cycle through combinations systematically."""
        all_combinations = [(p, v) for p in self.platforms for v in self.versions]
        combo_index = (self.request_count - 1) % len(all_combinations)
        platform, version = all_combinations[combo_index]
        return self.ua_generator.get_headers(platform=platform, chrome_version=version)

    def _avoid_duplicates_strategy(self):
        """Avoid recently used combinations."""
        max_attempts = 20

        for _ in range(max_attempts):
            platform = random.choice(self.platforms)
            version = random.choice(self.versions)
            combination = (platform, version)

            if combination not in self.used_combinations:
                self.used_combinations.add(combination)

                # Keep only last 10 combinations to prevent infinite growth
                if len(self.used_combinations) > 10:
                    oldest = list(self.used_combinations)[0]
                    self.used_combinations.remove(oldest)

                return self.ua_generator.get_headers(
                    platform=platform, chrome_version=version
                )

        # Fallback to random if all attempts failed
        return self._random_strategy()


def advanced_rotation_example():
    """Demonstrates advanced User-Agent rotation strategies."""
    print("=== Advanced Rotation Example ===")

    rotator = AdvancedUARotator()

    try:
        import requests

        session = requests.Session()

        strategies = ["random", "round_robin", "avoid_duplicates"]

        for strategy in strategies:
            print(f"\n{strategy.title()} strategy:")

            for i in range(3):
                headers = rotator.get_fresh_headers(strategy=strategy)
                session.headers.update(headers)

                try:
                    response = session.get("https://httpbin.org/headers", timeout=5)
                    if response.status_code == 200:
                        ua_string = response.json()["headers"]["User-Agent"]
                        platform = "macOS" if "Macintosh" in ua_string else "Windows"
                        version = ua_string.split("Chrome/")[1].split(".")[0]
                        print(f"  Request {i+1}: {platform} Chrome {version}")

                    time.sleep(0.5)  # Be nice to the server

                except Exception as e:
                    print(f"  Request {i+1}: Failed ({e})")

    except ImportError:
        print("requests library not available for rotation example")
    except Exception as e:
        print(f"Rotation example failed: {e}")

    print()


def custom_instance_example():
    """Demonstrates custom HeaderGenerator instances."""
    print("=== Custom Instance Example ===")

    # Create custom instances
    custom_ua1 = HeaderGenerator()
    custom_ua2 = HeaderGenerator()

    # Both use the same singleton DataManager internally, but are separate instances
    print(f"Instance 1 UA: {custom_ua1.chrome}")
    print(f"Instance 2 UA: {custom_ua2.mac}")

    # Custom headers with instance
    headers = custom_ua1.get_headers(
        platform="win", chrome_version="139", extra_headers={"X-Instance": "custom-1"}
    )
    print(f"Custom instance headers count: {len(headers)}")
    print()


def error_handling_example():
    """Demonstrates comprehensive error handling."""
    print("=== Error Handling Example ===")

    # Test valid requests first
    try:
        headers = ua.get_headers(platform="mac")
        print("✓ Valid mac platform request succeeded")
    except UAError as e:
        print(f"✗ Unexpected error: {e}")

    # Test invalid platform
    try:
        headers = ua.get_headers(platform="linux")
    except UAError as e:
        print(f"✓ Invalid platform correctly caught: {e}")

    # Test invalid Chrome version
    try:
        headers = ua.get_headers(chrome_version="999")
    except UAError as e:
        print(f"✓ Invalid Chrome version correctly caught: {e}")

    # Test specific exception types
    print("\nTesting specific exception handling:")

    try:
        # This should work normally
        headers = ua.get_headers()
        print("✓ Normal operation succeeded")
    except APIFetchError as e:
        print(f"✗ API Error: {e}")
    except CacheError as e:
        print(f"✗ Cache Error: {e}")
    except DataValidationError as e:
        print(f"✗ Data Validation Error: {e}")
    except UAError as e:
        print(f"✗ General UA Error: {e}")

    print()


def force_update_example():
    """Demonstrates force update functionality."""
    print("=== Force Update Example ===")

    print("Current UA (from cache):", ua.latest)

    try:
        print("Forcing update from API...")
        force_update()  # This will try to fetch fresh data from API
        print("✓ Force update completed successfully")
        print("Updated UA:", ua.latest)

    except APIFetchError as e:
        print(f"✗ API Error during update: {e}")
        print("(Fallback versions are being used)")
    except Exception as e:
        print(f"✗ Unexpected error during update: {e}")

    print()


def performance_benchmark():
    """Simple performance benchmark."""
    print("=== Performance Benchmark ===")

    # Benchmark header generation
    iterations = 5000

    start_time = time.time()
    for _ in range(iterations):
        _ = ua.get_headers()
    end_time = time.time()

    duration = end_time - start_time
    rate = iterations / duration
    print(f"Generated {iterations} headers in {duration:.3f}s ({rate:.0f} headers/sec)")

    # Benchmark property access
    start_time = time.time()
    for _ in range(iterations):
        _ = ua.chrome
    end_time = time.time()

    duration = end_time - start_time
    rate = iterations / duration
    print(
        f"Accessed {iterations} UA properties in {duration:.3f}s ({rate:.0f} accesses/sec)"
    )

    print()


def thread_safety_example():
    """Demonstrates thread safety."""
    print("=== Thread Safety Example ===")

    results = []
    errors = []

    def worker(worker_id):
        """Worker function for thread safety test."""
        try:
            local_results = []
            for i in range(50):
                # Mix different operations
                if i % 4 == 0:
                    headers = ua.get_headers(platform="mac")
                    local_results.append(f"W{worker_id}-mac-headers")
                elif i % 4 == 1:
                    ua_string = ua.windows
                    local_results.append(f"W{worker_id}-win-ua")
                elif i % 4 == 2:
                    headers = ua.get_headers(chrome_version="139")
                    local_results.append(f"W{worker_id}-v139-headers")
                else:
                    ua_string = ua.latest
                    local_results.append(f"W{worker_id}-latest-ua")

            results.extend(local_results)

        except Exception as e:
            errors.append(f"Worker {worker_id}: {e}")

    # Start multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    if errors:
        print(f"✗ Thread safety test failed with errors: {errors}")
    else:
        print(
            f"✓ Thread safety test passed! {len(results)} operations completed successfully"
        )

    print()


def comprehensive_showcase():
    """Comprehensive showcase of all library features."""
    print("=== Comprehensive Feature Showcase ===")

    # Show all available properties
    print("Available UA properties:")
    properties = ["chrome", "mac", "windows", "latest", "random"]
    for prop in properties:
        ua_value = getattr(ua, prop)
        print(f"  ua.{prop}: ...{ua_value[-40:]}")

    print("\nAvailable header configurations:")
    configs = [
        {"platform": "mac"},
        {"platform": "win"},
        {"chrome_version": "139"},
        {"platform": "mac", "chrome_version": "138"},
        {"extra_headers": {"X-Test": "showcase"}},
    ]

    for config in configs:
        try:
            headers = ua.get_headers(**config)
            config_str = ", ".join(f"{k}={v}" for k, v in config.items())
            print(f"  get_headers({config_str}): {len(headers)} headers")
        except Exception as e:
            print(f"  get_headers({config}): Error - {e}")

    print()


async def main():
    """Main function to run all examples."""
    print("MacWinUA Library Examples")
    print("=" * 50)
    print()

    # Run all examples
    basic_usage_examples()
    platform_specific_examples()
    version_specific_examples()
    custom_headers_examples()
    requests_example()
    await httpx_example()
    advanced_rotation_example()
    custom_instance_example()
    error_handling_example()
    force_update_example()
    performance_benchmark()
    thread_safety_example()
    comprehensive_showcase()

    print("All examples completed!")
    print("\n" + "=" * 50)
    print("For more information, visit: https://github.com/Nuung/MacWinUA")


if __name__ == "__main__":
    asyncio.run(main())
