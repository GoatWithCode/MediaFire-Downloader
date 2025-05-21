MediaFire Downloader (PyQt5)

A simple and elegant desktop application for downloading multiple files from MediaFire in bulk.

Features
✅ Load multiple MediaFire links from a .txt file

⬇ Download multiple files in parallel (configurable number of threads)

📊 Individual progress bars and status display for each download

📈 Live display of total download speed

📁 Files are automatically saved into a downloads/ folder


Requirements:
Python 3.8+

Google Chrome browser (for Selenium)

Required Python packages:
PyQt5
selenium
requests
webdriver-manager

Pyinstaller:
pyinstaller --onefile --windowed --add-data "chromium-1169;chromium-1169" --icon=app_icon.ico mediafire.py
