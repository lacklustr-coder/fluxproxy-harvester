"""
Advanced options and utilities for Proxy Scraper & Checker
Includes proxy filtering, grouping, and analysis utilities
"""

from typing import List, Dict, Set, Tuple
from proxy_models import Proxy, CheckResult, ProxyType, AnonymityLevel
from statistics import mean, median
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class ProxyAnalyzer:
    """Analyze proxy collections for insights and statistics"""
    
    @staticmethod
    def analyze_proxies(proxies: List[Proxy]) -> Dict:
        """Generate comprehensive statistics on proxy collection"""
        if not proxies:
            return {}
        
        total = len(proxies)
        by_type = defaultdict(int)
        by_country = defaultdict(int)
        by_anonymity = defaultdict(int)
        by_source = defaultdict(int)
        
        for proxy in proxies:
            by_type[proxy.proxy_type.value] += 1
            if proxy.country:
                by_country[proxy.country] += 1
            by_anonymity[proxy.anonymity.value] += 1
            if proxy.source:
                by_source[proxy.source] += 1
        
        return {
            "total": total,
            "by_type": dict(by_type),
            "by_country": dict(by_country),
            "by_anonymity": dict(by_anonymity),
            "by_source": dict(by_source),
            "working": sum(1 for p in proxies if p.is_working),
            "elite_count": sum(1 for p in proxies if p.anonymity == AnonymityLevel.ELITE),
            "average_speed": mean([p.speed for p in proxies if p.speed]) if any(p.speed for p in proxies) else None,
        }
    
    @staticmethod
    def analyze_results(results: List[CheckResult]) -> Dict:
        """Generate comprehensive statistics on check results"""
        if not results:
            return {}
        
        total = len(results)
        working = sum(1 for r in results if r.is_working)
        times = [r.response_time for r in results if r.response_time]
        
        return {
            "total": total,
            "working": working,
            "failed": total - working,
            "success_rate": (working / total * 100) if total > 0 else 0,
            "avg_response_time": mean(times) if times else None,
            "median_response_time": median(times) if times else None,
            "min_response_time": min(times) if times else None,
            "max_response_time": max(times) if times else None,
            "elite_anonymity": sum(1 for r in results if r.anonymity_verified == AnonymityLevel.ELITE),
            "anonymous_count": sum(1 for r in results if r.anonymity_verified == AnonymityLevel.ANONYMOUS),
        }

class ProxyFilter:
    """Advanced proxy filtering utilities"""
    
    @staticmethod
    def filter_by_type(proxies: List[Proxy], types: List[str]) -> List[Proxy]:
        """Filter proxies by type"""
        return [p for p in proxies if p.proxy_type.value in types]
    
    @staticmethod
    def filter_by_country(proxies: List[Proxy], countries: List[str]) -> List[Proxy]:
        """Filter proxies by country"""
        return [p for p in proxies if p.country in countries]
    
    @staticmethod
    def filter_by_anonymity(proxies: List[Proxy], level: str) -> List[Proxy]:
        """Filter by minimum anonymity level"""
        target_level = AnonymityLevel[level.upper()]
        level_order = {AnonymityLevel.TRANSPARENT: 0, AnonymityLevel.ANONYMOUS: 1, AnonymityLevel.ELITE: 2}
        target_rank = level_order[target_level]
        return [p for p in proxies if level_order.get(p.anonymity, 0) >= target_rank]
    
    @staticmethod
    def filter_working(results: List[CheckResult]) -> List[CheckResult]:
        """Filter for working proxies only"""
        return [r for r in results if r.is_working]
    
    @staticmethod
    def filter_by_speed(results: List[CheckResult], max_ms: int) -> List[CheckResult]:
        """Filter proxies by response time"""
        return [r for r in results if r.response_time and r.response_time <= max_ms]
    
    @staticmethod
    def filter_by_anonymity_result(results: List[CheckResult], level: str) -> List[CheckResult]:
        """Filter results by verified anonymity level"""
        target_level = AnonymityLevel[level.upper()]
        level_order = {AnonymityLevel.TRANSPARENT: 0, AnonymityLevel.ANONYMOUS: 1, AnonymityLevel.ELITE: 2}
        target_rank = level_order[target_level]
        return [r for r in results if level_order.get(r.anonymity_verified, 0) >= target_rank]

