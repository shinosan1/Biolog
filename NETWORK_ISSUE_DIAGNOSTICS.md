# Network issue 発生時の証拠採取手順

この手順は、Streamlit に `Cannot load Streamlit frontend code` が表示されたとき、
原因を推測せずに切り分けるためのものです。**Dockerを再起動する前**に実施します。
記載したコマンドは読み取り専用です。

## 1. ブラウザで保存する情報

1. `F12`でDevToolsを開く。
2. Consoleの内容を、時刻が分かる状態でスクリーンショットまたは保存する。
3. Networkで`Preserve log`を有効にする。
4. 赤色になったリクエストについて、URL、Status、Response、Initiatorを保存する。
5. `WS`でStreamlitのWebSocketを選び、切断コードと最後のメッセージ時刻を保存する。
6. JavaScriptが失敗している場合は、そのURLを新しいタブで直接開いた結果も保存する。

健康データ、Cookie、認証情報が表示されている場合は、外部へ共有する前に伏せます。

## 2. PowerShellで採取する情報

運用ディレクトリで次を順番に実行し、出力をテキストへ保存します。

```powershell
Get-Date
docker ps -a
docker inspect biolog-streamlit --format '{{json .State}}'
docker inspect biolog-api --format '{{json .State}}'
docker inspect biolog-streamlit --format 'RestartCount={{.RestartCount}} OOMKilled={{.State.OOMKilled}} StartedAt={{.State.StartedAt}}'
docker inspect biolog-api --format 'RestartCount={{.RestartCount}} OOMKilled={{.State.OOMKilled}} StartedAt={{.State.StartedAt}}'
docker logs biolog-streamlit --since 24h
docker logs biolog-api --since 24h
Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://127.0.0.1:8501
Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://127.0.0.1:8501/_stcore/health
Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://127.0.0.1:8766/api/health/health
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddDays(-1)} |
  Where-Object {$_.ProviderName -match 'Kernel-Power|Power-Troubleshooter|Hyper-V|Lxss|Docker'} |
  Select-Object TimeCreated, ProviderName, Id, LevelDisplayName, Message
```

DevToolsで失敗したJavaScript URLを確認できた場合は、そのURLも検査します。

```powershell
Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 'http://127.0.0.1:8501/static/js/失敗したファイル.js'
```

この手順には`docker restart`、`docker compose down`、`docker rm`を含めません。

## 3. 採取後の復旧切り分け

証拠を保存した後、影響の小さい順に一つずつ試し、どの段階で復旧したか記録します。

1. ブラウザの通常再読み込み（F5）
2. キャッシュを無視した再読み込み
3. Streamlitコンテナだけの再作成
4. Docker Desktop全体の再起動

各操作の前後で、トップページ、`/_stcore/health`、API healthの結果を記録します。

## 4. 判定基準

| 観測結果 | 疑う経路 |
|---|---|
| 8501自体が不通 | Dockerまたはポートフォワード |
| HTMLは200だがJavaScriptが404 | 静的アセットまたはブラウザキャッシュ |
| JavaScriptは200だがWebSocketが切断 | Streamlitセッション経路 |
| APIだけ不通またはunhealthy | API、DB、書き込みワーカー |
| F5だけで復旧 | ブラウザセッション |
| Streamlit再作成でのみ復旧 | Streamlitサーバー |
| Docker Desktop再起動でのみ復旧 | Docker DesktopまたはWSLネットワーク |

証拠が揃うまでは、`st.fragment`、`st.tabs`、Streamlitバージョン、
キャッシュ設定を原因対策として変更しません。
