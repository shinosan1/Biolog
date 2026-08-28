# BioLog Streamlit Frontend

BioLog の Streamlit フロントエンドを格納するディレクトリです。

> **プロジェクト全体の最新情報は [../README.md](../README.md) が正本です。**
> セットアップ手順、システム要件、Docker 構成、アーキテクチャ、Known Issues、
> Troubleshooting、用語解説、Roadmap、License はすべてルート README を参照してください。
> この README では `biolog_streamlit/` 配下に固有の情報だけを扱います。

---

## 主な役割

画面表示（UI）だけを担当します。**このディレクトリのコードは SQLite へ直接アクセスしません。**
データの読み書きは必ず `api_client.py` 経由の HTTP で FastAPI へ委ねます。

| ファイル / ディレクトリ | 担当 |
|---|---|
| `streamlit_app.py` | エントリポイント。サイドバー（ユーザー・期間フィルター、更新、ヘルスチェック）と 4 タブの組み立て |
| `views/summary.py` | 上部のサマリーカード（家族全員の直近データ） |
| `views/graph.py` | 時系列グラフ（複数ユーザー比較） |
| `views/list_view.py` | 一覧表示と CSV エクスポート |
| `views/create.py` | 新規登録フォーム |
| `views/edit.py` | 修正・削除 |
| `api_client.py` | FastAPI への HTTP クライアント。接続先をローカルのみに制限する |
| `cache.py` | 読み取りキャッシュと invalidate |
| `charts.py` / `formatters.py` | グラフ描画、表示用の整形 |
| `safe_table.py` / `ui_style.py` | HTML エスケープ済みテーブル、スタイル注入 |
| `form_fields.py` / `form_components.py` / `form_state.py` / `payloads.py` | 入力項目の定義、描画、Session State 管理、送信ペイロード生成 |
| `config.py` / `time_utils.py` | 接続先・ユーザー定義、JST 変換 |
| `.streamlit/config.toml` | Streamlit 設定 |
| `Dockerfile` / `requirements.txt` / `constraints.txt` | このコンテナのビルド定義と依存バージョンの固定 |

---

## このディレクトリ固有の設定

- 接続先 API は環境変数 **`BIOLOG_API_URL`** で与えます。`docker-compose.yml` では
  `http://biolog-api:8766` を指定しています。ローカル以外のホストは `api_client.py` が拒否します。
- `.streamlit/config.toml` でツールバーを最小表示にし、Streamlit の利用統計送信を無効化しています。

起動・停止・再起動・ログ確認の手順はルート README を参照してください。

---

## 参照先

| ファイル | 内容 |
|---|---|
| [../README.md](../README.md) | **プロジェクト全体の正本。** セットアップ / 構成 / Known Issues / 用語解説 |
| [../CHANGELOG.md](../CHANGELOG.md) | 全変更履歴 |
| [../docs/CODE_REFERENCE.md](../docs/CODE_REFERENCE.md) | ファイル単位のコード解説（現行版） |
| [../docs/spec.md](../docs/spec.md) | 利用者向けの機能仕様 |
| [仕様書.md](仕様書.md) | 設計思想・データフロー（**v1.5.5 時点の履歴スナップショット**） |
| [操作説明書.md](操作説明書.md) | 画面操作手順 |
| [../biolog_api/skills.md](../biolog_api/skills.md) | API リファレンス（curl 集） |
| `../CLAUDE.md` | 開発ルールと BioLog 固有の不変条件（開発リポジトリのみ・非公開） |
