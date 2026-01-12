# gopro-streetview-helper<br/>
GoPro Street View Helper 利用ガイド<br/>
<br/>
このツールは、GoPro MAXで撮影した .360 ファイルからGPS情報を抽出しGPXファイルを作成、Google Street View Studioの「内部エラー（時刻不一致）」を回避するための補正を行う補助ツールです。<br/>
また、GPS未捕捉による位置情報不正や跳びによる処理エラーを防ぐための、.360ファイル分析ツールを別途用意しました。<br/>
<br/>
1. 解決できる問題<br/>
<img src="https://github.com/petarou-archive/gopro-streetview-helper/blob/main/GoProStreetViewHelper_macOS.png"><br/>
Gopro Streetview Helper<br/>
GoPro Playerで書き出したMP4ファイルは、動画内の時刻（作成日時）が「書き出し完了時刻」に上書きされてしまうため、Google Street View Studioにアップロードすると「GPSと動画のタイムスタンプが一致しません」というエラーが発生します。<br/>
本ツールは、元の .360 ファイルから正しい撮影時刻を取得し、動画のメタデータを自動修正します。<br/>
<br/>
GoPro GPS Analizer<br/>
.360ファイルを参照し、GPS未捕捉による位置情報不正や跳びを分析し表示します。<br/>
GoPro Playerで.360ファイルの先頭から異常区間をトリミングで除くことで、Google Street View Studioの処理エラーを回避できます。<br/>
<br/>
2. 事前準備<br/>
<br/>
Gopro Streetview Helper<br/>
GoPro Player で .360 ファイルをエクスポートします。<br/>
投影法: 正距円筒図法 (Equirectangular) を選択<br/>
トリミング: 開始・終了地点をカットせず、そのまま書き出すことを強く推奨します。<br/>
本ツールのフォルダに以下のファイルが揃っていることを確認してください。<br/>
gopro_streetview_helper.exe<br/>
exiftool.exe / exiftool_files ( https://exiftool.org/ )<br/>
gpx.fmt<br/>
leaflet.js / leaflet.css ( https://leafletjs.com/ )<br/>
<br/>
3. ツールの使い方<br/>
<br/>
gopro_streetview_helper.exe を起動します。<br/>
<br/>
[1. 元の .360 ファイルを選択] を押し、撮影したオリジナルのファイルを指定します。<br/>
[2. エクスポート済みの .mp4 を選択] を押し、GoPro Playerで書き出した動画を指定します。<br/>
時刻修正の設定 を選択します。<br/>
  上書き修正: 選択したMP4を直接修正します。<br/>
  別名ファイルを作成: _fixed.mp4 という名前で新しく保存します。<br/>
[実行（時刻修正 ＆ GPX作成）] をクリックします。<br/>
処理完了後、地図にルートが表示されます。動画と同じ場所に .gpx ファイルが生成されます。<br/>
<br/>
4. Googleストリートビューへのアップロード<br/>
<br/>
Google Street View Studio にアクセスします。<br/>
本ツールで処理した 「MP4ファイル」をアップロード後、GPS情報がありませんの警告が表示されるので「GPXファイル」を追加でアップロードします。<br/>
※ _fixed 版を作成した場合は、必ず _fixed 同士をセットにしてください。<br/>
<br/>
5. FAQ / トラブルシューティング<br/>
<br/>
Q: 地図が表示されない / 白いまま<br/>
A: ルートの描画（青い線）にはインターネット接続が必要です。オフライン環境では地図タイルが表示されません。<br/>
Q: それでも「内部エラー」が出る<br/>
A: GoPro Playerでの書き出し時に「トリミング（カット）」を行っている場合、動画とGPSの同期が数秒ズレてエラーになることがあります。カットする場合はカット後の.360ファイルからMP4ファイルをエクスポートしてお試しください。<br/>
Q: 撮影した時刻とGPXの時刻が9時間ズレている<br/>
A: 正常です。Googleのシステムは世界標準時（UTC）を基準とするため、日本時間（JST）から9時間引いた時刻で記録されます。<br/>
<br/>
免責事項<br/>
<br/>
本ツールは個人が制作した補助ツールであり、Google公式のものではありません。<br/>
本ツールの利用により生じた損害等について、制作者は一切の責任を負いません。<br/>
Google側の仕様変更により、予告なく利用できなくなる場合があります。<br/>
<br/>
著作権・ライセンス<br/>
<br/>
本ツールは Leaflet.js (BSD License) および ExifTool (Perl Artist License/GPL) を利用しています。





