from typing import List

try:
    from pydantic import Field  # pyright: ignore[reportMissingImports]
    from pydantic_settings import BaseSettings  # pyright: ignore[reportMissingImports]
except ImportError:
    # If pydantic or pydantic_settings are not installed, raise ImportError with an informative message
    raise ImportError(
        "pydantic and pydantic_settings are required to run this module. "
        "Please install them via 'pip install pydantic pydantic-settings'."
    )


class ScraperConfig(BaseSettings):
    """Configuration for proxy scraper"""

    enabled_sources: List[str] = Field(
        default=[
            "free-proxy-list",
            "proxy-list",
            "sslproxies",
            "us-proxy-list",
            "uk-proxy-list",
            "fr-proxy-list",
            "de-proxy-list",
            "jp-proxy-list",
            "cn-proxy",
            "proxy-ipv4",
            "free-proxy-list2",
            "proxylist-plus",
            "proxy-nova",
            "newproxy",
            "hidemy-ip",
            "proxy-daily",
            "proxy-scrape",
            "geonode",
            "spys-one",
            "proxy-rack",
        ],
        description="Proxy sources to scrape",
    )
    timeout: int = Field(default=8, description="Request timeout in seconds")
    max_workers: int = Field(default=25, description="Concurrent scraping workers")
    retry_attempts: int = Field(default=1, description="Retry failed requests")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="Custom user agent",
    )
    proxy_types: List[str] = Field(
        default=["http", "https", "socks4", "socks5"],
        description="Proxy types to collect",
    )
    selected_proxy_types: List[str] = Field(
        default=["http", "https", "socks4", "socks5"],
        description="Currently selected proxy types for scraping",
    )
    selected_sources: List[str] = Field(
        default=[
            "free-proxy-list",
            "proxy-list",
            "sslproxies",
            "us-proxy-list",
            "uk-proxy-list",
            "fr-proxy-list",
            "de-proxy-list",
            "jp-proxy-list",
            "cn-proxy",
            "proxy-ipv4",
            "free-proxy-list2",
            "proxylist-plus",
            "proxy-nova",
            "newproxy",
            "hidemy-ip",
        ],
        description="Currently selected sources to scrape from",
    )
    custom_sources: List[str] = Field(
        default=[], description="Custom proxy source URLs"
    )
    filter_by_country: List[str] = Field(
        default=[], description="Filter proxies by country codes (e.g., ['US', 'DE'])"
    )
    min_anonymity: str = Field(
        default="transparent",
        description="Minimum anonymity level: transparent, anonymous, elite",
    )
    verify_ssl: bool = Field(
        default=False, description="Verify SSL certificates during scraping"
    )


class CheckerConfig(BaseSettings):
    """Configuration for proxy checker"""

    test_urls: List[str] = Field(
        default=[
            "http://httpbin.org/ip",
            "https://api.myip.com",
            "http://ipinfo.io/json",
            "http://www.google.com",
            "http://www.example.com",
            "http://www.wikipedia.org",
            "http://www.httpbin.org/status/200",
            "https://www.cloudflare.com/cdn-cgi/trace",
        ],
        description="URLs to test proxy connectivity",
    )
    timeout: int = Field(default=8, description="Connection timeout in seconds")
    max_workers: int = Field(
        default=50, description="Concurrent checking workers (can be increased to 100)"
    )
    retry_failed: bool = Field(default=True, description="Retry failed checks")
    protocols_to_test: List[str] = Field(
        default=["http", "https", "socks4", "socks5"], description="Protocols to test"
    )
    test_anonymity: bool = Field(default=True, description="Test proxy anonymity")
    get_geolocation: bool = Field(
        default=True, description="Get proxy geolocation info"
    )
    bandwidth_test: bool = Field(default=False, description="Test proxy bandwidth")
    speed_threshold: int = Field(default=5000, description="Speed threshold in ms")
    custom_test_url: str = Field(default="", description="Custom URL for testing")
    save_results: bool = Field(default=True, description="Save results to file")
    export_format: str = Field(
        default="txt", description="Export format: json, csv, txt"
    )
    verify_ssl: bool = Field(
        default=True, description="Verify SSL certificates during checking"
    )


class AppConfig(BaseSettings):
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    checker: CheckerConfig = Field(default_factory=CheckerConfig)
    app_theme: str = Field(default="dark", description="UI theme: dark, light")
    auto_save: bool = Field(default=True, description="Auto-save settings")

    class Config:
        env_file = ".env"

    def save_to_env(self):
        """Save current configuration to .env file"""
        import os
        from dotenv import set_key  # pyright: ignore[reportMissingImports]

        # Ensure .env file exists
        if not os.path.exists(".env"):
            with open(".env", "w") as f:
                f.write("# Proxy Scraper & Checker Configuration\n")

        # Save scraper settings
        set_key(".env", "SCRAPER_TIMEOUT", str(self.scraper.timeout))
        set_key(".env", "SCRAPER_MAX_WORKERS", str(self.scraper.max_workers))
        set_key(".env", "SCRAPER_RETRY_ATTEMPTS", str(self.scraper.retry_attempts))
        set_key(".env", "SCRAPER_USER_AGENT", self.scraper.user_agent)
        set_key(
            ".env", "SCRAPER_SELECTED_SOURCES", ",".join(self.scraper.selected_sources)
        )
        set_key(
            ".env",
            "SCRAPER_SELECTED_PROXY_TYPES",
            ",".join(self.scraper.selected_proxy_types),
        )
        set_key(".env", "SCRAPER_VERIFY_SSL", str(self.scraper.verify_ssl))

        # Save checker settings
        set_key(".env", "CHECKER_TIMEOUT", str(self.checker.timeout))
        set_key(".env", "CHECKER_MAX_WORKERS", str(self.checker.max_workers))
        set_key(".env", "CHECKER_TEST_ANONYMITY", str(self.checker.test_anonymity))
        set_key(".env", "CHECKER_GET_GEOLOCATION", str(self.checker.get_geolocation))
        set_key(".env", "CHECKER_SPEED_THRESHOLD", str(self.checker.speed_threshold))
        set_key(".env", "CHECKER_EXPORT_FORMAT", self.checker.export_format)
        set_key(".env", "CHECKER_CUSTOM_TEST_URL", self.checker.custom_test_url)
        set_key(".env", "CHECKER_VERIFY_SSL", str(self.checker.verify_ssl))

        # Save app settings
        set_key(".env", "APP_THEME", self.app_theme)
        set_key(".env", "AUTO_SAVE", str(self.auto_save))


def get_config():
    return AppConfig()
