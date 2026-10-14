# Befunde zum Korpus — BSI-Standard 200-3

**Stand: 08.09.2026** · Korpus: `standard_200_3.pdf` (54 Seiten, 110.732 Zeichen extrahiert) --> viel Text

Dieses Dokument hält fest, was beim ersten Blick in die Daten herauskam — **bevor** die
Retrieval-Pipeline gebaut wurde. Jeder Befund steht mit Symptom, Messung, Ursache, Lösungswegen
und der getroffenen Entscheidung.

**Warum es das gibt:** Wer die Qualität seines Retrievals verstehen will, muss zuerst wissen,
was überhaupt in den Daten steht. Fast jede spätere Fehlersuche endet hier — beim Einlesen.

---

# Befund 1 — Es gibt keine Absätze, nur Seiten

## Symptom

Der erste Zerlegungsversuch trennte den Text an Leerzeilen:

```python
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n\n"

stuecke = text.split("\n\n")
print(len(stuecke))          # 55
```

Ergebnis: **55 Stücke bei 54 Seiten.** Eine Zahl, die verdächtig genau zur Seitenzahl passt.

> **Faustregel:** Wenn eine gemessene Zahl auffällig glatt zu einer anderen passt, misst man
> meist die falsche Sache.

## Messung

```
Seiten:                   54
Zeichen gesamt:      110.732
Einfache Umbrüche \n:  1.809
Leerzeilen \n\n:           0     <- null, im gesamten Dokument
```

## Ursache

**Im extrahierten Text kommt `\n\n` kein einziges Mal vor.** Der einzige Trenner war der, den
das Skript selbst zwischen die Seiten setzte (`+ "\n\n"`). Das Programm hat also nicht Absätze
gezählt, sondern **Seiten** — plus ein leeres Stück am Ende, weil der Text mit dem Trenner
aufhört und `split` dahinter noch ein leeres Element erzeugt. Daher 55 statt 54.

Der tiefere Grund: **PDF kennt keine Absätze.** Ein PDF beschreibt, an welcher Koordinate
welches Zeichen mit welchem Font steht — es ist ein Druckformat, kein Textformat. Beim
Extrahieren entstehen Zeilenumbrüche dort, wo im Layout eine Zeile endet (1.809 Stück).
Ob zwei Zeilen zum selben Gedanken gehören, steht nirgends. **Diese Struktur muss man selbst
herstellen.**

## Warum das für RAG die wichtigste Entscheidung ist

Ein Retrieval-System arbeitet in fünf Schritten: **laden → zerteilen → einbetten → suchen →
antworten.** Schritt 2 wirkt harmlos, entscheidet aber über die Qualität aller folgenden.

### Ein Vektor ist ein Durchschnitt

Beim Einbetten wird ein Textstück in eine Liste von Zahlen verwandelt (hier: 768 Zahlen bei
`nomic-embed-text`). Diese Zahlen beschreiben, **wovon der Text handelt** — als eine Richtung
im Raum. Ähnliche Texte zeigen in ähnliche Richtungen; das misst später die
Kosinus-Ähnlichkeit.

Entscheidend: Der Vektor beschreibt das **ganze** Stück, das man hineingibt. Er ist eine Art
Durchschnitt über dessen Inhalt.

| Was eingebettet wird | Was der Vektor aussagt |
|---|---|
| Ein Absatz über Schutzbedarfsfeststellung | „Hier geht es um Schutzbedarf" — klare Richtung |
| Eine ganze Seite mit vier Themen | ein Mittelwert aus vier Richtungen — zeigt nirgendwo hin |
| Das ganze Dokument | ein Brei, der zu jeder Frage mittelmäßig passt |

**Zu große Stücke verwässern.** Eine Seite mit 2.000 Zeichen enthält typischerweise eine
Überschrift, einen Definitionsabsatz, ein Beispiel und einen Verweis. Ihr Vektor ist der
Kompromiss aus allem — und ein Kompromiss gewinnt keinen Ähnlichkeitsvergleich gegen einen
Absatz, der genau die gestellte Frage behandelt.

**Zu kleine Stücke verlieren Zusammenhang.** Schneidet man in 100-Zeichen-Schnipsel, steht in
einem Stück *„…dies gilt nicht für Systeme mit erhöhtem Schutzbedarf."* — ohne dass irgendwo
steht, worauf sich „dies" bezieht. Der Vektor ist scharf, aber der Inhalt unbrauchbar.

**Die Größe ist ein Handel**, keine richtige Antwort. Übliche Ausgangsgröße für Fachtexte:
**600–1.000 Zeichen**. Das entspricht grob einem gedanklichen Absatz.

### Warum Überlappung existiert

Ein harter Schnitt trifft irgendwann mitten in einen Zusammenhang:

```
Stück 12: "... Die Schutzbedarfsfeststellung erfolgt in drei Stufen. Die erste Stufe"
Stück 13: "umfasst die Erhebung der Geschäftsprozesse ..."
```

Die Frage *„Was umfasst die erste Stufe?"* findet keines von beiden gut — die Antwort liegt
auf der Naht. **Überlappung** löst das: Jedes Stück wiederholt die letzten ~100 Zeichen des
vorigen. Das kostet Speicher und erzeugt doppelte Treffer, rettet aber die Nahtstellen.

### Das Zahlenbeispiel für dieses Dokument

Bei 110.732 Zeichen:

| Stückgröße | Anzahl Stücke | Bewertung |
|---|---|---|
| 2.000 (ganze Seiten, aktueller Stand) | ~55 | zu grob — Vektoren verwässert |
| **800** | **~138** | brauchbarer Ausgangspunkt |
| 800 mit 100 Überlappung | ~158 | Nahtstellen abgesichert |
| 100 | ~1.107 | zu fein — Zusammenhang verloren |

## Gegenprobe: ein Zeichen weniger, ein völlig anderes Ergebnis

