# Wikipedia Random Article → EPUB

Fetches a random English Wikipedia article, cleans it up for e-ink reading, and converts it to EPUB.

## Usage

```bash
# Create an EPUB in the current directory
python projects/wikipedia-random/wikipedia_random.py

# Specify output path
python projects/wikipedia-random/wikipedia_random.py -o "My Article.epub"

# Create and upload to CrossPoint
python projects/wikipedia-random/wikipedia_random.py --upload

# Upload to a specific folder / device
python projects/wikipedia-random/wikipedia_random.py --upload --host 192.168.68.51 --dir /Wikipedia

# Daily cron mode — prepends the date to the title and filename
python projects/wikipedia-random/wikipedia_random.py --daily --upload
```

## Dependencies

These are included in the workspace `epub` extra:

- `ebooklib`
- `beautifulsoup4`
- `requests` (from the shared `crosspoint` library)

Install from the repo root (with the virtual environment activated):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[epub]"
```
