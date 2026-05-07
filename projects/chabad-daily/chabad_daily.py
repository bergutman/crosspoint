#!/usr/bin/env python3
"""Fetch the daily Chabad Jewish calendar and convert it to EPUB."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

CHABAD_URL = "https://www.chabad.org/calendar/view/day.asp"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def fetch_calendar(tdate: str) -> BeautifulSoup:
    """Fetch and parse the Chabad calendar page for a given date.

    tdate format: M/D/YYYY (e.g., 5/6/2026)
    """
    resp = requests.get(CHABAD_URL, params={"tdate": tdate}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_date_info(soup: BeautifulSoup) -> dict[str, str]:
    """Extract the date header and parsha from the page."""
    info: dict[str, str] = {}

    # Title contains both Gregorian and Hebrew dates
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # "Wednesday, May 6, 2026 / Iyar 19, 5786 - Jewish Calendar - Hebrew Calendar"
        m = re.match(r"^(.*?\d{4})\s*/\s*(.*?)\s+-", title_text)
        if m:
            info["gregorian"] = m.group(1).strip()
            info["hebrew"] = m.group(2).strip()
        else:
            info["title"] = title_text

    # Parsha from header notification area
    todays_date = soup.find("a", id="TodaysDate")
    if todays_date:
        parent = todays_date.find_parent("div")
        if parent:
            text = parent.get_text(separator=" ", strip=True)
            parsha_match = re.search(r"Torah reading is\s+(.+?)(?:\s+\||$)", text)
            if parsha_match:
                info["parsha"] = parsha_match.group(1).strip()

    return info


def extract_section(soup: BeautifulSoup, section_id: str) -> str | None:
    """Extract a named section's body text, cleaning up link cruft."""
    section = soup.find(id=section_id)
    if not section:
        return None

    # Clone so we don't mutate the original soup
    clone = BeautifulSoup(str(section), "html.parser").find()

    # Remove "Links:" blocks and any following <ul> or <a> tags
    for elem in clone.find_all(string=re.compile(r"^Links?:", re.I)):
        parent = elem.parent
        if parent:
            # Remove the links text and subsequent sibling link lists
            next_sib = parent.find_next_sibling()
            while next_sib and next_sib.name in {"ul", "ol", "div", "a"}:
                sib = next_sib
                next_sib = next_sib.find_next_sibling()
                sib.decompose()
            parent.decompose()

    # Remove empty paragraphs and excessive whitespace
    for p in clone.find_all("p"):
        if not p.get_text(strip=True):
            p.decompose()

    text = clone.get_text(separator="\n", strip=True)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def extract_daily_thought(soup: BeautifulSoup) -> str | None:
    """Extract the Daily Thought / Chassidic thought section."""
    thought = soup.find(id="DailyThoughtBody0")
    if not thought:
        return None
    text = thought.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def build_html(soup: BeautifulSoup, info: dict[str, str]) -> str:
    """Build clean HTML for the EPUB from scraped sections."""
    parts: list[str] = []

    # Header
    if "gregorian" in info and "hebrew" in info:
        parts.append(f"<h1>{info['gregorian']}</h1>")
        parts.append(f"<h2>{info['hebrew']}</h2>")
    elif "title" in info:
        parts.append(f"<h1>{info['title']}</h1>")

    if "parsha" in info:
        parts.append(f"<p><strong>Torah Reading:</strong> {info['parsha']}</p>")

    # Daily Study
    daily = extract_section(soup, "daily_study")
    if daily:
        parts.append("<h2>Daily Study</h2>")
        # Convert plain text lines into paragraphs for readability
        for line in daily.splitlines():
            line = line.strip()
            if line and not line.lower().startswith("daily study"):
                parts.append(f"<p>{line}</p>")

    # Laws and Customs
    laws = extract_section(soup, "laws_customs")
    if laws:
        parts.append("<h2>Laws and Customs</h2>")
        # Skip the redundant header line
        lines = laws.splitlines()
        if lines and "laws and customs" in lines[0].lower():
            lines = lines[1:]
        for line in lines:
            line = line.strip()
            if line:
                parts.append(f"<p>{line}</p>")

    # Jewish History
    history = extract_section(soup, "jewish_history")
    if history:
        parts.append("<h2>Jewish History</h2>")
        lines = history.splitlines()
        if lines and "jewish history" in lines[0].lower():
            lines = lines[1:]
        for line in lines:
            line = line.strip()
            if line:
                parts.append(f"<p>{line}</p>")

    # Daily Thought
    thought = extract_daily_thought(soup)
    if thought:
        parts.append("<h2>Daily Thought</h2>")
        parts.append(f"<p>{thought}</p>")

    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <title>Chabad Daily Calendar</title>
    <style>
        body {{ font-family: Georgia, "Times New Roman", serif; line-height: 1.6; margin: 1em; }}
        h1, h2, h3 {{ font-family: Helvetica, Arial, sans-serif; }}
        h1 {{ font-size: 1.6em; }}
        h2 {{ font-size: 1.3em; margin-top: 1.5em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }}
        p {{ margin: 0.6em 0; }}
    </style>
