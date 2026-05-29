# Changelog

BioLog プロジェクトの全変更履歴です。
形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に従います。

---

## [Unreleased]

次のリリースに向けた作業メモ。

### 残タスク（監査由来）
- M1: `schemas.py` の `date` に `YYYY-MM-DD` 形式バリデータ追加
- M2: `api.py` の `result_q.get(timeout=30)` で `queue.Empty` を捕捉して 504 Gateway Timeout を返却
- L1: `biocore.py:110` の `SELECT *` を明示列指定に置換
- 既知の運用課題: `migration_lock` 残存時の手動 `DELETE FROM migration_lock WHERE id = 1`

---

## [1.5.7] — 2026-05-29

### Fixed
- **新規登録後にサマリーカード / グラフ / 一覧に前日データが残る不具合**
  - 原因：`fetch_*.clear()` 方式では Eventual Consistency ラグ等で stale な fetch がキャッシュされる場合があった
  - 対応：`@st.cache_data` の cache key に `version: int` 引数を追加し、書き込み成功時に `st.session_state.data_version += 1` で明示 invalidate する方式に変更
- **新規登録フォームに前回入力値が残る不具合**
  - `with st.form("create_form")` に `clear_on_submit=True` を追加し、submit 後に全フィールドを自動リセット

### Changed
- `fetch_latest(uid)` → `fetch_latest(uid, version)`、`fetch_range_data(start, end)` → `fetch_range_data(start, end, version)`
- 全 4 箇所（「更新」ボタン / 新規登録 / 編集 / 削除）の `fetch_latest.clear()` / `fetch_range_data.clear()` を `st.session_state.data_version += 1` に置換
- `session_state.data_version` の初期値を **`int(time.time())`** にし、v1.5.5 で fix した「翌日跨ぎ cache 衝突」問題が再発しないように保証
- 新規登録成功時のメッセージを「登録を受け付けました（反映には数秒かかる場合があります）」から「**登録しました。最新データを更新しています。**」に変更（version 機構で即時反映されるため）

### Note
- v1.5.5 で廃止した version 引数方式を再導入する形になるが、初期値を `int(time.time())` にすることで「新セッションで `version=0` リセット → 過去 cache `(uid, 0)` に衝突」という v1.5.5 当時の問題は構造的に発生しない

---

## [1.5.6] — 2026-05-26

### Fixed
- **公開準備：API リファレンス（`biolog_api/skills.md`）に `meal_detail` / `activity_log` の記述漏れを補完**
  - DB スキーマ表、リクエストフィールド表、レスポンス例、返却辞書キー、curl 例の各箇所に追記
  - コード（worker.py / biocore.py / schemas.py / migrate_001 / Streamlit UI）側は対応済みだったが、ドキュメント側のみ追従漏れだった

### Changed
- `README.md` / `biolog_streamlit/README.md` の冒頭サマリーに「食事ログ」を追加（行動ログのみ言及だったのを修正）

### Removed
- StreamlitAPIException 再発防止のため、`session_state["del_id"]` 直接代入を deferred-clear パターンに変更（既に v1.5.5 で実装、本エントリで明文化）

---

## [1.5.5] — 2026-05-25

### Fixed
- **キャッシュのセッション跨ぎ staleness を構造的に解消**
  - 症状：登録 → 更新後、新しいブラウザセッションでトップ画面が古い値に戻る
  - 原因：`@st.cache_data` がプロセス global、`session_state.latest_version` が新セッションで `0` にリセットされて過去キャッシュキーに衝突
  - 修正：version 機構を完全廃止し、書き込み成功時に `fetch_latest.clear()` / `fetch_range_data.clear()` で per-function invalidate

### Changed
- `fetch_latest(uid)` / `fetch_range_data(start, end)` から `version` 引数を削除
- `st.session_state.range_version` / `latest_version` を完全削除
- サマリーカード・グラフ・一覧の呼び出し側から `version` 引数を削除
- 「更新」ボタン・新規登録成功・編集成功・削除成功の各箇所で `+= 1` を `fetch_latest.clear()` + `fetch_range_data.clear()` に置換
- 削除タブの cache invalidation 欠落も同時解消

---

## [1.5.4] — 2026-05-25

