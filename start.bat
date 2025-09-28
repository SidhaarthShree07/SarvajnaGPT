@echo off
echo Setting up SarvajñaGPT environment variables...

REM Find VS Code installation
SET VSCODE_CMD=

REM Try to locate VS Code in common installation paths
IF EXIST "%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe" (
    SET VSCODE_CMD="%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
    GOTO :FOUND
)

IF EXIST "C:\Program Files\Microsoft VS Code\Code.exe" (
    SET VSCODE_CMD="C:\Program Files\Microsoft VS Code\Code.exe"
    GOTO :FOUND
)

IF EXIST "C:\Program Files (x86)\Microsoft VS Code\Code.exe" (
    SET VSCODE_CMD="C:\Program Files (x86)\Microsoft VS Code\Code.exe"
    GOTO :FOUND
)

REM Try Microsoft Store installation
IF EXIST "%LOCALAPPDATA%\Microsoft\WindowsApps\code.exe" (
    SET VSCODE_CMD="%LOCALAPPDATA%\Microsoft\WindowsApps\code.exe"
    GOTO :FOUND
)

REM Try finding in PATH using where command
FOR /F "tokens=*" %%i IN ('where code 2^>NUL') DO (
    SET VSCODE_CMD="%%i"
    GOTO :FOUND
)

echo VS Code not found in common locations or PATH.
echo Please set POWER_VSCODE_BIN environment variable manually.
GOTO :CONTINUE

:FOUND
echo VS Code found at %VSCODE_CMD%
setx POWER_VSCODE_BIN %VSCODE_CMD%
echo POWER_VSCODE_BIN environment variable set!

:CONTINUE
echo Starting SarvajñaGPT...
python run.py

pause