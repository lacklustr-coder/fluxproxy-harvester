import json
import csv
from typing import List
from proxy_models import Proxy, ProxyType, AnonymityLevel, CheckResult
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class ProxyStorage:
    """Handle proxy data persistence"""
    
    @staticmethod
    def save_proxies_json(proxies: List[Proxy], filepath: str):
        """Save proxies to JSON file"""
        try:
            data = [
                {
                    "ip": p.ip,
                    "port": p.port,
                    "type": p.proxy_type.value,
                    "anonymity": p.anonymity.value,
                    "country": p.country,
                    "speed": p.speed,
                    "is_working": p.is_working,
                    "last_checked": p.last_checked.isoformat() if p.last_checked else None,
                    "source": p.source,
                    "username": p.username,
                    "password": p.password,
                    "notes": p.notes
                }
                for p in proxies
            ]
            
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(proxies)} proxies to {filepath}")
        except Exception as e:
            logger.error(f"Error saving proxies to JSON: {e}")
    
    @staticmethod
    def save_proxies_csv(proxies: List[Proxy], filepath: str):
        """Save proxies to CSV file"""
        try:
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["IP", "Port", "Type", "Anonymity", "Country", "Speed (ms)", "Working", "Last Checked", "Source"])
                for p in proxies:
                    writer.writerow([
                        p.ip, p.port, p.proxy_type.value, p.anonymity.value,
                        p.country or "N/A", p.speed or "N/A",
                        "Yes" if p.is_working else "No",
                        p.last_checked.isoformat() if p.last_checked else "N/A",
                        p.source or "Unknown"
                    ])
            logger.info(f"Saved {len(proxies)} proxies to {filepath}")
        except Exception as e:
            logger.error(f"Error saving proxies to CSV: {e}")
    
    @staticmethod
    def save_proxies_txt(proxies: List[Proxy], filepath: str):
        """Save proxies as plain IP:PORT list"""
        try:
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                for p in proxies:
                    f.write(f"{p.ip}:{p.port}\n")
            logger.info(f"Saved {len(proxies)} proxies to {filepath}")
        except Exception as e:
            logger.error(f"Error saving proxies to TXT: {e}")
    
    @staticmethod
    def load_proxies_json(filepath: str) -> List[Proxy]:
        """Load proxies from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            proxies = []
            for item in data:
                proxy = Proxy(
                    ip=item['ip'],
                    port=item['port'],
                    proxy_type=ProxyType[item['type'].upper()],
                    anonymity=AnonymityLevel[item.get('anonymity', 'transparent').upper()],
                    country=item.get('country'),
                    speed=item.get('speed'),
                    is_working=item.get('is_working', False),
                    last_checked=datetime.fromisoformat(item['last_checked']) if item.get('last_checked') else None,
                    source=item.get('source'),
                    username=item.get('username'),
                    password=item.get('password'),
                    notes=item.get('notes', '')
                )
                proxies.append(proxy)
            
            logger.info(f"Loaded {len(proxies)} proxies from {filepath}")
            return proxies
        except Exception as e:
            logger.error(f"Error loading proxies from JSON: {e}")
            return []
    
    @staticmethod
    def load_proxies_txt(filepath: str) -> List[Proxy]:
        """Load proxies from IP:PORT text file"""
        try:
            proxies = []
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        ip, port = line.split(':')
                        proxy = Proxy(
                            ip=ip.strip(),
                            port=int(port.strip()),
                            proxy_type=ProxyType.HTTP
                        )
                        proxies.append(proxy)
                    except ValueError:
                        logger.warning(f"Invalid proxy format: {line}")
                        continue
            
            logger.info(f"Loaded {len(proxies)} proxies from {filepath}")
            return proxies
        except Exception as e:
            logger.error(f"Error loading proxies from TXT: {e}")
            return []
    
    @staticmethod
    def save_results_json(results: List[CheckResult], filepath: str):
        """Save check results to JSON"""
        try:
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
            data = [
                {
                    "ip": r.proxy.ip,
                    "port": r.proxy.port,
                    "type": r.proxy.proxy_type.value,
                    "is_working": r.is_working,
                    "response_time_ms": r.response_time,
                    "anonymity": r.anonymity_verified.value,
                    "geolocation": r.geolocation,
                    "timestamp": r.timestamp.isoformat(),
                    "error": r.error
                }
                for r in results
            ]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(results)} results to {filepath}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