### Added
- **H4: API ログの PII マスク（軽量実装）**
  - `biolog_api/log_utils.py` を新規作成
  - `mask_pii(text)` 関数：6 種の regex で `user_id` / `request_id` / email / UUID をマスク
  - JSON 形式（`"user_id": "self"`）と key=value 形式（`user_id=self`）の両方に対応
  - UUID は 8-4-4-4-12 形式 + 32 文字 hex（ハイフン無し圧縮形）も対象

### Changed
- `api.py` POST 内 local `log()` の print 行に `mask_pii(json.dumps(...))` を適用
- `worker.py` `_log()` の print 行に `mask_pii(json.dumps(...))` を適用
- 健康数値（temperature / weight 等）はマスク対象外（読み続けられる）

---

## [1.5.3] — 2026-05-25

### Added
- **H3: migration runner の Docker 起動時自動実行化**
  - `biolog_api/entrypoint.sh` を新規作成
  - `set -e` + `python migrations/runner.py` → `exec uvicorn api:app` の直列実行
  - フェーズログ（`[entrypoint] running migrations...` / `[entrypoint] migrations complete, starting API...`）
  - migration 失敗時は exit 1 で API 起動を阻止

### Changed
- `biolog_api/Dockerfile` を `CMD ["uvicorn", ...]` から `ENTRYPOINT ["./entrypoint.sh"]` に変更
- `RUN chmod +x entrypoint.sh` を追加（Windows file system 由来の executable bit 喪失対策）

### Known Limitation
- runner.py の lock 競合時 exit 0 仕様は維持（S1 採用）。stale lock 残存時は schema 未整備のまま API が起動する可能性あり。手動 `DELETE FROM migration_lock WHERE id = 1` で復旧

---

## [1.5.2] — 2026-05-25

### Added
- **H2: `migrate_001_init.py` に `CREATE TABLE IF NOT EXISTS health_records` を追加**
  - 16 カラム + `request_id` UNIQUE + `created_at` DEFAULT `datetime('now','localtime')`
  - 新規環境（DB ファイル未作成）でもテーブルが自動生成されて API 起動可能に
  - 既存 ALTER TABLE 群（`ADD COLUMN request_id` / `meal_detail` / `activity_log`）は **環境差吸収のため併存維持**
  - CREATE と ALTER は冗長ではなく「二重互換構造」として削除・統合禁止
- CHECK 制約は省略（既存 DB との不整合を最小化、互換最優先）

---

## [1.5.1] — 2026-05-25

### Fixed
- **H1: Streamlit 起動ブロッカー修正（最優先）**
  - `streamlit_app.py:76-78` に存在した orphan な `except Exception` ブロックを削除
  - 前回の truncate 関数追加時に旧 `api_get()` の generic except 節が切り離されて残存していた
  - `SyntaxError: invalid syntax` で Streamlit アプリ起動不可だった状態を解消

---

## [1.5.0] — 2026-05-25

### Added
- **date 補完の JST 統一（深夜帯ズレ修正）**
  - `biolog_api/time_utils.py` を新規作成
    - `JST = timezone(timedelta(hours=9))`
    - `now_jst()` / `to_jst(dt)` / `jst_date()`
  - Docker コンテナの TZ が UTC でも JST 基準で date を確定

### Fixed
- `preprocess.py` の date 補完を `datetime.date.today().isoformat()` → `jst_date()` に変更
  - 深夜 0:00〜9:00（JST）に date 省略で POST すると前日扱いになる不具合を修正
- `streamlit_app.py` の新規登録フォーム日付初期値を `date.today()` → `datetime.now(JST).date()` に統一

### Note
- 本変更は WORKDIR=/app でのフラット import 構成を前提（`from time_utils import jst_date`）

---

## [1.4.5] — 2026-05-25

### Changed
- **一覧タブの長文セルを列別 truncate + expander 詳細展開に変更**
  - `_LIMITS` 列別上限（メモ 40 / 食事ログ 80 / 行動ログ 200）を導入
  - `_safe_str()` / `truncate()` / `is_truncated()` ヘルパー関数を追加
  - `st.dataframe` 直下に行別 expander 一覧を表示（`_LIMITS` を超えるセルのみ）
  - expander ラベル：`対象日 / ユーザー / 列名` で識別容易
  - full データは `disp.at[idx, col]` ベースの真実データ参照に統一
  - CSV ダウンロードは従来通り全文（変更なし）

---

## [1.4.4] — 2026-05-08

