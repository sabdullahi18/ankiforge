# ankiforge

Generates Anki flashcard decks from photos of Japanese textbook pages using the Gemini API.

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Add Gemini API key**

Create a `.env` file in the same directory as the script:

```
GEMINI_API_KEY=key_here
```

**3. (Optional) Enable OCR fallback**

If all Gemini models hit their rate limits, the script falls back to local OCR via Tesseract. To enable it, install the Tesseract engine with Japanese language data:

```bash
# Debian / Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-jpn

# Arch
sudo pacman -S tesseract tesseract-data-jpn

# macOS
brew install tesseract tesseract-lang
```

If Tesseract isn't installed, the script skips the OCR step and moves on cleanly.

## Usage

```bash
python3 generator.py --images page1.jpg page2.jpg
```

You'll be prompted to choose what to generate:

```
What would you like to generate?
  [1] Vocabulary cards
  [2] Grammar cards
```

Or skip the prompt by passing `--mode` directly:

```bash
python generator.py --images page1.jpg --mode vocab
python generator.py --images page1.jpg --mode grammar
```

## Options

| Flag          | Short | Description                        |
| ------------- | ----- | ---------------------------------- |
| `--images`    | `-i`  | One or more image paths (required) |
| `--mode`      | `-m`  | `vocab` or `grammar`               |
| `--deck-name` | `-d`  | Custom deck name                   |
| `--output`    | `-o`  | Output `.apkg` filename            |

## Card formats

**Vocabulary** — front shows the Japanese word, back reveals the reading and English meaning.

**Grammar** — front shows the grammar pattern (e.g. `〜てもいいです`), back reveals the meaning, example sentences, and a full explanation.

## Output

Produces an `.apkg` file (`vocab.apkg` or `grammar.apkg` by default) that you can import directly into Anki via **File → Import**.

If the OCR fallback is triggered, a `_ocr.txt` file is saved next to each affected image with the raw extracted text for manual review.

## Model fallback

The script tries Gemini models in this order if rate limits are hit:

1. `gemini-2.5-flash`
2. `gemini-2.0-flash-lite`
3. `gemini-flash-lite-latest`
4. OCR fallback (if Tesseract is installed)
