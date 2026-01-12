import sys
import os
import subprocess
import json
import platform
import math
import xml.etree.ElementTree as ET
import tempfile
from datetime import datetime, timedelta
from PySide6.QtWidgets import *
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import Qt, QUrl

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class GoProGPSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.exiftool_cmd = self.get_exiftool_cmd()
        self.setWindowTitle("GoPro MAX GPS Analyzer & Diagnostic Tool (v1.0.2)")
        self.setMinimumSize(1100, 850)
        self.path_360 = ""
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 左パネル
        self.control_panel = QVBoxLayout()
        self.main_layout.addLayout(self.control_panel, 1)
        
        self.btn_select_360 = QPushButton("1. .360ファイルを選択して診断")
        self.btn_select_360.setFixedHeight(50)
        self.btn_select_360.clicked.connect(self.select_360)
        self.control_panel.addWidget(self.btn_select_360)
        
        # 撮影情報表示用
        self.info_group = QGroupBox("撮影情報")
        self.info_layout = QVBoxLayout()
        self.label_info = QLabel("未選択")
        self.info_layout.addWidget(self.label_info)
        self.info_group.setLayout(self.info_layout)
        self.control_panel.addWidget(self.info_group)
        
        # 診断結果表示用
        self.diag_group = QGroupBox("GPS診断結果")
        self.diag_main_layout = QVBoxLayout() # GroupBox自体のレイアウト

        # 1. スクロールエリアの作成
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # 中身の大きさに合わせてリサイズ
        self.scroll_area.setFrameShape(QFrame.NoFrame) # 枠線を消してスッキリさせる

        # 2. スクロールエリア内に入れるコンテンツ用Widget
        self.scroll_content = QWidget()
        self.diag_layout = QVBoxLayout(self.scroll_content) # ここにラベルを追加していく
        
        # 3. 診断ラベルの設定
        self.label_diag = QLabel("結果はここに表示されます")
        self.label_diag.setWordWrap(True)
        self.label_diag.setAlignment(Qt.AlignTop) # 上詰めで表示
        self.diag_layout.addWidget(self.label_diag)
        self.diag_layout.addStretch() # 下側に余白を作る

        # 4. 組み立て
        self.scroll_area.setWidget(self.scroll_content)
        self.diag_main_layout.addWidget(self.scroll_area)
        self.diag_group.setLayout(self.diag_main_layout)
        
        # 5. グループボックスの最大高さを制限（任意：地図を広く見せるため）
        self.diag_group.setMaximumHeight(350) 
        
        self.control_panel.addWidget(self.diag_group)
        
        self.control_panel.addStretch()
        
        # 右側地図パネル
        self.web_view = QWebEngineView()
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        self.main_layout.addWidget(self.web_view, 3)
        self.init_map()

    def get_exiftool_cmd(self):
        if platform.system() == "Windows":
            return resource_path("exiftool.exe")
        
        # macOS環境
        exiftool_bin = resource_path("exiftool")
        exiftool_lib = resource_path("lib")
        
        # ExifToolが内部のlibフォルダを見つけられるように環境変数を設定
        os.environ["PERL5LIB"] = exiftool_lib
        
        # システムインストール版があれば優先、なければ同梱版
        if os.path.exists("/usr/local/bin/exiftool"):
            return "/usr/local/bin/exiftool"
        
        # 同梱版を使う場合は実行権限を確認（ビルド後の属性剥がれ対策）
        if os.path.exists(exiftool_bin):
            os.chmod(exiftool_bin, 0o755)
            return exiftool_bin
            
        return "exiftool" # 最終手段としてPATHに期待

    def init_map(self):
        js_path = QUrl.fromLocalFile(resource_path("leaflet.js")).toString()
        css_path = QUrl.fromLocalFile(resource_path("leaflet.css")).toString()
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="{css_path}" />
            <script src="{js_path}"></script>
            <style>body, #map {{ height: 100vh; margin: 0; }}</style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([35, 135], 5);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                var layers = [];

                function updateMap(invalidCoords, validCoords) {{
                    layers.forEach(l => map.removeLayer(l));
                    if (invalidCoords.length > 0) {{
                        invalidCoords.forEach(segment => {{
                            var l1 = L.polyline(segment, {{color: 'red', weight: 8, opacity: 0.7}}).addTo(map);
                            layers.push(l1);
                        }});
                    }}
                    if (validCoords.length > 0) {{
                        var l2 = L.polyline(validCoords, {{color: 'blue', weight: 4}}).addTo(map);
                        layers.push(l2);
                        map.fitBounds(l2.getBounds());
                    }}
                }}
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(html_content, QUrl.fromLocalFile(os.path.abspath(__file__)))

    def calculate_distance(self, p1, p2):
        R = 6371000 # 地球半径(m)
        lat1, lon1, lat2, lon2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def select_360(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select .360", "", "GoPro Files (*.360)")
        if file:
            self.path_360 = file
            self.run_diagnosis()

    def run_diagnosis(self):
        # macOS/.app環境でも書き込み可能な一時パスを生成
        temp_dir = tempfile.gettempdir()
        temp_gpx = os.path.join(temp_dir, "temp_diag.gpx")
        gpx_fmt = resource_path("gpx.fmt")
        
        try:
            # 1. 撮影日時・時間の取得
            #res_meta = subprocess.run([self.exiftool_cmd, "-CreationDate", "-CreateDate", "-Duration", "-s3", self.path_360], 
            #                          capture_output=True, text=True, check=True)
            #meta_lines = res_meta.stdout.strip().split('\n')
            
            # 各値の抽出 (ExifTool出力順に依存するためタグ名指定が安全だが簡易的に)
            # 2026年時点のGoPro MAX出力仕様に準拠
            meta_dict = {}
            #for line in meta_lines:
            #    if "CreationDate" in line: meta_dict['jst'] = line.split(': ', 1)[1]
            #    if "CreateDate" in line: meta_dict['utc'] = line.split(': ', 1)[1]
            #    if "Duration" in line: meta_dict['dur'] = line.split(': ', 1)[1]

            # 1. 撮影日時抽出
            res = subprocess.run([self.exiftool_cmd, "-CreateDate", "-s3", "-S", self.path_360], 
                                 capture_output=True, text=True, check=True)
            meta_dict['utc'] = res.stdout.strip()
            res = subprocess.run([self.exiftool_cmd, "-CreationDate", "-s3", "-S", self.path_360], 
                                 capture_output=True, text=True, check=True)
            meta_dict['jst'] = res.stdout.strip()
            res = subprocess.run([self.exiftool_cmd, "-Duration", "-s3", "-S", self.path_360], 
                                 capture_output=True, text=True, check=True)
            meta_dict['dur'] = res.stdout.strip()
            res = subprocess.run([self.exiftool_cmd, "-Duration", "-n", "-S", self.path_360], 
                                 capture_output=True, text=True, check=True)
            duration_sec = float(res.stdout.strip().split(': ', 1)[1])

            #duration_sec = float(meta_dict.get('dur', 0))
            self.label_info.setText(f"【ファイル名】 {os.path.basename(self.path_360)}\n"
                                    f"【日本時間】 {meta_dict.get('jst', '取得失敗')}\n"
                                    f"【UTC】 {meta_dict.get('utc', '取得失敗')}\n"
                                    f"【撮影時間】 {meta_dict.get('dur', '取得失敗')} ({round(duration_sec, 2)} 秒)")

            # 2. GPX抽出 (一時フォルダへ出力)
            # コマンドの stdout にファイルのパスを指定
            with open(temp_gpx, "w", encoding="utf-8") as f:
                subprocess.run([self.exiftool_cmd, "-p", gpx_fmt, "-ee", "-c", "%.8f", self.path_360], 
                               stdout=f, check=True)

            tree = ET.parse(temp_gpx)
            pts = []
            for trkpt in tree.getroot().iter():
                if trkpt.tag.endswith('trkpt'):
                    pts.append([float(trkpt.get('lat')), float(trkpt.get('lon'))])

            if not pts:
                QMessageBox.warning(self, "Warning", "GPSデータが含まれていません。")
                return

            # 3. 異常検知 (揺れ・跳び・未捕捉)
            invalid_segments = [] # 赤色表示用 (リストのリスト)
            current_invalid_seg = []
            
            valid_pts = [] # 青色表示用
            
            # 判定用閾値
            # StreetView Studioは急激な座標移動を「跳び」とみなす
            # 1地点あたりの許容移動距離を算出 (秒速45m × サンプリング間隔)
            # GoPro MAXのGPSは約18Hz(0.055秒毎)だが、ここでは1地点ごとの距離で判定
            MAX_DIST_PER_POINT = 15.0 # 15m以上のジャンプは異常（時速160km超相当）
            
            invalid_ranges = [] # 警告テキスト用 [(start_sec, end_sec), ...]
            
            is_collecting_invalid = False
            start_invalid_idx = 0

            for i in range(len(pts)):
                p_curr = pts[i]
                is_bad = False
                
                # A. 未捕捉判定 (0,0 または 最初から動かない)
                #if p_curr == [0,0] or p_curr == pts[0]:
                if p_curr == [0,0]:
                    is_bad = True
                
                # B. 跳び判定 (1つ前からの距離が異常)
                elif i > 0:
                    dist = self.calculate_distance(pts[i-1], p_curr)
                    # GPMFのサンプリング周期(約0.05~0.1s)で10m以上移動は異常
                    if dist > MAX_DIST_PER_POINT: 
                        is_bad = True

                if is_bad:
                    # 異常区間の開始または継続
                    if not is_collecting_invalid:
                        is_collecting_invalid = True
                        start_invalid_idx = i
                        # 視覚的な繋がりのため、直前の正常な地点を起点に含める
                        current_invalid_seg = []
                        if i > 0:
                            current_invalid_seg.append(pts[i-1])
                        current_invalid_seg.append(p_curr)
                    else:
                        current_invalid_seg.append(p_curr)
                else:
                    # 正常な地点
                    if is_collecting_invalid:
                        # 異常区間が終了したので確定
                        end_invalid_idx = i
                        # 秒数換算 (インデックス比率 × 総秒数)
                        start_sec = round((start_invalid_idx / len(pts)) * duration_sec, 2)
                        end_sec = round((end_invalid_idx / len(pts)) * duration_sec, 2)
                        
                        invalid_ranges.append((start_sec, end_sec))
                        invalid_segments.append(current_invalid_seg)
                        is_collecting_invalid = False
                    
                    valid_pts.append(p_curr)

            # 最後の地点が異常のまま終わった場合のクローズ処理
            if is_collecting_invalid:
                end_invalid_idx = len(pts) - 1
                start_sec = round((start_invalid_idx / len(pts)) * duration_sec, 2)
                end_sec = round(duration_sec, 2)
                invalid_ranges.append((start_sec, end_sec))
                invalid_segments.append(current_invalid_seg)

            # 4. 結果の表示
            if invalid_ranges:
                diag_text = "【異常検出】\n"
                for r in invalid_ranges:
                    diag_text += f"・{r[0]}s ～ {r[1]}s 付近 (GPS未捕捉または跳び)\n"
                diag_text += "\n上記区間をGoPro Playerでカットして書き出すことを推奨します。"
                self.label_diag.setText(diag_text)
                self.label_diag.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.label_diag.setText("【正常】\n全区間で安定したGPSデータが確認されました。")
                self.label_diag.setStyleSheet("color: green; font-weight: bold;")

            # 5. 地図更新
            self.web_view.page().runJavaScript(f"updateMap({json.dumps(invalid_segments)}, {json.dumps(valid_pts)})")
            
            if os.path.exists(temp_gpx): os.remove(temp_gpx)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"診断失敗: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GoProGPSApp()
    window.show()
    sys.exit(app.exec())
