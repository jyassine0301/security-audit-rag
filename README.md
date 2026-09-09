# RAG über den BSI-Standard 200-3 — ohne Framework

Eine Retrieval-Augmented-Generation-Pipeline in 136 Zeilen Python, gebaut ohne LangChain,
ohne LlamaIndex, ohne Vektordatenbank. Jeder Schritt von Hand, damit jeder Schritt messbar
und begründbar ist.

**Korpus:** BSI-Standard 200-3 — Risikoanalyse auf Basis von IT-Grundschutz
(54 Seiten, öffentlich verfügbar beim Bundesamt für Sicherheit in der Informationstechnik)

---

## Worum es hier eigentlich geht

Der Code ist der kleinere Teil. Der eigentliche Inhalt steht in
**[BEFUNDE.md](BEFUNDE.md)** — sieben Probleme, die beim Bauen auftraten, jedes mit
Messung, Ursachenanalyse, verworfenen Alternativen und einer begründeten Entscheidung.

Ein Auszug:

| # | Befund | Die Zahl dahinter |
|---|---|---|
| 1 | Das PDF enthält **keine Absätze**, nur Seiten | `\n\n` kommt **0×** im extrahierten Text vor |
| 2 | Die Textextraktion zerstört Zeichen | 359 zerrissene Wörter; pypdf und PyMuPDF liefern identischen Schaden |
| 3 | `nomic-embed-text` braucht Präfixe | ohne sie **kehrt sich die Rangfolge um** |
| 4 | Einbetten ist der Flaschenhals | 350 s für 138 Stücke = 2,5 s pro Stück |
| 5 | Das Generierungsmodell war zu klein | 3B lehnt ab, wo der Text die Antwort wörtlich enthält; 20B antwortet korrekt |
| 6 | Die Reparatur aus Befund 2 war unvollständig | 31 beschädigte Stellen statt der angenommenen 19 |
| 7 | **Die Ähnlichkeitswerte trennen nicht** | korrekte Fachfrage **0.658** — dokumentfremde Frage **0.663** |

Befund 7 ist der wichtigste: Ein Kosinuswert misst Ähnlichkeit im Vektorraum, nicht
Relevanz für die Frage. Die Rangfolge *innerhalb* einer Anfrage ist brauchbar — *zwischen*
zwei Anfragen sagt der Absolutwert nichts. Damit ist jeder globale Schwellenwert unbrauchbar.

---

## Die Pipeline

```
PDF laden          pypdf, 54 Seiten
   |
reparieren         359 weiche Trennstriche, 31 kaputte Umlaute  (Befund 2, 6)
   |
zerteilen          138 Stücke à 800 Zeichen                     (Befund 1)
   |
einbetten          nomic-embed-text -> 768 Merkmale je Stück    (Befund 3, 4)
   |
vergleichen        Kosinus-Ähnlichkeit, von Hand gerechnet
   |
sortieren          beste 3 Treffer
   |
generieren         qwen2.5:3b mit Guardrail-Prompt              (Befund 5)
```

Reparieren **vor** dem Zerteilen, und alle Seiten **vor** dem Reparieren zusammenkleben —
beides begründet in Befund 1 (Gegenprobe 2).

---

## Ausführen

Voraussetzung: [Ollama](https://ollama.com) läuft lokal.

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
pip install pypdf requests

python suche.py
```

Der Pfad zum PDF steht am Anfang von [`suche.py`](suche.py) und muss angepasst werden.

Der Start dauert **rund 6 Minuten** — alle 138 Stücke werden einmal eingebettet (Befund 4).
Danach beantwortet eine Schleife beliebig viele Fragen ohne Neustart.

```
Frage (Enter zum Beenden): Was ist ein Schutzbedarf?

0.686  llten vorrangig solche Gefährdungen gesucht werden, die diesen Grundwert ...
0.684  Auch diejenigen IT-Grundschutz-Anforderungen, die im IT-Grundschutz-Kompendium ...
0.660  Gefährdungen identifiziert werden, aus denen Risiken resultieren ...

Das steht nicht im Dokument.
```

Die drei Treffer werden bewusst mit angezeigt. Sie sind das Diagnosefenster: Ohne sie lässt
sich nicht unterscheiden, ob ein schlechtes Ergebnis aus dem **Korpus**, der **Suche** oder
der **Generierung** kommt — genau diese Unterscheidung trennt Befund 5 von Befund 7.

---

## Was hier bewusst fehlt

| Fehlt | Warum |
|---|---|
| Vektordatenbank | 138 Vektoren im Arbeitsspeicher; eine Datenbank würde verdecken, was ein Index tut |
| Framework | ebenso — der Kosinus ist von Hand geschrieben, damit er verstanden ist |
| Reranker | der nächste Schritt (Befund 7), aber erst nach der Eval-Suite: sonst ist die Verbesserung nicht messbar |
| Zwischenspeicher für die Vektoren | bekannt, dokumentiert in Befund 4 |
| Seitenzahl je Fundstelle | offener Punkt — Voraussetzung für Zitierbarkeit |

---

## Nächste Schritte

- Eval-Suite mit `Recall@k`, damit Verbesserungen gemessen statt gefühlt werden
- Hybride Suche (BM25 neben dem Kosinus) — Befund 7 zeigt, wo rein semantische Suche versagt
- BSI 200-2 in den Korpus: 200-3 verweist **11×** darauf, die Schutzbedarfsfeststellung
  steht dort
- Fundstellen mit Seitenzahl

---

## Hintergrund

Teil eines Lernpfads Richtung AI Engineering. Der Anspruch ist nicht, ein Tutorial
nachzubauen, sondern jede Entscheidung an eigenen Messungen zu begründen — auch dort, wo
die Messung die ursprüngliche Annahme widerlegt. Mehrere Befunde in
[BEFUNDE.md](BEFUNDE.md) dokumentieren genau solche Fälle.