Beim Ausprobieren wurde der selbstgesetzte Seitentrenner von `"\n\n"` auf `"\n"` geändert —
bei unverändertem `split("\n\n")`. Ergebnis: **3 Stücke statt 55.**

Nachgemessen: Ohne die 54 selbstgesetzten Trenner bleiben nur die Stellen übrig, an denen
`\n\n` zufällig entsteht — wo ein Seitentext bereits auf einem Umbruch endet und der Trenner
direkt anschließt.

```
Fundstellen von \n\n:  Position 9, 10, 3112
```

Position 9 und 10 liegen unmittelbar nebeneinander (dort stehen drei Umbrüche hintereinander;
`split` trennt an so einer Stelle nur einmal). Bleiben **zwei Schnitte → drei Stücke.**

Die Stelle bei 3112 ist inhaltlich aufschlussreich:

```
' . . . . . . . . . . . . . 54\n \n3 \n\n1 \n1 Ein'
```

Das ist der Übergang vom **Inhaltsverzeichnis zum ersten Kapitel**. Eines von drei Stücken
wäre demnach das gesamte Inhaltsverzeichnis gewesen — ein Textblock aus Punktreihen und
Seitenzahlen, dessen Vektor keinerlei inhaltliche Aussage trägt.

**Die Lehre:** Ein einziges Zeichen Unterschied ändert das Ergebnis um den Faktor 18. Wer an
Zeichen trennt, die er im Dokument *vermutet*, hängt vom Zufall des Layouts ab. Ein Schnitt
nach fester Zeichenzahl liefert dagegen ein vorhersagbares Ergebnis: 110.732 ÷ 800 ergibt
immer ~138 Stücke, unabhängig davon, wie das PDF gesetzt wurde. **Das ist der Hauptgrund für
Weg A.**

---

## Lösungswege

| Weg | Wie | Handel |
|---|---|---|
| **A — nach Zeichenzahl** | alle ~800 Zeichen schneiden, mit `range(0, len(text), 800)` | einfachster Code; **vorhersagbares Ergebnis**; zerschneidet Sätze mitten im Wort |
| **B — nach Sätzen** | an `". "` trennen, dann zu ~800 Zeichen bündeln | saubere Grenzen; scheitert an Abkürzungen wie „z. B." und „Abs. 3" |
| **C — mit Überlappung** | wie A, aber Schrittweite 700 bei Stückgröße 800 | Nahtstellen bleiben erhalten; ~15 % mehr Vektoren |
| **D — Layout-Blöcke aus dem PDF** | `PyMuPDF`: `seite.get_text("blocks")` | nutzt die echte Absatzstruktur des Layouts; erfordert ein zweites Werkzeug |

**Zu Weg D:** PyMuPDF (`fitz`, bereits installiert) liefert pro Seite die Textblöcke, die im
Layout tatsächlich zusammengehören — auf Seite 12 zum Beispiel **4 Blöcke** statt einer
undifferenzierten Textwand. Das ist die inhaltlich sauberste Zerlegung, weil sie nicht rät,
sondern die Struktur des Dokuments benutzt.

## Gegenprobe 2: Warum erst kleben und dann schneiden?

Beim Bauen kam die Frage auf, warum nicht jede Seite einzeln bereinigt und gleich zerteilt
wird — das spart den Umweg über den zusammengeklebten Text. Gemessen:

| | **A — kleben, dann schneiden** | **B — seitenweise schneiden** |
|---|---|---|
| Stücke | **138** | 162 |
| davon unter 200 Zeichen | **0** | **12** |
| kürzestes Stück | **519 Zeichen** | **10 Zeichen** |
| Durchschnitt | 797 | 679 |

**Seitenweises Schneiden erzeugt an jeder Seitengrenze einen Rest.** Hat eine Seite 2.100
Zeichen, ergibt das zwei volle Stücke und einen Rest von 500 — bei 54 Seiten fallen 54 solcher
Reste an, zwölf davon unter 200 Zeichen, der kürzeste mit 10 Zeichen.

Solche Fragmente sind schädlich, nicht bloß nutzlos: Sie bekommen einen Vektor, belegen Platz
im Index und können eine Suche sogar gewinnen, weil ein sehr kurzer Text zufällig nah an einer
kurzen Frage liegen kann. Dazu 17 % mehr Embedding-Aufrufe für ein schlechteres Ergebnis.

**Die allgemeine Regel:** *Erst zusammenführen, dann bereinigen, dann aufteilen.* Bereinigen
und Aufteilen wirken auf den ganzen Text; wer vorher zerlegt, arbeitet isoliert in jedem Stück,
und alles, was über eine Grenze läuft — Silbentrennung, Sätze, Tabellen — bleibt kaputt.

### Was diese Reihenfolge kostet

**Die Seitenzahl geht verloren.** Nach dem Zusammenkleben lässt sich nicht mehr sagen, aus
welcher Seite ein Stück stammt. Für die **Zitatpflicht** (Groundedness) wird das gebraucht:
Eine Antwort aus einem Sicherheitsdokument ohne überprüfbare Fundstelle ist wertlos.

**Lösung ist nicht Variante B**, sondern eine dritte: beim Zusammenkleben mitschreiben, an
welcher Zeichenposition jede Seite beginnt. Damit lässt sich zu jeder Textstelle die Seitenzahl
zurückrechnen. Rund fünf Zeilen — als nächster Schritt vorgemerkt, sobald die Suche läuft.

---

## Entscheidung

**Weg A zuerst** — Zerteilen nach Zeichenzahl, ~800 Zeichen, ohne Überlappung.

Begründung: Er ist in wenigen Zeilen selbst geschrieben und macht den Mechanismus sichtbar.
Wege C und D sind besser, aber ihr Vorteil ist eine **Behauptung**, solange er nicht gemessen
ist. Sobald eine Eval-Suite mit `Recall@k` existiert (geplant in P4), wird A gegen C und D
gemessen — dann steht im README eine Zahl statt einer Meinung.

