# Scraper Google Maps -> Google Sheets (gratuito)

Script Python che automatizza la ricerca su Google Maps, estrae dati dei business locali, recupera email dai siti e valuta se il sito è "migliorabile", scrivendo i risultati su Google Sheets (una riga per business).

## 🚀 Setup Rapido

### 1. Installa Python 3.10+
- Windows: Scarica da [python.org](https://www.python.org/downloads/)
- Verifica: `python --version` (deve essere 3.10 o superiore)

### 2. Esegui lo script di setup automatico
```bash
python setup.py
```

Lo script installerà automaticamente:
- Tutte le dipendenze da `requirements.txt`
- Browser Playwright (Chromium)
- Creerà file di esempio per la configurazione

### 3. Verifica l'installazione
```bash
python check_setup.py
```

### 4. Configurazione Manuale

#### Service Account Google
1. Vai su [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuovo progetto o seleziona uno esistente
3. Abilita l'API "Google Sheets API"
4. Crea un Service Account:
   - Vai su "IAM & Admin" > "Service Accounts"
   - Clicca "Create Service Account"
   - Assegna un nome e crea
   - Clicca sul service account creato > "Keys" > "Add Key" > "Create new key" > JSON
   - Scarica il file JSON (⚠️ **NON COMMITTARLO**)
5. Condividi il Google Sheet con l'email del service account (tipo: `nome@progetto.iam.gserviceaccount.com`)

#### Configurazione variabili d'ambiente (opzionale)
Puoi configurare le variabili in due modi:

**Opzione A: Variabili d'ambiente**
```bash
# Windows PowerShell
$env:SERVICE_ACCOUNT_FILE="path/to/service_account.json"

# Linux/Mac
export SERVICE_ACCOUNT_FILE="path/to/service_account.json"
```

**Opzione B: Passare come argomento CLI** (vedi sotto)

## Requisiti
- Python 3.10+
- Dipendenze: `pip install -r requirements.txt` (o usa `setup.py`)
- Browser Playwright: `python -m playwright install chromium` (o usa `setup.py`)
- Service account Google con accesso al foglio (JSON). Il file o il JSON inline non devono essere pubblicati.

## Configurazione
- Variabili possibili:
  - `SERVICE_ACCOUNT_FILE` → percorso del file JSON del service account (opzione alternativa a CLI).
  - `SERVICE_ACCOUNT_JSON` → JSON inline del service account.
- Foglio: crea il foglio e copia l'ID (parte tra `/d/` e `/edit` nell'URL). Il foglio verrà usato (default `Sheet1`), con intestazioni auto-create.

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
- Le euristiche "migliorabile" sono rigide: richiede almeno 5 problemi gravi o assenza di caratteristiche moderne (richiede ≥2 indicatori positivi per essere scartato).
- Estrazione email: cerca `mailto:` e pattern email su homepage + pagine contatto/chi siamo; non garantito per tutti i siti.

## 🔧 Troubleshooting

### Errore: "Python was not found"
- Installa Python 3.10+ da [python.org](https://www.python.org/downloads/)
- Durante l'installazione, assicurati di selezionare "Add Python to PATH"

### Errore: "Service account mancante"
- Verifica di aver passato `--service-account` o configurato `SERVICE_ACCOUNT_FILE`
- Controlla che il file JSON esista e sia valido
- Assicurati di aver condiviso il Google Sheet con l'email del service account

### Errore: "Playwright browser not found"
```bash
python -m playwright install chromium
```

### Errore: "Module not found"
```bash
pip install -r requirements.txt
```
Oppure esegui: `python setup.py`

### Il browser non si apre / CAPTCHA
- Prova con `--headful` per vedere cosa succede
- Aumenta i delay con `--min-delay` e `--max-delay`
- Google può bloccare richieste troppo frequenti

### Nessun risultato scritto su Google Sheets
- Verifica che il foglio sia condiviso con il service account
- Controlla che l'ID del foglio sia corretto
- Lo script filtra solo business con email E siti "migliorabili" (almeno 5 problemi)

## 📁 Struttura Progetto

```
scraper/
├── scraper.py              # Script principale di scraping
├── email_agent.py          # Script per invio email (vedi EMAIL_AGENT_README.md)
├── setup.py                # Script di setup automatico
├── check_setup.py          # Script di verifica ambiente
├── requirements.txt        # Dipendenze Python
├── .gitignore             # File da ignorare nel git
├── config.example.txt      # Esempio configurazione variabili
├── README.md               # Questo file
├── EMAIL_AGENT_README.md   # Documentazione email agent
└── templates/              # Template email Jinja2
    ├── email_template.html
    └── email_template.txt
```

