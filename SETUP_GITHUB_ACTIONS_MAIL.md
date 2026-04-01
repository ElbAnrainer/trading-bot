cat > SETUP_GITHUB_ACTIONS_MAIL.md <<'EOF'
# Setup: GitHub Actions Mail Versand

## Ziel
Automatischer Versand des Trading Reports per E-Mail (Gmail API)

## Voraussetzungen
- Google Cloud Projekt
- Gmail API aktiviert
- OAuth Credentials erstellt
- token.json vorhanden

## GitHub Secrets
- GMAIL_CLIENT_ID
- GMAIL_CLIENT_SECRET
- GMAIL_REFRESH_TOKEN

## Workflow
- GitHub Action startet täglich
- erzeugt Report
- versendet Mail mit PDF

## Hinweis
Keine Passwörter verwenden → nur OAuth Tokens!
EOF
