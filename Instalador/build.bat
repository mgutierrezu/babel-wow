@echo off
rem Genera output\InstalarTraductorWoW.exe: un solo archivo con el traductor y el addon dentro.
setlocal
cd /d "%~dp0"
set RAIZ=%~dp0..

if not exist "%RAIZ%\Traductor\dist\TraductorWoW.exe" (
    echo Falta Traductor\dist\TraductorWoW.exe. Ejecuta primero Traductor\build.bat.
    goto :error
)

echo Compilando el instalador...
python -m PyInstaller --onefile --noconsole --clean --name InstalarTraductorWoW ^
    --icon "%RAIZ%\Traductor\icono.ico" --exclude-module pystray --exclude-module PIL ^
    --distpath "%RAIZ%\output" --workpath "%~dp0build" --specpath "%~dp0build" ^
    --paths "%RAIZ%\Traductor" ^
    --add-data "%RAIZ%\Traductor\dist\TraductorWoW.exe;paquete" ^
    --add-data "%RAIZ%\Traductor\.env.example;paquete" ^
    --add-data "%RAIZ%\Traductor\prompt.txt;paquete" ^
    --add-data "%RAIZ%\Addon\TraductorWoW;paquete\TraductorWoW" ^
    instalador.py
if errorlevel 1 goto :error

copy /y LEEME.txt "%RAIZ%\output\" >nul

echo.
echo Listo: %RAIZ%\output\InstalarTraductorWoW.exe
echo Comparte la carpeta output completa (el instalador y LEEME.txt).
pause
exit /b 0

:error
echo.
echo La compilacion fallo. Revisa los mensajes de arriba.
pause
exit /b 1
