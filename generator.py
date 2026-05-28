import argparse
import json
import os
import random
import sys
from io import BytesIO
from pathlib import Path

import genanki
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# Anki model IDs — must stay stable once you've imported a deck into Anki,
# otherwise Anki treats them as brand-new card types.
# ─────────────────────────────────────────────────────────────────────────────
VOCAB_MODEL_ID = 1_607_392_319
GRAMMAR_MODEL_ID = 1_607_392_320


# ─────────────────────────────────────────────────────────────────────────────
# Anki card models
# ─────────────────────────────────────────────────────────────────────────────


def make_vocab_model() -> genanki.Model:
    return genanki.Model(
        VOCAB_MODEL_ID,
        "Japanese Vocabulary",
        fields=[
            {"name": "Word"},
            {"name": "Reading"},
            {"name": "Meaning"},
        ],
        templates=[
            {
                "name": "Vocab Card",
                "qfmt": '<div class="word">{{Word}}</div>',
                "afmt": """
                    <div class="word">{{Word}}</div>
                    <hr>
                    <div class="reading">{{Reading}}</div>
                    <div class="meaning">{{Meaning}}</div>
                """,
            }
        ],
        css="""
            .card {
                font-family: "Noto Sans JP", "Hiragino Sans", sans-serif;
                text-align: center;
                background: #fafafa;
                padding: 20px;
            }
            .word    { font-size: 48px; font-weight: bold; color: #1a1a2e; margin: 20px 0; }
            .reading { font-size: 24px; color: #4a4a8a; margin: 10px 0; }
            .meaning { font-size: 22px; color: #2d2d2d; margin: 10px 0; }
            hr       { border: none; border-top: 1px solid #ddd; margin: 15px 0; }
        """,
    )


