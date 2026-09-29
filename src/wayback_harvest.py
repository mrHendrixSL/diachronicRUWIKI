"""Pull whatever Wayback Machine snapshots exist for a list of Ruwiki article
titles and cache the raw HTML locally. Coverage is whatever IA's crawler (or
someone's Save Page Now) happened to capture -- not a full revision history.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

from ruwikipedia_pull import canonical_title

CDX_API = "https://web.archive.org/cdx/search/cdx"
MAX_RETRIES = 4
USER_AGENT = "ruwiki-diachronic-research/0.1 (contact: rasikahendrix@gmail.com)"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "raw" / "wayback"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "interim" / "wayback_manifest.jsonl"


def get_with_retries(session, url, params=None, timeout=60):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    raise last_exc


def cdx_query(session, title, from_date="2023", to_date=None, only_200=True):
    # Exact match, not a prefix wildcard: a trailing "*" makes CDX match every
    # article whose title starts with this one (e.g. "Россия*" also matches
    # "Россия в XX веке", "Российская Федерация", ...), which is both wrong
    # and, for common prefixes, slow enough to hang the query server-side.
    url = f"ru.ruwiki.ru/wiki/{title.replace(' ', '_')}"
    params = {
        "url": url,
        "output": "json",
        "collapse": "digest",
        "from": from_date,
    }
    if to_date:
        params["to"] = to_date
    if only_200:
        params["filter"] = "statuscode:200"

    resp = get_with_retries(session, CDX_API, params=params, timeout=60)
    rows = resp.json()
    if not rows:
        return []
    header, *records = rows
    return [dict(zip(header, record)) for record in records]


def snapshot_raw_url(timestamp, original_url):
    return f"https://web.archive.org/web/{timestamp}id_/{original_url}"


def safe_slug(title):
    invalid = '<>:"/\\|?*'
    slug = "".join("_" if c in invalid or ord(c) < 32 else c for c in title)
    return slug.strip().replace(" ", "_")


def harvest_title(session, title, out_dir, delay):
    # Resolve to ru.wikipedia.org's canonical title first (handles the
    # "Surname, Given Names" biographical format and any other redirect) --
    # Ruwiki inherited these titles at the June 2023 fork. This does NOT
    # catch a title Ruwiki has since deliberately renamed to (e.g. framing
    # changes); a zero-hit result here is still worth a manual substring
    # check against a bulk CDX dump before concluding an article is gone.
    canon = canonical_title(session, title)
    captures = cdx_query(session, canon)
    records = []
    title_dir = out_dir / safe_slug(canon)

    for cap in captures:
        record = {
            "title": title,
            "canonical_title": canon,
            "timestamp": cap["timestamp"],
            "original_url": cap["original"],
            "digest": cap["digest"],
            "statuscode": cap["statuscode"],
            "mimetype": cap["mimetype"],
            "length": cap["length"],
            "local_path": None,
            "fetch_error": None,
        }
        dest = title_dir / f"{cap['timestamp']}.html"
        if not dest.exists():
            title_dir.mkdir(parents=True, exist_ok=True)
            try:
                raw = get_with_retries(
                    session, snapshot_raw_url(cap["timestamp"], cap["original"])
                )
                dest.write_bytes(raw.content)
                time.sleep(delay)
            except requests.RequestException as exc:
                record["fetch_error"] = str(exc)
                records.append(record)
                continue
        record["local_path"] = str(dest.relative_to(REPO_ROOT))
        records.append(record)

    return records


def load_titles(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--titles-file", required=True, help="one article title per line")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--delay", type=float, default=1.5, help="seconds between snapshot downloads")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    titles = load_titles(args.titles_file)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    with open(manifest_path, "a", encoding="utf-8") as manifest_f:
        for title in titles:
            print(f"[{title}] querying CDX...", file=sys.stderr)
            try:
                records = harvest_title(session, title, out_dir, args.delay)
            except requests.RequestException as exc:
                print(f"[{title}] FAILED: {exc}", file=sys.stderr)
                continue
            print(f"[{title}] {len(records)} unique capture(s)", file=sys.stderr)
            for record in records:
                manifest_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                manifest_f.flush()


if __name__ == "__main__":
    main()
