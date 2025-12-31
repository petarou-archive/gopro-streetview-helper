import sys
import os
import subprocess
import json
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QMessageBox, QHBoxLayout)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import Qt, QUrl

class GoProGPSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro MAX Street View Helper (Local Map Mode)")
        self.setMinimumSize(1100, 750)
        
        self.path_360 = ""
        self.path_mp4 = ""
        self.coords_data = []

        # UI Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.control_panel = QVBoxLayout()
        self.main_layout.addLayout(self.control_panel, 1)

        self.btn_select_360 = QPushButton("1. 元の .360 ファイルを選択")
        self.btn_select_360.clicked.connect(self.select_360)
        self.control_panel.addWidget(self.btn_select_360)
        self.label_360 = QLabel("未選択")
        self.control_panel.setSpacing(10)
        self.control_panel.addWidget(self.label_360)

        self.btn_select_mp4 = QPushButton("2. エクスポート済みの .mp4 を選択")
        self.btn_select_mp4.clicked.connect(self.select_mp4)
        self.control_panel.addWidget(self.btn_select_mp4)
        self.label_mp4 = QLabel("未選択")
        self.control_panel.addWidget(self.label_mp4)

        self.btn_process = QPushButton("GPX作成 ＆ ルート表示")
        self.btn_process.setFixedHeight(60)
        self.btn_process.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.process_files)
        self.control_panel.addWidget(self.btn_process)
        self.control_panel.addStretch()

        # WebEngine設定
        self.web_view = QWebEngineView()
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        self.main_layout.addWidget(self.web_view, 3)
        self.init_map()

    def init_map(self):
        # ローカルファイルの絶対パスを取得 (Windowsのパス区切りに対応)
        base_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
        js_path = f"file:///{base_dir}/leaflet.js"
        css_path = f"file:///{base_dir}/leaflet.css"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <link rel="stylesheet" href="{css_path}" />
            <script src="{js_path}"></script>
            <style>
                body, html, #map {{ height: 100%; width: 100%; margin: 0; padding: 0; background-color: #f0f0f0; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map;
                var polyline = null;

                function initMap() {{
                    if (map) return;
                    map = L.map('map').setView([35.68, 139.76], 5);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        attribution: '&copy; OpenStreetMap'
                    }}).addTo(map);
                    console.log("Map Initialized");
                }}

                function updateRoute(coordsJson) {{
                    try {{
                        initMap();
                        var coords = JSON.parse(coordsJson);
                        if (polyline) map.removeLayer(polyline);
                        if (coords.length > 0) {{
                            polyline = L.polyline(coords, {{color: 'red', weight: 4, opacity: 0.8}}).addTo(map);
                            map.fitBounds(polyline.getBounds());
                            return "Drawing: " + coords.length + " points";
                        }}
                        return "No data";
                    }} catch (e) {{
                        return "JS Error: " + e.message;
                    }}
                }}
                window.onload = initMap;
            </script>
        </body>
        </html>
        """
        # baseUrlを指定することでローカルファイルの読み込みを許可
        self.web_view.setHtml(html_content, QUrl.fromLocalFile(os.path.abspath(__file__)))

    def select_360(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select .360", "", "GoPro Files (*.360)")
        if file:
            self.path_360 = file
            self.label_360.setText(os.path.basename(file))
            self.check_ready()

    def select_mp4(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select .mp4", "", "Video Files (*.mp4)")
        if file:
            self.path_mp4 = file
            self.label_mp4.setText(os.path.basename(file))
            self.check_ready()

    def check_ready(self):
        if self.path_360 and self.path_mp4:
            self.btn_process.setEnabled(True)

    def process_files(self):
        # 拡張子変更の修正
        output_gpx = os.path.splitext(self.path_mp4)[0] + ".gpx"
        exiftool_exe = os.path.join(os.path.dirname(__file__), "exiftool.exe")
        gpx_fmt = os.path.join(os.path.dirname(__file__), "gpx.fmt")

        if not os.path.exists(exiftool_exe):
            QMessageBox.critical(self, "Error", f"exiftool.exeが見つかりません:\n{exiftool_exe}")
            return

        try:
            # 1. GPX抽出
            with open(output_gpx, "w", encoding="utf-8") as f:
                subprocess.run([exiftool_exe, "-p", gpx_fmt, "-ee", self.path_360], stdout=f, check=True)

            # 2. GPX解析
            self.coords_data = self.parse_gpx(output_gpx)
            
            if self.coords_data:
                # 3. 地図描画
                json_data = json.dumps(self.coords_data)
                self.web_view.page().runJavaScript(f"updateRoute('{json_data}')", self.js_callback)
                QMessageBox.information(self, "完了", f"GPXファイルを作成し、地図を更新しました。\n保存先: {os.path.basename(output_gpx)}")
            else:
                QMessageBox.warning(self, "警告", "GPSデータが抽出できませんでした。")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"処理中にエラーが発生しました: {str(e)}")

    def parse_gpx(self, gpx_path):
        coords = []
        try:
            tree = ET.parse(gpx_path)
            for trkpt in tree.getroot().iter():
                if trkpt.tag.endswith('trkpt'):
                    lat = trkpt.get('lat')
                    lon = trkpt.get('lon')
                    if lat and lon:
                        coords.append([float(lat), float(lon)])
        except Exception as e:
            print(f"GPX Parse Error: {e}")
        return coords

    def js_callback(self, result):
        print(f"JavaScript Response: {result}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 高DPIディスプレイ対応 (2025年の標準的PC向け)
    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    window = GoProGPSApp()
    window.show()
    sys.exit(app.exec())