def make_grammar_model() -> genanki.Model:
    return genanki.Model(
        GRAMMAR_MODEL_ID,
        "Japanese Grammar",
        fields=[
            {"name": "GrammarPoint"},
            {"name": "Meaning"},
            {"name": "Examples"},
            {"name": "Explanation"},
        ],
        templates=[
            {
                "name": "Grammar Card",
                "qfmt": """
                    <div class="label">Grammar Point</div>
                    <div class="grammar-point">{{GrammarPoint}}</div>
                """,
                "afmt": """
                    <div class="grammar-point">{{GrammarPoint}}</div>
                    <div class="meaning">{{Meaning}}</div>
                    <hr>
                    <div class="section-label">Examples</div>
                    <div class="examples">{{Examples}}</div>
                    <hr>
                    <div class="section-label">Explanation</div>
                    <div class="explanation">{{Explanation}}</div>
                """,
            }
        ],
        css="""
            .card {
                font-family: "Noto Sans JP", "Hiragino Sans", sans-serif;
                text-align: left;
                background: #fafafa;
                padding: 20px;
                max-width: 600px;
                margin: 0 auto;
            }
            .label         { font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
            .grammar-point { font-size: 36px; font-weight: bold; color: #1a1a2e; margin: 12px 0; }
            .meaning       { font-size: 20px; color: #4a4a8a; margin: 8px 0 16px; }
            .section-label { font-size: 12px; color: #aaa; text-transform: uppercase; margin: 10px 0 4px; }
            .examples      { font-size: 17px; line-height: 1.8; color: #2d2d2d; }
            .explanation   { font-size: 16px; line-height: 1.7; color: #444; }
            hr             { border: none; border-top: 1px solid #ddd; margin: 14px 0; }
        """,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gemini prompts
# ─────────────────────────────────────────────────────────────────────────────

VOCAB_PROMPT = """Analyse the textbook page image(s) carefully. Extract ALL vocabulary items from the page. Respond with ONLY a JSON array.
Each element must have exactly these keys:
  "word"    – the word in kanji/kana exactly as it appears in the book
  "reading" – the full reading in hiragana (or katakana for loanwords)
  "meaning" – clear English translation(s)

Example output:
[
  {"word": "学生", "reading": "がくせい", "meaning": "student"},
  {"word": "食べる", "reading": "たべる", "meaning": "to eat"}
]

If no vocabulary is found, return an empty array: []
"""

GRAMMAR_PROMPT = """Analyse this textbook page image carefully. Extract ALL grammar points or grammar patterns taught on this page.

Respond with ONLY a JSON array.
Each element must have exactly these keys:
  "grammar_point" – the pattern in Japanese (e.g. 〜てもいいです, Nounの, etc.)
  "meaning"       – a concise English gloss of what it expresses
  "examples"      –  single STRING (not an array) containing 2-3 example sentence pairs.
                    Format: "Japanese sentence。\\nEnglish translation."
                    Separate pairs with "\\n\\n".
                    Example value: "寒くなります。\\nIt becomes cold.\\n\\n元気になります。\\nI will get well."
  "explanation"   – a clear English explanation of when/how to use the pattern,
                    including conjugation or attachment rules

If no grammar points are found, return an empty array: []
"""


# ─────────────────────────────────────────────────────────────────────────────
# Image helpers
# ─────────────────────────────────────────────────────────────────────────────


def load_image_bytes(path: str) -> bytes:
    img = Image.open(path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def extract_from_image(
    client: genai.Client,
    image_path: str,
    prompt: str,
    label: str,
) -> list[dict]:
    print(f"  Processing {Path(image_path).name} …")

    image_bytes = load_image_bytes(image_path)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt,
        ],
    )

    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            raise ValueError("Expected a JSON array")
        print(f"  {len(items)} {label} item(s) found")
        return items
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  Could not parse response: {e}")
        print(f"  Raw output:\n{raw[:500]}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Deck builders — one per mode
# ─────────────────────────────────────────────────────────────────────────────


def build_vocab_deck(deck_name: str, items: list[dict]) -> genanki.Deck:
    deck = genanki.Deck(random.randrange(1_000_000_000, 2_000_000_000), deck_name)
    model = make_vocab_model()
    seen = set()

    for item in items:
        word = str(item.get("word", "")).strip()
        reading = str(item.get("reading", "")).strip()
        meaning = str(item.get("meaning", "")).strip()

        if not word or word in seen:
            continue
        seen.add(word)
        deck.add_note(genanki.Note(model=model, fields=[word, reading, meaning]))

    print(f"\n  Vocabulary deck '{deck_name}': {len(seen)} card(s)")
    return deck


def build_grammar_deck(deck_name: str, items: list[dict]) -> genanki.Deck:
    deck = genanki.Deck(random.randrange(1_000_000_000, 2_000_000_000), deck_name)
    model = make_grammar_model()
    seen = set()

    for item in items:
        point = str(item.get("grammar_point", "")).strip()
        meaning = str(item.get("meaning", "")).strip()
        examples = str(item.get("examples", "")).strip()
        explanation = str(item.get("explanation", "")).strip()

        if not point or point in seen:
            continue
        seen.add(point)

        examples_html = examples.replace("\n\n", "<br><br>").replace("\n", "<br>")
        deck.add_note(
            genanki.Note(
                model=model,
                fields=[point, meaning, examples_html, explanation],
            )
        )

    print(f"\n  Grammar deck '{deck_name}': {len(seen)} card(s)")
    return deck


# ─────────────────────────────────────────────────────────────────────────────
# Interactive mode selection
# ─────────────────────────────────────────────────────────────────────────────


def prompt_mode() -> str:
    print("\n┌─────────────────────────────────────┐")
    print("│   Japanese Anki Flashcard Generator  │")
    print("└─────────────────────────────────────┘")
    print("\nWhat would you like to generate?")
    print("  [1] Vocabulary cards")
    print("  [2] Grammar cards")

    while True:
        choice = input("\nEnter 1 or 2: ").strip()
        if choice == "1":
            return "vocab"
        if choice == "2":
            return "grammar"
        print("  Please enter 1 or 2.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate Anki flashcards from Japanese textbook photos using Gemini."
    )
    p.add_argument(
        "--images",
        "-i",
        nargs="+",
        required=True,
        metavar="IMAGE",
        help="One or more image paths (jpg, png, etc.)",
    )
    p.add_argument(
        "--mode",
        "-m",
        choices=["vocab", "grammar"],
        default=None,
        help="What to extract: 'vocab' or 'grammar'. Prompted interactively if omitted.",
    )
    p.add_argument(
        "--deck-name",
        "-d",
        default=None,
        help="Name for the Anki deck. Defaults to 'Japanese Vocabulary' or 'Japanese Grammar'.",
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output .apkg file path. Defaults to vocab.apkg or grammar.apkg.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "  GEMINI_API_KEY not found.\n"
            "  Add it to a .env file in this directory:\n"
            "      GEMINI_API_KEY=your_key_here"
        )

    for path in args.images:
        if not Path(path).exists():
            sys.exit(f"  Image not found: {path}")

    mode = args.mode or prompt_mode()

    if mode == "vocab":
        deck_name = args.deck_name or "Japanese Vocabulary"
        output_path = args.output or "vocab.apkg"
        prompt = VOCAB_PROMPT
        label = "vocab"
    else:
        deck_name = args.deck_name or "Japanese Grammar"
        output_path = args.output or "grammar.apkg"
        prompt = GRAMMAR_PROMPT
        label = "grammar"

    client = genai.Client(api_key=api_key)

    print(f"\n  Mode: {mode.upper()} | {len(args.images)} image(s)\n")

    all_items = []
    for image_path in args.images:
        items = extract_from_image(client, image_path, prompt, label)
        all_items.extend(items)

    if not all_items:
        sys.exit("  No items extracted. Check your images and try again.")

    if mode == "vocab":
        deck = build_vocab_deck(deck_name, all_items)
    else:
        deck = build_grammar_deck(deck_name, all_items)

    genanki.Package(deck).write_to_file(output_path)
    print(f"  Saved: {output_path}\n")


if __name__ == "__main__":
    main()
