---
name: morning-intel
description: Build a daily newspaper-style PDF intel brief.
version: 0.1.0
author: Lance (lancewilhelm), Hermes Agent
license: Apache-2.0
platforms:
  - linux
  - macos
metadata:
  hermes:
    tags:
      - news
      - briefing
      - pdf
      - newspaper
      - research
      - daily
    category: productivity
    requires_toolsets:
      - web
      - terminal
      - file
    config:
      - key: morning_intel.config_path
        description: "Path to your morning-intel.yaml (copy of references/config.example.yaml)"
        default: "~/morning-intel/morning-intel.yaml"
        prompt: "Where is your Morning Intel config file?"
    blueprint:
      schedule: "0 5 * * *"
      deliver: origin
      prompt: "Produce today's issue of The Morning Intel using the morning-intel skill and my config."
---

# Morning Intel Skill

Researches the morning's news on a fixed set of topics, checks it against primary sources,
and lays it out as a 2-3 page, two-column US Letter PDF newspaper ("The Morning Intel"):
masthead, BLUF card, weather, personal items, intel sections, Friday outings, sources and a
could-not-verify list. Rendering is headless Chrome; QA is poppler. No Python packages needed.

## When to Use

- "Make this morning's paper / brief / Morning Intel", or a scheduled cron run of this skill.
- Re-running today's issue after a fix (same issue number, overwrite).
- Don't use for: one-off research answers, long reports, or slide decks.

## Prerequisites

- Chrome or Chromium (`google-chrome`, `chromium`, or set `CHROME=/path`). Playwright's Chromium also works.
- poppler-utils (`pdftoppm`, `pdfinfo`, `pdftotext`): `apt install poppler-utils` / `brew install poppler`.
- Fonts Inter, IBM Plex Serif, IBM Plex Mono: run `scripts/install_fonts.sh` once (downloads the OFL fonts from github.com/google/fonts).
- Python 3.9+ (stdlib only).
- A config file made from `references/config.example.yaml` (skill config key `morning_intel.config_path`).
- Optional inputs, formats in `references/inputs.md`: personal feed, running window, watchlist, feedback file.
- Mail access for newsletters (whatever mailbox tool this agent has, e.g. the Himalaya skill). If none, skip newsletters and say so in could-not-verify.

## How to Run

Through the `terminal` tool, from the skill directory (`${HERMES_SKILL_DIR}`):

```bash
python3 scripts/nws_weather.py --lat 38.8951 --lon -77.0364 --contact you@example.com --commute 07:00-08:30
python3 scripts/render.py ~/morning-intel/issues/2026-10-30.html      # -> .pdf + -page-N.png
python3 scripts/qa.py ~/morning-intel/issues/2026-10-30.pdf --max-pages 3
```

## Quick Reference

| File | Purpose |
|---|---|
| `templates/newspaper.html` | Fill-in template (CSS is final; fill `{{...}}`, delete unused blocks) |
| `scripts/render.py` | HTML → PDF (Chrome headless) + page PNGs (pdftoppm, 110 dpi). Exit 2 missing dep, 3 render fail |
| `scripts/qa.py` | Page count, leftover `{{`, margin/gutter overflow, clipped words, orphaned headings. Exit 1 on FAIL |
| `scripts/nws_weather.py` | NWS forecast JSON: high/low, rain %, wind, gusts, commute hours, source URLs |
| `scripts/install_fonts.sh` | Installs Inter, IBM Plex Serif, IBM Plex Mono |
| `references/sourcing.md` | Source tiers, recency, two-source rule, dedupe, paywalls, citations. **Read every run** |
| `references/config.example.yaml` | Config template (location, commute, sections, newsletters, outings, delivery) |
| `references/inputs.md` | Personal feed, running window, feedback, watchlist, state and covered-list formats |
| `examples/sample-issue.html` | A filled-in fictional issue showing every block |
| `examples/sample-issue.pdf`, `examples/sample-issue-page-1.png`, `examples/sample-issue-page-2.png` | What the output should look like |

## Procedure

Work in the config's `workdir` (default `~/morning-intel`). Paths below are relative to it.

