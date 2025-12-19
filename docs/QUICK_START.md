# ScreenScribe - Szybki Start

Przewodnik dla użytkowników, którzy chcą analizować nagrania ekranu.

---

## Co robi ScreenScribe?

ScreenScribe to narzędzie, które:

1. **Słucha** co mówisz podczas nagrywania ekranu
2. **Wyłapuje** gdy wspominasz o błędach, zmianach, problemach
3. **Robi screenshoty** w tych momentach
4. **Generuje raport** z listą rzeczy do poprawy

Idealne do: code review, testowania aplikacji, zbierania feedbacku UX.

---

## Zanim zaczniesz

### Potrzebujesz:

1. **Klucz API LibraxisAI** - dostaniesz go od admina
2. **FFmpeg** - do przetwarzania wideo

### Instalacja FFmpeg (jednorazowo)

**Mac:**
```bash
brew install ffmpeg
```

**Windows:**
```bash
choco install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### Ustawienie klucza API (jednorazowo)

```bash
screenscribe config --set-key TWOJ_KLUCZ_API
```

---

## Jak używać?

### Krok 1: Nagraj ekran

Nagraj swój ekran (np. QuickTime, OBS, Loom) i **mów na głos** co widzisz:

> "Tu jest błąd - ten przycisk nie działa"
> "Trzeba zmienić ten layout"
> "Ten modal powinien być większy"

Zapisz nagranie jako plik `.mov` lub `.mp4`.

### Krok 2: Uruchom analizę

```bash
screenscribe review ~/Desktop/moje-nagranie.mov
```

To wszystko! ScreenScribe:
- Wyciągnie audio z nagrania
- Przetworzy Twoją mowę na tekst
- Znajdzie wszystkie miejsca gdzie wspominasz problemy
- Zrobi screenshoty
- Wygeneruje raport

### Krok 3: Sprawdź wyniki

W folderze `moje-nagranie_review/` znajdziesz:

```
moje-nagranie_review/
├── transcript.txt      ← Pełna transkrypcja (co mówiłeś)
├── report.md           ← Raport do czytania
├── report.json         ← Raport dla programistów
└── screenshots/        ← Zrzuty ekranu z momentów gdy wspominasz problemy
```

Otwórz `report.md` w dowolnym edytorze Markdown (np. VS Code, Typora) lub na GitHub.

---

## Opcje dla zaawansowanych

### Szybsza analiza (bez AI)

Jeśli nie potrzebujesz analizy AI i chcesz tylko screenshoty:

```bash
screenscribe review nagranie.mov --no-semantic --no-vision
```

### Analiza po angielsku

```bash
screenscribe review nagranie.mov --lang en
```

### Wznowienie przerwanej analizy

Jeśli analiza się przerwała (np. przez brak internetu):

```bash
screenscribe review nagranie.mov --resume
```

### Własne słowa kluczowe

Jeśli używasz specyficznego słownictwa w projekcie:

```bash
# Wygeneruj plik z domyślnymi słowami kluczowymi
screenscribe config --init-keywords

# Edytuj keywords.yaml i dodaj swoje słowa
# Potem uruchom analizę - automatycznie użyje Twojego pliku
screenscribe review nagranie.mov
```

---

## Wskazówki

### Jak mówić żeby ScreenScribe lepiej rozumiał?

Używaj słów kluczowych:

| Kategoria | Przykłady słów |
|-----------|----------------|
| **Błędy** | "bug", "błąd", "nie działa", "zepsute", "crash" |
| **Zmiany** | "trzeba zmienić", "powinno być", "poprawić", "dodać" |
| **UI** | "przycisk", "layout", "modal", "menu", "ekran" |

### Przykład dobrego komentarza:

> ❌ "Hmm, to jest dziwne..."
>
> ✅ "Tu jest **błąd** - przycisk **nie działa** gdy kliknę"

---

## Rozwiązywanie problemów

### "No API key"

Ustaw klucz:
```bash
screenscribe config --set-key TWOJ_KLUCZ
```

### "FFmpeg not found"

Zainstaluj FFmpeg (patrz wyżej).

### Analiza trwa bardzo długo

Użyj `--no-vision` żeby pominąć analizę obrazów (najwolniejsza część):
```bash
screenscribe review nagranie.mov --no-vision
```

### Nie wykrywa moich komentarzy

1. Sprawdź czy mówisz wystarczająco głośno
2. Używaj słów kluczowych (bug, błąd, zmiana, etc.)
3. Sprawdź język: `--lang pl` dla polskiego, `--lang en` dla angielskiego

---

## Pomoc

```bash
# Zobacz wszystkie opcje
screenscribe review --help

# Sprawdź konfigurację
screenscribe config --show

# Wersja
screenscribe version
```

---

**Made with (งಠ_ಠ)ง by ⌜ScreenScribe⌟**
