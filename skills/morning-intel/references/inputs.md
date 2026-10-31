# Input file formats

All inputs are optional. A missing file means a one-line note (personal feed) or
nothing at all (running window, watchlist, feedback). Never invent the content.

## Personal feed (`personal_feed.file`)

Made by another agent or script that has mailbox and calendar access. The paper only
reads it. Dated header, a coverage line, then four groups of bullets:

```markdown
# Personal feed, 2026-10-30
Coverage: inbox and calendar, last 24 h, checked 05:05 ET.

## Today
- 10:00 Dentist cleaning (calendar)

## Action needed
- Utility bill posted, $84.10 due Nov 12. Pay or confirm AutoPay.

## Alerts
- Bank: new device sign-in notice Oct 29. Confirm it was you.

## Pointers
- Package from <store> arrives Saturday.
```

Rendering: Today → UPCOMING chip per event (CLEAR chip if the group is empty);
Action needed → ACTION; Alerts → ALERT; Pointers → plain line.
If the header date is not today, treat the feed as missing.
Never print passwords, codes, account numbers, or message bodies, even if the feed has them.

## Running window (`running_window.file`)

Pass the file to `scripts/nws_weather.py --running-window`. The script inserts the `.rw` box under the weather tiles; do not also paste it by hand. It skips the `#` heading, turns each bullet and any other non-empty line into an `<li>`, and escapes `&`, `<`, and `>`. Typical shape:

```markdown
# Running window, 2026-10-30 (<park or route>)
- Best time: 6:30-7:30 AM, 52°F, wind 5 mph
- Also OK: 5:00-6:00 PM
- Daylight: 7:31 AM - 6:06 PM
- Concerns: wet leaves on the trail
- Session: easy 30 min
Source: Open-Meteo, fetched 04:50 ET.
```

## Feedback (`feedback_file`)

Free text, newest first. Read it every run and follow it (e.g. "more white space",
"always include AI trends on X", "fewer contract stories"). When a note changes the
layout, change the template once and leave a dated line here saying so.

## Watchlist (`watchlist_file`)

One topic, name, program, or URL per line. Search each one every run and place hits
in the matching section. Lines starting with `#` are comments.

## State (`<workdir>/issues/state.json`)

```json
{"last_issue_no": 12, "last_date": "2026-10-29", "volume": 1}
```

Issue number = last_issue_no + 1 when today's date is newer than last_date;
re-runs on the same date keep the same number. Write the file only after the PDF passes QA.

## Covered list (`<workdir>/issues/covered.txt`)

One line per published story, tab-separated: `date  section  key  url`.
Used for dedupe (sourcing.md §8).