class ProxySorter:
    """Sorting utilities for proxies and results"""
    
    @staticmethod
    def sort_by_speed(results: List[CheckResult], descending=False) -> List[CheckResult]:
        """Sort by response time"""
        return sorted(results, key=lambda r: r.response_time or float('inf'), reverse=descending)
    
    @staticmethod
    def sort_by_country(proxies: List[Proxy]) -> List[Proxy]:
        """Sort by country"""
        return sorted(proxies, key=lambda p: p.country or 'ZZ')
    
    @staticmethod
    def sort_by_type(proxies: List[Proxy]) -> List[Proxy]:
        """Sort by proxy type"""
        return sorted(proxies, key=lambda p: p.proxy_type.value)
    
    @staticmethod
    def sort_by_anonymity(proxies: List[Proxy]) -> List[Proxy]:
        """Sort by anonymity level"""
        level_order = {AnonymityLevel.TRANSPARENT: 0, AnonymityLevel.ANONYMOUS: 1, AnonymityLevel.ELITE: 2}
        return sorted(proxies, key=lambda p: level_order.get(p.anonymity, 0), reverse=True)

class DuplicateHandler:
    """Handle duplicate proxies"""
    
    @staticmethod
    def remove_duplicates(proxies: List[Proxy]) -> List[Proxy]:
        """Remove duplicate proxies (same IP:PORT)"""
        seen: Set[str] = set()
        unique = []
        for proxy in proxies:
            key = f"{proxy.ip}:{proxy.port}"
            if key not in seen:
                seen.add(key)
                unique.append(proxy)
        return unique
    
    @staticmethod
    def find_duplicates(proxies: List[Proxy]) -> Dict[str, List[Proxy]]:
        """Find duplicate proxies"""
        duplicates: Dict[str, List[Proxy]] = defaultdict(list)
        for proxy in proxies:
            key = f"{proxy.ip}:{proxy.port}"
            duplicates[key].append(proxy)
        return {k: v for k, v in duplicates.items() if len(v) > 1}

class ProxyGrouper:
    """Group proxies by various criteria"""
    
    @staticmethod
    def group_by_country(proxies: List[Proxy]) -> Dict[str, List[Proxy]]:
        """Group proxies by country"""
        grouped: Dict[str, List[Proxy]] = defaultdict(list)
        for proxy in proxies:
            country = proxy.country or 'Unknown'
            grouped[country].append(proxy)
        return dict(grouped)
    
    @staticmethod
    def group_by_type(proxies: List[Proxy]) -> Dict[str, List[Proxy]]:
        """Group proxies by type"""
        grouped: Dict[str, List[Proxy]] = defaultdict(list)
        for proxy in proxies:
            grouped[proxy.proxy_type.value].append(proxy)
        return dict(grouped)
    
    @staticmethod
    def group_by_anonymity(proxies: List[Proxy]) -> Dict[str, List[Proxy]]:
        """Group proxies by anonymity level"""
        grouped: Dict[str, List[Proxy]] = defaultdict(list)
        for proxy in proxies:
            grouped[proxy.anonymity.value].append(proxy)
        return dict(grouped)
    
    @staticmethod
    def group_by_source(proxies: List[Proxy]) -> Dict[str, List[Proxy]]:
        """Group proxies by source"""
        grouped: Dict[str, List[Proxy]] = defaultdict(list)
        for proxy in proxies:
            source = proxy.source or 'Unknown'
            grouped[source].append(proxy)
        return dict(grouped)

class ProxyValidator:
    """Validation utilities for proxies"""
    
    @staticmethod
    def validate_proxy_format(proxy_string: str) -> Tuple[bool, str]:
        """Validate proxy string format (IP:PORT)"""
        try:
            parts = proxy_string.strip().split(':')
            if len(parts) != 2:
                return False, "Invalid format. Expected IP:PORT"
            
            ip, port = parts
            
            # Validate IP
            ip_parts = ip.split('.')
            if len(ip_parts) != 4:
                return False, "Invalid IP address"
            
            for part in ip_parts:
                if not part.isdigit() or not (0 <= int(part) <= 255):
                    return False, "Invalid IP address"
            
            # Validate port
            if not port.isdigit() or not (1 <= int(port) <= 65535):
                return False, "Invalid port number"
            
            return True, "Valid"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def validate_batch(lines: List[str]) -> Tuple[int, int, List[str]]:
        """Validate batch of proxy strings"""
        valid_count = 0
        invalid_lines = []
        
        for i, line in enumerate(lines):
            is_valid, _ = ProxyValidator.validate_proxy_format(line)
            if is_valid:
                valid_count += 1
            else:
                invalid_lines.append(f"Line {i+1}: {line}")
        
        return valid_count, len(lines) - valid_count, invalid_lines
