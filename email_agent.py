#!/usr/bin/env python3
"""
Email Agent - Sistema automatizzato per inviare email personalizzate
da Google Sheets usando template Jinja2 e Gmail SMTP (gratuito).

Requisiti:
- Account Gmail con App Password (non password normale)
- Service Account Google per accedere a Google Sheets
- Template email in formato Jinja2
"""

import argparse
import json
import os
import smtplib
import time
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gspread
from jinja2 import Environment, FileSystemLoader, Template


@dataclass
class RecipientData:
    """Dati del destinatario estratti da Google Sheets."""
    email: str
    phone: str
    website: str
    keyword: str
    nome_proprietario: str
    location: str
    # Campi aggiuntivi opzionali
    row_number: int = 0
    extra_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}

    def to_dict(self) -> Dict[str, Any]:
        """Converte i dati in dizionario per il template Jinja2."""
        return {
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "keyword": self.keyword,
            "nome_proprietario": self.nome_proprietario or "Gentile Cliente",
            "location": self.location,
            "row_number": self.row_number,
            **self.extra_data,
        }


def parse_args() -> argparse.Namespace:
    """Parse degli argomenti da riga di comando."""
    parser = argparse.ArgumentParser(
        description="Email Agent - Invia email personalizzate da Google Sheets (gratuito)."
    )
    parser.add_argument(
        "--sheet-id",
        required=True,
        help="ID del Google Sheet (parte tra /d/ e /edit nell'URL).",
    )
    parser.add_argument(
        "--worksheet",
        default="Sheet1",
        help="Nome del foglio di lavoro (default: Sheet1).",
    )
    parser.add_argument(
        "--template",
        required=True,
        help="Percorso al file template email (formato Jinja2).",
    )
    parser.add_argument(
        "--subject",
        required=True,
        help="Oggetto dell'email (può contenere variabili Jinja2).",
    )
    parser.add_argument(
        "--service-account",
        help="Percorso al file JSON del service account.",
    )
    parser.add_argument(
        "--service-account-json",
        help="JSON del service account inline (oppure setta env SERVICE_ACCOUNT_JSON).",
    )
    parser.add_argument(
        "--gmail-email",
        help="Email Gmail per inviare (oppure setta env GMAIL_EMAIL).",
    )
    parser.add_argument(
        "--gmail-password",
        help="App Password Gmail (oppure setta env GMAIL_APP_PASSWORD).",
    )
    parser.add_argument(
        "--sender-name",
        default="Email Agent",
        help="Nome del mittente (default: Email Agent).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modalità test: mostra le email senza inviarle.",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=2,
        help="Riga di partenza (default: 2, salta header).",
    )
    parser.add_argument(
        "--max-emails",
        type=int,
        help="Numero massimo di email da inviare (utile per test).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in secondi tra un'email e l'altra (default: 2.0).",
    )
    parser.add_argument(
        "--skip-sent",
        action="store_true",
        help="Salta righe con colonna 'Inviata' = 'Sì' o 'Si'.",
    )
    parser.add_argument(
        "--mark-sent-column",
        default="Inviata",
        help="Nome colonna per marcare email inviate (default: 'Inviata').",
    )
    return parser.parse_args()


def build_gspread_client(
    service_account_path: Optional[str], service_account_json: Optional[str]
) -> gspread.Client:
    """Costruisce il client gspread per accedere a Google Sheets."""
    if service_account_json:
        data = json.loads(service_account_json)
        return gspread.service_account_from_dict(data)
    env_json = os.getenv("SERVICE_ACCOUNT_JSON")
    if env_json:
        data = json.loads(env_json)
        return gspread.service_account_from_dict(data)
    if service_account_path:
        path_obj = Path(service_account_path)
        if path_obj.exists():
            return gspread.service_account(filename=str(path_obj))
    env_path = os.getenv("SERVICE_ACCOUNT_FILE")
    if env_path and Path(env_path).exists():
        return gspread.service_account(filename=env_path)
    raise ValueError(
        "Service account mancante: passa --service-account o --service-account-json o variabile env."
    )


