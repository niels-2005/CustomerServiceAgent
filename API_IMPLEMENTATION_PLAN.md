# API Implementation Plan

## Ziel

Diese Datei beschreibt, wie die aktuelle API unter `src/customer_bot/api` schrittweise in Richtung einer produktionsnäheren Customer-Support-API entwickelt werden sollte.

Der Fokus liegt bewusst nicht auf "alles sofort enterprise-ready machen", sondern auf einer sinnvollen Reihenfolge:

1. Die API stabil und kontrollierbar machen.
2. Missbrauch und riskante Eingaben abfangen.
3. Antworten des LLM absichern.
4. Betrieb, Telemetrie und spätere Erweiterungen vorbereiten.

Die aktuelle API ist noch sehr schlank:
- `GET /health`
- `POST /chat`
- keine Authentisierung
- keine Middleware-Schicht für Schutzmechanismen
- keine explizite Guardrail-Pipeline vor oder nach dem Agenten
- nur einfache Request-Validierung über Pydantic

Deshalb ist dieser Plan in konkrete Todos gegliedert, die nacheinander abgearbeitet werden können.

## Grundprinzipien

- Kleine, explizite Schritte statt großer Sicherheits-Refactors.
- Guardrails nicht nur im Prompt, sondern als eigene Anwendungsschicht.
- Nutzerfreundliche Soft-Blocks statt aggressiver Hard-Blocks in der ersten Ausbaustufe.
- Klare Trennung zwischen `answered`, `no_match`, `blocked`, `handoff` und `error`.
- Alles, was Verhalten oder Betrieb verändert, soll über Settings konfigurierbar sein.

## Priorisierung

### Phase 1: Unmittelbar sinnvoll

- Request-ID und strukturierte Fehler
- fail-fast Startup-Checks im `lifespan`
- Request-Grenzen und Timeouts
- CORS/Trusted Host Basisschutz
- Rate Limiting
- Input-Guardrails
- Output-Guardrails
- Outcome- und Safety-Telemetrie

### Phase 2: Produktreife

- Grounding-/Evidence-Checks
- strukturierter Handoff
- feinere Konfiguration der Guardrails
- bessere Session-Lifecycle-Regeln

### Phase 3: Später bei echter öffentlicher Exponierung

- Captcha oder Bot-Mitigation
- feinere Quotas
- Redaction für produktive Speicherung
- Admin-/Ops-Auswertung für Guardrail-Ereignisse

## Schritt-für-Schritt Todos

### - [x] Todo 1: Request-ID und strukturierte Fehler einführen

**Was ist das?**

Jeder Request bekommt eine eindeutige ID. Fehlerantworten sollen nicht nur generische HTTP-Fehler sein, sondern ein stabiles JSON-Format mit Fehlercode, Nachricht und Request-ID haben.

**Warum ist das nötig?**

Ohne Request-ID lassen sich Logs, Langfuse-Traces und Nutzerfehler schwer korrelieren. Ohne strukturiertes Fehlerformat sind Debugging, Monitoring und spätere Frontend-Integration unnötig fragil.

**Was sollte konkret umgesetzt werden?**

- Middleware für `request_id` einführen.
- `X-Request-ID` im Response-Header zurückgeben.
- Zentrales Fehlerformat definieren, zum Beispiel:
  - `error.code`
  - `error.message`
  - `request_id`
- Eigene Exception-Typen für bekannte API-Fehler vorbereiten.
- Standardfehler für 400, 429, 500 und Guardrail-Fälle vereinheitlichen.

**Akzeptanzkriterien**

- Jeder Request hat eine eindeutige Request-ID.
- Fehlerantworten haben ein stabiles JSON-Schema.
- Request-ID erscheint in Logs und Responses konsistent.

### - [x] Todo 2: Kritische Startup-Checks im `lifespan` einführen

**Was ist das?**

Kritische Voraussetzungen für den API-Betrieb sollen bereits beim Start geprüft werden. Wenn diese Prüfungen fehlschlagen, startet der Service nicht erfolgreich. `/health` bleibt danach bewusst simpel und liefert nur dann `ok`, wenn die App überhaupt sauber hochgekommen ist.

**Warum ist das nötig?**

Für eure aktuelle kleine API bringt ein zusätzlicher `/ready`-Endpoint wenig Mehrwert, wenn die wirklich wichtigen Fehler ohnehin schon beim Start erkannt werden können. Ein fail-fast Startup-Verhalten ist hier einfacher, klarer und robuster als getrennte Liveness-/Readiness-Semantik.

