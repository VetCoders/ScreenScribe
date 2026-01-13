# ScreenScribe - Agent Guide

> Claude for Claude & other Agents: jak uzywac ScreenScribe

## Co to jest?

ScreenScribe to CLI ktore zamienia screencasty (nagrania gdzie ktos slownie recenzuje aplikacje/UI) w ustrukturyzowane raporty bugow. Wyciaga mowe, wykrywa problemy, robi screenshoty w kluczowych momentach i uzywa AI do analizy severity i sugestii napraw. Usprawnia pracę i komunikację. Daje super efekty dla obu stron!

## Kiedy używac

User nagral video recenzujac swoja appke i ma:

- Transkrypt tego co powiedzial
- Liste bugow/issues ktore wspomnial
- Screenshoty w momentach problemow
- Analize AI z severity i action items z jego komentarzami
- Eksport: JSON, Markdown, HTML dashboard
-

/Users/silver/Git/ScreenScribe/USAGE.md

## Podstawowe uzycie

```bash
# Pelna analiza (zalecane)
screenscribe review /path/to/video.mov

# Szybki tryb (bez AI)
screenscribe review video.mov --no-semantic --no-vision

# Tylko transkrypt
screenscribe transcribe video.mov -o transcript.txt

# Custom output directory
screenscribe review video.mov -o ~/Desktop/my_review
```

## Struktura outputu

```
video_review/
├── transcript.txt      # Transkrypt plain text
├── report.json         # Dane strukturalne (do programowego uzycia)
├── report.md           # Raport czytelny dla ludzi
├── report.html USERA   # Interaktywny dashboard z adnotacjami - nie dla agenta
└── screenshots/
    ├── 01_bug_01-23.jpg
    ├── 02_ui_02-45.jpg
    └── ...
```

## Kluczowe featury

| Feature                 | Opis                                                                          |
| ----------------------- | ----------------------------------------------------------------------------- |
| **Semantic pre-filter** | AI analizuje caly transkrypt zeby znalezc issues (nie tylko keyword matching) |
| **Unified VLM**         | Jeden call AI analizuje screenshot + kontekst transkryptu razem               |
| **Sentiment detection** | Rozroznia "to jest zepsute" od "to mi nie przeszkadza"                        |
| **Dual API support**    | Dziala z LibraxisAI (Responses API) i OpenAI (Chat Completions)               |
| **HTML Pro report**     | Dashboard z narzędziami do adnotacji (pen, rect, arrow) i eksport ZIP         |

## HTML Pro Report - adnotacje

Po wygenerowaniu raportu, otworz `report.html` w przegladarce:

1. **Kliknij na screenshot** → otwiera sie lightbox
2. **Toolbar na dole**:
   - Pen - rysowanie odreczne
   - Rect - prostokaty
   - Arrow - strzalki
   - Color picker - kolor adnotacji
   - Undo/Clear - cofnij/wyczysc
3. **Done** - zapisuje i zamyka

**Eksport:**

- JSON - dane z human review
- TODO - markdown checklist
- ZIP - review.json + folder `annotated/` z obrazkami z wypalonymi adnotacjami

## Konfiguracja

Plik: `~/.config/screenscribe/config.env`

```env
# LibraxisAI (domyslnie)
LIBRAXIS_API_KEY=vista-xxx

# Lub OpenAI
OPENAI_API_KEY=sk-proj-xxx
SCREENSCRIBE_LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
SCREENSCRIBE_VISION_ENDPOINT=https://api.openai.com/v1/chat/completions

# Lub lokalna Ollama
SCREENSCRIBE_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions
SCREENSCRIBE_VISION_ENDPOINT=http://localhost:11434/v1/chat/completions
```

### Env vars

| Zmienna                        | Opis                             |
| ------------------------------ | -------------------------------- |
| `SCREENSCRIBE_STT_ENDPOINT`    | Speech-to-text API               |
| `SCREENSCRIBE_LLM_ENDPOINT`    | LLM do semantic analysis         |
| `SCREENSCRIBE_VISION_ENDPOINT` | VLM do screenshot analysis       |
| `SCREENSCRIBE_STT_MODEL`       | Model STT (np. whisper-v3-large) |
| `SCREENSCRIBE_LLM_MODEL`       | Model LLM                        |
| `SCREENSCRIBE_VISION_MODEL`    | Model VLM                        |
| `LIBRAXIS_API_KEY`             | Klucz API LibraxisAI             |
| `OPENAI_API_KEY`               | Klucz API OpenAI                 |

## Uruchamianie z repo (development)

```bash
cd /Users/silver/Git/ScreenScribe
uv run screenscribe review /path/to/video.mov -o /output/dir
```

## Typowe problemy

| Problem                          | Przyczyna                          | Rozwiazanie                                 |
| -------------------------------- | ---------------------------------- | ------------------------------------------- |
| "No issues detected"             | Video bez mowy lub bez slow-kluczy | Sprawdz transcript.txt                      |
| Pusty transkrypt                 | Video bez sciezki audio            | Sprawdz czy nagranie ma dzwiek              |
| API errors                       | Zla konfiguracja                   | Sprawdz endpointy i klucze                  |
| Adnotacje nie zapisuja sie w ZIP | Obrazki jako file:// nie base64    | Uzyj HTML z prawdziwego uv run screenscribe |

## Lokalizacja repo

```
/Users/silver/Git/ScreenScribe
```

Branche:

- `develop` - glowny branch
- `feat/html-reports-pro` - nowe featury (adnotacje, ZIP export)

---

*Last updated: 2026-01-10*
