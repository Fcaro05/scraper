@echo off
REM Script helper per eseguire lo scraper usando 'py' invece di 'python'
REM Uso: run_scraper.bat [opzioni aggiuntive]

REM Se non viene passato nessun argomento, mostra help
if "%~1"=="" (
    echo Uso: run_scraper.bat --sheet-id [ID] --service-account [file.json] [altre opzioni]
    echo.
    echo Esempio:
    echo   run_scraper.bat --sheet-id 1ABC123 --service-account scraper-maps-484210-8f7e62a75bdc.json
    echo   run_scraper.bat --sheet-id 1ABC123 --service-account scraper-maps-484210-8f7e62a75bdc.json --headful
    exit /b 1
)

REM Esegui lo scraper usando 'py' (Python Launcher)
py scraper.py %*
