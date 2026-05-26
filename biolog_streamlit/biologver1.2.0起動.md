変更サマリー（v1.2.0）
BUG-001 修正（UPSERT実装）
biolog_api/api.py:37 — DDL に UNIQUE INDEX を追加


CREATE UNIQUE INDEX IF NOT EXISTS uidx_hr_user_date ON health_records(user_id, date);
biolog_api/worker.py:82-100 — INSERT を UPSERT に変更

同一 user_id + date への再登録は上書き更新（重複行が増えない）
同一 request_id の再送は引き続き冪等 success（既存動作を維持）
BUG-002 / IMPROVEMENT-001 修正（削除プレビュー）
biolog_api/biocore.py — get_record_by_id() を追加

biolog_api/api.py — GET /api/health/record/{record_id} を追加

biolog_streamlit/streamlit_app.py — 削除タブ改修

ID 入力時にリアルタイムでレコット内容をプレビュー表示
存在しない ID は「存在しません」警告 → 削除ボタンが表示されず 404 を事前防止
削除成功後に st.rerun() でプレビューを自動クリア
起動コマンド

docker-compose up -d --build biolog-api biolog-streamlit
docker logs biolog-api