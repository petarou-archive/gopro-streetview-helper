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

def resource_path(relative_path):
    """ PyInstallerの一時フォルダ、または現在のディレクトリから絶対パスを取得 """
    #if hasattr(sys, '_MEIPASS'):
    #    return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class GoProGPSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro MAX Street View Helper (Final Fix 2025)")
        self.setMinimumSize(1100, 750)
        
        self.path_360 = ""
        self.path_mp4 = ""
        self.coords_data = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.control_panel = QVBoxLayout()
        self.main_layout.addLayout(self.control_panel, 1)

        self.btn_select_360 = QPushButton("1. 元の .360 ファイルを選択")
        self.btn_select_360.clicked.connect(self.select_360)
        self.control_panel.addWidget(self.btn_select_360)
        self.label_360 = QLabel("未選択")
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
        
        self.info_label = QLabel("※GPXはMP4と同じ場所に保存されます")
        self.info_label.setStyleSheet("color: gray; font-size: 10px;")
        self.control_panel.addWidget(self.info_label)
        self.control_panel.addStretch()

        self.web_view = QWebEngineView()
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        self.main_layout.addWidget(self.web_view, 3)
        self.init_map()

    def init_map(self):
        js_path = QUrl.fromLocalFile(resource_path("leaflet.js")).toString()
        css_path = QUrl.fromLocalFile(resource_path("leaflet.css")).toString()

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
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                }}
                function updateRoute(coordsJson) {{
                    try {{
                        initMap();
                        var coords = JSON.parse(coordsJson);
                        if (polyline) map.removeLayer(polyline);
                        if (coords.length > 0) {{
                            polyline = L.polyline(coords, {{color: 'blue', weight: 5}}).addTo(map);
                            map.fitBounds(polyline.getBounds());
                            return "Success";
                        }}
                    }} catch (e) {{ return e.message; }}
                }}
                window.onload = initMap;
            </script>
        </body>
        </html>
        """
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
        # 1. パスと出力ファイル名の設定
        mp4_dir = os.path.dirname(self.path_mp4)
        mp4_base = os.path.basename(self.path_mp4)
        name_only = os.path.splitext(mp4_base)[0]
        
        # 新しいMP4ファイル名 (例: original_fixed.mp4)
        fixed_mp4_path = os.path.join(mp4_dir, f"{name_only}_fixed.mp4")
        # 新しいGPXファイル名 (Street View StudioのためにMP4名と一致させる)
        output_gpx = os.path.join(mp4_dir, f"{name_only}_fixed.gpx")
        
        exiftool_exe = resource_path("exiftool.exe")
        gpx_fmt = resource_path("gpx.fmt")

        try:
            # 2. 元の .360 から正しい撮影日時(UTC)を抽出
            res = subprocess.run([exiftool_exe, "-CreateDate", "-s3", "-S", self.path_360], 
                                 capture_output=True, text=True, check=True)
            correct_date = res.stdout.strip()

            if not correct_date:
                QMessageBox.warning(self, "警告", ".360ファイルから撮影日時を取得できませんでした。")
                return

            # 3. MP4を別名でコピーしながら、メタデータを修正して出力
            # -o オプションで別名保存。既存の fixed ファイルがあれば上書き。
            print(f"Creating fixed MP4: {fixed_mp4_path} with date {correct_date}")
            subprocess.run([
                exiftool_exe,
                f"-CreateDate={correct_date}",
                f"-ModifyDate={correct_date}",
                f"-TrackCreateDate={correct_date}",
                f"-TrackModifyDate={correct_date}",
                f"-MediaCreateDate={correct_date}",
                f"-MediaModifyDate={correct_date}",
                "-o", fixed_mp4_path,
                self.path_mp4
            ], check=True)

            # 4. GPXの抽出 (ミリ秒精度のISO形式)
            # ここでは .360 から抽出するため、時刻は自動的に correct_date と一致します
            cmd = [
                exiftool_exe,
                "-api", "TimePrecision=3",
                "-p", gpx_fmt,
                "-ee",
                "-c", "%.8f",
                self.path_360
            ]
            with open(output_gpx, "w", encoding="utf-8") as f:
                subprocess.run(cmd, stdout=f, check=True)

            # 5. 地図描画・完了通知
            self.coords_data = self.parse_gpx(output_gpx)
            if self.coords_data:
                json_data = json.dumps(self.coords_data)
                self.web_view.page().runJavaScript(f"updateRoute('{json_data}')")
                
                QMessageBox.information(
                    self, "成功", 
                    f"処理が完了しました。\n\n"
                    f"1. 動画: {os.path.basename(fixed_mp4_path)}\n"
                    f"2. GPS: {os.path.basename(output_gpx)}\n\n"
                    "上記2つのファイルを同時にアップロードしてください。"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"失敗しました: {str(e)}")

    def parse_gpx(self, gpx_path):
        coords = []
        try:
            tree = ET.parse(gpx_path)
            for trkpt in tree.getroot().iter():
                if trkpt.tag.endswith('trkpt'):
                    coords.append([float(trkpt.get('lat')), float(trkpt.get('lon'))])
        except Exception as e:
            print(f"GPX Parse Error: {e}")
        return coords

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GoProGPSApp()
    window.show()
    sys.exit(app.exec())
