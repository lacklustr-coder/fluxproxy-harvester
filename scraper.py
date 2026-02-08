import asyncio
import aiohttp  # pyright: ignore[reportMissingImports]
import requests  # Move requests import to top-level for reliability
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]
import re
from typing import List, Set, Optional, Callable
from proxy_models import Proxy, ProxyType, AnonymityLevel
from config import ScraperConfig
import logging
from urllib.parse import urljoin
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxyScraper:
    """Enterprise proxy scraper with multiple sources"""

    SOURCES = {
        "free-proxy-list": "https://free-proxy-list.net",
        "proxy-list": "https://www.proxy-list.download/api/v1/get?type=http",
        "sslproxies": "https://www.sslproxies.org",
        "us-proxy-list": "https://www.us-proxy-list.net",
        "uk-proxy-list": "https://www.uk-proxy-list.net",
        "fr-proxy-list": "https://www.fr-proxy-list.net",
        "de-proxy-list": "https://www.de-proxy-list.net",
        "jp-proxy-list": "https://www.jp-proxy-list.net",
        "cn-proxy": "http://cn-proxy.com/services/getIpList",
        "proxy-ipv4": "https://proxyipv4.com/proxy-list",
        "free-proxy-list2": "https://free-proxy-list.com",
        "proxylist-plus": "https://proxylist.plus",
        "proxy-nova": "https://www.proxy-nova.com/proxy-list/",
        "newproxy": "https://newproxy.com/proxy-list",
        "advanced-web-ranking": "https://www.advancedwebranking.com/proxies.html",
        "proxy-checker": "https://proxychecker.com",
        "hidemy-ip": "https://hidemy.name/en/proxy-list/",
        "elite-proxy": "https://elite-proxy.com/proxy-list/",
        "freeproxylists": "https://www.freeproxylists.net/",
    }

    COUNTRY_MAP = {
        "free-proxy-list": "US",
        "sslproxies": "US",
        "us-proxy-list": "US",
        "uk-proxy-list": "GB",
        "fr-proxy-list": "FR",
        "de-proxy-list": "DE",
        "jp-proxy-list": "JP",
        "free-proxy-list2": "US",
        "proxylist-plus": "US",
        "proxy-nova": "US",
        "newproxy": "US",
        "advanced-web-ranking": "US",
        "proxy-checker": "US",
        "hidemy-ip": "US",
        "elite-proxy": "US",
        "freeproxylists": "US",
    }

    def __init__(
        self, config: ScraperConfig, progress_callback: Optional[Callable] = None
    ):
        self.config = config
        self.progress_callback = progress_callback
        self.found_proxies: Set[str] = set()
        self.proxies: List[Proxy] = []

    def _log_progress(self, message: str):
        """Log and report progress"""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)

    def _parse_proxy_table(self, html: str, source: str) -> List[Proxy]:
        """Parse HTML table for proxies with multiple strategies"""
        proxies = []
        try:
            # Use a robust parser that does not require optional dependencies
            soup = BeautifulSoup(html, "html.parser")

            # Try to find proxies in any table
            tables = soup.find_all("table")
            if not tables:
                # Fallback: try to extract from any text containing IP:PORT pattern
                return self._extract_proxies_from_text(html, source)

            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    try:
                        cols = row.find_all("td")
                        if len(cols) < 2:
                            continue

                        # Try different column positions
                        ip = port = protocol = None

                        # Strategy 1: Standard layout (IP, Port in first 2 cols)
                        ip_text = cols[0].text.strip()
                        port_text = cols[1].text.strip()

                        if self._is_valid_ip(ip_text) and port_text.isdigit():
                            ip = ip_text
                            port = int(port_text)
                            protocol = (
                                cols[4].text.strip().lower()
                                if len(cols) > 4
                                else "http"
                            )
                        else:
                            # Strategy 2: Try alternative column positions
                            for i in range(len(cols)):
                                for j in range(i + 1, len(cols)):
                                    test_ip = cols[i].text.strip()
                                    test_port = cols[j].text.strip()
                                    if (
                                        self._is_valid_ip(test_ip)
                                        and test_port.isdigit()
                                    ):
                                        ip = test_ip
                                        port = int(test_port)
                                        # Find protocol if available
                                        for k in range(len(cols)):
                                            prot_text = cols[k].text.strip().lower()
                                            if prot_text in [
                                                "http",
                                                "https",
                                                "socks4",
                                                "socks5",
                                            ]:
                                                protocol = prot_text
                                                break
                                        break
                                if ip and port:
                                    break

                        if not ip or not port:
                            continue

                        protocol = protocol or "http"

                        # Get country and anonymity
                        country = self.COUNTRY_MAP.get(source, "US")
                        for col in cols:
                            col_text = col.text.strip()
                            if len(col_text) == 2 and col_text.isupper():
                                country = col_text
                                break

                        anonymity_text = "transparent"
                        for col in cols:
                            col_text = col.text.strip().lower()
                            if any(
                                x in col_text
                                for x in ["elite", "anonymous", "transparent"]
                            ):
                                anonymity_text = col_text
                                break

                        anonymity = self._parse_anonymity(anonymity_text)
                        proxy_type = self._parse_proxy_type(protocol)

                        proxy_key = f"{ip}:{port}"
                        if proxy_key not in self.found_proxies:
                            self.found_proxies.add(proxy_key)
                            proxy = Proxy(
                                ip=ip,
                                port=port,
                                proxy_type=proxy_type,
                                anonymity=anonymity,
                                country=country,
                                source=source,
                            )
                            proxies.append(proxy)
                    except Exception as e:
                        logger.debug(f"Error parsing row: {e}")
                        continue

            self._log_progress(f"[{source}] Found {len(proxies)} proxies")
        except Exception as e:
            logger.error(f"Error parsing proxies from {source}: {e}")

        return proxies

    def _extract_proxies_from_text(self, html: str, source: str) -> List[Proxy]:
        """Extract proxies using regex as fallback"""
        proxies = []
        try:
            # IP:PORT regex pattern
            pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:\s]+(\d{2,5})"
            matches = re.findall(pattern, html)

            for ip, port in matches:
                try:
                    if not self._is_valid_ip(ip) or not (1 <= int(port) <= 65535):
                        continue

                    proxy_key = f"{ip}:{port}"
                    if proxy_key not in self.found_proxies:
                        self.found_proxies.add(proxy_key)
                        proxy = Proxy(
                            ip=ip,
                            port=int(port),
                            proxy_type=ProxyType.HTTP,
                            country=self.COUNTRY_MAP.get(source, "US"),
                            source=source,
                        )
                        proxies.append(proxy)
                except Exception:
                    continue

            if proxies:
                self._log_progress(f"[{source}] Found {len(proxies)} proxies (regex)")
        except Exception as e:
            logger.debug(f"Regex extraction failed for {source}: {e}")

        return proxies

    def _parse_proxy_type(self, protocol_str: str) -> ProxyType:
        """Parse proxy type from string"""
        protocol_str = protocol_str.lower().strip()
        if "socks5" in protocol_str:
            return ProxyType.SOCKS5
        elif "socks4" in protocol_str:
            return ProxyType.SOCKS4
        elif "https" in protocol_str:
            return ProxyType.HTTPS
        else:
            return ProxyType.HTTP

    def _parse_anonymity(self, anon_str: str) -> AnonymityLevel:
        """Parse anonymity level"""
        anon_str = anon_str.lower()
        if "elite" in anon_str or "high" in anon_str:
            return AnonymityLevel.ELITE
        elif "anonymous" in anon_str:
            return AnonymityLevel.ANONYMOUS
        else:
            return AnonymityLevel.TRANSPARENT

    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address"""
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(pattern, ip):
            return False
        parts = ip.split(".")
        return all(0 <= int(part) <= 255 for part in parts)

    def _scrape_free_proxy_list(self, source: str) -> List[Proxy]:
        """Scrape free-proxy-list style sites with retry logic"""
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com",
            "Connection": "keep-alive",
        }

        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                response = requests.get(
                    self.SOURCES[source],
                    headers=headers,
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                    allow_redirects=True,
                )
                response.raise_for_status()

                # If we got content, parse it
                if response.text:
                    proxies = self._parse_proxy_table(response.text, source)
                    if proxies:
                        return proxies
                    else:
                        # Retry if no proxies found
                        if attempt < self.config.retry_attempts:
                            time.sleep(1)
                            continue
                        return []
                else:
                    if attempt < self.config.retry_attempts:
                        time.sleep(1)
                        continue
                    return []

            except requests.exceptions.Timeout:
                if attempt < self.config.retry_attempts:
                    logger.debug(
                        f"[{source}] Timeout, retrying ({attempt}/{self.config.retry_attempts})"
                    )
                    time.sleep(2)
                    continue
                logger.error(
                    f"Error scraping {source}: Timeout after {self.config.retry_attempts} attempts"
                )
                return []
            except requests.exceptions.ConnectionError:
                if attempt < self.config.retry_attempts:
                    logger.debug(
                        f"[{source}] Connection error, retrying ({attempt}/{self.config.retry_attempts})"
                    )
                    time.sleep(2)
                    continue
                logger.error(f"Error scraping {source}: Connection error")
                return []
            except Exception as e:
                if attempt < self.config.retry_attempts:
                    logger.debug(
                        f"[{source}] Error ({str(e)[:50]}), retrying ({attempt}/{self.config.retry_attempts})"
                    )
                    time.sleep(1)
                    continue
                logger.error(f"Error scraping {source}: {e}")
                return []

        return []

    def _scrape_proxy_list_download(self) -> List[Proxy]:
        """Scrape proxy-list.download JSON API"""
        try:
            headers = {"User-Agent": self.config.user_agent}
            response = requests.get(
                self.SOURCES["proxy-list"],
                headers=headers,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            response.raise_for_status()
            data = response.json()

            proxies = []
            for item in data.get("LISTA", []):
                ip = item.get("IP")
                port = item.get("PORT")
                protocol = item.get("PROTOCOL", "http").lower()

                if self._is_valid_ip(ip) and port:
                    proxy_key = f"{ip}:{port}"
                    if proxy_key not in self.found_proxies:
                        self.found_proxies.add(proxy_key)
                        proxy = Proxy(
                            ip=ip,
                            port=int(port),
                            proxy_type=self._parse_proxy_type(protocol),
                            source="proxy-list",
                        )
                        proxies.append(proxy)

            self._log_progress(f"[proxy-list] Found {len(proxies)} proxies")
            return proxies
        except Exception as e:
            logger.error(f"Error scraping proxy-list: {e}")
            return []

    def scrape_all(self) -> List[Proxy]:
        """Scrape all enabled sources"""
        self._log_progress("Starting proxy scraper...")
        # Use selected_sources if available, otherwise fall back to enabled_sources
        sources_to_scrape = (
            getattr(self.config, "selected_sources", None)
            or self.config.enabled_sources
        )
        self._log_progress(f"Scraping from {len(sources_to_scrape)} sources...")
        all_proxies = []
        completed_sources = 0
        total_sources = len(sources_to_scrape)

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {}

            for source in sources_to_scrape:
                if source not in self.SOURCES:
                    self._log_progress(f"[SKIP] {source} - not found in sources")
                    completed_sources += 1
                    continue

                self._log_progress(f"[QUEUE] {source}...")
                if source == "proxy-list":
                    future = executor.submit(self._scrape_proxy_list_download)
                else:
                    future = executor.submit(self._scrape_free_proxy_list, source)
                futures[future] = source

            for future in as_completed(futures):
                source_name = futures[future]
                completed_sources += 1
                try:
                    proxies = future.result()
                    all_proxies.extend(proxies)
                    self._log_progress(
                        f"[OK] {source_name}: {len(proxies)} proxies found ({completed_sources}/{total_sources})"
                    )
                except Exception as e:
                    self._log_progress(
                        f"[ERROR] {source_name}: {str(e)[:100]} ({completed_sources}/{total_sources})"
                    )
                    logger.error(f"Error scraping {source_name}: {e}")

        self._log_progress(f"Total raw proxies collected: {len(all_proxies)}")

        # Filter by configuration
        filtered_proxies = self._filter_proxies(all_proxies)
        self.proxies = filtered_proxies
        self._log_progress(
            f"Scraping complete: {len(filtered_proxies)} proxies after filtering"
        )
        self._log_progress(
            f"Summary: {len(all_proxies)} raw -> {len(filtered_proxies)} filtered"
        )
        return filtered_proxies

    def _filter_proxies(self, proxies: List[Proxy]) -> List[Proxy]:
        """Filter proxies based on config"""
        if not proxies:
            return proxies

        filtered = proxies
        initial_count = len(filtered)

        # Filter by type (use selected_proxy_types if set, otherwise use proxy_types)
        selected_types = (
            getattr(self.config, "selected_proxy_types", None)
            or self.config.proxy_types
        )
        if selected_types:
            before = len(filtered)
            filtered = [p for p in filtered if p.proxy_type.value in selected_types]
            self._log_progress(
                f"[FILTER] By type {selected_types}: {before} -> {len(filtered)}"
            )

        # Filter by anonymity - only if explicitly set to non-transparent
        if (
            self.config.min_anonymity
            and self.config.min_anonymity.lower() != "transparent"
        ):
            before = len(filtered)
            min_level = AnonymityLevel[self.config.min_anonymity.upper()]
            level_order = {
                AnonymityLevel.TRANSPARENT: 0,
                AnonymityLevel.ANONYMOUS: 1,
                AnonymityLevel.ELITE: 2,
            }
            filtered = [
                p
                for p in filtered
                if level_order.get(p.anonymity, 0) >= level_order.get(min_level, 0)
            ]
            self._log_progress(
                f"[FILTER] By anonymity (min {self.config.min_anonymity}): {before} -> {len(filtered)}"
            )

        # Filter by country
        if self.config.filter_by_country:
            before = len(filtered)
            filtered = [
                p for p in filtered if p.country in self.config.filter_by_country
            ]
            self._log_progress(f"[FILTER] By country: {before} -> {len(filtered)}")

        self._log_progress(
            f"[FILTER] Total: {initial_count} raw -> {len(filtered)} final"
        )
        return filtered


# Requests import now at module top-level; no lazy import needed
