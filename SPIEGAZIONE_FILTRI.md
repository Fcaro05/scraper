# 📊 Spiegazione Dettagliata Filtri "Migliorabile"

## Come Funziona `assess_site_quality()`

La funzione analizza ogni sito web e assegna un punteggio basato su problemi trovati.

### 🔍 Problemi Rilevati (Reasons)

1. **Assenza HTTPS** - Sito usa `http://` invece di `https://`
2. **Non responsive** - Manca tag `<meta name="viewport">`
3. **Meta description mancante** - Manca `<meta name="description">`
4. **Favicon assente** - Manca `<link rel="icon">`
5. **jQuery 1.x** - Usa versioni vecchie di jQuery
6. **Bootstrap datato** - Usa Bootstrap 2.x o 3.x
7. **Layout a tabelle** - Troppi `<table>` e pochi `<div>` (sito vecchio)
8. **Pagina pesante** - HTML > 400KB
9. **Contenuti scarsi** - Testo totale < 200 caratteri
10. **Titolo mancante** - Manca `<title>` o è vuoto
11. **Titolo troppo corto** - `<title>` < 10 caratteri
12. **Servizio gratuito** - Usa Wix, Weebly, Squarespace

### ✅ Indicatori Positivi (Positive Indicators)

Conta quante di queste caratteristiche moderne ha:
1. **Framework moderno** - React, Vue, Angular, Next.js
2. **Structured data** - Schema.org o microdata
3. **Open Graph tags** - `<meta property="og:...">`
4. **Canonical URL** - `<link rel="canonical">`
5. **Robots meta** - `<meta name="robots">`

### 🎯 Logica di Filtro Attuale

```python
# Se ha >= 2 indicatori positivi → SCARTA (sito troppo buono)
if positive_indicators >= 2:
    migliorabile = False
else:
    # Se ha < 2 indicatori positivi → richiedi ALMENO 3 problemi
    migliorabile = len(reasons) >= 3
```

### 📈 Risultati Attuali

Dai log vedo:
- **29 business con email** trovati
- **Solo 1 passa il filtro migliorabile** (rimossi 28)

Questo significa che:
- La maggior parte dei siti ha **>= 2 indicatori positivi** (siti moderni)
- O hanno **< 3 problemi** (siti accettabili)

### 🔧 Possibili Modifiche

**Opzione 1: Ridurre soglia problemi (da 3 a 2)**
```python
migliorabile = len(reasons) >= 2  # Più permissivo
```

**Opzione 2: Ridurre indicatori positivi richiesti (da 2 a 3)**
```python
if positive_indicators >= 3:  # Più permissivo
    migliorabile = False
```

**Opzione 3: Cambiare logica completamente**
- Accetta siti con almeno 2 problemi E < 2 indicatori positivi
- O accetta tutti i siti con email (rimuovi filtro migliorabile)

### 💡 Raccomandazione

Guardando i log, molti siti hanno problemi ma non raggiungono la soglia di 3.
Esempi trovati:
- `beautyroom_milano` - 4 problemi ma senza email → scartato
- `eknam.com` - 5 problemi ma senza email → scartato
- `chiaraventuri.it` - 5 problemi CON email → ✅ passa!

**Suggerimento**: Ridurre a 2 problemi invece di 3, così catturiamo più siti migliorabili.