### Changed
- 一覧タブの `created_at` 表示を `time_utils.to_jst()` ベースへ統一
  （JST 表示責務を UI 側ではなく `time_utils` に集約）
- priority 列に 基礎代謝(kcal)・体脂肪率(%)・筋肉量(kg) を追加

---

## [1.4.3] — 2026-05-08

### Changed
- 一覧タブの列名を日本語化（体重(kg)・体温(℃)・収縮期血圧・記録日時 など）
- 表示列順を整理（ID・ユーザー・記録日時を左固定、健康指標を優先表示）
- `created_at` を一覧表示に追加し `YYYY-MM-DD HH:MM` 形式にフォーマット
- CSV ダウンロードも日本語列名・並び替え済みで出力

---

## [1.4.2] — 2026-05-07

### Changed
- 修正フォームの選択方式を ID 手入力から「ユーザー選択 → 日付 selectbox」に変更
  - 登録済み日付のみ選択肢に表示（`GET /api/health/records` から日付一覧を取得）
  - `GET /api/health/record/day` で既存値を取得してフォーム全フィールドにプリフィル
  - 更新 URL を `edit_id` から取得レコードの `id` フィールドに変更

---

## [1.4.1] — 2026-05-07

### Added
- `GET /api/health/record/day?user_id=self&date=2026-05-07` エンドポイントを追加
  - `user_id` + `date` でレコードを1件取得（編集用途）
  - 存在しない場合は 404 を返す
  - `biocore.get_record_by_user_date()` を新規追加（`SELECT *` で将来カラム追加に追従）

---

## [1.4.0] — 2026-05-07

### Added
- `biolog_streamlit/time_utils.py` を新規作成（UTC→JST 変換ユーティリティ）
  - `to_jst(dt)` 関数: `str` / `datetime` の両方を受け付け、スペース区切りも対応
  - 削除プレビューの `created_at` を JST（Asia/Tokyo）に変換して表示

### Fixed
- 修正・削除タブで memo フィールドが更新されないバグを修正
  - `api.py`: `exclude_none=True` → `exclude_unset=True`（UI が明示的に送ったフィールドのみ payload 化）
  - `worker.py`: UPDATE に型チェック付きホワイトリスト `ALLOWED_FIELDS` を導入。`None` はスキップ、`memo` は `"" ` も上書き対象
  - `streamlit_app.py`: `if edit_memo:` を `body["memo"] = edit_memo or ""` に変更し、常に memo を送信
  - 修正フォームの memo 欄に現在値をプリフィル
  - 更新成功後に `st.rerun()` + version++ を追加
- `api.py` lifespan の重複削除 + UNIQUE INDEX 挿入順序を整理
  - DROP 旧 INDEX → DELETE 重複行（MAX(id) 残し）→ CREATE UNIQUE INDEX の順序に統一
  - `(user_id, date)` 重複がある状態でも起動時に UNIQUE INDEX 作成が成功するよう保証

### Changed
- サマリーカードの表示順を変更（体重→体温→脈拍→収縮期血圧→拡張期血圧）
- グラフタブの表示順をサマリーカードと統一（体重→体温→脈拍→血圧）

---

## [1.3.9] — 2026-05-06

### Added
- タブ2「一覧」に CSV ダウンロードボタンを追加
  - 現在表示中のデータを `biolog_{開始日}_{終了日}.csv` でダウンロード
  - Excel で日本語が文字化けしないよう UTF-8 BOM 付きで出力

---

## [1.3.8] — 2026-05-06

### Changed
- API 呼び出しに `@st.cache_data` を適用し Streamlit 再実行の副作用を抑制
  - `fetch_range_data(start, end, version)` / `fetch_latest(uid, version)` ラッパーを追加
  - `range_version` / `latest_version` を session_state で管理（version はキャッシュ無効化トリガー）
  - サイドバーに「更新」ボタンを追加（version++ で即時再取得）
  - 登録成功後も version++ してキャッシュを無効化
  - 登録成功メッセージを「登録を受け付けました（反映には数秒かかる場合があります）」に変更
  - 常時注記「データは非同期で反映されます」を追加

---

## [1.3.7] — 2026-05-06

### Fixed
- グラフが重複して表示される問題を修正
  - 原因: Streamlit の再描画でスクリプトが複数回実行され `st.pyplot()` が積み重なっていた
    （デバッグログで同じ描画ブロックが1回のロードで3回実行されることを確認）
  - 修正: `st.pyplot(fig, clear_figure=True)` に変更（Streamlit が figure を自動クリア）
  - データ処理・groupby・xticks は変更なし

