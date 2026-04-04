# Dokumentation

Dieser Ordner enthaelt die Projekt-Dokumentation getrennt vom ausfuehrbaren Code.

## Struktur

- `manual/` -> Handbuchdateien und Manpages
- `operations/` -> Betriebs- und Laufzeitdokumentation
- `refactor/` -> Refactor-Dokumente und Begleitunterlagen

## Aktueller Inhalt

- `manual/trading-bot.1` -> Manpage fuer das Projekt
- `operations/runtime-data.md` -> Datenpfade, Migration und CI-Verhalten
- `refactor/Refactor_Dokumentation.pdf` -> Refactor-Dokumentation als PDF
- `refactor/Refactor_Dokumentation.docx` -> Refactor-Dokumentation als DOCX

## Manpage-Installation

Fuer einen direkten Aufruf ueber `man trading-bot` kann die Manpage mit
`bash ./install_manpage.sh` in einen passenden `man1`-Ordner aus dem
aktuellen `MANPATH` installiert werden.
