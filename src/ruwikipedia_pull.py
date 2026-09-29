"""Pull, for a list of article titles, the full ru.wikipedia.org revision
history plus the wikitext of two key revisions: the one nearest the June 2023
Ruwiki fork date (the common baseline both corpora started from) and the
current one. This is the "original" side counterpart to wayback_harvest.py.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

API_URL = "https://ru.wikipedia.org/w/api.php"
USER_AGENT = "ruwiki-diachronic-research/0.1 (contact: rasikahendrix@gmail.com)"
FORK_DATE = "2023-06-24T00:00:00Z"  # Ruwiki beta launch
MAX_RETRIES = 4

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "raw" / "ru_wikipedia"


def get_with_retries(session, params, timeout=30):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(API_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    raise last_exc


def canonical_title(session, title):
    data = get_with_retries(session, {
        "action": "query", "titles": title, "redirects": 1, "format": "json",
    })
    query = data["query"]
    if "redirects" in query:
        return query["redirects"][0]["to"]
    return title


def fetch_revision_list(session, title):
    revisions = []
    params = {
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "ids|timestamp|user|comment|size", "rvlimit": "max",
        "rvdir": "newer", "format": "json",
    }
    while True:
        data = get_with_retries(session, params)
        pages = data["query"]["pages"]
        page = list(pages.values())[0]
        if "missing" in page:
            return []
        revisions.extend(page.get("revisions", []))
        if "continue" in data:
            params["rvcontinue"] = data["continue"]["rvcontinue"]
        else:
            return revisions


def fetch_revision_content(session, title, at_or_before=None):
    """Content of the revision at `at_or_before` (nearest earlier timestamp),
    or the current revision if `at_or_before` is None."""
    params = {
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "ids|timestamp|content", "rvslots": "main",
        "rvlimit": 1, "format": "json",
    }
    if at_or_before:
        params["rvdir"] = "older"
        params["rvstart"] = at_or_before
    data = get_with_retries(session, params)
    page = list(data["query"]["pages"].values())[0]
    if "missing" in page or not page.get("revisions"):
        return None
    rev = page["revisions"][0]
    return {
        "revid": rev["revid"],
        "timestamp": rev["timestamp"],
        "content": rev["slots"]["main"]["*"],
    }


def safe_slug(title):
    invalid = '<>:"/\\|?*'
    slug = "".join("_" if c in invalid or ord(c) < 32 else c for c in title)
    return slug.strip().replace(" ", "_")


def harvest_title(session, title, out_dir):
    canon = canonical_title(session, title)
    title_dir = out_dir / safe_slug(canon)
    title_dir.mkdir(parents=True, exist_ok=True)

    revisions = fetch_revision_list(session, canon)
    (title_dir / "revisions.json").write_text(
        json.dumps(revisions, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    baseline = fetch_revision_content(session, canon, at_or_before=FORK_DATE)
    if baseline:
        (title_dir / f"baseline_{baseline['revid']}.wikitext").write_text(
            baseline["content"], encoding="utf-8"
        )

    current = fetch_revision_content(session, canon)
    if current:
        (title_dir / f"current_{current['revid']}.wikitext").write_text(
            current["content"], encoding="utf-8"
        )

    return {
        "title": title,
        "canonical_title": canon,
        "revision_count": len(revisions),
        "first_revision": revisions[0]["timestamp"] if revisions else None,
        "last_revision": revisions[-1]["timestamp"] if revisions else None,
        "baseline_revid": baseline["revid"] if baseline else None,
        "current_revid": current["revid"] if current else None,
    }


def load_titles(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--titles-file", required=True)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--manifest",
        default=str(REPO_ROOT / "data" / "interim" / "ru_wikipedia_manifest.jsonl"),
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    titles = load_titles(args.titles_file)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    with open(manifest_path, "a", encoding="utf-8") as manifest_f:
        for title in titles:
            print(f"[{title}] fetching...", file=sys.stderr)
            try:
                record = harvest_title(session, title, out_dir)
            except requests.RequestException as exc:
                print(f"[{title}] FAILED: {exc}", file=sys.stderr)
                continue
            print(f"[{title}] -> {record['canonical_title']!r}, "
                  f"{record['revision_count']} revisions", file=sys.stderr)
            manifest_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            manifest_f.flush()


if __name__ == "__main__":
    main()
