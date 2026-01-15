@echo off
REM Comando completo per eseguire lo scraper con tutti i parametri OTTIMIZZATI
REM Parametri velocità: --min-delay 0.1 --max-delay 0.3 --max-concurrent 10
py scraper.py --sheet-id 1T-nvSgaC-bRu4PEYDREyeGEADh0SmSqIlLSwP7YS8_g --service-account scraper-maps-484210-8f7e62a75bdc.json --worksheet Sheet1 --max-per-query 8 --min-delay 0.1 --max-delay 0.3 --max-concurrent 10 --save-to results.json