0. **Load.** Read the config, `references/sourcing.md`, `feedback_file`, `watchlist_file`, `issues/state.json`, and the last 5 `issues/*.html` (or the injected previous-run output). Done when you know today's date, weekday, issue number, and what already ran.
1. **Gather.** For each section in config order, search within the recency window (sourcing.md §2), read the configured newsletters, run the watchlist, run `scripts/nws_weather.py`, and read the personal feed and running-window files if present. Keep a scratch list: claim, URL, publish date, tier. Done when every section has candidates or is marked empty.
2. **Verify.** Open every page you will cite. Confirm the date on the page, apply the two-source rule, label vendor figures, drop aggregator-only items, dedupe against prior issues (sourcing.md §3-§9). Anything uncertain moves to the could-not-verify list. Done when every kept item has a working T1 link or two independent T2 links.
3. **Write.** Copy `templates/newspaper.html` to `issues/YYYY-MM-DD.html` and fill it (rules below). Done when no `{{` remains and every unused block is deleted.
4. **Lay out.** Fit to at most 3 pages by cutting words, never by editing CSS: shorten the lowest-value story, then drop the weakest item in the longest section, then trim Context lines.
5. **Render.** `python3 scripts/render.py issues/YYYY-MM-DD.html`. Done when the PDF and `-page-N.png` files exist.
6. **QA.** `python3 scripts/qa.py issues/YYYY-MM-DD.pdf --max-pages 3` must PASS. Then look at each page PNG (`vision_analyze` or `read_file`): no clipped text, no heading alone at a column or page bottom, no table row split across columns, chips readable. Fix by cutting text, re-render, re-run QA. Done when QA passes and the PNGs look like `examples/sample-issue-page-1.png`.
7. **Deliver.** Update `issues/state.json` and append to `issues/covered.txt`. Final response: the 2-3 line BLUF in plain text, then `MEDIA:/absolute/path/issues/YYYY-MM-DD.pdf` on its own line. Done when the response is the only output (cron delivers it; see Hermes section).

## Content rules

**Masthead.** "The Morning Intel", long weekday date, `Vol. N · No. M` (issue number counts up by 1 per publishing day; state in `issues/state.json`), edition line, research cutoff time with zone.

**Section order** (skip any that is empty; never pad):
1. **BLUF** card: 3-4 lines, the most decision-relevant facts first, one line per theme.
2. **Weather** (NWS): big numbers for high, low, rain chance, wind; bold commute line (jacket / umbrella) on weekdays only; running-window box pasted verbatim if today's file exists, otherwise omitted; one small NWS source note.
3. **Personal**: from the feed file only, groups Today / Action needed / Alerts / Pointers with ACTION, ALERT, UPCOMING, CLEAR chips. Missing or stale feed → one-line note. Never passwords, codes, account numbers, or message bodies.
4. **Intel**, in this order: Budget and appropriations; S&T (org-specific); Defense; AI and tech; AI Trends on X (always keep its caveat note; signal, not fact); Learning; Fitness science; Agent frameworks (every item ends with a `Worth stealing:` box saying what to copy into your own agent setup). Sections with nothing new go in one "nothing new today" line.
5. **Weekend Outings**, Fridays only: 4-6 free or cheap, transit-reachable picks, each tagged EASY or CHECK WITH DOCTOR per config, then the exclusions line and the stop rule.
6. **Sources** block (one line per section) and **COULD NOT VERIFY** list, always present ("(none today)" if empty).

**Story shape.** Headline (plain, specific), then 2-4 short paragraphs: what happened (BLUF style, the fact first), why it matters to this reader, optional `Context:` line, cite at the end. 40-110 words per story. "In brief" one-liners are fine for minor items.

**Fact vs claim.** State facts plainly with a cite. Attribute claims ("the company says"). Wrap every vendor-reported or single-source number in `<span class="claim">` and list it under could-not-verify. Never upgrade "could" to "will".

**Never fabricate.** No invented numbers, quotes, links, DOIs, dates or events. Public, unclassified information only. If in doubt, leave it out or list it.

**Feedback.** Apply every note in `feedback_file` (e.g. spacing, sections to always include, topics of interest).

## Hermes: scheduling and delivery

Facts below are from the Hermes Agent docs (NousResearch/hermes-agent, main branch, checked 2026-10-30). Items marked **(unverified)** are not stated in the docs; test them before relying on them.

