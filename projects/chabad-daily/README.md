# Chabad Daily Calendar → EPUB

Fetches the daily Jewish calendar from Chabad.org and converts it to a clean EPUB for e-ink reading.

## What's included

- Gregorian and Hebrew dates
- Weekly Torah portion (Parsha)
- Daily Study (Chumash, Tehillim, Tanya, Rambam, Hayom Yom)
- Laws and Customs (Omer count, etc.)
- Jewish History events
- Daily Thought (Chassidic teaching)

## Usage

```bash
# Today's calendar
python projects/chabad-daily/chabad_daily.py

# Specific date
python projects/chabad-daily/chabad_daily.py --date 5/6/2026

# Create and upload to CrossPoint
python projects/chabad-daily/chabad_daily.py --upload

# Daily cron mode (prepends date to title)
python projects/chabad-daily/chabad_daily.py --daily --upload

# Upload to a specific folder
python projects/chabad-daily/chabad_daily.py --upload --dir /Jewish
```

## Dependencies

Part of the workspace `epub` extra:

```bash
pip install -e ".[epub]"
```
