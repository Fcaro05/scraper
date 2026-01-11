# Email Agent - Sistema Automatizzato di Invio Email

Sistema completamente **gratuito** per inviare email personalizzate ai contatti presenti in Google Sheets, utilizzando template Jinja2 e Gmail SMTP.

## 🎯 Caratteristiche

- ✅ **Completamente gratuito** (usa Gmail SMTP)
- ✅ Lettura automatica da Google Sheets
- ✅ Template personalizzabili con Jinja2
- ✅ Supporto HTML e testo semplice
- ✅ Tracciamento email inviate (colonna opzionale)
- ✅ Modalità dry-run per test senza inviare
- ✅ Delay configurabile tra le email
- ✅ Gestione errori robusta

## 📋 Requisiti

1. **Python 3.10+**
2. **Account Gmail** con App Password (vedi configurazione sotto)
3. **Service Account Google** per accedere a Google Sheets (stesso del scraper)
4. **Dipendenze**: `pip install -r requirements.txt`

## 🔧 Configurazione

### 1. Creare App Password Gmail

Gmail richiede una **App Password** (non la password normale) per l'autenticazione SMTP:

1. Vai su [Google Account](https://myaccount.google.com/)
2. Sezione **Sicurezza**
3. Attiva **Verifica in due passaggi** (se non già attiva)
4. Vai su **Password delle app**
5. Seleziona "App" → "Mail" e "Dispositivo" → "Altro (nome personalizzato)"
6. Inserisci un nome (es. "Email Agent")
7. Copia la password generata (16 caratteri senza spazi)

⚠️ **IMPORTANTE**: Salva questa password, non la vedrai più!

### 2. Preparare Google Sheets

Il foglio deve avere almeno queste colonne (nell'ordine):
- **Email** (obbligatoria)
- **Phone**
- **Website**
- **Keyword**
- **Nome proprietario**
- **Location**

Colonne aggiuntive saranno disponibili nel template come `extra_data['NomeColonna']`.

**Opzionale**: Aggiungi una colonna "Inviata" per tracciare le email già inviate.

### 3. Creare Template Email

Crea un file template usando la sintassi Jinja2. Esempi in `templates/`:

**Variabili disponibili nel template:**
- `{{ email }}` - Email del destinatario
- `{{ phone }}` - Telefono
- `{{ website }}` - Sito web
- `{{ keyword }}` - Keyword/attività
- `{{ nome_proprietario }}` - Nome (default: "Gentile Cliente")
- `{{ location }}` - Location/indirizzo
- `{{ row_number }}` - Numero riga nel foglio
- `{{ NomeColonna }}` - Qualsiasi colonna extra dal foglio

**Esempio template semplice:**
```html
Ciao {{ nome_proprietario }}!

Abbiamo notato la tua attività {{ keyword }} a {{ location }}.

Contattaci per maggiori informazioni!

Cordiali saluti,
Il Team
```

## 🚀 Utilizzo

### Comando Base

```bash
python email_agent.py \
  --sheet-id <ID_FOGLIO> \
  --template templates/email_template.html \
  --subject "Proposta per {{ keyword }}" \
  --gmail-email tua-email@gmail.com \
  --gmail-password tua-app-password \
  --service-account /path/to/service_account.json
```

### Opzioni Principali

| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `--sheet-id` | ID del Google Sheet (obbligatorio) | - |
| `--worksheet` | Nome del foglio | `Sheet1` |
| `--template` | Percorso al template (obbligatorio) | - |
| `--subject` | Oggetto email (può contenere variabili) | - |
| `--gmail-email` | Email Gmail mittente | Env: `GMAIL_EMAIL` |
| `--gmail-password` | App Password Gmail | Env: `GMAIL_APP_PASSWORD` |
| `--service-account` | File JSON service account | Env: `SERVICE_ACCOUNT_FILE` |
| `--sender-name` | Nome mittente | `Email Agent` |
| `--dry-run` | Test senza inviare email | `False` |
| `--start-row` | Riga di partenza (salta header) | `2` |
| `--max-emails` | Limite email da inviare | Nessun limite |
| `--delay` | Secondi tra email | `2.0` |
| `--skip-sent` | Salta righe già inviate | `False` |
| `--mark-sent-column` | Nome colonna per tracking | `Inviata` |

### Esempi Pratici

#### 1. Test (Dry Run)
```bash
python email_agent.py \
  --sheet-id 1ABC123... \
  --template templates/email_template.html \
  --subject "Test per {{ nome_proprietario }}" \
  --dry-run \
  --max-emails 3 \
  --service-account service_account.json
```

#### 2. Invio Reale
```bash
python email_agent.py \
  --sheet-id 1ABC123... \
  --template templates/email_template.html \
  --subject "Proposta commerciale - {{ keyword }}" \
  --gmail-email mario.rossi@gmail.com \
  --gmail-password abcd efgh ijkl mnop \
  --service-account service_account.json \
  --delay 3.0 \
  --skip-sent \
  --mark-sent-column "Inviata"
```

#### 3. Usando Variabili d'Ambiente
```bash
export GMAIL_EMAIL="mario.rossi@gmail.com"
export GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"
export SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

python email_agent.py \
  --sheet-id 1ABC123... \
  --template templates/email_template.html \
  --subject "Proposta per {{ keyword }}"
```

#### 4. Invio Limitato (Test)
```bash
python email_agent.py \
  --sheet-id 1ABC123... \
  --template templates/email_template.txt \
  --subject "Test - {{ nome_proprietario }}" \
  --max-emails 5 \
  --delay 1.0 \
  --service-account service_account.json \
  --gmail-email tua-email@gmail.com \
  --gmail-password tua-app-password
```

## 📊 Struttura Google Sheets

Il foglio deve avere questa struttura (minima):

| Email | Phone | Website | Keyword | Nome proprietario | Location | Inviata |
|-------|-------|---------|---------|-------------------|----------|---------|
| mario@example.com | +39... | https://... | Centro estetico - ABC | Mario Rossi | Milano | |
| luigi@example.com | +39... | https://... | Parrucchiere - XYZ | Luigi Verdi | Roma | |

**Note:**
- La colonna "Inviata" è opzionale ma utile per tracciare
- Colonne extra sono disponibili nel template
- Righe senza email valida vengono saltate

## 🎨 Personalizzazione Template

### Template HTML

```html
<!DOCTYPE html>
<html>
<body>
    <h1>Ciao {{ nome_proprietario }}!</h1>
    <p>La tua attività <strong>{{ keyword }}</strong> a {{ location }} è interessante.</p>
    
    {% if website %}
    <p>Visita: <a href="{{ website }}">{{ website }}</a></p>
    {% endif %}
    
    <p>Cordiali saluti,<br>Il Team</p>
</body>
</html>
```

### Template Testo Semplice

```
Ciao {{ nome_proprietario }}!

La tua attività {{ keyword }} a {{ location }} è interessante.

{% if website %}
Visita: {{ website }}
{% endif %}

Cordiali saluti,
Il Team
```

### Variabili Avanzate

```jinja2
{# Accesso a colonne extra #}
{% if extra_data['Note'] %}
Nota: {{ extra_data['Note'] }}
{% endif %}

{# Numero riga #}
Riga {{ row_number }} del foglio

{# Condizionali #}
{% if phone %}
Telefono: {{ phone }}
{% else %}
Telefono non disponibile
{% endif %}
```

## ⚠️ Limitazioni Gmail

Gmail ha limiti per account gratuiti:
- **500 email/giorno** per account personale
- **2000 email/giorno** per account Google Workspace

⚠️ **Raccomandazioni:**
- Usa `--delay` di almeno 2-3 secondi
- Non superare 400-450 email/giorno per sicurezza
- Monitora eventuali blocchi temporanei

## 🔍 Troubleshooting

### Errore: "Autenticazione Gmail fallita"
- Verifica di usare **App Password**, non password normale
- Controlla che la verifica in due passaggi sia attiva
- Assicurati che l'App Password sia corretta (16 caratteri)

### Errore: "Service account mancante"
- Fornisci `--service-account` o `--service-account-json`
- Oppure setta `SERVICE_ACCOUNT_FILE` o `SERVICE_ACCOUNT_JSON` come env

### Email non vengono inviate
- Usa `--dry-run` per vedere cosa verrebbe inviato
- Verifica che le email nel foglio siano valide
- Controlla i log per errori specifici

### Template non trovato
- Verifica il percorso del template
- Usa percorso assoluto o relativo corretto

## 📝 Best Practices

1. **Sempre testare con `--dry-run`** prima di inviare
2. **Usa `--max-emails`** per test iniziali
3. **Abilita `--skip-sent`** per evitare duplicati
4. **Mantieni `--delay` di almeno 2 secondi** per evitare rate limiting
5. **Personalizza il template** per ogni campagna
6. **Monitora le email inviate** usando la colonna "Inviata"

## 🔐 Sicurezza

- ⚠️ **NON committare** file con credenziali
- ⚠️ Usa variabili d'ambiente per password sensibili
- ⚠️ Mantieni il file service account privato
- ⚠️ Non condividere App Password

## 📚 Risorse

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Gmail SMTP Settings](https://support.google.com/mail/answer/7126229)
- [Google Service Account](https://cloud.google.com/iam/docs/service-accounts)

## 🆘 Supporto

Per problemi o domande:
1. Verifica i log di errore
2. Usa `--dry-run` per debug
3. Controlla la configurazione Gmail
4. Verifica i permessi del Service Account

---

**Sistema completamente gratuito** - Nessun costo per l'utilizzo di Gmail SMTP e Google Sheets API (entro i limiti gratuiti).