def get_worksheet(client: gspread.Client, sheet_id: str, worksheet_name: str):
    """Ottiene o crea il worksheet specificato."""
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        raise ValueError(f"Worksheet '{worksheet_name}' non trovato nel foglio.")
    return ws


def load_recipients(
    ws, start_row: int = 2, max_emails: Optional[int] = None, skip_sent: bool = False, sent_column: str = "Inviata"
) -> List[RecipientData]:
    """
    Carica i destinatari dal Google Sheet.
    
    Assume struttura: Email, Phone, Website, Keyword, Nome proprietario, Location
    """
    try:
        all_values = ws.get_all_values()
    except Exception as e:
        raise ValueError(f"Errore nel leggere il foglio: {e}")

    if len(all_values) < start_row:
        return []

    # Trova l'indice della colonna "Inviata" se esiste
    headers = all_values[0] if all_values else []
    sent_col_idx = None
    if skip_sent and sent_column:
        try:
            sent_col_idx = headers.index(sent_column)
        except ValueError:
            sent_col_idx = None

    recipients: List[RecipientData] = []
    end_row = len(all_values)
    if max_emails:
        end_row = min(start_row + max_emails, len(all_values))

    for idx in range(start_row - 1, end_row):  # -1 perché è 0-based
        row = all_values[idx]
        if len(row) < 6:  # Almeno 6 colonne attese
            continue

        # Salta se già inviata
        if skip_sent and sent_col_idx is not None and sent_col_idx < len(row):
            sent_value = row[sent_col_idx].strip().lower()
            if sent_value in ["sì", "si", "yes", "y", "1", "true"]:
                continue

        email = row[0].strip() if len(row) > 0 else ""
        if not email or "@" not in email:
            continue

        recipient = RecipientData(
            email=email,
            phone=row[1].strip() if len(row) > 1 else "",
            website=row[2].strip() if len(row) > 2 else "",
            keyword=row[3].strip() if len(row) > 3 else "",
            nome_proprietario=row[4].strip() if len(row) > 4 else "",
            location=row[5].strip() if len(row) > 5 else "",
            row_number=idx + 1,  # 1-based per l'utente
        )

        # Aggiungi colonne extra come extra_data
        if len(row) > 6:
            for i, header in enumerate(headers[6:], start=6):
                if i < len(row) and header:
                    recipient.extra_data[header] = row[i]

        recipients.append(recipient)

    return recipients


def load_template(template_path: str) -> Template:
    """Carica il template Jinja2 dal file."""
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template non trovato: {template_path}")

    # Usa FileSystemLoader per permettere include/extends
    template_dir = path.parent
    template_file = path.name
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    return env.get_template(template_file)


def render_email(template: Template, subject_template: str, recipient: RecipientData) -> Tuple[str, str]:
    """Renderizza il template con i dati del destinatario."""
    context = recipient.to_dict()
    body = template.render(**context)
    subject = subject_template.format(**context) if "{" in subject_template else subject_template
    return subject, body


def get_gmail_credentials() -> Tuple[str, str]:
    """Ottiene le credenziali Gmail da args o env."""
    email = os.getenv("GMAIL_EMAIL")
    password = os.getenv("GMAIL_APP_PASSWORD")
    return email, password


def send_email(
    gmail_email: str,
    gmail_password: str,
    sender_name: str,
    recipient_email: str,
    subject: str,
    body: str,
    dry_run: bool = False,
) -> bool:
    """
    Invia un'email via Gmail SMTP.
    
    Nota: richiede App Password, non la password normale di Gmail.
    Per creare App Password: Google Account > Sicurezza > Verifica in due passaggi > Password app.
    """
    if dry_run:
        print(f"\n{'='*60}")
        print(f"DRY RUN - Email NON inviata")
        print(f"{'='*60}")
        print(f"A: {recipient_email}")
        print(f"Oggetto: {subject}")
        print(f"\nCorpo:\n{body}")
        print(f"{'='*60}\n")
        return True

    try:
        # Crea il messaggio
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{gmail_email}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Aggiungi il corpo (testo semplice)
        # Se il body contiene HTML, potresti voler usare MIMEText con 'html'
        is_html = "<html" in body.lower() or "<body" in body.lower() or "<p>" in body.lower()
        msg.attach(MIMEText(body, "html" if is_html else "plain", "utf-8"))

        # Invia via SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_email, gmail_password)
            server.send_message(msg)

        return True
    except smtplib.SMTPAuthenticationError:
        print(f"ERRORE: Autenticazione Gmail fallita. Verifica email e App Password.")
        return False
    except Exception as e:
        print(f"ERRORE nell'invio a {recipient_email}: {e}")
        return False


