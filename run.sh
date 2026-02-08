#!/bin/bash
# Proxy Scraper & Checker Launcher for Linux/Mac

cd "$(dirname "$0")"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed"
    echo "Please install Python 3.9+ from python.org"
    exit 1
fi

# Check if dependencies are installed
python3 -c "import PyQt6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies"
        exit 1
    fi
fi

# Start the application
python3 main.py
