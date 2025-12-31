import sys
import os
import subprocess
import json
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QFileDialog, QLabel, QMessageBox,
                             QHBoxLayout, QRadioButton, QButtonGroup, QFrame)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import Qt, QUrl

def resource_path(relative_path):
    #if hasattr(sys, '_MEIPASS'):
    #    return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class GoProGPSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro MAX Street View Helper (2025 Edition)")
        self.setMinimumSize(1100, 750)

        self.path_360 = ""
        self.path_mp4 = ""
        self.coords_data = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # --- 左側コントロールパネル ---
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

        # 保存設定（ラジオボタン）
        self.group_box = QFrame()
        self.group_box.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.vbox_radio = QVBoxLayout(self.group_box)
        self.vbox_radio.addWidget(QLabel("MP4時刻修正の設定:"))

        self.radio_overwrite = QRadioButton("MP4を直接上書き修正")
        self.radio_overwrite.setChecked(True) # デフォルト
        self.radio_copy = QRadioButton("別名ファイルを作成 (_fixed)")

        self.vbox_radio.addWidget(self.radio_overwrite)
        self.vbox_radio.addWidget(self.radio_copy)
        self.control_panel.addWidget(self.group_box)

        self.btn_process = QPushButton("実行（時刻修正 ＆ GPX作成）")
        self.btn_process.setFixedHeight(60)
        self.btn_process.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; font-size: 14px;")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.process_files)
        self.control_panel.addWidget(self.btn_process)

        self.control_panel.addStretch()

        # --- 右側地図パネル ---
        self.web_view = QWebEngineView()
        self.main_layout.addWidget(self.web_view, 3)
        self.init_map()

    def init_map(self):
        js_path = QUrl.fromLocalFile(resource_path("leaflet.js")).toString()
        css_path = QUrl.fromLocalFile(resource_path("leaflet.css")).toString()
        html_content = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8"/><link rel="stylesheet" href="{css_path}"/><script src="{js_path}"></script>
        <style>body,html,#map {{height:100%;width:100%;margin:0;padding:0;background:#f0f0f0;}}</style></head>
        <body><div id="map"></div><script>
        var map; var polyline = null;
        function initMap() {{ if (map) return; map = L.map('map').setView([35.68, 139.76], 5);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map); }}
        function updateRoute(coordsJson) {{ try {{ initMap(); var coords = JSON.parse(coordsJson);
        if (polyline) map.removeLayer(polyline); if (coords.length > 0) {{
        polyline = L.polyline(coords, {{color:'blue',weight:5}}).addTo(map); map.fitBounds(polyline.getBounds());
        return "OK"; }} }} catch(e) {{ return e.message; }} }}
        window.onload = initMap;</script></body></html>
        """
        self.web_view.setHtml(html_content, QUrl.fromLocalFile(os.path.abspath(__file__)))

    def select_360(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select .360", "", "GoPro Files (*.360)")
        if file: self.path_360 = file; self.label_360.setText(os.path.basename(file)); self.check_ready()

    def select_mp4(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select .mp4", "", "Video Files (*.mp4)")
        if file: self.path_mp4 = file; self.label_mp4.setText(os.path.basename(file)); self.check_ready()

    def check_ready(self):
        if self.path_360 and self.path_mp4: self.btn_process.setEnabled(True)

    def process_files(self):
        exiftool_exe = resource_path("exiftool.exe")
        gpx_fmt = resource_path("gpx.fmt")

        # 保存パスの決定
        if self.radio_overwrite.isChecked():
            target_mp4 = self.path_mp4
            output_gpx = os.path.splitext(self.path_mp4)[0] + ".gpx"
        else:
            target_mp4 = os.path.splitext(self.path_mp4)[0] + "_fixed.mp4"
            output_gpx = os.path.splitext(self.path_mp4)[0] + "_fixed.gpx"
            # 別名保存で同名ファイルがある場合は削除（ExifToolの仕様回避）
            if os.path.exists(target_mp4): os.remove(target_mp4)

        try:
            # 1. 撮影日時の抽出
            res = subprocess.run([exiftool_exe, "-CreateDate", "-s3", "-S", self.path_360], capture_output=True, text=True, check=True)
            correct_date = res.stdout.strip()

            if not correct_date:
                QMessageBox.warning(self, "Error", "撮影日時を取得できませんでした。")
                return

            # 2. MP4時刻修正
            meta_args = [
                exiftool_exe,
                f"-CreateDate={correct_date}", f"-ModifyDate={correct_date}",
                f"-TrackCreateDate={correct_date}", f"-TrackModifyDate={correct_date}",
                f"-MediaCreateDate={correct_date}", f"-MediaModifyDate={correct_date}"
            ]

            if self.radio_overwrite.isChecked():
                meta_args.append("-overwrite_original")
                meta_args.append(self.path_mp4)
            else:
                meta_args.append("-o")
                meta_args.append(target_mp4)
                meta_args.append(self.path_mp4)

            subprocess.run(meta_args, check=True)

            # 3. GPX作成 (ミリ秒・ISO形式)
            cmd_gpx = [exiftool_exe, "-api", "TimePrecision=3", "-p", gpx_fmt, "-ee", "-c", "%.8f", self.path_360]
            with open(output_gpx, "w", encoding="utf-8") as f:
                subprocess.run(cmd_gpx, stdout=f, check=True)

            # 4. 地図描画
            self.coords_data = self.parse_gpx(output_gpx)
            if self.coords_data:
                self.web_view.page().runJavaScript(f"updateRoute('{json.dumps(self.coords_data)}')")
                QMessageBox.information(self, "完了", f"処理が完了しました。\n\n動画: {os.path.basename(target_mp4)}\nGPX: {os.path.basename(output_gpx)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"エラーが発生しました: {str(e)}")

    def parse_gpx(self, gpx_path):
        coords = []
        try:
            tree = ET.parse(gpx_path)
            for trkpt in tree.getroot().iter():
                if trkpt.tag.endswith('trkpt'):
                    coords.append([float(trkpt.get('lat')), float(trkpt.get('lon'))])
        except Exception as e: print(f"GPX Error: {e}")
        return coords

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GoProGPSApp()
    window.show()
    sys.exit(app.exec())