**Was sollte konkret umgesetzt werden?**

- Kritische Initialisierung in den `lifespan` verlagern oder dort zentralisieren.
- Beim Startup nur deterministische und leichtgewichtige Checks ausführen:
  - Settings geladen
  - Kernservices initialisierbar
  - optional Retriever/Vector-Backend erreichbar
  - optional Observability-Grundzustand verfügbar
- Keine echten LLM-Smoke-Tests oder Sample-Fragen beim Startup ausführen.
- Wenn kritische Checks fehlschlagen, soll die App fail-fast nicht erfolgreich starten.
- `/health` als einfachen Endpoint behalten, der nach erfolgreichem Start `200 {"status":"ok"}` liefert.
- Einen separaten `/ready` erst dann ergänzen, wenn sich `process alive` und `service ready` in der Praxis wirklich trennen.

**Akzeptanzkriterien**

- Die App startet nicht erfolgreich, wenn kritische Voraussetzungen fehlen.
- `/health` bleibt schnell und simpel.
- Es gibt keine langsamen oder nicht-deterministischen Startup-Checks über echte Modellanfragen.

### - [x] Todo 3: Eingabegrenzen und API-Basis-Schutz ergänzen

**Was ist das?**

Die API soll definierte Grenzen für Eingaben und HTTP-Zugriff haben, damit sie nicht durch triviale Fehl- oder Missbrauchsfälle unnötig belastet wird.

**Warum ist das nötig?**

Anonyme Chat-APIs werden schnell mit sehr langen Inputs, Spam oder ungeeigneten Browser-Origin-Konfigurationen konfrontiert. Ohne Basisschutz entstehen unnötige Kosten, Latenzprobleme und instabile Fehlerbilder.

**Was sollte konkret umgesetzt werden?**

- Maximale Länge für `user_message` definieren.
- Maximale Länge für `session_id` definieren.
- Ggf. maximale Request-Body-Größe ergänzen.
- Request-Timeouts auf API-Ebene definieren.
- CORS explizit konfigurieren, nicht offen lassen.
- Trusted Host Middleware für spätere öffentliche Exponierung vorbereiten.
- Optional einfache Security Headers ergänzen.

**Akzeptanzkriterien**

- Zu große oder ungültige Requests werden sauber mit 4xx abgelehnt.
- CORS ist explizit konfiguriert.
- Timeouts sind definiert und dokumentiert.

### - [x] Todo 4: Rate Limiting einführen

**Was ist das?**

Rate Limiting begrenzt, wie viele Requests ein Client in einem Zeitraum an die API senden darf.

**Warum ist das nötig?**

Für einen anonymen Website-Chat ist Rate Limiting einer der wichtigsten praktischen Standards. Es schützt vor Spam, versehentlicher Überlastung, Skriptmissbrauch und unnötigen Modellkosten.

**Was sollte konkret umgesetzt werden?**

- Limiting zunächst per IP-Adresse umsetzen.
- Optional zusätzlich per `session_id`, wenn sinnvoll.
- Einfache, konservative Standardgrenzen definieren.
- Bei Überschreitung `429 Too Many Requests` mit strukturiertem Fehlerformat zurückgeben.
- Ereignisse im Logging und Tracing markieren.

**Akzeptanzkriterien**

- Wiederholte Requests überschreiten deterministisch das Limit.
- API liefert saubere 429-Antworten.
- Rate-Limit-Ereignisse sind beobachtbar.

### Todo 5: Input-Guardrail-Pipeline vor dem Agenten einbauen

**Was ist das?**

Vor dem Aufruf von `ChatService` bzw. `AgentService` wird eine Sicherheits- und Qualitätsprüfung für die Nutzereingabe ausgeführt.

**Warum ist das nötig?**

Der wichtigste Schutzpunkt liegt vor dem LLM. Wenn problematische Eingaben ungefiltert in den Agenten gehen, kann es zu Prompt-Injection, Jailbreaks, Missbrauch von Tools oder unnötiger Modelllast kommen.

**Was sollte konkret umgesetzt werden?**

- Eigenen Vorverarbeitungsschritt für Chat-Requests einführen.
- Prüfen auf:
  - Prompt Injection
  - Jailbreak-Muster
  - offensichtlichen Tool-Missbrauch
  - Spam oder Abuse-Signale
  - extrem ungewöhnliche oder zerstückelte Eingaben
