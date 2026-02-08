from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime

class ProxyType(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

class AnonymityLevel(str, Enum):
    ELITE = "elite"
    ANONYMOUS = "anonymous"
    TRANSPARENT = "transparent"

@dataclass
class Proxy:
    """Proxy data model"""
    ip: str
    port: int
    proxy_type: ProxyType
    anonymity: AnonymityLevel = AnonymityLevel.TRANSPARENT
    country: Optional[str] = None
    speed: Optional[float] = None  # ms
    last_checked: Optional[datetime] = None
    is_working: bool = False
    response_time: Optional[float] = None  # ms
    source: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    notes: str = ""
    
    def format_proxy_url(self) -> str:
        """Format proxy as URL"""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type.value}://{auth}{self.ip}:{self.port}"
    
    def format_proxy_string(self) -> str:
        """Format proxy as IP:PORT"""
        return f"{self.ip}:{self.port}"
    
    def __str__(self) -> str:
        status = "✓" if self.is_working else "✗"
        return f"{status} {self.ip}:{self.port} ({self.proxy_type.value.upper()}) - {self.country or 'N/A'}"

@dataclass
class CheckResult:
    """Proxy check result"""
    proxy: Proxy
    is_working: bool
    response_time: Optional[float] = None
    ip_leaked: bool = False
    anonymity_verified: AnonymityLevel = AnonymityLevel.TRANSPARENT
    geolocation: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    tested_protocol: Optional[str] = None
    
    def __str__(self) -> str:
        status = "PASS" if self.is_working else "FAIL"
        time_str = f"{self.response_time:.0f}ms" if self.response_time else "N/A"
        return f"[{status}] {self.proxy.format_proxy_string()} - {time_str} - {self.geolocation or 'Unknown'}"