</head>
<body>
    {body}
</body>
</html>
"""


def create_epub(title: str, html_content: str, output_path: Path) -> Path:
    """Create an EPUB file from HTML content."""
    book = epub.EpubBook()
    book.set_identifier(f"chabad-{title.replace(' ', '_')}")
    book.set_title(title)
    book.set_language("en")
    book.add_author("Chabad.org")

    chapter = epub.EpubHtml(title=title, file_name="article.xhtml", lang="en")
    chapter.content = html_content
    book.add_item(chapter)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.toc = (epub.Link("article.xhtml", title, title),)

    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content="BODY { font-family: Georgia, serif; line-height: 1.6; }",
    )
    book.add_item(nav_css)
    book.spine = ["nav", chapter]

    epub.write_epub(str(output_path), book)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Chabad Daily Calendar → EPUB")
    parser.add_argument("--date", default=date.today().strftime("%-m/%-d/%Y"), help="Date to fetch (M/D/YYYY)")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    parser.add_argument("--upload", "-u", action="store_true", help="Upload to CrossPoint")
    parser.add_argument("--host", default="192.168.68.51", help="CrossPoint host/IP")
    parser.add_argument("--dir", default="/Jewish", help="Remote directory")
    parser.add_argument("--daily", action="store_true", help="Daily run mode: prepend date to title and filename")
    args = parser.parse_args()

    today_iso = date.today().isoformat()

    print(f"Fetching Chabad calendar for {args.date}...")
    soup = fetch_calendar(args.date)
    info = extract_date_info(soup)

    date_label = info.get("gregorian", args.date)
    hebrew_date = info.get("hebrew", "")
    base_title = f"Chabad Daily Calendar - {date_label}"
    if hebrew_date:
        base_title += f" ({hebrew_date})"

    if args.daily:
        title = f"{today_iso} - {base_title}"
    else:
        title = base_title

    print(f"Title: {title}")

    html = build_html(soup, info)

    if args.output:
        output_path = args.output
    else:
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        output_path = Path(f"{safe}.epub")

    print(f"Writing EPUB: {output_path}")
    create_epub(title, html, output_path)

    if args.upload:
        from crosspoint import CrossPointClient
        from crosspoint.queue import UploadQueue

        client = CrossPointClient(host=args.host)
        queue = UploadQueue()

        try:
            client.mkdir(args.dir.strip("/"), parent="/")
        except Exception:
            pass

        print(f"Uploading to {args.host}{args.dir} ...")
        try:
            result = client.upload_file(output_path, args.dir)
            print(result)
        except requests.exceptions.ConnectionError:
            entry = queue.add(output_path, args.dir, args.host)
            print(f"Device unreachable — queued {entry.filename} for later transfer.")
            print("Run: python -m crosspoint queue --process")

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
