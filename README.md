# Auto Transcriber

Program do automatycznego generowania transkrypcji w formacie .srt z plików wideo.

## Wymagania

- Python 3.7 lub nowszy
- FFmpeg (musi być zainstalowany w systemie i dostępny w ścieżce PATH)

## Instalacja

1. Sklonuj lub pobierz to repozytorium
2. Zainstaluj wymagane biblioteki:

```
pip install -r requirements.txt
```

3. Upewnij się, że masz zainstalowany FFmpeg:
   - Windows: Pobierz z [ffmpeg.org](https://ffmpeg.org/download.html) i dodaj do PATH
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

## Użycie

```
python auto_transcriber.py ścieżka_do_pliku_wideo [opcje]
```

### Opcje

- `-o, --output` - Ścieżka wyjściowa pliku SRT (domyślnie: nazwa_pliku.srt)
- `-l, --language` - Język transkrypcji (domyślnie: pl)

### Przykłady

```
# Podstawowe użycie
python auto_transcriber.py moje_wideo.mp4

# Określenie niestandardowej ścieżki wyjściowej
python auto_transcriber.py moje_wideo.mp4 -o napisy.srt

# Transkrypcja w języku angielskim
python auto_transcriber.py moje_wideo.mp4 -l en
```

## Obsługiwane języki

Program wykorzystuje OpenAI Whisper, który obsługuje wiele języków, w tym:

- Polski (pl)
- Angielski (en)
- Niemiecki (de)
- Francuski (fr)
- Hiszpański (es)
- Włoski (it)

## Modele Whisper

Program domyślnie używa modelu "base", który oferuje dobry kompromis między jakością a szybkością. Dostępne modele:

- tiny: najszybszy, ale najmniej dokładny
- base: dobry kompromis (domyślny)
- small: dokładniejszy, ale wolniejszy
- medium: bardzo dokładny, ale wymaga więcej zasobów
- large: najdokładniejszy, ale najwolniejszy i wymaga dużo pamięci

Aby zmienić model, edytuj linię `model = whisper.load_model("base")` w pliku `auto_transcriber.py`.

## Integracja z Adobe Premiere Pro

Wygenerowane pliki .srt można łatwo zaimportować do Adobe Premiere Pro:

1. W Premiere Pro wybierz "File" > "Import"
2. Wybierz wygenerowany plik .srt
3. Przeciągnij plik napisów na ścieżkę wideo
4. Dostosuj styl i wygląd napisów w panelu "Captions"

## Uwagi

- Jakość transkrypcji zależy od jakości dźwięku w pliku wideo
- Dla długich plików wideo proces może zająć dużo czasu
- Whisper działa lokalnie na Twoim komputerze i nie wymaga połączenia z internetem