**Das ist die Reihenfolge, die dieses Projekt durchgehend verfolgt: erst das Einfachste bauen,
dann mit Messwerten verbessern.**

---

# Befund 2 — Einzelne Zeichen sind beim Extrahieren zerstört

## Symptom

Seite 12, wörtlich extrahiert:

```
'2 Vorarbeiten zur Risikoanalyse\n \nFfr die Installation, Inbetriebnahme, den Betrieb,
 die Wartung und Konfiguration des SMGW ist \nder Smart-Meter-Gateway-Administrator
 (SMGW-Admin) verantwortlich. Da es sich hierbei teil\xad\nweise um sensible
 Informationen handelt, ...'
```

Zwei Auffälligkeiten: **`Ffr`** statt „Für", und **`teil\xad\nweise`** — ein unsichtbares
Zeichen mitten im Wort „teilweise".

## Messung

Der erste Eindruck aus diesem Ausschnitt war, die Umlaute seien generell zerstört. **Die
Messung widerlegt das:**

```
Echte Umlaute im extrahierten Text
   ä : 648      ö : 175      ü : 438
   Ä :   4      Ö :   0      Ü :  14      ß : 183

Verstümmelte Stellen (Wortliste, nicht überlappend gezählt)
   'ffr'  : 17x
   'Ffr'  :  5x
   '(ffr' :  2x
                 zusammen 24 Stellen bei 110.732 Zeichen  =  0,02 %

Betroffene Seiten: 11, 12, 17, 18, 21, 22, 26, 28, 35, 40   (10 von 54)

Weiche Trennstriche (U+00AD)
   362x, davon 359 direkt gefolgt von einem Zeilenumbruch
```

**Korrektur der ersten Einschätzung:** Das Encoding ist **nicht** flächendeckend defekt. Rund
1.460 Umlaute kommen korrekt an.

**Zweite Korrektur — die Zahl 48 war falsch.** Sie entstand durch überlappendes Zählen: das
Muster `"fr "` steckt bereits in `"ffr "`. Eine Wortliste ergibt **24 echte Stellen**. Und alle
24 sind **dasselbe Wort: „für"** — kein einziger Fall steckt in einem längeren Wort.

**Der eigentlich relevante Fund sind die 362 weichen Trennstriche.**

## Ursache

**`Ffr` statt „Für":** Ein PDF speichert keine Buchstaben, sondern Zeichennummern eines Fonts.
Welche Nummer welchem Buchstaben entspricht, steht in einer Tabelle im Font (dem
CID-/ToUnicode-Mapping). Ist diese Tabelle unvollständig oder fehlerhaft eingebettet, rät der
Extraktor — und liefert das falsche Zeichen. Das passiert im Dokument selbst, **nicht** im
auslesenden Programm.

**`\xad` (weicher Trennstrich):** Ein unsichtbares Steuerzeichen, das dem Textsatz erlaubt,
ein Wort am Zeilenende zu trennen. Im Druck sieht man einen Bindestrich, in den Daten steht
`teil\xad\nweise`. Für ein Programm sind das die Bruchstücke `teil` und `weise` — das Wort
„teilweise" existiert nicht mehr.

## Werkzeugvergleich

Naheliegender Gedanke: ein anderer Extraktor macht es besser. **Gemessen — er tut es nicht.**

| | pypdf 6.14.2 | PyMuPDF (fitz) |
|---|---|---|
| Zeichen gesamt | 110.732 | 111.107 |
| Leerzeilen `\n\n` | 0 | 0 |
| `Ffr` | 5x | **5x** |
| `ffr` | 19x | **19x** |
| weiche Trennstriche | 362 | **362** |
| Absatz-/Layout-Blöcke | nein | **ja** (`get_text("blocks")`) |

**Beide Werkzeuge liefern identisch beschädigte Zeichen.** Das bestätigt: Die Ursache liegt im
PDF. Ein Werkzeugwechsel behebt Befund 2 nicht — er hilft nur bei Befund 1, wegen der
Layout-Blöcke.

## Warum das Retrieval darunter leidet

Ein Embedding-Modell vergleicht Zeichenfolgen, kein Verständnis. Für das Modell sind
`"Für"` und `"Ffr"` zwei verschiedene Wörter, ebenso `"teilweise"` und `"teil" + "weise"`.

Konkret: Eine Frage nach *„teilweise sensible Informationen"* findet die betroffene Stelle
schlechter, weil im indexierten Text an dieser Stelle etwas anderes steht als in der Frage.
Bei einem deutschen Fachdokument mit vielen Komposita und entsprechend häufiger Silbentrennung
ist das kein Randfall.

## Lösungswege

| Problem | Weg | Bewertung |
|---|---|---|
| **Weiche Trennstriche** (362x) | `text.replace("\xad\n", "").replace("\xad", "")` | **einfach und wirksam** — setzt 359 getrennte Wörter wieder zusammen. Reihenfolge beachten: erst die Variante mit Umbruch, sonst bleibt `teil\nweise` stehen |
| **Verstümmelte Zeichen** (24x) | `text.replace("ffr", "für").replace("Ffr", "Für")` | **risikolos** — `ffr` ist im Deutschen keine gültige Buchstabenfolge, und die Wortliste zeigt: alle 24 Fälle sind das Wort „für" |
| **Verstümmelte Zeichen** | OCR über die Seitenbilder | löst auch unentdeckte Fälle, ist aber ein eigenes Teilprojekt |
| **Kontrolle** | vor dem Einbetten zählen, wie viele Stücke `\xad` enthalten | billig; verhindert, dass der Fehler unbemerkt in den Index wandert |

## Entscheidung

