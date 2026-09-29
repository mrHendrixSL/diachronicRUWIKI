"""Given a titles file, print ru.wikipedia.org's canonical (post-redirect)
title and the Wayback capture count on ru.ruwiki.ru for each -- a sanity
check for title-format guesses (e.g. biographical "Surname, Given Names")
before feeding them to the harvester."""

import sys

import requests

from wayback_harvest import USER_AGENT, cdx_query

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT


def canonical_title(title):
    resp = session.get(
        "https://ru.wikipedia.org/w/api.php",
        params={"action": "query", "titles": title, "redirects": 1, "format": "json"},
        timeout=30,
    )
    data = resp.json()["query"]
    if "redirects" in data:
        target = data["redirects"][0]["to"]
    else:
        target = title
    page = list(data["pages"].values())[0]
    return target, "missing" in page


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        titles = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for title in titles:
        canon, missing = canonical_title(title)
        captures = cdx_query(session, canon) if not missing else []
        print(f"{title!r} -> canonical {canon!r} (missing={missing}) -> {len(captures)} Wayback capture(s)")
