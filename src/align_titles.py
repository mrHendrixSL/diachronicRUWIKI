"""Build the title-alignment table joining the two manifests: for each title
we've pulled, how many Ruwiki Wayback snapshots exist vs. how much
ru.wikipedia.org revision history exists, and whether both sides have any
data at all. This is the join key both later steps (diffing, notebook) read
from -- one row per canonical title.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WAYBACK_MANIFEST = REPO_ROOT / "data" / "interim" / "wayback_manifest.jsonl"
RUWIKIPEDIA_MANIFEST = REPO_ROOT / "data" / "interim" / "ru_wikipedia_manifest.jsonl"
OUT_PATH = REPO_ROOT / "data" / "interim" / "title_alignment.jsonl"


def load_jsonl(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    wayback_records = load_jsonl(WAYBACK_MANIFEST)
    ruwikipedia_records = load_jsonl(RUWIKIPEDIA_MANIFEST)

    # The manifest is an append-only log -- re-running the harvester appends
    # the same captures again even though it skips re-downloading files, so
    # dedupe here by (title, timestamp) rather than trusting row count.
    wayback_by_title = defaultdict(dict)
    for r in wayback_records:
        key = r.get("canonical_title", r["title"])
        wayback_by_title[key][r["timestamp"]] = r

    ruwikipedia_by_title = {r["canonical_title"]: r for r in ruwikipedia_records}

    all_titles = set(wayback_by_title) | set(ruwikipedia_by_title)
    rows = []
    for title in sorted(all_titles):
        wb = list(wayback_by_title.get(title, {}).values())
        wb_ok = [r for r in wb if r.get("local_path") and not r.get("fetch_error")]
        rw = ruwikipedia_by_title.get(title)
        rows.append({
            "canonical_title": title,
            "ruwiki_snapshot_count": len(wb_ok),
            "ruwiki_first_snapshot": min((r["timestamp"] for r in wb_ok), default=None),
            "ruwiki_last_snapshot": max((r["timestamp"] for r in wb_ok), default=None),
            "ru_wikipedia_revision_count": rw["revision_count"] if rw else None,
            "ru_wikipedia_first_revision": rw["first_revision"] if rw else None,
            "ru_wikipedia_last_revision": rw["last_revision"] if rw else None,
            "ru_wikipedia_baseline_revid": rw["baseline_revid"] if rw else None,
            "ru_wikipedia_current_revid": rw["current_revid"] if rw else None,
            "both_sides_present": bool(wb_ok) and rw is not None,
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    ready = sum(r["both_sides_present"] for r in rows)
    print(f"{len(rows)} title(s) total, {ready} with data on both sides -> {OUT_PATH}",
          file=sys.stderr)
    for row in rows:
        flag = "OK" if row["both_sides_present"] else "--"
        print(f"  [{flag}] {row['canonical_title']!r}: "
              f"{row['ruwiki_snapshot_count']} Ruwiki snapshot(s), "
              f"{row['ru_wikipedia_revision_count']} ru.wikipedia.org revision(s)",
              file=sys.stderr)


if __name__ == "__main__":
    main()
