MediaFire Downloader (PyQt5)

A simple and elegant desktop application for downloading multiple files from MediaFire in bulk.

Features
✅ Load multiple MediaFire links from a .txt file

⬇ Download multiple files in parallel (configurable number of threads)

📊 Individual progress bars and status display for each download

📈 Live display of total download speed

📁 Files are automatically saved into a downloads/ folder


Requirements:

    youtube_downloader/
    PyQt5
    selenium
    requests
    webdriver-manager


Pyinstaller:

    pyinstaller --onefile --windowed --add-data "chromium-1169;chromium-1169" --icon=app_icon.ico mediafire.py


Download the Binary here:

<img src="https://github.com/GoatWithCode/MediaFire-Downloader/blob/main/Screenshot%202025-05-21%20194056.png" alt="MediaFire-downloader" width="800" height="400">
