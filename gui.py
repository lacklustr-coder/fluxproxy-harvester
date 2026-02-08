import sys
from typing import List, Optional
from PyQt6.QtWidgets import (  # pyright: ignore[reportMissingImports]
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QGridLayout, QFormLayout, QDialog,
    QHeaderView, QDoubleSpinBox, QSlider, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize, QTimer  # pyright: ignore[reportMissingImports]
from PyQt6.QtGui import QColor, QFont, QIcon  # pyright: ignore[reportMissingImports]
from proxy_models import Proxy, ProxyType, CheckResult, AnonymityLevel
from scraper import ProxyScraper
from checker import ProxyChecker
from storage import ProxyStorage
from config import get_config, ScraperConfig, CheckerConfig
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperThread(QThread):
    """Worker thread for proxy scraping"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, config: ScraperConfig):
        super().__init__()
        self.config = config

    def run(self):
        try:
            scraper = ProxyScraper(self.config, self.progress.emit)
            proxies = scraper.scrape_all()
            self.finished.emit(proxies)
        except Exception as e:
            self.error.emit(str(e))

class CheckerThread(QThread):
    """Worker thread for proxy checking"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, config: CheckerConfig, proxies: List[Proxy]):
        super().__init__()
        self.config = config
        self.proxies = proxies

    def run(self):
        try:
            checker = ProxyChecker(self.config, self.progress.emit)
            results = checker.check_proxies(self.proxies)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class SourceSelectionDialog(QDialog):
    """Dialog for selecting proxy sources"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.selected_sources = self.config.scraper.selected_sources.copy()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Select Proxy Sources")
        self.setGeometry(100, 100, 700, 750)
        layout = QVBoxLayout()

        # Title
        layout.addWidget(QLabel("Select which proxy sources to scrape from:"))
        layout.addWidget(QLabel(f"Available: {len(ProxyScraper.SOURCES)} sources"))

        # Source list with checkboxes
        self.source_checks = {}
        sources_container = QWidget()
        sources_layout = QVBoxLayout()

        for source_name in sorted(ProxyScraper.SOURCES.keys()):
            check = QCheckBox(source_name)
            check.setChecked(source_name in self.selected_sources)
            self.source_checks[source_name] = check
            sources_layout.addWidget(check)

        sources_layout.addStretch()
        sources_container.setLayout(sources_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidget(sources_container)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Quick buttons
        quick_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        quick_layout.addWidget(select_all_btn)
        quick_layout.addWidget(deselect_all_btn)
        layout.addLayout(quick_layout)

        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def select_all(self):
        for check in self.source_checks.values():
            check.setChecked(True)

    def deselect_all(self):
        for check in self.source_checks.values():
            check.setChecked(False)

    def get_selected_sources(self):
        return [name for name, check in self.source_checks.items() if check.isChecked()]

class SettingsDialog(QDialog):
    """Settings configuration dialog"""

    def __init__(self, parent=None, is_scraper=True):
        super().__init__(parent)
        self.is_scraper = is_scraper
        self.config = get_config()
        self.selected_sources = self.config.scraper.selected_sources.copy() if is_scraper else []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 700, 600)
        layout = QVBoxLayout()

        if self.is_scraper:
            self._setup_scraper_settings(layout)
        else:
            self._setup_checker_settings(layout)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def _setup_scraper_settings(self, layout: QVBoxLayout):
        form = QFormLayout()

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setValue(self.config.scraper.timeout)
        self.timeout_spin.setRange(5, 60)
        form.addRow("Timeout (seconds):", self.timeout_spin)

        self.workers_spin = QSpinBox()
        self.workers_spin.setValue(self.config.scraper.max_workers)
        self.workers_spin.setRange(1, 250)
        form.addRow("Max Workers:", self.workers_spin)

        self.retry_spin = QSpinBox()
        self.retry_spin.setValue(self.config.scraper.retry_attempts)
        form.addRow("Retry Attempts:", self.retry_spin)

        self.user_agent_edit = QLineEdit()
        self.user_agent_edit.setText(self.config.scraper.user_agent)
        form.addRow("User Agent:", self.user_agent_edit)

        # Source selection button
        sources_layout = QHBoxLayout()
        sources_btn = QPushButton("Select Sources...")
        sources_btn.clicked.connect(self.open_source_selector)
        sources_info = QLabel(f"{len(self.selected_sources)} sources selected")
        self.sources_info_label = sources_info
        sources_layout.addWidget(sources_btn)
        sources_layout.addWidget(sources_info)
        form.addRow("Proxy Sources:", sources_layout)

        layout.addLayout(form)

    def open_source_selector(self):
        dialog = SourceSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_sources = dialog.get_selected_sources()
            self.sources_info_label.setText(f"{len(self.selected_sources)} sources selected")

    def _setup_checker_settings(self, layout: QVBoxLayout):
        form = QFormLayout()

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setValue(self.config.checker.timeout)
        self.timeout_spin.setRange(5, 60)
        form.addRow("Timeout (seconds):", self.timeout_spin)

        self.workers_spin = QSpinBox()
        self.workers_spin.setValue(self.config.checker.max_workers)
        self.workers_spin.setRange(1, 50)
        form.addRow("Max Workers:", self.workers_spin)

        self.test_anonymity_check = QCheckBox("Test Anonymity")
        self.test_anonymity_check.setChecked(self.config.checker.test_anonymity)
        form.addRow(self.test_anonymity_check)

        self.get_geo_check = QCheckBox("Get Geolocation")
        self.get_geo_check.setChecked(self.config.checker.get_geolocation)
        form.addRow(self.get_geo_check)

        self.speed_threshold_spin = QSpinBox()
        self.speed_threshold_spin.setValue(self.config.checker.speed_threshold)
        self.speed_threshold_spin.setRange(500, 20000)
        self.speed_threshold_spin.setSuffix(" ms")
        form.addRow("Speed Threshold:", self.speed_threshold_spin)

        self.export_format = QComboBox()
        self.export_format.addItems(["json", "csv", "txt"])
        self.export_format.setCurrentText(self.config.checker.export_format)
        form.addRow("Export Format:", self.export_format)

        self.custom_url_edit = QLineEdit()
        self.custom_url_edit.setText(self.config.checker.custom_test_url)
        form.addRow("Custom Test URL:", self.custom_url_edit)

        layout.addLayout(form)

class ScraperTab(QWidget):
    """Proxy Scraper Tab"""

    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.proxies: List[Proxy] = []
        self.scraper_thread: Optional[ScraperThread] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Proxy type filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Proxy Types:"))

        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems([
            "All (HTTP, HTTPS, SOCKS4, SOCKS5)",
            "HTTP Only",
            "HTTPS Only",
            "SOCKS4 Only",
            "SOCKS5 Only",
            "HTTP + HTTPS",
            "HTTP + SOCKS4 + SOCKS5",
            "HTTPS + SOCKS4 + SOCKS5"
        ])
        self.proxy_type_combo.setMinimumWidth(300)
        filter_layout.addWidget(self.proxy_type_combo)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Top controls
        controls = QHBoxLayout()

        self.scrape_btn = QPushButton("Start Scraping")
        self.scrape_btn.setMinimumHeight(35)
        self.scrape_btn.clicked.connect(self.start_scraping)
        controls.addWidget(self.scrape_btn)

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        controls.addWidget(self.settings_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_proxies)
        controls.addWidget(self.clear_btn)

        layout.addLayout(controls)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)

        # Proxy table
        self.proxy_table = QTableWidget()
        self.proxy_table.setColumnCount(8)
        self.proxy_table.setHorizontalHeaderLabels([
            "IP", "Port", "Type", "Anonymity", "Country", "Speed", "Status", "Source"
        ])
        self.proxy_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.proxy_table)

        # Bottom export controls
        export_layout = QHBoxLayout()

        self.export_json_btn = QPushButton("Save as JSON")
        self.export_json_btn.clicked.connect(lambda: self.export_proxies("json"))
        export_layout.addWidget(self.export_json_btn)

        self.export_csv_btn = QPushButton("Save as CSV")
        self.export_csv_btn.clicked.connect(lambda: self.export_proxies("csv"))
        export_layout.addWidget(self.export_csv_btn)

        self.export_txt_btn = QPushButton("Save as TXT (IP:PORT)")
        self.export_txt_btn.clicked.connect(lambda: self.export_proxies("txt"))
        export_layout.addWidget(self.export_txt_btn)

        self.load_btn = QPushButton("Load Proxies")
        self.load_btn.clicked.connect(self.load_proxies)
        export_layout.addWidget(self.load_btn)

        layout.addLayout(export_layout)

        self.setLayout(layout)

    def start_scraping(self):
        if not self.config.scraper.selected_sources:
            QMessageBox.warning(self, "No Sources", "Please select at least one proxy source in Settings")
            return

        self.clear_proxies()
        self.scrape_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Apply proxy type filter based on dropdown selection
        selected_index = self.proxy_type_combo.currentIndex()
        proxy_type_map = {
            0: ["http", "https", "socks4", "socks5"],
            1: ["http"],
            2: ["https"],
            3: ["socks4"],
            4: ["socks5"],
            5: ["http", "https"],
            6: ["http", "socks4", "socks5"],
            7: ["https", "socks4", "socks5"],
        }
        self.config.scraper.selected_proxy_types = proxy_type_map[selected_index]

        self.scraper_thread = ScraperThread(self.config.scraper)
        self.scraper_thread.progress.connect(self.on_progress)
        self.scraper_thread.finished.connect(self.on_scrape_finished)
        self.scraper_thread.error.connect(self.on_error)
        self.scraper_thread.start()

    def on_progress(self, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_scrape_finished(self, proxies: List[Proxy]):
        self.proxies = proxies
        self.display_proxies()
        self.scrape_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.on_progress(f"Scraping complete: {len(proxies)} proxies found")

    def on_error(self, error: str):
        self.on_progress(f"ERROR: {error}")
        self.scrape_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", error)

    def display_proxies(self):
        self.proxy_table.setRowCount(len(self.proxies))
        for row, proxy in enumerate(self.proxies):
            self.proxy_table.setItem(row, 0, QTableWidgetItem(proxy.ip))
            self.proxy_table.setItem(row, 1, QTableWidgetItem(str(proxy.port)))
            self.proxy_table.setItem(row, 2, QTableWidgetItem(proxy.proxy_type.value.upper()))
            self.proxy_table.setItem(row, 3, QTableWidgetItem(proxy.anonymity.value.title()))
            self.proxy_table.setItem(row, 4, QTableWidgetItem(proxy.country or "N/A"))
            self.proxy_table.setItem(row, 5, QTableWidgetItem(f"{proxy.speed or 'N/A'}"))
            status = "✓" if proxy.is_working else "⊘"
            self.proxy_table.setItem(row, 6, QTableWidgetItem(status))
            self.proxy_table.setItem(row, 7, QTableWidgetItem(proxy.source or "Unknown"))

    def export_proxies(self, format_type: str):
        if not self.proxies:
            QMessageBox.warning(self, "No Proxies", "Please scrape proxies first")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Proxies as {format_type.upper()}",
            "",
            f"{format_type.upper()} Files (*.{format_type})"
        )

        if filename:
            if format_type == "json":
                ProxyStorage.save_proxies_json(self.proxies, filename)
            elif format_type == "csv":
                ProxyStorage.save_proxies_csv(self.proxies, filename)
            elif format_type == "txt":
                ProxyStorage.save_proxies_txt(self.proxies, filename)
            QMessageBox.information(self, "Success", f"Proxies saved to {filename}")

    def load_proxies(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Proxies",
            "",
            "All Files (*.json *.txt);;JSON Files (*.json);;Text Files (*.txt)"
        )

        if filename:
            if filename.endswith('.json'):
                self.proxies = ProxyStorage.load_proxies_json(filename)
            else:
                self.proxies = ProxyStorage.load_proxies_txt(filename)
            self.display_proxies()
            self.on_progress(f"Loaded {len(self.proxies)} proxies from {filename}")

    def clear_proxies(self):
        self.proxies = []
        self.proxy_table.setRowCount(0)
        self.log_text.clear()

    def open_settings(self):
        dialog = SettingsDialog(self, is_scraper=True)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.scraper.timeout = dialog.timeout_spin.value()
            self.config.scraper.max_workers = dialog.workers_spin.value()
            self.config.scraper.retry_attempts = dialog.retry_spin.value()
            self.config.scraper.user_agent = dialog.user_agent_edit.text()
            if hasattr(dialog, 'selected_sources'):
                self.config.scraper.selected_sources = dialog.selected_sources
            # Save the updated config
            self.config.save_to_env()

class CheckerTab(QWidget):
    """Proxy Checker Tab"""

    def __init__(self, scraper_tab: ScraperTab):
        super().__init__()
        self.config = get_config()
        self.scraper_tab = scraper_tab
        self.results: List[CheckResult] = []
        self.checker_thread: Optional[CheckerThread] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Top controls
        controls = QHBoxLayout()

        self.load_from_scraper_btn = QPushButton("Load from Scraper")
        self.load_from_scraper_btn.clicked.connect(self.load_from_scraper)
        controls.addWidget(self.load_from_scraper_btn)

        self.load_file_btn = QPushButton("Load from File")
        self.load_file_btn.clicked.connect(self.load_from_file)
        controls.addWidget(self.load_file_btn)

        self.check_btn = QPushButton("Start Checking")
        self.check_btn.setMinimumHeight(35)
        self.check_btn.clicked.connect(self.start_checking)
        controls.addWidget(self.check_btn)

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        controls.addWidget(self.settings_btn)

        layout.addLayout(controls)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "IP", "Port", "Type", "Working", "Speed (ms)", "Anonymity", "Geolocation", "Timestamp"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.results_table)

        # Bottom export controls
        export_layout = QHBoxLayout()

        self.filter_working_check = QCheckBox("Only Working")
        self.filter_working_check.toggled.connect(self.display_results)
        export_layout.addWidget(self.filter_working_check)

        self.fast_speed_spin = QSpinBox()
        self.fast_speed_spin.setRange(100, 20000)
        self.fast_speed_spin.setValue(5000)
        self.fast_speed_spin.setSuffix(" ms")
        export_layout.addWidget(QLabel("Filter Fast:"))
        export_layout.addWidget(self.fast_speed_spin)

        self.filter_fast_check = QCheckBox("Apply")
        self.filter_fast_check.toggled.connect(self.display_results)
        export_layout.addWidget(self.filter_fast_check)

        layout.addLayout(export_layout)

        # Save results
        save_layout = QHBoxLayout()

        self.save_json_btn = QPushButton("Save Results as JSON")
        self.save_json_btn.clicked.connect(lambda: self.export_results("json"))
        save_layout.addWidget(self.save_json_btn)

        self.save_csv_btn = QPushButton("Save Results as CSV")
        self.save_csv_btn.clicked.connect(lambda: self.export_results("csv"))
        save_layout.addWidget(self.save_csv_btn)

        self.save_txt_btn = QPushButton("Save Working Proxies")
        self.save_txt_btn.clicked.connect(lambda: self.export_results("txt"))
        save_layout.addWidget(self.save_txt_btn)

        layout.addLayout(save_layout)

        self.setLayout(layout)

    def load_from_scraper(self):
        if not self.scraper_tab.proxies:
            QMessageBox.warning(self, "No Proxies", "Please scrape proxies first in the Scraper tab")
            return

        self.log_text.append(f"Loaded {len(self.scraper_tab.proxies)} proxies from scraper")
        self.log_text.append("Ready to check. Click 'Start Checking' to begin.")

    def load_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Proxies",
            "",
            "All Files (*.json *.txt);;JSON Files (*.json);;Text Files (*.txt)"
        )

        if filename:
            if filename.endswith('.json'):
                self.scraper_tab.proxies = ProxyStorage.load_proxies_json(filename)
            else:
                self.scraper_tab.proxies = ProxyStorage.load_proxies_txt(filename)
            self.log_text.append(f"Loaded {len(self.scraper_tab.proxies)} proxies from {filename}")

    def start_checking(self):
        if not self.scraper_tab.proxies:
            QMessageBox.warning(self, "No Proxies", "Load proxies first")
            return

        self.check_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.checker_thread = CheckerThread(self.config.checker, self.scraper_tab.proxies)
        self.checker_thread.progress.connect(self.on_progress)
        self.checker_thread.finished.connect(self.on_check_finished)
        self.checker_thread.error.connect(self.on_error)
        self.checker_thread.start()

    def on_progress(self, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_check_finished(self, results: List[CheckResult]):
        self.results = results
        self.display_results()
        self.check_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        working = sum(1 for r in results if r.is_working)
        self.on_progress(f"Check complete: {working}/{len(results)} proxies working")

    def on_error(self, error: str):
        self.on_progress(f"ERROR: {error}")
        self.check_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", error)

    def display_results(self):
        filtered = self.results

        if self.filter_working_check.isChecked():
            filtered = [r for r in filtered if r.is_working]

        if self.filter_fast_check.isChecked():
            threshold = self.fast_speed_spin.value()
            filtered = [r for r in filtered if r.response_time and r.response_time <= threshold]

        self.results_table.setRowCount(len(filtered))
        for row, result in enumerate(filtered):
            self.results_table.setItem(row, 0, QTableWidgetItem(result.proxy.ip))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(result.proxy.port)))
            self.results_table.setItem(row, 2, QTableWidgetItem(result.proxy.proxy_type.value.upper()))
            status = "✓ PASS" if result.is_working else "✗ FAIL"
            self.results_table.setItem(row, 3, QTableWidgetItem(status))
            speed = f"{result.response_time:.0f}" if result.response_time else "N/A"
            self.results_table.setItem(row, 4, QTableWidgetItem(speed))
            self.results_table.setItem(row, 5, QTableWidgetItem(result.anonymity_verified.value.title()))
            self.results_table.setItem(row, 6, QTableWidgetItem(result.geolocation or "N/A"))
            timestamp = result.timestamp.strftime("%H:%M:%S") if result.timestamp else "N/A"
            self.results_table.setItem(row, 7, QTableWidgetItem(timestamp))

    def export_results(self, format_type: str):
        if not self.results:
            QMessageBox.warning(self, "No Results", "Check proxies first")
            return

        # Filter for working proxies for txt export
        export_data = self.results
        if format_type == "txt":
            export_data = [r for r in self.results if r.is_working]

        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Results as {format_type.upper()}",
            "",
            f"{format_type.upper()} Files (*.{format_type})"
        )

        if filename:
            if format_type == "json":
                ProxyStorage.save_results_json(export_data, filename)
            elif format_type == "csv":
                checker = ProxyChecker(self.config.checker)
                checker.export_results(export_data, filename)
            elif format_type == "txt":
                with open(filename, 'w') as f:
                    for result in export_data:
                        f.write(f"{result.proxy.ip}:{result.proxy.port}\n")

            QMessageBox.information(self, "Success", f"Results saved to {filename}")

    def open_settings(self):
        dialog = SettingsDialog(self, is_scraper=False)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.checker.timeout = dialog.timeout_spin.value()
            self.config.checker.max_workers = dialog.workers_spin.value()
            self.config.checker.test_anonymity = dialog.test_anonymity_check.isChecked()
            self.config.checker.get_geolocation = dialog.get_geo_check.isChecked()
            self.config.checker.speed_threshold = dialog.speed_threshold_spin.value()
            self.config.checker.export_format = dialog.export_format.currentText()
            self.config.checker.custom_test_url = dialog.custom_url_edit.text()

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxy Scraper & Checker - Enterprise Edition")
        self.setGeometry(100, 100, 1400, 900)

        # Create tabs
        tabs = QTabWidget()

        scraper_tab = ScraperTab()
        checker_tab = CheckerTab(scraper_tab)

        tabs.addTab(scraper_tab, "📥 Proxy Scraper")
        tabs.addTab(checker_tab, "🔍 Proxy Checker")

        self.setCentralWidget(tabs)

        # Style
        self.setStyle()

    def setStyle(self):
        style = """
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0d3d8f;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                gridline-color: #404040;
            }
            QHeaderView::section {
                background-color: #0d47a1;
                color: white;
                padding: 5px;
                border: none;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #00ff00;
                font-family: Courier;
            }
        """
        self.setStyleSheet(style)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
