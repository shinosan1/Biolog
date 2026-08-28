# サードパーティライセンス(BioLog)

作成日: 2026-08-28

BioLogが`biolog_api/requirements.txt`・`biolog_streamlit/requirements.txt`で直接依存している外部ライブラリのライセンス情報です。ライセンス種別は、インストール済みパッケージのメタデータ(`.dist-info/METADATA`)から確認した内容をそのまま記載しています。BioLogは専用の`.venv`をリポジトリ内に持たない(Dockerコンテナ内で依存関係を解決する)ため、システムのPython環境にインストールされた同名パッケージのメタデータから確認しました。**確認に使ったバージョンは、`requirements.txt`で固定されている実際の稼働バージョンとは異なる場合があります**(パッケージ名・ライセンスの傾向を確認する目的での参照です)。

## biolog_api の直接依存

| パッケージ | requirements.txt指定 | 確認したライセンス表記 | 用途 |
|---|---|---|---|
| `fastapi` | ==0.115.5 | MIT | APIフレームワーク |
| `uvicorn` | ==0.32.1 | BSD-3-Clause | ASGIサーバー |
| `pydantic` | ==2.10.3 | MIT | データバリデーション |

## biolog_streamlit の直接依存

| パッケージ | requirements.txt指定 | 確認したライセンス表記 | 用途 |
|---|---|---|---|
| `streamlit` | ==1.40.2 | Apache-2.0 | Web UIフレームワーク |
| `pandas` | ==2.2.3 | BSD 3-Clause License | データ処理 |
| `requests` | ==2.32.3 | Apache-2.0 | HTTP通信(API呼び出し) |
| `matplotlib` | ==3.9.4 | matplotlib独自ライセンス(BSD/PSF系、"License agreement for matplotlib versions 1.3.0 and later") | グラフ描画 |
| `seaborn` | ==0.13.2 | BSD License | グラフ描画(matplotlib上位) |
| `japanize-matplotlib` | ==1.1.3 | **確認できず**(システムのPython環境にインストールされておらず、メタデータを確認できませんでした) | matplotlibの日本語フォント設定 |

## biolog_api の間接依存(`biolog_api/constraints.txt`固定)

`annotated-types` / `anyio` / `click` / `h11` / `idna` / `pydantic_core` / `starlette` / `typing_extensions` は、上記直接依存(主にfastapi/pydantic/uvicorn)が要求する間接依存としてバージョン固定されています。個別のライセンス確認は行っていません。いずれもPython Webエコシステムで一般的なMIT/BSD系ライセンスのパッケージですが、正確なライセンス種別は各パッケージの配布物を個別に確認してください。

## テスト専用依存

`pytest==8.3.5`(`requirements-test.txt`)は開発・テスト時のみ使用し、実行時(Docker稼働時)の配布物には含まれません。

## 確認方法についての注記

本文書のライセンス種別は、システムPython環境の`site-packages`配下にある各パッケージの`.dist-info/METADATA`から確認しています。`japanize-matplotlib`のように未確認のものは、推測せず「確認できず」と明記しています。`requirements.txt`のバージョンを更新した場合、または正式にライセンス情報が必要になった場合は、実際に使用するバージョンのパッケージから再確認してください。

依存パッケージのライセンス全文自体は本文書に転記していません。各パッケージのPyPIページまたは配布物内のライセンスファイルを参照してください。