---

## [1.3.6] — 2026-05-06

### Fixed
- X 軸ティック密集問題を解決（DayLocator → set_xticks に変更）
  - `DayLocator(interval=1)` はデータのない日にも毎日ティックを打つため廃止
  - `ax.set_xticks(sorted(df["date"].unique()))` でデータが実在する日付だけにティックを固定
  - `udf["date"].dt.date` 変換を削除し datetime64 のまま matplotlib に渡す
  - 対象: 血圧・体温・脈拍・体重の全グラフ

---

## [1.3.5] — 2026-05-06

### Changed
- データ集約責務を描画関数の外（DataFrame 読み込み直後）に集約
  - `df.sort_values("date").groupby(["user_id", "date"], as_index=False).last()` で
    全ユーザー・全メトリクスの「1日1点」を一括確立
  - `_plot_metric()` と血圧グラフから per-user groupby を削除（前集約済みのため不要）
  - `drop_duplicates` / `FuncFormatter(_jp_date)` の使用を廃止
  - `print("after_groupby:", len(df))` で集約後件数を確認可能

---

## [1.3.4] — 2026-05-06

### Fixed
- X 軸ラベル重複を DayLocator で強制排除
  - `udf["date"] = pd.to_datetime(udf["date"]).dt.date` で date 型にフラット化
  - `AutoDateLocator` → `DayLocator(interval=1)` に変更（1日=1ティック固定）
  - `st.pyplot` 直後に `"Labels fixed with DateFormatter"` デバッグログを追加
  - 対象: 血圧・体温・脈拍・体重の全グラフ

---

## [1.3.3] — 2026-05-06

### Fixed
- X 軸の日付ラベル重複問題を根本解決
  - `pd.to_datetime(df["date"]).dt.normalize()` で時刻成分を除去し、日付集約を確実に実行
  - `groupby("date").last().reset_index()` の順序を統一（dropna を後置）
  - `FuncFormatter(_jp_date)` → `mdates.DateFormatter("%m-%d")` に変更してラベル二重化を防止
  - `AutoDateLocator()` でデータ量に応じた自動間隔調整

---

## [1.3.2] — 2026-05-06

### Fixed
- X 軸の日付ラベルが重複して表示される問題を修正
  - `drop_duplicates` を `groupby("date").last()` に変更し、同日複数レコードを最新値1件に集約
  - `AutoDateLocator(minticks=3, maxticks=10)` を追加し、FuncFormatter 使用時のティック重複を防止
  - 対象: 血圧・体温・脈拍・体重の全グラフ

---

## [1.3.1] — 2026-05-06

### Fixed
- 同一日付のデータが複数回描画される問題を修正
  - 各グラフ描画前に `plt.clf()` を追加してキャンバスをクリア
  - `drop_duplicates(subset=['user_id', 'date', col])` で重複データを排除
  - デバッグログ（`print("DEBUG: ... data count = N")`）を追加（`docker logs -f biolog-streamlit` で確認可）

---

## [1.3.0] — 2026-05-06

### Changed
- 描画エンジンを Plotly から Matplotlib + Seaborn に移行
  - `st.pyplot()` による静止画像出力でモバイルのピンチズーム問題を根本解決
  - `japanize-matplotlib` で日本語フォントを自動適用（Dockerfile 変更不要）
  - X 軸日付を「2026年5月6日」形式の日本語表記に変更
  - `dark_background` スタイルで Streamlit ダークモードとデザインを統一
  - 血圧グラフに `axhline` で収縮期 120 / 拡張期 80 の参考線を維持

### Removed
- Plotly (`plotly==5.24.1`) を requirements.txt から削除
- v1.2.2〜v1.2.9 で実装した CSS シールド / JS ガードパネル / touch-action ハックを全削除
  （静止画像化により不要になったため）

---

## [1.2.9] — 2026-05-06

### Changed
- JS による動的透明ガードパネルを実装
  - `.stPlotlyChart` の上に `z-index: 99999` の透明 `<div>` を動的生成してグラフへのタッチを物理遮断
  - ガード自身は `touch-action: pan-y` を持ち縦スクロールは通す
  - `setInterval` で 1 秒ごとにスキャンし Streamlit の再描画後も自動適用

