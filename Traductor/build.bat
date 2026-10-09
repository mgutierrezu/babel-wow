@echo off
rem Genera dist\TraductorWoW.exe con PyInstaller.
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ y marca "Add to PATH".
    goto :error
)

echo Instalando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Compilando...
python -m PyInstaller --onefile --noconsole --clean --name TraductorWoW --icon icono.ico ^
    --add-data ".env.example;." --add-data "prompt.txt;." --add-data "prompt_en.txt;." --add-data "icono.ico;." ^
    --exclude-module pystray --exclude-module PIL traductor.py
if errorlevel 1 goto :error

rem Copia los archivos editables junto al .exe. Si ya tienes un .env propio se usa ese;
rem si no, se parte de la plantilla. Un dist\.env existente no se sobrescribe.
copy /y prompt.txt dist\ >nul
copy /y prompt_en.txt dist\ >nul
copy /y .env.example dist\ >nul
if not exist dist\.env (
    if exist .env (copy /y .env dist\ >nul) else (copy /y .env.example dist\.env >nul)
)

echo.
echo Listo: %~dp0dist\TraductorWoW.exe
echo Puedes editar dist\.env y dist\prompt.txt sin recompilar.
pause
exit /b 0

:error
echo.
echo La compilacion fallo. Revisa los mensajes de arriba.
pause
exit /b 1
