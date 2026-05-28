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

