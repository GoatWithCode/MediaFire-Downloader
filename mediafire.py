import sys
import os
import time
import requests
import rarfile  # Für RAR entpacken (bleibt, falls du es später brauchst)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QSpinBox, QFileDialog, QProgressBar, QFrame, QCheckBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, pyqtSlot

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    speed = pyqtSignal(float)
    status = pyqtSignal(str)
    done = pyqtSignal()


class DownloadWorker(QRunnable):
    def __init__(self, url, output_folder, ui_elements, window):
        super().__init__()
        self.url = url
        self.output_folder = output_folder
        self.ui_elements = ui_elements
        self.window = window
        self.signals = WorkerSignals()

        self.signals.progress.connect(self.ui_elements['progress'].setValue)
        self.signals.status.connect(self.ui_elements['status'].setText)

    @pyqtSlot()
    def run(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get(self.url)

            wait = WebDriverWait(driver, 30)
            download_button = wait.until(EC.presence_of_element_located((By.ID, "downloadButton")))
            direct_link = download_button.get_attribute("href")
            driver.quit()

            filename = direct_link.split("/")[-1].split("?")[0]
            file_path = os.path.join(self.output_folder, filename)

            with requests.get(direct_link, stream=True) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                last_update = 0

                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = int((downloaded / total) * 100) if total else 0
                            self.signals.progress.emit(percent)

                            now = time.time()
                            if now - last_update > 0.5:
                                speed = downloaded / (now - start_time) / (1024 * 1024)
                                self.signals.speed.emit(speed)
                                self.window.update_total_speed()
                                last_update = now

            self.signals.status.emit(f"✅ Fertig: {filename}")
        except Exception as e:
            self.signals.status.emit(f"❌ Fehler: {str(e)}")
        finally:
            self.signals.done.emit()


class MediafireDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MediaFire Downloader")
        self.resize(800, 740)
        self.download_items = []
        self.total_speed = 0.0
        self.active_workers = 0

        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;  /* Weißer Hintergrund */
                font-family: Segoe UI, sans-serif;
                font-size: 12pt;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 8px;
                height: 16px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #5cb85c;
                border-radius: 8px;
            }
            QLabel {
                font-size: 11pt;
            }
        """)

        main_layout = QVBoxLayout()

        # Logo oben
        logo_label = QLabel()
        pixmap = QPixmap("logo.png")
        pixmap = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignHCenter)
        main_layout.addWidget(logo_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.load_button = QPushButton("📂 Links laden")
        self.load_button.clicked.connect(self.load_links)
        self.start_button = QPushButton("⬇ Download starten")
        self.start_button.clicked.connect(self.start_downloads)
        btn_layout.addWidget(self.load_button)
        btn_layout.addWidget(self.start_button)
        main_layout.addLayout(btn_layout)

        # Max Threads
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("🧵 Max. parallel:"))
        self.thread_spin = QSpinBox()
        self.thread_spin.setMinimum(1)
        self.thread_spin.setMaximum(20)
        self.thread_spin.setValue(2)
        thread_layout.addWidget(self.thread_spin)
        thread_layout.addStretch()
        main_layout.addLayout(thread_layout)

        # Scrollbereich für einzelne Fortschritte
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Checkbox entfernt - nur Speed Label unten
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.speed_label = QLabel("⬇ Gesamtgeschwindigkeit: 0 MB/s")
        self.speed_label.setStyleSheet("font-weight: bold; padding: 8px;")
        bottom_layout.addWidget(self.speed_label)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        self.thread_pool = QThreadPool()

        # Downloadordner anlegen
        self.download_folder = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

    def load_links(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Links aus Datei laden", "", "Textdateien (*.txt)")
        if not file_path:
            return
        with open(file_path, 'r') as f:
            links = [line.strip() for line in f if line.strip()]
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.download_items.clear()

        for i in reversed(range(self.scroll_layout.count())):
            widget_to_remove = self.scroll_layout.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)

        for url in links:
            self.add_download_widget(url)

    def add_download_widget(self, url):
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(container)

        label = QLabel(url)
        progress = QProgressBar()
        status = QLabel("Warte...")
        layout.addWidget(label)
        layout.addWidget(progress)
        layout.addWidget(status)

        self.scroll_layout.addWidget(container)

        item = {
            'url': url,
            'progress': progress,
            'status': status,
            'container': container,
            'speed': 0.0
        }
        self.download_items.append(item)

    def update_total_speed(self):
        self.total_speed = sum(item['speed'] for item in self.download_items)
        self.speed_label.setText(f"⬇ Gesamtgeschwindigkeit: {self.total_speed:.2f} MB/s")

    def start_downloads(self):
        self.thread_pool.setMaxThreadCount(self.thread_spin.value())
        self.active_workers = 0
        for item in self.download_items:
            worker = DownloadWorker(
                item['url'], self.download_folder, item, self
            )
            worker.signals.speed.connect(lambda s, it=item: self.set_item_speed(it, s))
            worker.signals.done.connect(self.handle_worker_done)
            self.active_workers += 1
            self.thread_pool.start(worker)

    def set_item_speed(self, item, speed):
        item['speed'] = speed

    def handle_worker_done(self):
        self.active_workers -= 1
        if self.active_workers == 0:
            self.speed_label.setText("⬇ Gesamtgeschwindigkeit: 0 MB/s")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MediafireDownloader()
    window.show()
    sys.exit(app.exec_())
