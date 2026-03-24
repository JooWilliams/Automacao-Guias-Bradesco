@echo off
chcp 65001 >nul
echo ============================================================
echo  AUTOMACAO GUIAS BRADESCO SAUDE
echo ============================================================
echo.

REM Tenta abrir o Chrome em modo debug com perfil isolado
REM O --user-data-dir separado permite abrir junto com o Chrome normal

set CHROME_DEBUG_DIR=%~dp0chrome-debug-profile
set CHROME_DEBUG_PORT=9223

echo [1/2] Abrindo Chrome para login no Bradesco...
echo.

REM Tenta os caminhos mais comuns do Chrome no Windows
REM ATENCAO: %PROGRAMFILES(X86)% nao pode ser usado dentro de bloco if()
REM pois o ")" do nome da variavel quebra a sintaxe. Por isso e salvo antes.
set PROG86=%PROGRAMFILES(X86)%
set CHROME_PATH=chrome.exe --remote-debugging-port=9223 --user-data-dir="C:\temp\chrome"


if "%CHROME_PATH%"=="" (
    echo [ERRO] Chrome nao encontrado nos caminhos padrao.
    echo Instale o Google Chrome e tente novamente.
    pause
    exit /b 1
)

start "" %CHROME_PATH% --remote-debugging-port=%CHROME_DEBUG_PORT% --user-data-dir="%CHROME_DEBUG_DIR%"

echo.
echo ============================================================
echo  Faca login no portal Bradesco Saude que acabou de abrir.
echo  Quando estiver logado, volte aqui e pressione ENTER.
echo ============================================================
echo.
pause

echo.
echo [2/2] Iniciando automacao...
echo.

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Python nao encontrado.
    echo Instale o Python em python.org e marque "Add to PATH" durante a instalacao.
    pause
    exit /b 1
)

python "%~dp0script2.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERRO] O script encerrou com erro. Veja a mensagem acima.
)
pause
