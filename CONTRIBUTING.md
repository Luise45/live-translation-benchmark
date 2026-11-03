# Contributing

Dieses Dokument beschreibt den gemeinsamen Git- und GitHub-Workflow für das Projekt.

## Grundregeln

- nicht direkt auf `main` entwickeln oder pushen
- Änderungen werden in einem eigenen Branch umgesetzt
- Änderungen werden über einen Pull Request in `main` gemerged
- für ein Jira-Ticket/Subtask wird grundsätzlich ein eigener Branch verwendet
- unabhängige Funktionen oder Aufgaben sollen nicht im selben Branch vermischt werden
- für kleine Fehlerbehebungen: `fix/`-Branch ohne Jira-Ticket 
- API Keys, Tokens, Passwörter und `.env`-Dateien dürfen niemals committed werden

## Branch-Namen

für Jira-Tickets und Subtasks:

`<type>/<JIRA-ID>-<kurze-beschreibung>`

mögliche Branch-Typen:

- `feature/` für neue Funktionen
- `fix/` für Fehlerbehebungen
- `docs/` für Dokumentation
- `test/` für Tests
- `refactor/` für Änderungen am bestehenden Code ohne neue Funktion

Beispiele:

- `feature/XY-116-candidate-interface`
- `feature/XY-93-error-handling`
- `docs/XY-110-sprint-2-docs`
- `fix/XY-125-rate-limit`

für kleine Fixes ohne eigenes Jira-Ticket kurzen Fix-Branch verwenden:

`fix/<kurze-beschreibung>`

Beispiele:

- `fix/readme-link`
- `fix/import-error`

Branch-Namen sollen kurz und eindeutig sein.

für Branch-Namen möglichst nur:
- Buchstaben
- Zahlen
- `-`
- `/`

keine Leerzeichen, Umlaute oder unnötigen Sonderzeichen verwenden

## Neuen Branch erstellen

vor Beginn einer neuen Aufgabe zuerst prüfen, ob lokale Änderungen vorhanden sind:

```bash
git status
```

wenn der working tree sauber ist, auf `main` wechseln:

```bash
git switch main
```

den aktuellen Stand des remote Repos abrufen:

```bash
git fetch origin
```

anschließend neuesten Stand von `main`holen:

```bash
git pull --ff-only origin main
```

jetzt den neuen Branch vom aktuellen Stand von `main` erstellen:

```bash
git switch -c feature/XY-123-kurze-beschreibung
```

Beispiel:

```bash
git switch -c feature/XY-116-candidate-interface
```

## Änderungen committen

Änderungen prüfen:

```bash
git status
```

Datei hinzufügen:

```bash
git add <datei>
```

alle Änderungen hinzufügen:

```bash
git add .
```

Vor dem Commit erneut mit `git status` prüfen, ob wirklich nur die gewünschten Dateien enthalten sind.

Commit erstellen:

```bash
git commit -m "add candidate interface"
```

## Branch zum ersten Mal pushen

beim ersten Push eines neuen Branches:

```bash
git push -u origin feature/XY-116-candidate-interface
```

bei weiteren Änderungen auf demselben Branch reicht:

```bash
git push
```

## Pull Request erstellen

Wenn die Änderung fertig und bereit für ein Review ist, wird auf GitHub ein Pull Request erstellt.

- Base Branch: `main`
- Head Branch: der eigene Feature-, Fix-, Docs-, Test- oder Refactor-Branch

PR-Titel bei Jira-Tickets:

`[XY-116] Implement candidate interface`

für Fixes ohne Jira-Ticket zum Beispiel:

`[FIX] Correct import error`

im Pull Request sollte kurz beschrieben werden:
- was geändert wurde
- warum die Änderung notwendig ist
- wie die Änderung getestet wurde

## Vor dem Pull Request prüfen

vor Erstellung bzw. spätestens vor dem Merge eines Pull Requests:

- Code lokal ausführen
- relevante Tests ausführen
- `git status` prüfen
- prüfen, ob nur Dateien der aktuellen Aufgabe verändert wurden
- prüfen, dass keine Secrets committed wurden
- vorhandene verpflichtende CI-Checks müssen erfolgreich sein

## Wenn sich `main` während der Entwicklung geändert hat

wenn andere Pull Requests bereits in `main` gemerged wurden und der eigene Branch aktualisiert werden muss:

```bash
git fetch origin
git merge origin/main
```

Falls Merge-Konflikte auftreten, müssen diese gelöst werden. Danach:
```bash
git add .
git commit
git push
```

## Merge

Änderungen werden ausschließlich über einen Pull Request in `main` gemerged.
Nicht direkt auf `main` pushen.

vor dem Merge müssen:

- notwendige Reviews abgeschlossen sein
- notwendige Änderungen umgesetzt sein
- Merge-Konflikte gelöst sein
- verpflichtende CI-Checks erfolgreich sein

## Branch nach dem Merge löschen

Ein Feature-, Fix-, Docs-, Test- oder Refactor-Branch kann nach erfolgreichem Merge gelöscht werden.

Für spätere Änderungen oder Fehlerbehebungen wird ein neuer Branch vom aktuellen Stand von `main` erstellt.

Beispiel:
```bash
git switch main
git fetch origin
git pull --ff-only origin main
git switch -c fix/XY-140-candidate-timeout
```

## Secrets und Umgebungsvariablen

Secrets dürfen niemals in Git committed werden.

dazu gehören insbesondere:
- API Keys
- Tokens
- Passwörter
- Credentials
- private Zugangsdaten
- `.env`

lokale Secrets gehören in:

`.env`

## Kurzablauf

1. `main` aktualisieren
2. neuen Branch für das Jira-Ticket erstellen
3. Änderung implementieren
4. Änderungen prüfen
5. Commit mit Jira-ID erstellen
6. Branch pushen
7. Pull Request erstellen
8. Review durchführen lassen
9. gegebenenfalls Review-Änderungen im selben Branch umsetzen
10. CI-Checks prüfen
11. Pull Request in `main` mergen
12. Branch nach erfolgreichem Merge löschen
13. für weitere Änderungen wieder einen neuen Branch vom aktuellen `main` erstellen