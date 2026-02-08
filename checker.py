import requests  # pyright: ignore[reportMissingModuleSource]
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable
from proxy_models import Proxy, CheckResult, AnonymityLevel, ProxyType
from config import CheckerConfig
import logging
import time
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProxyChecker:
    """Enterprise proxy checker with comprehensive testing"""

    def __init__(self, config: CheckerConfig, progress_callback: Optional[Callable] = None):
        self.config = config
        self.progress_callback = progress_callback
        self.results: List[CheckResult] = []

    def _log_progress(self, message: str):
        """Log and report progress"""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)

    def check_proxy(self, proxy: Proxy) -> CheckResult:
        """Check single proxy with all tests"""
        result = CheckResult(proxy=proxy, is_working=False)

        try:
            # Test connectivity first
            logger.debug(f"Testing connectivity for {proxy.format_proxy_string()}")

            is_working = False
            try:
                is_working = self._test_connectivity(proxy)
            except Exception as e:
                logger.error(f"Connectivity test error for {proxy.format_proxy_string()}: {e}")
                result.error = f"Connectivity test failed: {str(e)[:100]}"
                result.timestamp = datetime.now()
                return result

            if not is_working:
                logger.debug(f"Proxy {proxy.format_proxy_string()} failed connectivity test")
                result.timestamp = datetime.now()
                return result

            # Proxy is working!
            result.is_working = True
            logger.debug(f"Proxy {proxy.format_proxy_string()} PASSED connectivity test")

            # Get response time (required test)
            try:
                result.response_time = self._measure_response_time(proxy)
            except Exception as e:
                logger.debug(f"Response time measurement failed: {e}")
                result.response_time = None

            # Test anonymity (optional)
            if self.config.test_anonymity:
                try:
                    result.anonymity_verified = self._test_anonymity(proxy)
                except Exception as e:
                    logger.debug(f"Anonymity test failed: {e}")
                    result.anonymity_verified = AnonymityLevel.TRANSPARENT

            # Get geolocation (optional)
            if self.config.get_geolocation:
                try:
                    result.geolocation = self._get_geolocation(proxy)
                except Exception as e:
                    logger.debug(f"Geolocation lookup failed: {e}")
                    result.geolocation = None

        except Exception as e:
            result.error = str(e)
            logger.error(f"Critical error checking {proxy.format_proxy_string()}: {e}")

        result.timestamp = datetime.now()
        proxy.is_working = result.is_working
        proxy.last_checked = result.timestamp
        proxy.response_time = result.response_time

        return result

    def _test_connectivity(self, proxy: Proxy) -> bool:
        """Test if proxy is working - proper proxy validation"""

        # Test URLs - use reliable endpoints
        test_urls = []
        if self.config.custom_test_url:
            test_urls = [self.config.custom_test_url]
        else:
            # Primary: Simple HTTP tests (most reliable for proxies)
            test_urls = [
                "http://www.google.com",
                "http://www.example.com",
                "http://www.wikipedia.org",
                "http://www.httpbin.org/status/200",
            ]

        # Build proxy configuration based on proxy type
        for url in test_urls:
            try:
                # Create appropriate proxy dictionary for the proxy type
                if proxy.proxy_type == ProxyType.HTTP:
                    proxy_dict = {"http": proxy.format_proxy_url()}
                elif proxy.proxy_type == ProxyType.HTTPS:
                    proxy_dict = {"https": proxy.format_proxy_url()}
                elif proxy.proxy_type in [ProxyType.SOCKS4, ProxyType.SOCKS5]:
                    # SOCKS proxies need special handling
                    proxy_dict = {
                        "http": proxy.format_proxy_url(),
                        "https": proxy.format_proxy_url()
                    }
                else:
                    logger.debug(f"Unsupported proxy type: {proxy.proxy_type.value}")
                    continue

                response = requests.get(
                    url,
                    proxies=proxy_dict,
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                    allow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
                    }
                )

                # Strict validation: only 200-299 accepted
                if 200 <= response.status_code <= 299:
                    # Verify meaningful content received
                    if response.text and len(response.text) > 20:
                        logger.info(f"✓ Proxy {proxy.format_proxy_string()} ({proxy.proxy_type.value}) WORKING - {url} returned {response.status_code}")
                        return True
                    else:
                        logger.debug(f"Proxy {proxy.format_proxy_string()}: Got {response.status_code} but empty response from {url}")
                        continue
                else:
                    logger.debug(f"Proxy {proxy.format_proxy_string()}: Got HTTP {response.status_code} from {url}")
                    continue

            except requests.exceptions.Timeout:
                logger.debug(f"Timeout ({self.config.timeout}s) testing {proxy.format_proxy_string()} on {url}")
                continue
            except requests.exceptions.ProxyError as e:
                logger.debug(f"Proxy error for {proxy.format_proxy_string()}: {str(e)[:50]}")
                continue
            except requests.exceptions.ConnectionError as e:
                logger.debug(f"Connection failed for {proxy.format_proxy_string()} on {url}: {str(e)[:50]}")
                continue
            except Exception as e:
                logger.debug(f"Test failed for {proxy.format_proxy_string()} on {url}: {str(e)[:50]}")
                continue

        logger.debug(f"✗ Proxy {proxy.format_proxy_string()} FAILED all connectivity tests")
        return False

    def _test_anonymity(self, proxy: Proxy) -> AnonymityLevel:
        """Test proxy anonymity level"""
        try:
            test_url = "http://httpbin.org/ip"

            # Create appropriate proxy dict based on type
            if proxy.proxy_type == ProxyType.HTTP:
                proxies = {"http": proxy.format_proxy_url()}
            elif proxy.proxy_type == ProxyType.HTTPS:
                proxies = {"https": proxy.format_proxy_url()}
            else:  # SOCKS proxies
                proxies = {
                    "http": proxy.format_proxy_url(),
                    "https": proxy.format_proxy_url()
                }

            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl
            )

            if response.status_code == 200:
                response_data = response.json()
                client_ip = response_data.get('origin', '').split(',')[0].strip()

                # Check for IP leak - this is the most reliable test
                if client_ip == proxy.ip:
                    return AnonymityLevel.ELITE
                elif 'via' not in response.headers and 'x-forwarded-for' not in response.headers:
                    return AnonymityLevel.ANONYMOUS
                else:
                    return AnonymityLevel.TRANSPARENT
        except Exception as e:
            logger.debug(f"Anonymity test failed: {e}")

        return AnonymityLevel.TRANSPARENT

    def _get_geolocation(self, proxy: Proxy) -> Optional[str]:
        """Get proxy geolocation info"""
        try:
            # Use IP geolocation API
            url = f"http://ip-api.com/json/{proxy.ip}?fields=country,city,org"
            response = requests.get(url, timeout=5, verify=self.config.verify_ssl)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country = data.get('country', '')
                    city = data.get('city', '')
                    org = data.get('org', '')
                    return f"{city}, {country} ({org})" if city and country else f"{country} ({org})"
        except Exception as e:
            logger.debug(f"Geolocation lookup failed: {e}")

        return None

    def _measure_response_time(self, proxy: Proxy) -> Optional[float]:
        """Measure proxy response time - use same connection that already works"""
        # Use a simple fast endpoint
        test_url = "http://www.example.com"

        # Build proxy dict for the proxy type
        if proxy.proxy_type == ProxyType.HTTP:
            proxy_dict = {"http": proxy.format_proxy_url()}
        elif proxy.proxy_type == ProxyType.HTTPS:
            proxy_dict = {"https": proxy.format_proxy_url()}
        else:  # SOCKS proxies
            proxy_dict = {
                "http": proxy.format_proxy_url(),
                "https": proxy.format_proxy_url()
            }

        try:
            start = time.time()
            response = requests.get(
                test_url,
                proxies=proxy_dict,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
                }
            )
            elapsed = (time.time() - start) * 1000

            # Only count if we got a valid response
            if 200 <= response.status_code <= 299 and response.text and len(response.text) > 20:
                logger.debug(f"Response time for {proxy.format_proxy_string()}: {elapsed:.0f}ms")
                return elapsed
            else:
                logger.debug(f"Speed test got invalid response: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.debug(f"Speed test timeout for {proxy.format_proxy_string()}")
            return None
        except Exception as e:
            logger.debug(f"Speed test failed for {proxy.format_proxy_string()}: {str(e)[:50]}")
            return None

    def check_proxies(self, proxies: List[Proxy]) -> List[CheckResult]:
        """Check multiple proxies concurrently"""
        self._log_progress(f"Starting proxy check for {len(proxies)} proxies...")
        self._log_progress(f"Using {self.config.max_workers} workers, {self.config.timeout}s timeout")
        self.results = []

        # Allow up to 100 workers for high-performance checking
        max_workers = min(self.config.max_workers, 100)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.check_proxy, proxy): proxy for proxy in proxies}

            completed = 0
            working = 0
            failed = 0

            for future in as_completed(futures):
                try:
                    result = future.result()
                    self.results.append(result)
                    completed += 1

                    if result.is_working:
                        working += 1
                        status = "PASS"
                        speed = f"{result.response_time:.0f}ms" if result.response_time else "N/A"
                        self._log_progress(f"[{completed}/{len(proxies)}] {status} {result.proxy.format_proxy_string()} ({speed}) - {result.geolocation or 'Unknown'}")
                    else:
                        failed += 1
                        self._log_progress(f"[{completed}/{len(proxies)}] FAIL {result.proxy.format_proxy_string()}")

                    # Live stats update every 10 proxies
                    if completed % 10 == 0 or completed == len(proxies):
                        win_pct = (working / completed * 100) if completed > 0 else 0
                        self._log_progress(f"  Stats: {working} working, {failed} failed, {win_pct:.1f}% success rate")

                except Exception as e:
                    logger.error(f"Error checking proxy: {e}")
                    completed += 1
                    failed += 1

        working_count = sum(1 for r in self.results if r.is_working)
        success_rate = (working_count / len(proxies) * 100) if proxies else 0
        self._log_progress(f"Check complete: {working_count}/{len(proxies)} proxies working ({success_rate:.1f}% success rate)")
        return self.results

    def get_fast_proxies(self, results: List[CheckResult], max_ms: Optional[int] = None) -> List[CheckResult]:
        """Filter for fast proxies"""
        if max_ms is None:
            max_ms = self.config.speed_threshold
        return [
            r for r in results
            if r.is_working and r.response_time is not None and r.response_time <= max_ms
        ]

    def export_results(self, results: List[CheckResult], filepath: str):
        """Export check results"""
        if self.config.export_format == "json":
            data = [
                {
                    "ip": r.proxy.ip,
                    "port": r.proxy.port,
                    "type": r.proxy.proxy_type.value,
                    "working": r.is_working,
                    "response_time_ms": r.response_time,
                    "anonymity": r.anonymity_verified.value,
                    "geolocation": r.geolocation,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in results
            ]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

        elif self.config.export_format == "csv":
            import csv
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["IP", "Port", "Type", "Working", "Response Time (ms)", "Anonymity", "Geolocation"])
                for r in results:
                    writer.writerow([
                        r.proxy.ip, r.proxy.port, r.proxy.proxy_type.value,
                        "Yes" if r.is_working else "No",
                        f"{r.response_time:.0f}" if r.response_time else "N/A",
                        r.anonymity_verified.value, r.geolocation or "N/A"
                    ])

        elif self.config.export_format == "txt":
            with open(filepath, 'w') as f:
                f.write("PROXY CHECK RESULTS\n")
                f.write("=" * 80 + "\n\n")
                for r in results:
                    f.write(str(r) + "\n")
                    if r.proxy.country:
                        f.write(f"  Country: {r.proxy.country}\n")
                    if r.response_time:
                        f.write(f"  Speed: {r.response_time:.0f}ms\n")
                    if r.error:
                        f.write(f"  Error: {r.error}\n")
                    f.write("\n")

        self._log_progress(f"Results exported to {filepath}")
