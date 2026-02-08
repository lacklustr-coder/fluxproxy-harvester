#!/usr/bin/env python3
"""
Enterprise Proxy Scraper & Checker
A badass application for scraping and validating HTTP(S)/SOCKS4/SOCKS5 proxies
"""

import sys
import logging
from gui import main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
