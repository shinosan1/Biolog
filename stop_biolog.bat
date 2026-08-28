@echo off
setlocal

rem ---------------------------------------------------------------
rem BioLog 停止用バッチ
rem
rem このバッチ自身の置き場所を基準に docker compose down を実行する。
rem 記録データは data フォルダの SQLite ファイルに残るため、
rem 停止してもデータは失われない。
rem ---------------------------------------------------------------

cd /d "%~dp0"

title BioLog 停止

rem PATH に Git 等の同名コマンドがあっても Windows 標準のものを使う
set "SLEEP_EXE=%SystemRoot%\System32\timeout.exe"

if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml が見つかりません。
    echo         このバッチは biolog のリポジトリ直下に置いてください。
    echo         現在の場所 : %CD%
    goto :FAILED
)

echo BioLog を停止します。
echo  停止元 : %CD%
echo.

docker compose down
if errorlevel 1 (
    echo.
    echo [ERROR] 停止に失敗しました。上に表示されたメッセージを確認してください。
    goto :FAILED
)

echo.
echo 停止しました。記録データは data フォルダに残っています。
"%SLEEP_EXE%" /t 5 /nobreak >nul
endlocal
exit /b 0

:FAILED
echo.
pause
endlocal
exit /b 1
