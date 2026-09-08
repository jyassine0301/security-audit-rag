# Befunde zum Korpus — BSI-Standard 200-3

**Stand: 08.09.2026** · Korpus: `standard_200_3.pdf` (54 Seiten, 110.732 Zeichen extrahiert)

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

# Offene Punkte

- [ ] Stückgröße messen statt schätzen — sobald `Recall@k` aus der Eval-Suite (P4) vorliegt,
      Weg A gegen C und D antreten lassen
- [ ] Weiche Trennstriche entfernen und die Stückzahl erneut messen
- [ ] Prüfen, ob die verstümmelten Stellen auf bestimmten Seiten geballt auftreten (dann wäre
      ein einzelner Font die Ursache und eine gezielte Behandlung doch lohnend)
- [ ] Weitere Korpus-Dokumente (BSI/ANSSI Zero Trust, NIST AI 600-1) mit denselben Messungen
      prüfen — bevor sie in den Index kommen

---

# Methodische Lehre

Beide Befunde kamen zustande, weil eine **Zahl auf Plausibilität geprüft** wurde statt
akzeptiert: 55 Stücke bei 54 Seiten. Ohne diese Prüfung wäre die Pipeline mit
seitengroßen, teilweise beschädigten Stücken gebaut worden — und die schlechte Trefferqualität
wäre später beim Modell oder bei der Vektordatenbank gesucht worden, wo sie nicht liegt.

**Beim Debuggen einer RAG-Pipeline zuerst anschauen, was tatsächlich im Index steht.**
Nicht das Modell, nicht die Datenbank, nicht den Prompt.