- Erstmal Soft-Block statt Hard-Block:
  - Anfrage markieren
  - sicheren Antworttext zurückgeben
  - Ereignis loggen und tracen
- Ergebnis als strukturierte Guardrail-Entscheidung modellieren.

**Akzeptanzkriterien**

- Verdächtige Eingaben erreichen den Agenten nicht mehr ungefiltert.
- Soft-Block-Fälle sind sauber vom technischen Fehler getrennt.
- Guardrail-Entscheidungen sind testbar und beobachtbar.

### Todo 6: Toxicity- und Abuse-Screening für Input pragmatisch ergänzen

**Was ist das?**

Zusätzlich zur Prompt-Injection-Erkennung soll die API grobe Beleidigungs-, Missbrauchs- oder Eskalationsmuster erkennen können.

**Warum ist das nötig?**

Nicht jede problematische Eingabe ist eine Injection. In der Praxis gibt es auch Beschimpfungen, Spam, Provokationen oder missbräuchliche Tests, die Produktverhalten, Monitoring und spätere UX-Entscheidungen beeinflussen.

**Was sollte konkret umgesetzt werden?**

- Einfache Klassifikation für `toxic`, `abusive`, `spam_like` oder `safe`.
- In v1 keine überkomplexe Policy-Engine bauen.
- Soft-Block oder Warnmarkierung abhängig vom Schweregrad.
- Die Erkennung muss konfigurierbar sein, damit False Positives später kalibriert werden können.

**Akzeptanzkriterien**

- Offensichtliche abusive Inputs werden markiert.
- Die API bleibt bei legitimen Anfragen möglichst tolerant.
- Klassifikation ist im Trace sichtbar.

### Todo 7: PII auf Input-Seite für Logging und Telemetrie berücksichtigen

**Was ist das?**

PII-Checks sollen erkennen, ob Nutzer potenziell personenbezogene oder sensible Daten eingeben.

**Warum ist das nötig?**

Für euer Portfolio-Projekt ist PII nicht zwingend ein Blocker. Trotzdem ist es sinnvoll, dieses Thema früh mitzudenken, damit spätere öffentliche Nutzung nicht in unkontrolliertes Logging persönlicher Daten kippt.

**Was sollte konkret umgesetzt werden?**

- PII-Detection zunächst als Flagging- oder Logging-Thema behandeln.
- Noch keine harte Blockierung erzwingen.
- Optional markieren:
  - E-Mail
  - Telefonnummer
  - Adressen
  - IDs oder Kontonummern, falls relevant
- Später erweiterbar auf Redaction vor Log-/Trace-Speicherung.

**Akzeptanzkriterien**

- PII-Hinweise können erkannt und im Trace markiert werden.
- Nutzeranfragen werden dadurch in v1 nicht unnötig geblockt.
- Der Mechanismus ist für spätere Redaction erweiterbar.

### Todo 8: Output-Guardrails nach dem LLM einführen

**Was ist das?**

Nachdem der Agent eine Antwort generiert hat, wird diese Antwort vor der Auslieferung erneut geprüft.

**Warum ist das nötig?**

Ein sicheres Input-System reicht nicht aus. Das LLM kann trotzdem unpassende, leere, halluzinierte oder policy-widrige Antworten erzeugen. Gerade diese zweite Kontrollschicht ist in produktiven LLM-APIs sehr wichtig.

**Was sollte konkret umgesetzt werden?**

- Nachgelagerte Prüf-Schicht für Antworten einbauen.
- Prüfen auf:
  - leere oder kaputte Antworten
  - toxische oder beleidigende Formulierungen
  - policy-widrige Inhalte
  - Prompt-Leaks
  - Tool- oder Systemprompt-Leaks
- Bei Verstoß Antwort durch sicheren Fallback oder Handoff-Hinweis ersetzen.

**Akzeptanzkriterien**

- Riskante Antworten werden vor Auslieferung abgefangen.
- Output-Block und normaler Error-Fallback sind unterscheidbar.
- Die letzte ausgelieferte Antwort ist kontrolliert und nachvollziehbar.

### Todo 9: Grounding- und Evidence-Checks für Antworten ergänzen

**Was ist das?**

Die API soll prüfen, ob eine Antwort ausreichend auf FAQ-Treffern basiert oder ob sie zu spekulativ ist.

