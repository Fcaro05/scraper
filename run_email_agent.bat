@echo off
REM Script helper per eseguire email_agent usando 'py' invece di 'python'
REM Uso: run_email_agent.bat [opzioni]

if "%~1"=="" (
    echo Uso: run_email_agent.bat --sheet-id [ID] --template [template] --subject [subject] [altre opzioni]
    echo.
    echo Esempio:
    echo   run_email_agent.bat --sheet-id 1ABC123 --template templates/email_template.html --subject "Test" --service-account scraper-maps-484210-8f7e62a75bdc.json --dry-run
    exit /b 1
)

REM Esegui email_agent usando 'py' (Python Launcher)
py email_agent.py %*
