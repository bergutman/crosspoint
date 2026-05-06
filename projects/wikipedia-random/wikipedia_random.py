#!/usr/bin/env python3
"""Fetch a random Wikipedia article and convert it to EPUB for the CrossPoint reader."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "CrossPointScripts/0.1 (https://github.com/crosspoint-reader; personal-project)"}


def get_random_article() -> dict[str, int | str]:
    """Get a random Wikipedia article title and page ID."""
    params = {
        "action": "query",
        "list": "random",
        "rnnamespace": 0,
        "rnlimit": 1,
        "format": "json",
    }
    resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    article = data["query"]["random"][0]
    return {"title": article["title"], "pageid": article["id"]}


def get_article_html(title: str) -> str:
    """Fetch the parsed HTML content of a Wikipedia article."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }
    resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["parse"]["text"]["*"]


def clean_html(html: str, title: str) -> str:
    """Clean Wikipedia HTML for e-ink consumption."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove noisy elements that don't belong in an ebook
    selectors_to_remove = [
        "style",                      # Embedded CSS blocks
        "sup.reference",              # Inline citation markers [1], [2]...
        "span.mw-editsection",        # [edit] links
        ".noprint",
        ".mw-empty-elt",
        ".toc",                       # Table of contents
        "table.navbox",
        "table.metadata",
        ".infobox",
        ".thumbinner .thumbcaption",  # Image captions
        ".mw-cite-backlink",          # ^ a b c citation backlinks
        ".mw-references-wrap",        # References wrapper div
        "ol.references",              # The numbered reference list
        "div.reflist",
    ]
    for selector in selectors_to_remove:
        for element in soup.select(selector):
            element.decompose()

    # 2. Strip ALL class and style attributes (they're useless in an EPUB)
    for element in soup.find_all():
        element.attrs.pop("class", None)
        element.attrs.pop("style", None)
        element.attrs.pop("data-mw-deduplicate", None)

    # 3. Remove the entire "References" section (heading + everything after it until next h2)
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True).lower()
        if text in {"references", "notes", "footnotes", "citations", "bibliography"}:
            # Remove this heading and all siblings after it until the next same-level heading
            next_sibling = heading.find_next_sibling()
            while next_sibling and next_sibling.name not in {"h2", "h3"}:
                sibling_to_remove = next_sibling
                next_sibling = next_sibling.find_next_sibling()
                sibling_to_remove.decompose()
            heading.decompose()

    # 4. Neutralize any remaining citation links (e.g. stray #cite_note anchors)
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("#cite_note"):
            link.decompose()
        elif href.startswith("/"):
            link["href"] = f"https://en.wikipedia.org{href}"
        elif href.startswith("#"):
            link["href"] = "#"

    # 5. Convert relative image sources to absolute
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src.startswith("//"):
            img["src"] = f"https:{src}"
        elif src.startswith("/"):
            img["src"] = f"https://en.wikipedia.org{src}"

    body_content = str(soup)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>
        body {{ font-family: Georgia, "Times New Roman", serif; line-height: 1.6; margin: 1em; }}
        h1, h2, h3, h4 {{ font-family: Helvetica, Arial, sans-serif; }}
        img {{ max-width: 100%; height: auto; display: block; margin: 1em auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
        th, td {{ border: 1px solid #999; padding: 0.4em; }}
        a {{ color: #000; text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {body_content}
</body>
</html>
"""


def create_epub(title: str, html_content: str, output_path: Path) -> Path:
    """Create an EPUB file from HTML content."""
    book = epub.EpubBook()

    book.set_identifier(f"wikipedia-{title.replace(' ', '_')}")
    book.set_title(title)
    book.set_language("en")
    book.add_author("Wikipedia Contributors")

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
    parser = argparse.ArgumentParser(description="Random Wikipedia article → EPUB")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    parser.add_argument("--upload", "-u", action="store_true", help="Upload to CrossPoint")
    parser.add_argument("--host", default="172.20.10.8", help="CrossPoint host/IP")
    parser.add_argument("--dir", default="/Wikipedia", help="Remote directory")
    parser.add_argument("--daily", action="store_true", help="Daily run mode: prepend date to title and filename")
    args = parser.parse_args()

    from datetime import date

    today = date.today().isoformat()

    print("Fetching random article...")
    article = get_random_article()
    wiki_title = str(article["title"])
    print(f"Selected: {wiki_title}")

    if args.daily:
        title = f"{today} - {wiki_title}"
    else:
        title = wiki_title

    print("Downloading content...")
    raw_html = get_article_html(wiki_title)

    print("Cleaning HTML...")
    clean = clean_html(raw_html, title)

    if args.output:
        output_path = args.output
    else:
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        output_path = Path(f"{safe_title}.epub")

    print(f"Writing EPUB: {output_path}")
    create_epub(title, clean, output_path)

    if args.upload:
        from crosspoint import CrossPointClient

        client = CrossPointClient(host=args.host)

        # Ensure target folder exists
        try:
            client.mkdir(args.dir.strip("/"), parent="/")
        except Exception:
            # Folder likely already exists; safe to ignore
            pass

        print(f"Uploading to {args.host}{args.dir} ...")
        result = client.upload_file(output_path, args.dir)
        print(result)

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