- **Cron runs in the gateway.** Install it as a service with `hermes gateway install`, or jobs never fire. [cron docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md)
- **Delivery is automatic.** "The agent's final response is automatically delivered to the configured `deliver:` target — the agent does not send messages itself." So the run must end with the BLUF + `MEDIA:` line and must not send mail itself. This also gives one send per issue.
- **Email target.** Configure the email gateway with `hermes gateway setup` (see the email docs for the variables); `EMAIL_HOME_ADDRESS` is the "default delivery target for cron jobs". "Include `MEDIA:/path/to/file` in the response and the file is attached to the outgoing email." The docs recommend a dedicated mailbox. [email docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/email.md)
- **Weekday email, weekend chat.** Two jobs (cron expressions are read in `--timezone` or the profile timezone):

  ```bash
  hermes cron create "30 5 * * 1-5" "Produce today's Morning Intel." --skill morning-intel \
    --name "Morning Intel (weekday email)" --deliver email --timezone America/New_York
  hermes cron create "0 6 * * 0,6" "Produce today's Morning Intel." --skill morning-intel \
    --name "Morning Intel (weekend)" --deliver origin --timezone America/New_York
  ```

  Or from chat with the `cronjob` tool: `cronjob(action="create", skill="morning-intel", prompt="...", schedule="30 5 * * 1-5", name="...", deliver="email", continuity=True)`.
- **Dedupe across runs.** `continuity=True` (cronjob tool) injects the job's own last output so the run can "avoid repeating what was already reported". The CLI `create` has no flag for it; use the tool or keep `issues/covered.txt`.
- **Wrapper text.** Delivered output gets a "Cronjob Response:" header and footer unless `cron.wrap_response: false` in `~/.hermes/config.yaml`.
- **Attachments.** Each media send times out after `cron.media_send_timeout_seconds` (default 300). A timed-out attachment still delivers the text.
- **Installing this skill** gives it a suggested daily job (the `blueprint` above); accept it with `/suggestions accept N` or ignore it and create the two jobs above. [creating-skills docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/creating-skills.md)
- **(unverified)** Setting a custom email subject for cron delivery. The docs do not describe one; expect a default subject.
- **(unverified)** That the email adapter attaches `MEDIA:` files on cron deliveries the same way it does on replies. Test with `hermes cron run <job>` and check the inbox before the first real morning.
- **(unverified)** A "check Sent before retrying" step: Hermes tracks delivery itself (`hermes cron runs`, `last_status: delivery_failed`). If a delivery fails, look there and re-send by hand with `hermes send` rather than re-running the job.

## Pitfalls

- **Stale search results.** Search snippets can show old dates. Open the live page and read its date (sourcing.md §3-§4).
- **Fonts missing** → Chrome substitutes and the layout reflows to 4 pages. `render.py` warns; run `scripts/install_fonts.sh`.
- **Do not pass `--user-data-dir` to Chrome** in `render.py`; with a fresh profile dir headless Chrome can hang until the timeout.
- `pdftoppm` prints "Syntax Warning: Bad bounding box in Type 3 glyph" for some emoji fonts. Harmless.
- QA cannot see a table row split across columns or a chip cut in half; that is why step 6 includes looking at the PNGs. The template's `break-inside: avoid` rule prevents most of it.
- Don't edit the CSS to make an issue fit. Cut words. CSS edits drift the look away from the examples.
- Escape `&`, `<`, `>` in filled text (`&amp;`), or the HTML breaks silently.
- Cron jobs start with no memory; without `continuity` or `covered.txt` the paper repeats yesterday's stories.
- NWS is US-only and flaky at times (500/503). The script retries; after that, print the one-line note, never estimated weather.

## Verification

- `python3 scripts/render.py examples/sample-issue.html --pdf /path/to/out.pdf` then `python3 scripts/qa.py /path/to/out.pdf` prints `PASS` with 2 pages.
- Today's issue: `qa.py` PASS, ≤ 3 pages, the PNGs match the look of `examples/sample-issue-page-1.png`, every cite opens, and the could-not-verify block is present.
- After the first scheduled run: `hermes cron runs` shows `ok` (not `delivery_failed`) and the email arrived with the PDF attached.
