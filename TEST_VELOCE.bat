@echo off
REM Test veloce con solo 1 query per verificare le ottimizzazioni
REM Salva solo in locale senza scrivere su Google Sheets

echo ========================================
echo TEST VELOCE - 1 Query
echo ========================================
echo.

py scraper.py ^
  --service-account scraper-maps-484210-8f7e62a75bdc.json ^
  --max-per-query 3 ^
  --min-delay 0.1 ^
  --max-delay 0.3 ^
  --max-concurrent 10 ^
  --save-to test_veloce.json ^
  --headful

echo.
echo ========================================
echo Test completato! Risultati in: test_veloce.json
echo ========================================
pause
