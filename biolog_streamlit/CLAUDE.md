# BioLog プロジェクト — CLAUDE.md

> 本ファイルは AI コーディングアシスタント（Claude Code 等）向けの設計ルール集です。
> 人間の開発者にとっても「絶対に破ってはいけない制約」として参照価値があります。

---

## プロジェクト概要

家族（self / father / mother）の健康データ（血圧・体温・脈拍・体重等）を記録・可視化する
Streamlit + FastAPI アプリ。SQLite ファイル 1 つで完結し、ローカル/LAN 内で動作する。

- **FastAPI（biolog-api）**: 書き込み受付・読み取り API。ポート 8766
- **Streamlit（biolog-streamlit）**: 閲覧・登録・修正 UI。ポート 8501
- **DB**: `${BIOLOG_DATA_DIR:-./data}/biolog.db`

---

## 環境・ファイル構成

```
<repository-root>/
├── docker-compose.yml
├── .env.sample
├── biolog_api/
│   ├── api.py            FastAPI エンドポイント
│   ├── biocore.py        読み取り専用クエリ
│   ├── db_manager.py     DB 接続の唯一の入口
│   ├── queue_manager.py  Queue singleton
│   ├── worker.py         単一 Writer スレッド
│   ├── schemas.py        Pydantic バリデーション
│   ├── preprocess.py     正規化（JST date 補完含む）
│   ├── time_utils.py     JST ユーティリティ
│   ├── log_utils.py      PII マスク
│   ├── entrypoint.sh     migration → uvicorn 直列
│   ├── migrations/
│   ├── skills.md         API リファレンス・curl 集
│   ├── Dockerfile
│   └── requirements.txt
└── biolog_streamlit/
    ├── streamlit_app.py  4タブ UI
    ├── time_utils.py
    ├── Dockerfile
    └── requirements.txt
```

---

## 絶対に破ってはいけないルール

これらは SQLite ロック競合・データ整合性を守るための設計上の制約。変更・例外禁止。

1. **書き込み経路は 1 本のみ**: `FastAPI → Queue → Worker(1 スレッド) → db_manager → SQLite`
2. **`sqlite3.connect()` は `db_manager.py` 以外で呼ばない**（migration runner は例外として隔離接続 OK）
3. **`PRAGMA journal_mode=WAL` 禁止** — Windows NTFS バインドマウントで I/O エラーになる。必ず `DELETE`
4. **Worker は daemon スレッド 1 本のみ**（`threading.Thread(daemon=True)`）
5. **Queue は `queue_manager.get_queue()` で取得する global singleton 1 個のみ**
6. **FastAPI エンドポイント内で DB を直接操作しない**（GET は biocore 経由で SELECT のみ許可）
7. **Streamlit から DB に直接アクセスしない**（FastAPI への HTTP リクエストのみ）
8. **`lifespan` 内に migration / cleanup を書かない**（runner.py + entrypoint.sh で実行）
9. **`@st.cache_data` の invalidate は per-function `.clear()` を使う**（session_state version 機構は使わない）
10. **ログ出力に PII（user_id / request_id / UUID / email）を生で出さない**（`log_utils.mask_pii()` を通す）

---

## デバッグチェックリスト

```
[ ] docker ps -a — ゾンビコンテナ・ポート競合がないか
[ ] docker logs biolog-api — Worker が起動しているか、locked エラーが頻発していないか
[ ] curl /api/health/health — db が "/data/biolog.db" を指しているか
[ ] .db-shm / .db-wal ファイルが ${BIOLOG_DATA_DIR}/... に存在しないか（WAL 残骸）
[ ] journal_mode=DELETE が使われているか（WAL 禁止）
[ ] text_factory=str が設定されているか（日本語文字化け防止）
[ ] Queue が full(100) になっていないか（Worker 停止疑い）
[ ] migration_lock テーブルにロック残存がないか
```

---

## 設計補足

詳細な設計思想・データフロー・整合性モデルは [仕様書.md](仕様書.md) を参照。
画面操作は [操作説明書.md](操作説明書.md) を参照。