def mark_as_sent(ws, row_number: int, sent_column: str = "Inviata"):
    """Marca una riga come inviata nel Google Sheet."""
    try:
        headers = ws.row_values(1)
        if sent_column not in headers:
            # Aggiungi la colonna se non esiste
            col_letter = chr(ord("A") + len(headers))
            ws.update(f"{col_letter}1", [[sent_column]])
            headers.append(sent_column)

        col_idx = headers.index(sent_column)
        col_letter = chr(ord("A") + col_idx)
        ws.update(f"{col_letter}{row_number}", [["Sì"]])
    except Exception as e:
        print(f"Avviso: impossibile marcare riga {row_number} come inviata: {e}")


def main():
    """Funzione principale."""
    args = parse_args()

    # Carica credenziali Gmail
    gmail_email = args.gmail_email or os.getenv("GMAIL_EMAIL")
    gmail_password = args.gmail_password or os.getenv("GMAIL_APP_PASSWORD")

    if not args.dry_run and (not gmail_email or not gmail_password):
        raise ValueError(
            "Credenziali Gmail mancanti. Fornisci --gmail-email e --gmail-password "
            "o setta GMAIL_EMAIL e GMAIL_APP_PASSWORD come variabili d'ambiente."
        )

    # Carica template
    print(f"Caricamento template da: {args.template}")
    template = load_template(args.template)

    # Connetti a Google Sheets
    print(f"Connessione a Google Sheets (ID: {args.sheet_id})...")
    client = build_gspread_client(args.service_account, args.service_account_json)
    ws = get_worksheet(client, args.sheet_id, args.worksheet)

    # Carica destinatari
    print("Caricamento destinatari dal foglio...")
    recipients = load_recipients(
        ws,
        start_row=args.start_row,
        max_emails=args.max_emails,
        skip_sent=args.skip_sent,
        sent_column=args.mark_sent_column,
    )

    if not recipients:
        print("Nessun destinatario trovato.")
        return

    print(f"Trovati {len(recipients)} destinatari.")

    # Invia email
    success_count = 0
    error_count = 0

    for i, recipient in enumerate(recipients, 1):
        print(f"\n[{i}/{len(recipients)}] Elaborazione: {recipient.email}")

        try:
            # Renderizza template
            subject, body = render_email(template, args.subject, recipient)

            # Invia email
            success = send_email(
                gmail_email or "test@example.com",
                gmail_password or "dummy",
                args.sender_name,
                recipient.email,
                subject,
                body,
                dry_run=args.dry_run,
            )

            if success:
                success_count += 1
                if not args.dry_run and args.mark_sent_column:
                    mark_as_sent(ws, recipient.row_number, args.mark_sent_column)
                print(f"✓ Email inviata con successo a {recipient.email}")
            else:
                error_count += 1
                print(f"✗ Errore nell'invio a {recipient.email}")

        except Exception as e:
            error_count += 1
            print(f"✗ Errore nell'elaborazione di {recipient.email}: {e}")

        # Delay tra email
        if i < len(recipients) and args.delay > 0:
            time.sleep(args.delay)

    # Riepilogo
    print(f"\n{'='*60}")
    print(f"RIEPILOGO")
    print(f"{'='*60}")
    print(f"Email inviate con successo: {success_count}")
    print(f"Errori: {error_count}")
    print(f"Totale: {len(recipients)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