---

## [1.2.8] — 2026-05-06

### Fixed
- iOS/Android でグラフをピンチするとズームが発生する問題を根本解決
  - 原因: `pointer-events` / `::before` はコンポジタースレッドより上位レイヤーのみに作用し、
    ブラウザネイティブのピンチジェスチャーを止められていなかった

### Changed
- CSS を `touch-action: pan-x pan-y !important` に変更（コンポジタースレッドに直接ピンチ禁止を指示）
- JS `touchstart` / `touchmove` を `passive: false` で登録し、2本指タッチを `preventDefault()` でキャンセル
- MutationObserver により動的追加グラフにも自動適用
- 効果がなかった `::before` シールドと `position: relative` ルールを削除

---

## [1.2.7] — 2026-05-06

### Changed
- CSS 擬似要素（`::before`）による透明シールドをグラフ上に配置
  - 指が触れる先が Plotly ではなく透明な膜になり、あらゆるイベントを物理的に遮断
  - iOS (Safari/Chrome) および Android でのピンチズーム・誤タップを 100% 封鎖
  - 既存の `pointer-events: none !important` と `staticPlot: true` も継続

---

## [1.2.6] — 2026-05-06

### Changed
- グラフエリアに CSS `pointer-events: none` を適用し、iOS/Android のスクロール競合を完全解消
  - `.stPlotlyChart` コンテナを DOM レベルでタッチ・マウスイベント透過状態にする
  - iPhone (Safari/Chrome) および Android でグラフ上をスワイプしてもページスクロールが阻害されない
  - JS 側の `staticPlot` / `fixedrange` / `dragmode=False` との組み合わせで二重に封鎖

---

## [1.2.5] — 2026-05-06

### Changed
- Plotly グラフに `staticPlot: true` を追加し、JS インタラクションを根本から無効化
  - ドラッグ・ズーム・ホバー・クリック等の全イベントを物理的に封鎖
  - グラフは完全な静止画像として扱われる
  - 既存の `fixedrange=True` / `dragmode=False` / `doubleClick=False` は維持
  - 対象: 血圧・体温・脈拍・体重の全グラフ

---

## [1.2.4] — 2026-05-06

### Changed
- Plotly グラフを「見るだけのダッシュボード」として完全固定（v1.2.3 の強化版）
  - X・Y 軸を `fixedrange=True` で物理的に固定（軸ドラッグによるズーム不可）
  - ダブルクリックによるズームリセットを `doubleClick=False` で無効化
  - `dragmode="pan"` を `dragmode=False` に変更（ドラッグ操作を完全無効化）
  - 対象: 血圧・体温・脈拍・体重の全グラフ

---

## [1.2.3] — 2026-05-06

### Changed
- Plotly グラフの操作性改善（血圧・体温・脈拍・体重の全グラフに適用）
  - マウスホイールによる誤ズームを無効化（`scrollZoom: false`）— ホイールでページスクロール可能に
  - グラフ右上のモードバーを非表示（`displayModeBar: false`）
  - ドラッグ操作をズームからパン（移動）に変更（`dragmode: "pan"`）

---

## [1.2.2] — 2026-05-06

### Added
- サマリーカードをメイン画面最上部（グラフ・タブの上）に追加
  （自分・父・母の最新の収縮期/拡張期血圧・体温・脈拍を `st.metric` で3列横並び表示）
- データがないユーザーは「データなし」と優しく表示（`suppress_404=True` で 404 を事前吸収）
- グラフを `st.line_chart` から **Plotly** (`plotly.graph_objects`) に全面刷新
- ユーザー選択を `st.selectbox`（単一）から `st.multiselect`（複数可）に変更
  （デフォルト: 自分 / 選択しない場合は「選択してください」案内を表示）
- 選択した全ユーザーのデータを色分けして1グラフに重ね描き
  （自分: 青 `#1f77b4` / 父: 緑 `#2ca02c` / 母: 赤 `#d62728`）
- 血圧グラフに目標値の参考線を追加（収縮期 120 mmHg / 拡張期 80 mmHg — 点線）
- `_plot_metric()` ヘルパー関数を追加（体温・脈拍・体重グラフの共通描画ロジック）
- `biolog_streamlit/requirements.txt` に `plotly==5.24.1` を追加

