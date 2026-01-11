# Scraper Google Maps -> Google Sheets (gratuito)

Script Python che automatizza la ricerca su Google Maps, estrae dati dei business locali, recupera email dai siti e valuta se il sito è “migliorabile”, scrivendo i risultati su Google Sheets (una riga per business).

## Requisiti
- Python 3.10+
- Dipendenze: `pip install -r requirements.txt`
- Browser Playwright: `python -m playwright install chromium`
- Service account Google con accesso al foglio (JSON). Il file o il JSON inline non devono essere pubblicati.

## Configurazione
- Variabili possibili:
  - `SERVICE_ACCOUNT_FILE` → percorso del file JSON del service account (opzione alternativa a CLI).
  - `SERVICE_ACCOUNT_JSON` → JSON inline del service account.
- Foglio: crea il foglio e copia l’ID (parte tra `/d/` e `/edit` nell’URL). Il foglio verrà usato (default `Sheet1`), con intestazioni auto-create.

## Esecuzione rapida (usa le query predefinite)
```bash
python scraper.py --sheet-id <ID_FOGLIO> --service-account /percorso/service_account.json
# oppure inline:
# SERVICE_ACCOUNT_JSON='{"type":"service_account", ...}' python scraper.py --sheet-id <ID>
```

## Parametri utili
- `--worksheet` nome del tab (default `Sheet1`).
- `--headful` per vedere il browser (di default headless).
- `--max-per-query` numero massimo di card per ogni query (default 8).
- `--min-delay` / `--max-delay` ritardi random tra card (secondi, default 1.0 / 3.5).
- `--queries-file` file JSON custom (lista di oggetti `{ "keyword": "...", "city": "...", "max": opzionale }`).

## Output scritto su Google Sheets
Intestazioni (auto-create o forzate sulla prima riga):  
`Email, Phone, Website, Keyword, Nome proprietario, Location`

La colonna `Keyword` viene popolata come `tipologia business + nome attività` (es. `Idraulico - ABC Idraulica`). `Nome proprietario` non è fornito da Maps e resta vuoto.

Dedup: prima di scrivere, lo script legge le keyword già presenti sul foglio e scarta quelle già viste (match sulla colonna `Keyword`).

## Note e limiti
- Google scoraggia lo scraping; mantieni volumi bassi, usa pause e controlla eventuali CAPTCHA.
- Le euristiche “migliorabile” sono leggere: assenza HTTPS, viewport/meta description mancanti, favicon assente, librerie datate, layout a tabelle, pagina molto pesante, contenuti scarsi (richiede ≥2 condizioni negative).
- Estrazione email: cerca `mailto:` e pattern email su homepage + pagine contatto/chi siamo; non garantito per tutti i siti.