**Warum ist das nötig?**

Für diese Anwendung ist das einer der wichtigsten produktiven Standards. Eine höfliche, aber ungrounded Antwort ist fachlich oft gefährlicher als eine toxische Antwort, weil sie plausibel klingt und trotzdem falsch sein kann.

**Was sollte konkret umgesetzt werden?**

- Antwortmodus stärker an Retrieval-Ergebnis koppeln.
- Wenn keine ausreichende Grundlage vorliegt:
  - `no_match` oder `handoff` statt freie Antwort
- Optional interne Entscheidung anhand von:
  - Match-Anzahl
  - Ähnlichkeitsschwelle
  - Tool-Fehlern
  - Signal, ob der Agent sich außerhalb des Materials bewegt
- Kein kompliziertes Forschungsprojekt daraus machen; einfache explizite Regeln reichen für v1.

**Akzeptanzkriterien**

- Antworten ohne ausreichende Grundlage werden seltener ausgeliefert.
- `answered` und `no_match` lassen sich klar unterscheiden.
- FAQ-only-Verhalten wird robuster.

### Todo 10: Ergebnis-Typen und strukturierte Outcomes einführen

**Was ist das?**

Die API soll nicht nur einen Freitext zurückgeben, sondern auch den internen Antwortstatus explizit machen.

**Warum ist das nötig?**

Ohne Outcome-Typen vermischen sich echte Antworten, Blockierungen, No-Match-Fälle und technische Fallbacks. Das erschwert Frontend-Verhalten, Telemetrie und spätere Handoff-Logik.

**Was sollte konkret umgesetzt werden?**

- Response-Modell erweitern, zum Beispiel um `outcome`.
- Empfohlene Werte:
  - `answered`
  - `no_match`
  - `blocked`
  - `handoff`
  - `error`
- Interne Services ebenfalls auf diese Unterscheidung ausrichten.

**Akzeptanzkriterien**

- Frontend oder Tests können den API-Ausgang explizit interpretieren.
- Fallback-Fälle sind nicht mehr nur implizit im Antworttext versteckt.

### Todo 11: Handoff als expliziten Pfad vorbereiten

**Was ist das?**

Wenn der Bot nicht sicher antworten kann oder bewusst nicht antworten sollte, soll er kontrolliert an einen menschlichen Supportpfad verweisen können.

**Warum ist das nötig?**

Ein produktiver Bot braucht einen sauberen Ausstiegsweg. Ohne Handoff endet jeder schwierige Fall in einem unklaren Text, obwohl das Produkt eigentlich sagen sollte: "Hier endet die Bot-Zuständigkeit."

**Was sollte konkret umgesetzt werden?**

- Handoff zunächst als Outcome und Antwortmodus modellieren.
- Klare Trigger definieren:
  - wiederholter No-Match
  - policy block
  - zu wenig Evidenz
  - kritischer technischer Fehler
- In v1 reicht ein strukturierter Handoff-Hinweis.
- Später kann daran ein echtes Tool oder Ticketing-System angeschlossen werden.

**Akzeptanzkriterien**

- Handoff ist ein expliziter Ausgangszustand.
- Nutzer erhalten klare, kontrollierte Weiterleitungsantworten.
- Die spätere Tool-Integration bleibt möglich.

### Todo 12: Logging, Langfuse und Safety-Telemetrie ausbauen

**Was ist das?**

Guardrails und Outcomes sollen nicht nur wirken, sondern auch beobachtbar sein.

**Warum ist das nötig?**

Ohne Telemetrie kann man Guardrails nicht kalibrieren. Gerade bei Soft-Block-Strategien muss sichtbar sein, wie oft etwas greift, ob es zu streng ist und welche Arten von Problemen auftreten.

**Was sollte konkret umgesetzt werden?**

- Strukturierte Logs für:
  - request_id
  - session_id
  - outcome
  - guardrail_flags
  - fallback_reason
- Langfuse-Attribute oder Warnings für:
  - input_flagged
  - output_flagged
  - rate_limited
  - no_match
  - handoff_triggered
- Klare Benennung der Failure-Reasons einführen.

**Akzeptanzkriterien**

- Safety- und Outcome-Ereignisse sind in Logs und Traces sichtbar.
- Guardrails sind im Betrieb nachvollziehbar.
- Fehlersuche wird deutlich einfacher.

### Todo 13: Konfiguration für produktive API-Features explizit machen

**Was ist das?**

