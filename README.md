# Ruwiki Diachronic

A research project measuring how **Ruwiki** (`ruwiki.ru`) — a Russian state-linked fork of Russian Wikipedia — has diverged from the original Russian Wikipedia (`ru.wikipedia.org`) since its creation, and how that divergence keeps evolving over time.

---

## Start here (no installation needed)

Open **[`notebooks/01_wayback_coverage_scan.ipynb`](notebooks/01_wayback_coverage_scan.ipynb)** right here on GitHub. It's already been run, so all the tables and the chart are saved inside it and will just display in your browser — nothing to install, nothing to run.

That notebook answers one core question: *how much of Ruwiki can we actually reconstruct from the Internet Archive's Wayback Machine, since Ruwiki itself blocks direct access?* Short version: quite a lot — **269,204 unique articles** with at least one archived snapshot, spanning June 2023 to mid-2026.

---

## What's in this repo

| Path | What it is |
|---|---|
| `notebooks/01_wayback_coverage_scan.ipynb` | The main notebook — start here |
| `src/` | The Python scripts behind the notebook and the data pull (see below) |
| `data/raw/wayback/` | Downloaded Ruwiki article snapshots (raw HTML), pulled from the Wayback Machine |
| `data/raw/ru_wikipedia/` | Downloaded revision history + article text from the *original* Russian Wikipedia, for the same articles |
| `data/interim/cdx_full_index.parquet` | Full index of every Ruwiki capture the Wayback Machine has (which article, which date, content hash) — this is what the notebook builds |
| `data/interim/title_alignment.jsonl` | Which articles have data on both the Ruwiki side and the original-Wikipedia side, ready for comparison |

Scripts in `src/`:
- `wayback_harvest.py` — downloads Ruwiki article snapshots from the Wayback Machine
- `ruwikipedia_pull.py` — downloads matching article history from `ru.wikipedia.org`
- `align_titles.py` — joins the two into `title_alignment.jsonl`
- `check_titles.py` — sanity-checks a title before trusting a "no data found" result (see note below)

## If you want to run things yourself

1. Install Python 3.11+
2. `pip install -r requirements.txt`
3. Open the notebook in Jupyter or VS Code and run the cells — or run the scripts directly, e.g. `python src/wayback_harvest.py --titles-file src/seed_titles.txt`

---

## Background

- Ruwiki was created by copying roughly 1.9 million articles from `ru.wikipedia.org` in June 2023 (public beta June 2023, full launch January 2024).
- Since the fork, Ruwiki has been edited under separate, reportedly state-influenced editorial control. Content on politically sensitive topics has been reported to be rewritten or removed.
- This is a **live, ongoing** divergence, not a one-time snapshot: both wikis have kept editing independently since the fork, so the gap between them is still growing.
- Two existing academic studies have already done smaller-scale versions of this comparison:
  - Zhuravskaya, Matter, Durante & Avetian, *"The Anatomy of Censorship and Propaganda: Evidence from Russian Wikipedias"* (CEPR Discussion Paper 21698, 2026).
  - Vestel & Degaetano-Ortlieb, *"Rewriting Reality: Tracking Russian Propaganda Through Wikipedia"* (DH2026 poster, Saarland University).

  Neither team's underlying dataset is publicly available as of this writing — this project is an independent attempt to build our own.

## Why we're pulling from the Wayback Machine instead of Ruwiki directly

Ruwiki blocks direct access from our network (confirmed HTTP 401/403 on both the site and its API). The Internet Archive's Wayback Machine, however, has been extensively crawling `ru.ruwiki.ru` since its June 2023 launch. The data in this repo — snapshots, manifests, the full coverage index — is what that archive already holds and makes freely viewable to anyone at web.archive.org; we're just re-hosting local copies of that same public material in one convenient place.

One trap worth knowing: Russian Wikipedia titles biography pages "Surname, Given Names" (e.g. `Путин, Владимир Владимирович`, not `Владимир Путин`). Querying the natural word order looks like the article is missing — it's just the wrong title. `check_titles.py` resolves this against `ru.wikipedia.org`'s own redirect table before concluding anything is actually absent.

## Status

- 269,204 unique Ruwiki articles have at least one Wayback snapshot (~14% of Ruwiki's ~1.9M total) — see the notebook for the full breakdown.
- A small proof-of-concept sample (9 articles) has been pulled on both sides and aligned, ready for diffing.
- Diffing / change-measurement itself hasn't been built yet.

## Research questions (open)

- Which topics see the most rewriting? Does it match the "three pillars" the CEPR paper identified (Russia's international image, domestic politics/opposition, war/Ukraine)?
- How much is outright deletion vs. substantial rewriting vs. left untouched?
- Do Ruwiki's edit timestamps show a pattern distinct from volunteer editing (e.g. clustering in weekday office hours, suggesting paid staff)?
- Can we detect euphemistic reframing (e.g. "invasion" → "special military operation") systematically, not just anecdotally?
- Is divergence concentrated at the fork itself, or does it keep accumulating afterward?

## Open questions for the team

- **Scope**: mine as much of Ruwiki as the Wayback Machine allows (269K articles), or focus on a curated, hypothesis-driven sample?
- **Live access**: worth attempting a Russian-based connection to Ruwiki directly, given it blocks this network outright?
- **Prior work**: reach out to the CEPR / DH2026 authors for their data or methodology?
- **Output**: a public dataset, a paper, both?

## Contributors

- [fill in]