1. **Weiche Trennstriche werden entfernt**, bevor zerteilt wird — direkt nach dem
   Zusammenkleben der Seiten. Grund für diese Position: Trennstriche laufen über Zeilen- und
   Seitengrenzen; wer erst zerteilt, lässt die Stellen an den Schnittkanten kaputt.
2. **Die 24 „für"-Stellen werden ebenfalls repariert.** *(Geändert gegenüber der ersten
   Fassung dieses Dokuments: Dort stand „nicht lohnend", gestützt auf die falsche Zahl 48 und
   die Annahme, eine Ersetzung sei fragil. Die Wortliste zeigt das Gegenteil — ein einziges
   betroffenes Wort, kein Treffer innerhalb längerer Wörter.)*
3. **Ein Restrisiko bleibt und gehört ins README:** Der Fontfehler betrifft 10 von 54 Seiten.
   Andere Wörter können ebenfalls verstümmelt sein, ohne aufzufallen — nämlich dann, wenn das
   Ergebnis zufällig wie ein gültiges Wort aussieht. Repariert wird, was erkennbar ist.
4. **Vor dem Einbetten wird gezählt**, wie viele Stücke noch Steuerzeichen enthalten — als
   Kontrollwert.

### Schreibweise im Code

`\xad` als **Escape-Sequenz** schreiben, nicht das Zeichen selbst einfügen. Es ist unsichtbar —
kopiert man es direkt, steht im Editor scheinbar ein leerer String zwischen den
Anführungszeichen, und niemand kann die Zeile später lesen.

---

# Befund 3 — `nomic-embed-text` braucht Präfixe

## Symptom

Erster Test der Ähnlichkeitsrechnung mit drei Vergleichstexten gegen die Frage
*„Wie schütze ich sensible Daten?"* — **die Rangfolge war falsch:**

```
0.629  PASST         "Die Schutzbedarfsfeststellung ermittelt, welche Werte ..."
0.635  passt nicht   "Wie beantrage ich Urlaub fuer naechste Woche?"     <- hoeher!
0.931  Wortsalat     "Daten Daten Daten schuetze schuetze sensible"
```

Eine Suche nach Datenschutz hätte den Urlaubsantrag zurückgegeben.

## Ursache

`nomic-embed-text` wurde mit **Aufgaben-Präfixen** trainiert. Das Modell behandelt Fragen und
Dokumente unterschiedlich und erwartet, dass ihm gesagt wird, was es gerade vor sich hat.
Ohne Präfix fehlt diese Information, und die Vektoren werden von der **Satzform** dominiert —
beide Testfragen beginnen mit „Wie … ich …?".

## Messung mit Präfixen

```
                              ohne      mit
PASST         Schutzbedarf    0.629    0.598     <- jetzt oben
passt nicht   Urlaub          0.635    0.581
Wortsalat                     0.931    0.845
```

**Die Rangfolge zwischen passendem und unpassendem Text dreht sich um.**

## Entscheidung

Vor jedem Text wird ein Präfix gesetzt:

| Was | Präfix |
|---|---|
| Textstücke aus dem Korpus | `"search_document: "` |
| Die Suchanfrage | `"search_query: "` |

Nicht in der `embed`-Funktion selbst, sondern beim Aufruf — die Präfixe unterscheiden sich je
nach Verwendung, und die Funktion soll modellneutral bleiben.

## Was auch mit Präfixen nicht funktioniert

**Wortwiederholung schlägt weiterhin durch.** Der reine Wortsalat aus den Frage-Wörtern erhält
0.845 und gewinnt gegen den inhaltlich passenden Text. Embeddings messen Bedeutung **und**
Wortüberlappung, nicht Bedeutung allein. In echten Dokumenten tritt dieser Extremfall nicht
auf, die Grenze ist aber real.

**Der Abstand zwischen richtig (0.598) und falsch (0.581) beträgt nur 0.017.** Das ist der
Grund, warum ernsthafte Retrieval-Systeme ein **Reranking** nachschalten: ein zweites Modell,
das die besten Kandidaten der Vektorsuche nochmals genauer sortiert. Vorgemerkt für P2/P4,
sobald die Grundsuche misst.

**Verneinung wird kaum erkannt:** *„Der Schutz ist zwingend erforderlich"* und *„… ist nicht
erforderlich"* erreichen 0.934 Ähnlichkeit — gegenteilige Aussagen, fast identischer Vektor.
Für ein Sicherheitsdokument mit vielen Muss-/Kann-Bestimmungen ist das eine ernstzunehmende
Einschränkung und gehört ins README.

---

# Befund 4 — Einbetten dauert 6 Minuten pro Durchlauf

## Messung

```
138 Stuecke:      349,8 s   =  5 min 50 s
pro Stueck:       2,5 s
erster Aufruf:    2,8 s     (Modell wird geladen)
```

Gemessen auf der Entwicklungsmaschine (7,8 GB RAM, keine GPU) mit `nomic-embed-text` über
Ollama, 800-Zeichen-Stücke.

## Folge

Bei jedem Programmstart werden dieselben Vektoren neu berechnet, obwohl sich weder Korpus noch
Modell geändert haben. Das macht Entwickeln unbrauchbar — jeder Test kostet sechs Minuten.

## Entscheidung

1. **Während der Entwicklung** mit `stuecke[:20]` arbeiten (~50 s).
2. **Danach** die Vektoren einmal berechnen und in einer Datei ablegen; beim Start laden statt
   neu rechnen.

## Einordnung

Genau diese Aufgabe übernimmt eine **Vektordatenbank**: Vektoren dauerhaft speichern und
schnell durchsuchen. Der Bedarf ist hier aus einer eigenen Messung entstanden, nicht aus einer
Tutorial-Empfehlung — 2,5 Sekunden pro Stück auf CPU sind der konkrete Grund.

