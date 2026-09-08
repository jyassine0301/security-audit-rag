# suche.py - findet den passenden Absatz in BSI 200-3
from pathlib import Path
from pypdf import PdfReader
# 1. PDF laden und Text holen

PDF = Path.home() / "lernprogress" / "plan" / "material" / "pdfs" / "standard_200_3.pdf"
reader = PdfReader(PDF)
print(f"Seiten: {len(reader.pages)}")

# 2. Text in Absaetze zerteilen, kurze wegwerfen, erstmal nur 20 behalten
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n\n"

text = text.replace("\xad\n", "").replace("\xad", "")     # 359 getrennte Woerter zusammensetzen
text = text.replace("ffr", "für").replace("Ffr", "Für")   # 24 Stellen reparieren


stuecke = []                              # leerer Tisch
for i in range(0, len(text), 800):        # Startpositionen: 0, 800, 1600, ...
    stuecke.append(text[i:i+800])         # Stueck abschneiden und ablegen

print(f"Stuecke: {len(stuecke)}")                  

# 3. Funktion: Text rein -> Liste von Zahlen raus (Ollama fragen)

# 4. Funktion: zwei Listen rein -> eine Aehnlichkeitszahl raus (Kosinus)

# 5. Alle 20 Absaetze einbetten, die Frage einbetten

# 6. Jeden Absatz mit der Frage vergleichen, sortieren, die besten 3 ausgeben