@echo off
setlocal

rem ---------------------------------------------------------------
rem BioLog 起動用バッチ
rem
rem このバッチ自身が置かれたディレクトリを基準に docker compose を
rem 実行する。パスを一切ハードコードしていないため、C: の開発ソース
rem でも D: の運用環境でも、コピーするだけでそのまま動作する。
rem
rem 使い方 : ダブルクリック
rem 引数   : --build を付けるとイメージを強制的に再ビルドする
rem ---------------------------------------------------------------

cd /d "%~dp0"

title BioLog

set "UI_URL=http://localhost:8501"
set "HEALTH_URL=http://localhost:8501/_stcore/health"
set "WAIT_LIMIT=300"
set "WAIT_STEP=3"

rem PATH に Git 等の同名コマンドがあっても Windows 標準のものを使う
set "CURL_EXE=%SystemRoot%\System32\curl.exe"
set "SLEEP_EXE=%SystemRoot%\System32\timeout.exe"

set "BUILD_OPT="
if /i "%~1"=="--build" set "BUILD_OPT=--build"

if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml が見つかりません。
    echo         このバッチは biolog のリポジトリ直下に置いてください。
    echo         現在の場所 : %CD%
    goto :FAILED
)

echo ===============================================
echo  BioLog
echo ===============================================
echo  起動元 : %CD%
echo.

docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker に接続できませんでした。
    echo         Docker Desktop を起動し、完全に立ち上がってから
    echo         もう一度このバッチを実行してください。
    goto :FAILED
)

if defined BUILD_OPT (
    echo イメージを再ビルドしてから起動します。数分かかります。
) else (
    echo コンテナを起動しています。
    echo ※ イメージが未作成の場合は、ここで自動的にビルドされます。
    echo    初回のみ 3-5 分ほどかかります。
)
echo.

docker compose up -d %BUILD_OPT%
if errorlevel 1 (
    echo.
    echo [ERROR] 起動に失敗しました。上に表示されたメッセージを確認してください。
    goto :FAILED
)

echo.
echo 画面の準備を待っています ...

if not exist "%CURL_EXE%" goto :WAIT_FIXED

set /a WAITED=0

:WAIT_LOOP
"%CURL_EXE%" --silent --fail --max-time 3 --output NUL "%HEALTH_URL%"
if not errorlevel 1 goto :READY
if %WAITED% GEQ %WAIT_LIMIT% goto :TIMEOUT
"%SLEEP_EXE%" /t %WAIT_STEP% /nobreak >nul
set /a WAITED+=%WAIT_STEP%
goto :WAIT_LOOP

:WAIT_FIXED
rem curl.exe が無い環境では固定時間だけ待ってから開く
"%SLEEP_EXE%" /t 20 /nobreak >nul
goto :READY

:READY
echo   準備ができました。
echo.
start "" "%UI_URL%"
echo ブラウザで %UI_URL% を開きました。
echo 停止するときは stop_biolog.bat を実行してください。
echo.
"%SLEEP_EXE%" /t 5 /nobreak >nul
endlocal
exit /b 0

:TIMEOUT
echo.
echo [WARN] 待ち時間内に画面の準備が終わりませんでした。
echo        コンテナ自体は起動している可能性があります。
echo        次のコマンドで状態を確認してください。
echo.
echo          docker compose ps
echo          docker logs biolog-streamlit --tail 50
echo.
echo        ブラウザだけ先に開く場合は %UI_URL% を開いてください。
echo.
pause
endlocal
exit /b 1

:FAILED
echo.
pause
endlocal
exit /b 1