Alle neuen Verhaltensweisen sollen über `Settings`, `.env.example` und Dokumentation nachvollziehbar konfigurierbar sein.

**Warum ist das nötig?**

Versteckte Defaults sind bei LLM-Systemen besonders riskant. Guardrails, Rate Limits und Fallbacks müssen explizit einsehbar sein, sonst wird später unklar, welches Verhalten warum greift.

**Was sollte konkret umgesetzt werden?**

- Neue Settings für:
  - Rate Limits
  - Input-Guardrails an/aus
  - Output-Guardrails an/aus
  - Thresholds und Schweregrade
  - Handoff-Texte
  - CORS Origins
  - Timeouts
- `.env.example` und `README.md` synchron halten.

**Akzeptanzkriterien**

- Alle relevanten API-Schutzmechanismen sind konfigurierbar.
- Kein wichtiges Verhalten existiert nur implizit im Code.

### Todo 14: Session-Lifecycle für spätere echte Nutzung vorbereiten

**Was ist das?**

Die Session-Verwaltung soll nicht nur logisch isoliert sein, sondern auch für längere Laufzeiten kontrollierbar bleiben.

**Warum ist das nötig?**

Aktuell gibt es bereits isolierte Session-Historien. Für produktiveren Betrieb fehlen aber Strategien für Ablauf, Bereinigung und kontrollierte Speichernutzung.

**Was sollte konkret umgesetzt werden?**

- Session-TTL oder Cleanup-Strategie vorbereiten.
- Begrenzung der History ist bereits da, sollte aber als Betriebsverhalten dokumentiert werden.
- Später erweiterbar für persistente oder externe Session-Speicher.

**Akzeptanzkriterien**

- Session-Verhalten ist nicht nur fachlich, sondern auch betrieblich definiert.
- Langlaufende Nutzung führt nicht zu unkontrolliertem Wachstum.

### Todo 15: Tests für alle neuen API-Schutzschichten ergänzen

**Was ist das?**

Jede neue produktive Schutzfunktion braucht gezielte Tests.

**Warum ist das nötig?**

Guardrails ohne Tests regressieren schnell. Außerdem besteht bei Safety-Features immer die Gefahr, dass sie stillschweigend zu streng, zu locker oder technisch wirkungslos werden.

**Was sollte konkret umgesetzt werden?**

- Unit-Tests für:
  - Request-ID
  - Fehlerformat
  - Rate Limiting
  - Input-Guardrails
  - Output-Guardrails
  - Outcome-Modelle
- API-Tests für:
  - 429-Verhalten
  - Block-/Fallback-Verhalten
  - `answered` vs `no_match` vs `handoff`
- Regression-Tests für bestehendes Verhalten:
  - Session-Isolation
  - Error-Fallback
  - No-Match-Verhalten

**Akzeptanzkriterien**

- Neue Schutzmechanismen sind automatisch testbar.
- Bestehende Kerninvarianten bleiben erhalten.

## Was zusätzlich oft übersehen wird

Diese Punkte sind keine eigenen ersten Todos, sollten aber im Hinterkopf bleiben:

- **Kostenkontrolle:** Ohne Limits und Telemetrie kann eine kleine Chat-API schnell unnötig teuer werden.
- **Degradationsstrategie:** Wenn Guardrails oder Observability ausfallen, muss klar sein, ob die API offen oder konservativ weiterläuft.
- **Frontend-Vertrag:** Das Frontend sollte nicht nur Freitext bekommen, sondern auch maschinenlesbare Outcomes.
- **Dokumentation:** Jede neue Schutzschicht muss in `README.md` und `.env.example` nachvollziehbar beschrieben werden.
- **False Positives:** Ein Guardrail, der zu aggressiv blockt, ist produktseitig oft genauso schädlich wie ein fehlender Guardrail.

## Definition of Done für diese Ausbauphase

Die API ist für diese Phase ausreichend verbessert, wenn:

- Requests und Fehler sauber identifizierbar sind.
- Anonyme Nutzung durch Rate Limits und Basisschutz begrenzt ist.
- Riskante Inputs vor dem Agenten kontrolliert werden.
- Riskante Outputs vor der Auslieferung kontrolliert werden.
- No-Match, Block, Error und Handoff klar getrennt sind.
- Guardrail-Ereignisse in Logs und Langfuse sichtbar sind.
- Neue Konfiguration dokumentiert und testbar ist.
