# suche.py - Retrieval-Suche im BSI-Standard 200-3, ohne Framework
# laden -> reparieren -> zerteilen -> einbetten -> vergleichen -> ausgeben
# Messungen und Begruendungen: siehe BEFUNDE.md

from pathlib import Path
from pypdf import PdfReader
import requests
import math

PDF = Path.home() / "lernprogress" / "plan" / "material" / "pdfs" / "standard_200_3.pdf"


# --- 1. Laden --------------------------------------------------------------
reader = PdfReader(PDF)
print(f"Seiten: {len(reader.pages)}")                    # 54 seiten


# --- 2a. Alle Seiten zu EINEM Text kleben ----------------------------------
# Zusammen statt seitenweise: sonst bleibt an jeder Seitengrenze ein Rest
# (54 statt 1) und Saetze werden an den Grenzen zerrissen.
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n\n"


# --- 2b. Reparieren - VOR dem Zerteilen ------------------------------------
# 359x Silbentrennung \xad zerreisst Woerter ("teil\xad\nweise"), 24x "ffr"
# statt "für" (Font-Fehler im PDF). Embeddings vergleichen Zeichenfolgen -
# kaputter Text = kaputte Treffer.
# Reihenfolge: erst "\xad\n", sonst bleibt "teil\nweise" stehen.
text = text.replace("\xad\n", "").replace("\xad", "")
text = text.replace("ffr", "für").replace("Ffr", "Für")


# --- 2c. Zerteilen in 800-Zeichen-Stuecke ----------------------------------
# Feste Zeichenzahl statt Absaetze: das PDF enthaelt NULL Leerzeilen (gemessen).
# Ein Vektor beschreibt den Durchschnitt seines Stuecks - grosse Stuecke
# verwaessern, winzige verlieren den Zusammenhang. 800 = grob ein Absatz.
stuecke = []                              # leere Liste
for i in range(0, len(text), 800):        # durchlaufen
    stuecke.append(text[i:i+800])         # Ergebnis anhaengen

print(f"Stuecke: {len(stuecke)}")                        # 138


# --- 3. Einbetten: Text rein -> 768 Zahlen raus ----------------------------
# POST http://localhost:11434/api/embeddings
# senden:   {"model": "nomic-embed-text", "prompt": "..."}
# zurueck:  {"embedding": [0.906, 0.251, ...]}

def embed(eingabe):
    antwort = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": eingabe}
    )
    return antwort.json()["embedding"]


print(f"Merkmale je Text: {len(embed('Schutzbedarf'))}")  # 768 - immer gleich viele,
                                                         # egal wie lang der Text ist


# --- 4. Kosinus-Aehnlichkeit: zwei Vektoren -> eine Zahl -------------------
# Zaehler: paarweise multiplizieren, addieren
# Nenner:  Laenge mal Laenge - rechnet die Textlaenge heraus,
#          sonst gewinnt immer das laengste Stueck
def kosinus(a, b):
    # Schritt 1 - Zaehler
    zaehler = 0
    for x, y in zip(a, b):
        zaehler += x * y

    # Schritt 2 - Laenge von a
    summe_a = 0
    for x in a:
        summe_a += x * x
    laenge_a = math.sqrt(summe_a)

    # Schritt 3 - Laenge von b
    summe_b = 0
    for y in b:
        summe_b += y * y
    laenge_b = math.sqrt(summe_b)

    # Schritt 4 - teilen
    return zaehler / (laenge_a * laenge_b)


# [3,4] und [6,8] zeigen in dieselbe Richtung, nur doppelt so lang.
# Kommt nicht 1.0 heraus, rechnet die Formel die Laenge nicht heraus.
print(f"Selbsttest kosinus: {kosinus([3, 4], [6, 8])}")  # muss 1.0 sein


# --- 5. Alle Stuecke EINMAL einbetten -------------------------------------
# Vor der Schleife, nicht darin: 138 Stuecke kosten 350 s (BEFUNDE.md 4).
# So faellt die Wartezeit einmal beim Start an statt bei jeder Frage.
# Praefix "search_document: " ist bei nomic-embed-text Pflicht - ohne ihn
# kehrt sich die Rangfolge um (BEFUNDE.md 3).
vektoren = []
for stueck in stuecke:
    vektoren.append(embed("search_document: " + stueck))

print(f"Vektoren: {len(vektoren)}")                      # 138 - je Stueck einer


# --- 6+7. Fragen beantworten, bis Enter gedrueckt wird --------------------
# Schleife statt fester Variable: neue Frage ohne Neustart - die 350 s
# aus Schritt 5 bleiben erhalten.
while True:
    frage = input("\nFrage (Enter zum Beenden): ")
    if not frage:
        break

    # anderes Praefix als oben: Frage und Dokument sind zwei Rollen
    frage_vektor = embed("search_query: " + frage)

    # Wert und Stueck als Paar - beim Sortieren bleiben sie zusammen
    ergebnisse = []
    for v, stueck in zip(vektoren, stuecke):
        ergebnisse.append((kosinus(frage_vektor, v), stueck))
    ergebnisse.sort(reverse=True)          # groesster Wert nach vorn

    # Treffer mit anzeigen: bei einer falschen Antwort zeigt sich hier sofort,
    # ob die Suche danebenlag oder das Modell den Text nicht verstanden hat.
    print(f"\nFrage: {frage}\n")
    for wert, stueck in ergebnisse[:3]:
        print(f"{wert:.3f}  {stueck[:200]}")
        print()

    # nur die besten 3 ans Modell - mehr Kontext heisst mehr Ablenkung
    kontext = ""
    for wert, stueck in ergebnisse[:3]:
        kontext += stueck + "\n\n"

    # Der zweite Satz ist der Guardrail gegen Halluzination. Preis: das Modell
    # lehnt manchmal ab, obwohl die Antwort dasteht - Abwaegung, keine Loesung.
    prompt = f"""Beantworte die Frage AUSSCHLIESSLICH mit den folgenden Textstellen.
Steht die Antwort nicht darin, antworte: "Das steht nicht im Dokument."

Textstellen:
{kontext}

Frage: {frage}"""

    # temperature 0 = immer dieselbe Antwort, Voraussetzung fuers Messen.
    # qwen2.5:3b lehnt zu oft faelschlich ab (BEFUNDE.md 5).
    antwort = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "qwen2.5:3b", "prompt": prompt, "stream": False,
              "options": {"temperature": 0}}
    )
    print(antwort.json()["response"])