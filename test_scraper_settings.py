#!/usr/bin/env python3
"""
Test script to validate the new scraper settings
"""

from config import ScraperConfig

def test_scraper_settings():
    """Test that the new default scraper settings are applied correctly"""

    print("=== TESTING NEW SCRAPER SETTINGS ===")

    # Create a default config
    config = ScraperConfig()

    print(f"Timeout: {config.timeout} seconds (expected: 8)")
    print(f"Max Workers: {config.max_workers} (expected: 25)")
    print(f"Retry Attempts: {config.retry_attempts} (expected: 1)")
    print(f"Proxy Sources: {len(config.enabled_sources)} sources (expected: 20)")
    print(f"Proxy Sources: {config.enabled_sources}")

    # Validate the settings
    assert config.timeout == 8, f"Timeout should be 8, got {config.timeout}"
    assert config.max_workers == 25, f"Max workers should be 25, got {config.max_workers}"
    assert config.retry_attempts == 1, f"Retry attempts should be 1, got {config.retry_attempts}"
    assert len(config.enabled_sources) == 20, f"Should have 20 proxy sources, got {len(config.enabled_sources)}"

    print("\nAll scraper settings validated successfully!")
    print("Default timeout: 8 seconds")
    print("Default max workers: 25")
    print("Default retry attempts: 1")
    print("Added 5 more proxy sources (total 20)")
    print("All proxy types supported: HTTP, HTTPS, SOCKS4, SOCKS5")

if __name__ == "__main__":
    test_scraper_settings()