### Changed
- グラフレイアウトを2列から縦1列に変更（複数ユーザー比較時の視認性向上）
- タブ2「一覧」: 単一ユーザー選択時のみ `user_id` フィルタを適用、複数または未選択は全員表示

---

## [1.2.1] — 2026-05-06

### Fixed
- `api.py` の lifespan 起動時、既存 DB に `(user_id, date)` 重複行がある場合に
  `CREATE UNIQUE INDEX` が失敗してコンテナが再起動ループに陥る `IntegrityError` を修正
- DDL 実行順序を「テーブル作成 → 重複クリーンアップ → インデックス作成」の3ステップに変更し、
  重複行を削除してからインデックスを作成することで確実に成功するようにした
- クリーンアップ件数を構造化ログ（`"event": "cleanup_duplicates"`）として標準出力に記録
  （重複がなければサイレント処理）

### Changed
- `api.py` の `_DDL` を `_DDL_TABLE` / `_CLEANUP_DUPLICATES` / `_DDL_INDEXES` の3定数に分割

---

## [1.2.0] — 2026-05-06

### Fixed
- **BUG-001**: 同一 `user_id` + `date` で複数回 POST すると重複行が増える問題を修正
- **BUG-002**: Streamlit の削除画面で存在しない ID を入力すると `404 Not Found` になる問題を修正
- **IMPROVEMENT-001**: 削除画面でレコード内容が確認できない問題を同時解消

### Added
- `worker.py` の INSERT を `ON CONFLICT(user_id, date) DO UPDATE SET` による UPSERT に変更
  （同一ユーザー・同一日付の再登録は上書き更新になる）
- `api.py` の DDL に `CREATE UNIQUE INDEX uidx_hr_user_date ON health_records(user_id, date)` を追加
- `biocore.py` に `get_record_by_id(record_id: int)` 関数を追加
- `api.py` に `GET /api/health/record/{record_id}` エンドポイントを追加
- Streamlit の削除タブにリアルタイムプレビュー表示を追加
  - ID 入力時に対象レコードの内容を `st.table()` で表示
  - 存在しない ID は「存在しません」警告を表示し、削除ボタン自体を非表示に
  - 削除成功後に `st.rerun()` でプレビューを自動クリア
- `streamlit_app.py` の `api_get()` に `suppress_404=True` オプションを追加
  （プレビュー取得時の 404 をエラー表示せず `None` で返す）

---

## [1.1.0] — 2026-05-05

### Added
- 初期リリース
- **アーキテクチャ**: `FastAPI → Queue → Worker(1スレッド) → db_manager → SQLite` の単一 Writer モデル
- **DB**: `health_records` テーブル新規作成（初期は他プロジェクトの SQLite ファイルに同居、後に独立 DB `biolog.db` へ移行）
- **対応ユーザー**: `self` / `father` / `mother`
- **計測項目**: 体温・脈拍・収縮期血圧・拡張期血圧・体重・体脂肪率・筋肉量・基礎代謝・メモ
- **Pydantic バリデーション**: 体温 34–42 ℃、脈拍 30–200 bpm、血圧上 50–250 / 下 30–150 mmHg
- **冪等性**: `request_id` UNIQUE 制約により重複リクエストを成功扱いで吸収
- **Worker リトライ**: `database is locked` のみ対象、指数バックオフ（最大5回）
- **Graceful Shutdown**: SIGTERM ハンドリング + Worker への `None` タスク送信
- **構造化ログ**: Worker の処理状況を JSON 形式で標準出力に記録
- **FastAPI エンドポイント**:
  - `GET  /api/health/health` — ヘルスチェック
  - `POST /api/health/record` — 登録（Queue 経由）
  - `PUT  /api/health/record/{id}` — 更新（Queue 経由）
  - `DELETE /api/health/record/{id}` — 削除（Queue 経由）
  - `GET  /api/health/records` — 一覧（直接 SELECT、ページング対応）
  - `GET  /api/health/records/range` — 日付範囲取得（グラフ用）
  - `GET  /api/health/records/latest/{user_id}` — 最新1件取得
- **Streamlit UI**: 4タブ構成（グラフ・一覧・新規登録・修正削除）
- **Docker Compose 統合**: `biolog-api`（ポート 8766）、`biolog-streamlit`（ポート 8501）
- **ドキュメント**: `biolog_api/skills.md`（API リファレンス・curl 集）、`CLAUDE.md`（設計ルール・既知バグ）