Mit GPU läge die Zeit im Millisekundenbereich; auf dem Hetzner-Server (Track G) später zu prüfen.

---

# Befund 5 — Das Generierungsmodell ist zu klein für den Guardrail

## Symptom

Frage *„was sind schutzmassnahmen"*. Das Retrieval lieferte **drei passende Treffer**
(0.660 / 0.642 / 0.630) — alle drei über Angemessenheit, Prüfkriterien und ein konkretes
Maßnahmenbeispiel. Die Antwort des Modells lautete trotzdem:

```
Das steht nicht im Dokument.
```

**Der Fehler saß nicht im Retrieval, sondern in der Generierung.**

## Eingrenzung

Drei Hypothesen, einzeln geprüft mit `qwen2.5:3b`, Temperatur 0:

| # | Hypothese | Test | Ergebnis |
|---|---|---|---|
| 1 | Prompt zu streng formuliert | lockerere Fassung („auch Teilaspekte zählen") | **widerlegt** — identische Ablehnung |
| 2 | Frage passt nicht zum Kontext | Frage gestellt, deren Antwort wörtlich im Kontext steht | **widerlegt** — ebenfalls abgelehnt |
| 3 | Modell zu klein | siehe unten | **bestätigt** |

## Der entscheidende Test

Frage: *„Nenne ein Beispiel für eine ergänzende Maßnahme."*
Im Kontext steht wörtlich: *„…wird ein Rollen- und Rechtekonzept umgesetzt und dokumentiert,
das den Grundsätzen einer Funktionstrennung genügt."*

```
MIT Guardrail-Satz:    "Das steht nicht im Dokument."          <- Falsch-Negativ
OHNE Guardrail-Satz:   "...koennte eine Verwaltungsstruktur     <- Halluzination
                        sein, die eine klare Abgrenzung der
                        Rollen ermoeglicht..."
```

`qwen2.5:3b` kennt nur zwei Zustände: **alles ablehnen** oder **frei erfinden**. Die Mitte —
*nimm, was dasteht, und nur das* — trifft es nicht.

## Gegenprobe mit größeren Modellen

Identischer Prompt, identischer Kontext, über Groq:

| Modell | Größe | Antwort |
|---|---|---|
| `qwen2.5:3b` (lokal) | 3 Mrd | „Das steht nicht im Dokument." |
| `openai/gpt-oss-20b` | 20 Mrd | **korrekt, wörtlich aus dem Text** |
| `openai/gpt-oss-120b` | 120 Mrd | **korrekt, wörtlich aus dem Text** |

*(`qwen/qwen3.8-27b` lief in ein Groq-Ratenlimit — nicht getestet.)*

**Die Fähigkeitsgrenze liegt zwischen 3 und 20 Milliarden Parametern.** Schon das kleinere
Cloud-Modell löst die Aufgabe.

## Einordnung

Das ist der Kompromiss aus dem Guardrail-Lernblatt, an eigenen Daten gemessen:

| | |
|---|---|
| **Guardrail an** bei zu kleinem Modell | hohe **Falsch-Negativ-Rate** — richtige Antworten werden verweigert |
| **Guardrail aus** | Halluzination — das Modell geht über den Beleg hinaus |

Ein Guardrail ist keine reine Prompt-Frage. **Er setzt ein Modell voraus, das der Anweisung
folgen kann.** Wird das übersehen, wirkt das System vorsichtig und ist in Wahrheit unbrauchbar.

## Entscheidung

1. **Lokal bleibt `qwen2.5:3b`** für die Entwicklung — kostenlos, keine Daten verlassen den
   Rechner.
2. **Für Qualitätsmessungen** wird der Generierungsschritt gegen ein größeres Modell getestet.
   Groq ist dafür gesetzt (Schlüssel vorhanden, kostenloses Kontingent).
3. **Datenschutz-Vorbehalt:** BSI 200-3 ist öffentlich, der Cloud-Test daher unkritisch.
   Sobald ein Korpus vertrauliche Kundendokumente enthält, ist der Cloud-Weg **gesperrt** —
   dann entweder lokal mit größerem Modell (mehr RAM nötig) oder auf eigener Infrastruktur
   (Hetzner, Track G). Das gehört ins Bedrohungsmodell.
4. **In der Eval-Suite (P4)** wird Modellgröße gegen Antwortqualität systematisch gemessen —
   dieser Befund ist die erste Datenreihe dafür.

---

# Befund 6 — Die Encoding-Reparatur aus Befund 2 war unvollständig

## Symptom

Beim Gegentest zur Frage *„Was ist ein Schutzbedarf?"* stand mitten im zweitbesten Treffer:

```
Auch diejenigen IT-Grundschutz-Anforderungen, die im IT-Grundschutz-Kompendium
als Anforderungen bei erhöhtem Schutzbedarf aufgeffhrt sind ...
                                              ^^^^^^^^^
```

`aufgeffhrt` statt `aufgeführt`. Befund 2 hatte nur das Muster `ffr` → `für` behandelt und
war damit **nicht vollständig** — die Reparatur greift zu kurz, nicht falsch.

## Messung

Alle Vorkommen von `ff` gefolgt von einem Konsonanten, im Rohtext nach der
Trennstrich-Reparatur:

| Muster | Fälle | Beispiele | Bewertung |
|---|---|---|---|
| `ffr` → `für` | 19 | *(in Befund 2 bereits behandelt)* | kaputt |
| `ffh` → `füh` | 6 | `durchgeffhrt`, `ffhren`, `aufgeffhrt`, `weiterffhrende`, `Durchffhrung` | kaputt |
| `ffg` → `füg` | 5 | `Verffgung`, `Verffgbarkeit`, `verffgen` | kaputt |
| `ffl` → `fül` | 1 | `Erffllung` | kaputt |
| `ffs` | 3 | `Zugriffsberechtigungen`, `Angriffspunkte` | **korrekt** |
| `fft` | 2 | `betrifft`, `beschafft` | **korrekt** |

**31 kaputte Vorkommen, 5 korrekte.** Eine pauschale `ff`-Regel hätte die fünf korrekten
Wörter zerstört — deshalb nur die vier belegten Muster.

## Der Fehler tritt sporadisch auf

Das ist die eigentliche Überraschung. Dasselbe Wort steht im Dokument mal heil, mal kaputt:

| Wort | korrekt im Rohtext | beschädigt |
|---|---|---|
| Verfügbarkeit | 32× | 2× |
| durchgeführt | 15× | 2× |

Es ist also **kein durchgängiger Font-Fehler**, sondern hängt an einzelnen Textstellen —
vermutlich an bestimmten Absätzen, die mit einer anderen Font-Einbettung gesetzt wurden.
Das erklärt auch, warum Befund 2 den Schaden mit 0,02 % als gering einstufte: gemessen an
allen Zeichen stimmt das, gemessen an *einzelnen Suchbegriffen* nicht.

## Warum das für das Retrieval teuer ist

`Verffgbarkeit` ist der teuerste der 31 Fälle. **Verfügbarkeit ist einer der drei
BSI-Grundwerte** (neben Vertraulichkeit und Integrität) — ein zentraler Suchbegriff im
gesamten Themenfeld. Zwei Textstellen dazu waren für jede Anfrage unauffindbar, weil ein
Embedding Zeichenfolgen vergleicht: `Verffgbarkeit` und `Verfügbarkeit` sind für das Modell
zwei verschiedene Wörter.

## Gegenprobe: Zerstört die Reparatur etwas?

Zwei Wörter standen zunächst unter Verdacht, weil sie in der Messung ohne Umlaut auftauchten:
`ffentlich` und `ckgegriffen`. Beide im Kontext geprüft:

```
'banwendung öffentlich bekann'      -> korrekt, "öffentlich"
'kumente zurückgegriffen we'        -> korrekt, "zurückgegriffen"
```

**Falschalarm** — mein Suchmuster `[A-Za-z]*ff[A-Za-z]*` schneidet an Umlauten ab, weil `ö`
und `ü` nicht in `A-Za-z` enthalten sind. Der Fehler lag im Messwerkzeug, nicht im Text.

Nach der Reparatur:

| Prüfung | Ergebnis |
|---|---|
| Übrige `ff`-Wörter | nur noch korrekte (`Begriffe`, `getroffen`, `Zugriff`, …) |
| `Verfügbarkeit` | 32 → **34** |
| `durchgeführt` | 15 → **17** |
| `Zugriffsberechtigungen`, `betrifft` | unverändert — nicht angefasst |
| Zeichenzahl | 110 119 → 110 119 (**Differenz 0**) |
| Stückzahl | 138 → 138 |

Die Zeichenzahl bleibt gleich, weil jedes Muster genau drei Zeichen gegen drei Zeichen
tauscht (`ffr` → `für`). Deshalb verschieben sich die Stückgrenzen nicht und alle früheren
Messungen bleiben vergleichbar.

## Lösungswege

1. **Vier gezielte Ersetzungen** — belegt, risikolos, drei Zeilen Code. *(gewählt)*
2. **Rechtschreibprüfung über den Gesamttext** — findet auch unbekannte Muster, bringt aber
   eine Abhängigkeit und neue Fehlerquellen (Fachbegriffe, Abkürzungen).
3. **Anderes Extraktionswerkzeug** — in Befund 2 bereits ausgeschlossen: PyMuPDF liefert
   dieselben beschädigten Zeichen, der Fehler steckt in der PDF-Datei.
4. **OCR statt Textextraktion** — überdimensioniert für 31 Stellen.

## Entscheidung

Weg 1, als Schleife über eine Musterliste statt als verkettete `replace`-Aufrufe — die Liste
zeigt auf einen Blick, welche Muster behandelt werden und welche bewusst nicht:

```python
for kaputt, heil in [("ffr", "für"), ("Ffr", "Für"),
                     ("ffh", "füh"), ("ffg", "füg"), ("ffl", "fül")]:
    text = text.replace(kaputt, heil)
```

## Methodische Lehre

Befund 2 war nicht falsch, sondern **zu eng gefragt**. Gesucht wurde nach `"ffr"`, gefunden
wurde `"ffr"` — die Frage bestimmte die Antwort. Erst die offene Frage *„welche `ff`-Muster
gibt es überhaupt?"* zeigte drei weitere.

**Bei Datenqualität nicht nach dem bekannten Fehler suchen, sondern nach der Fehlerklasse.**
Und den Fund im Kontext gegenprüfen — zwei von sechzehn Verdachtsfällen waren ein Artefakt
meines eigenen Suchmusters.

---

# Befund 7 — Die Ähnlichkeitswerte trennen relevant und irrelevant nicht

## Symptom

Zwei Fragen an denselben Index, eine passend zum Dokument, eine völlig fremd:

| Frage | Platz 1 | Platz 2 | Platz 3 |
|---|---|---|---|
| „Was ist ein Schutzbedarf?" (passend) | **0.686** | 0.684 | 0.660 |
| „Wie beantrage ich urlaub?" (fremd) | **0.663** | 0.641 | 0.626 |

Die passende Frage gewinnt — aber nur um **0.023**.

## Der entscheidende Vergleich

```
Platz 3 der PASSENDEN Frage:   0.660
Platz 1 der FREMDEN Frage:     0.663   <- hoeher
```

Ein Textstück, das nichts mit dem Thema zu tun hat, erreicht bei einer dokumentfremden Frage
einen **höheren** Wert als ein Treffer, den die passende Frage auf Platz 3 gebracht hat.

## Ursache

Ein Kosinuswert misst **Ähnlichkeit im Vektorraum**, nicht **Relevanz für die Frage**. Alle
138 Stücke stammen aus einem einzigen deutschen Fachtext zu einem einzigen Thema — sie
liegen im Raum ohnehin dicht beieinander. Der Wertebereich, in dem sich überhaupt etwas
abspielt, ist deshalb schmal: gemessen liegt alles zwischen etwa 0.62 und 0.69.

`nomic-embed-text` ist auf *semantische Nähe* trainiert, nicht darauf zu beurteilen, ob ein
Absatz eine Frage **beantwortet**. Das ist keine Fehlfunktion, sondern die Aufgabe, für die
das Modell gebaut wurde.

## Folge: ein fester Schwellenwert funktioniert nicht

Die naheliegende Idee — *„unter 0.65 gar nicht erst antworten"* — scheitert an diesen Zahlen:

| Schwelle | Wirkung |
|---|---|
| 0.67 | wirft Platz 2 und 3 der **richtigen** Frage weg |
| 0.65 | lässt Platz 1 der **falschen** Frage durch |
| dazwischen | existiert nicht |

Absolute Schwellen sind für dieses Retrieval damit unbrauchbar. Was bleibt, ist der
**relative** Abstand innerhalb einer Anfrage — der Abstand zwischen Platz 1 und Platz 10
sagt mehr als der Absolutwert von Platz 1.

## Nachmessung: drei Schreibweisen derselben Frage

Nach der Encoding-Reparatur aus Befund 6 wurde gezielt nach `Verfügbarkeit` gefragt — einem
der drei BSI-Grundwerte, dessen Textstellen vorher als `Verffgbarkeit` unauffindbar waren.
Drei Formulierungen, derselbe Index:

| Eingabe | Platz 1 | Platz 2 | Platz 3 | Treffer mit dem Wort im Text |
|---|---|---|---|---|
| `Verfügbarkeit` (nur das Wort) | **0.686** | 0.684 | 0.673 | **2 von 3** |
| `Was bedeutet Verfügbarkeit?` | 0.658 | 0.647 | 0.643 | 1 von 3 |
| `Was bedeutet Verfuegbarkeit?` (Tippfehler) | 0.665 | 0.656 | 0.651 | 1 von 3 |
| *(Vergleich)* `Wie beantrage ich urlaub?` | 0.663 | 0.641 | 0.626 | — |

### Erkenntnis 1: Frageworte verwässern den Vektor

Das nackte Wort erreicht **0.686**, derselbe Begriff in einen Satz verpackt nur **0.658** —
ein Verlust von 0.028, mehr als der gesamte Abstand zur dokumentfremden Urlaubsfrage.

Die Ursache ist dieselbe wie beim Chunking (Befund 1): **ein Vektor ist der Durchschnitt über
seinen Text.** „Was bedeutet … ?" trägt nichts zum Thema bei, zieht den Durchschnitt aber in
Richtung Allgemeinsprache. Je mehr inhaltsleere Wörter in der Frage stehen, desto unschärfer
der Suchvektor.

Auch die Trefferqualität folgt dem: beim nackten Wort enthalten **zwei von drei** Treffern
`Verfügbarkeit` wörtlich, beim Satz nur einer.

### Erkenntnis 2: Absolutwerte sind zwischen Fragen nicht vergleichbar

Das ist die schärfere Fassung dieses Befundes:

```
Was bedeutet Verfügbarkeit?   0.658   <- korrekte Fachfrage zum Kernbegriff
Wie beantrage ich urlaub?     0.663   <- Thema kommt im Dokument nicht vor
```

**Die dokumentfremde Frage erreicht den höheren Wert.** Nicht weil sie besser passt, sondern
weil ihr Vektor zufällig günstiger im Raum liegt.

Damit ist präzisiert, was oben allgemein formuliert war: Die Rangfolge **innerhalb** einer
Anfrage ist brauchbar — der Kosinus sortiert die 138 Stücke sinnvoll. **Zwischen** zwei
Anfragen sagt der Absolutwert nichts. Jede Frage hat ihr eigenes Niveau.

Genau deshalb funktioniert kein globaler Schwellenwert: Er würde Werte vergleichen, die aus
verschiedenen Anfragen stammen und nicht auf derselben Skala liegen.

### Erkenntnis 3: Der Tippfehler-Test fällt aus dem Rahmen

`Verfuegbarkeit` statt `Verfügbarkeit` liefert **höhere** Werte (0.665 gegen 0.658) bei
**schlechteren** Treffern — Platz 1 handelt von elementaren Gefährdungen und enthält den
Begriff überhaupt nicht.

Ein Embedding scheitert an der Umlautschreibung nicht (die Rangfolge bleibt grob brauchbar),
aber der höhere Zahlenwert bei schlechterem Inhalt ist der direkteste Beleg dieses Befundes:
**Der Wert misst nicht, was er zu messen scheint.**

### Folgerungen

1. **Frage vor dem Einbetten kürzen** wäre ein billiger Gewinn — aber nicht pauschal:
   bei „Wer ist verantwortlich für die Risikoanalyse?" trägt „wer ist verantwortlich"
   Bedeutung. Gehört als Variante in die Eval-Suite (P4), nicht als Bauchentscheidung
   in den Code.
2. **Hybride Suche (BM25 daneben)** gewinnt an Gewicht: Bei `Verfügbarkeit` würde reine
   Wortübereinstimmung die Stellen, die den Begriff enthalten, sofort nach oben ziehen —
   genau die, die der Kosinus auf Platz 2 und 3 schiebt.
3. **Die Reparatur aus Befund 6 hat gewirkt:** Die Stücke mit `Verfügbarkeit` erscheinen
   überhaupt erst jetzt in den Trefferlisten. Vorher waren sie als `Verffgbarkeit` für
   jede Anfrage unsichtbar.

## Zweiter Befund aus demselben Lauf: die Frage passt nicht zum Korpus

Keiner der drei Treffer **definiert** Schutzbedarf, sie erwähnen ihn nur. Nachgemessen:

| Suche im Dokument | Vorkommen |
|---|---|
| „Schutzbedarf" | 21× |
| „Schutzbedarfsfeststellung" | 3× |
| Verweis auf „200-2" | 11× |

**BSI 200-3 ist die Risikoanalyse.** Die Schutzbedarfsfeststellung wird in **BSI 200-2**
beschrieben; 200-3 setzt sie voraus und verweist elfmal darauf. Die Definition steht also
tatsächlich nicht im Korpus.

`Das steht nicht im Dokument.` war hier **die richtige Antwort** — der umgekehrte Fall zu
Befund 5, wo dieselbe Ausgabe ein Fehler war.

## Abgrenzung zu Befund 5

| | Befund 5 | Befund 7 |
|---|---|---|
| Frage | „was sind schutzmaßnahmen" | „Was ist ein Schutzbedarf?" |
| Antwort im Kontext? | **ja, wörtlich** | **nein** |
| Ausgabe | „Das steht nicht im Dokument." | „Das steht nicht im Dokument." |
| Fehler sitzt in | Generierung (Modell zu klein) | Korpus (Thema fehlt) |

**Dieselbe Ausgabe, zwei völlig verschiedene Ursachen.** Unterscheiden lassen sie sich nur,
weil die drei Treffer mit angezeigt werden. Ohne dieses Diagnosefenster wäre Befund 7 als
weiterer Modellfehler fehlgedeutet worden — und die Zeit ins falsche Problem geflossen.

## Lösungswege

1. **Reranker** — ein zweites Modell bewertet nur die besten 20 Treffer, diesmal auf die
   Frage bezogen (Cross-Encoder). Erzeugt einen breiten, aussagekräftigen Wertebereich.
   Der übliche Weg; kostet einen zweiten Modellaufruf.
2. **Hybride Suche** — Kosinus mit BM25 (Wortübereinstimmung) kombinieren. Fängt genau die
   Fälle, in denen der Fachbegriff wörtlich vorkommt.
3. **Relativer statt absoluter Schwellenwert** — nur Treffer behalten, die nahe am besten
   Treffer liegen. Billig, aber schwach: bei einer fremden Frage sind auch die schlechten
   Treffer untereinander ähnlich.
4. **Korpus erweitern** — BSI 200-2 aufnehmen, damit Fragen zur Schutzbedarfsfeststellung
   überhaupt beantwortbar werden.

## Entscheidung

1. **Kein Schwellenwert im aktuellen Stand.** Die Zahlen tragen ihn nicht; ein erfundener
   Grenzwert würde Qualität vortäuschen.
2. **Reranking ist der nächste substanzielle Schritt** (Weg 1) — aber erst, nachdem die
   Eval-Suite (P4) steht. Sonst ist die Verbesserung nicht messbar, sondern nur gefühlt.
3. **BSI 200-2 kommt in den Korpus** (Weg 4), zusammen mit den übrigen geplanten Dokumenten.
   Vorher dieselben Encoding-Messungen wie in Befund 2 und 6 durchführen.
4. **Die Trefferanzeige bleibt dauerhaft im Code.** Sie ist kein Debug-Rest, sondern das
   Werkzeug, das Korpus-, Such- und Modellfehler auseinanderhält.

## Methodische Lehre

Ein bestandener Test ist noch kein guter Test. Die Prüfung *„passende Frage schlägt fremde
Frage"* war bestanden — und hätte allein als Bestätigung getaugt. Erst der Blick auf den
**Abstand** statt nur auf die Reihenfolge zeigte, dass die Trennschärfe fehlt.

**Nicht fragen, ob die Zahl in die richtige Richtung zeigt, sondern wie weit.**

---

# Offene Punkte

- [ ] **Reranker einbauen** (Befund 7) — nach der Eval-Suite, damit die Wirkung messbar ist
- [ ] **BSI 200-2 in den Korpus** (Befund 7) — enthält die Schutzbedarfsfeststellung, auf die
      200-3 elfmal verweist; vorher Encoding-Messung wie in Befund 2 und 6
- [ ] Prüfen, ob die 31 beschädigten `ff`-Stellen (Befund 6) auf bestimmten Seiten geballt
      auftreten — dann wäre eine einzelne Font-Einbettung die Ursache
- [ ] Stückgröße messen statt schätzen — sobald `Recall@k` aus der Eval-Suite (P4) vorliegt,
      Weg A gegen C und D antreten lassen
- [x] ~~Weiche Trennstriche entfernen und die Stückzahl erneut messen~~ — erledigt, 138 Stücke
- [ ] **Seitenzahl je Stück zurückgewinnen** — beim Zusammenkleben die Startposition jeder
      Seite mitschreiben, damit zu jedem Stück eine Fundstelle genannt werden kann
      (Voraussetzung für die Zitatpflicht)
- [ ] Weitere Korpus-Dokumente (BSI/ANSSI Zero Trust, NIST AI 600-1) mit denselben Messungen
      prüfen — bevor sie in den Index kommen

---

# Methodische Lehre

*(Diese Lehre stammt aus Befund 1 und 2; die späteren Befunde tragen ihre eigene am Ende.)*

Beide Befunde kamen zustande, weil eine **Zahl auf Plausibilität geprüft** wurde statt
akzeptiert: 55 Stücke bei 54 Seiten. Ohne diese Prüfung wäre die Pipeline mit
seitengroßen, teilweise beschädigten Stücken gebaut worden — und die schlechte Trefferqualität
wäre später beim Modell oder bei der Vektordatenbank gesucht worden, wo sie nicht liegt.

**Beim Debuggen einer RAG-Pipeline zuerst anschauen, was tatsächlich im Index steht.**
Nicht das Modell, nicht die Datenbank, nicht den Prompt.
