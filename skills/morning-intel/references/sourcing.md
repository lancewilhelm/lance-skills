# Sourcing playbook: how The Morning Intel finds and checks news

The paper is only useful if every line can be trusted at 6 AM without re-checking.
This file is the research half of the skill. Follow it for every issue.

## 1. Source tiers

Always prefer the highest tier that has the fact. Lower tiers find stories; higher tiers confirm them.

| Tier | What it is | Use it for | Trust rule |
|---|---|---|---|
| **T1 Primary** | The document or the organization itself | Numbers, dates, quotes, official status | Can stand alone. Cite the document, not a story about it. |
| **T2 Trade press / analysts** | Reporters and think tanks who cover the beat full time | Context, scoops, "what it means" | One T2 is enough for context. A T2 scoop with no T1 still gets "reports" language. |
| **T3 Newsletters** | Curated digests in the reader's inbox | Discovery and quick summaries | Never the only cite for a number. Follow the link to T1/T2 and cite that. |
| **T4 Social (X, Reddit, forums)** | Posts and machine-made trend summaries | Signal only: what people are talking about | Never a fact source. Only allowed in "AI Trends on X", always under the caveat note. |
| **Vendor** | A company talking about itself (press release, launch blog, benchmark post) | What the company says | Always label: wrap the figure in `<span class="claim">` and say "the company says" / "vendor-reported". |

### T1 primary sources by section

**Budget and appropriations**
- Service budget books: Air Force/Space Force (DAF) budget materials at `saffm.hq.af.mil` (FM Resources > Budget). R-1 (RDT&E program list) and the R-2/R-2A/R-3 justification exhibits for each program element (PE), e.g. `0602788F`, `0603788F`. Search the PDF for the PE number; quote the FY column and the exhibit date.
- DoD Comptroller: `comptroller.defense.gov` (budget request, reprogrammings, CR guidance).
- Congress: `congress.gov` for bill text, status and reports (H.R./S. numbers, H. Rept./S. Rept.). House and Senate Appropriations and Armed Services committee press pages for markups.
- CRS reports (`congress.gov/crs-products` or `crsreports.congress.gov`) for neutral background.
- OMB (`whitehouse.gov/omb`) for statements of administration policy and apportionment notes.

**S&T (org-specific, e.g. a research lab and its directorates)**
- The lab's own news page and the parent service's release pages (e.g. `afrl.af.mil`, `af.mil`, `spaceforce.mil`, `saf` releases).
- `sam.gov` for solicitations, BAAs, special notices and award notices. Search by office name, NAICS, or the BAA number. Record the notice ID and response date.
- `defense.gov/News/Contracts` (DoD/Department of War daily list of contracts valued at **$7.5M or more**, posted each business day ~5 PM ET). Search the page for the lab, the location (e.g. "Rome, New York"), and the contracting office.
- SBIR/STTR topic and award sites (`dodsbirsttr.mil`, `sbir.gov`) for small-business awards.
- Papers: `arxiv.org`, `pubmed.ncbi.nlm.nih.gov`, `doi.org/<doi>` for anything a lab or company says it published.

**Defense**
- `defense.gov` releases and transcripts, service release pages, combatant command pages, GAO reports (`gao.gov`), DoD IG.
- Contract announcements as above; cross-check large awards against `usaspending.gov` or `sam.gov` when the announcement is unclear.

**AI and tech**
- The lab or company's own blog, model card, paper, repo release, or changelog (`github.com/<org>/<repo>/releases`, `huggingface.co/<org>/<model>`). This is T1 for "what shipped" and **Vendor** for "how good it is".
- Independent evaluations (public leaderboards, academic evals) for performance claims. If none exist yet, say so.
- Government AI policy: `whitehouse.gov`, `nist.gov`, `federalregister.gov`, agency pages.

**Learning, fitness science**
- Course provider pages for course facts (dates, price, length).
- For science: the paper itself (journal page, `doi.org`, PubMed). Report design (RCT / cohort / protocol / review), sample size, population, and the main limitation. A press release or a news story about a study is T2 at best.

**Agent frameworks**
- Release notes, changelogs, docs and repos of the frameworks on the watchlist. Read the actual release, not a tweet about it.

### T2 trade press (defense and budget)
Air & Space Forces Magazine (`airandspaceforces.com`, including its Daily Report), Breaking Defense, Defense News, Inside Defense (often paywalled), DefenseScoop, Federal News Network, Roll Call and Politico Pro (congressional process), CSIS, CNAS, AEI, Brookings and Mitchell Institute analysis (budget). For AI: established tech desks (Reuters, AP, The Verge, Ars Technica, TechCrunch, Wired) and expert newsletters.

### T3 newsletters
Read the configured newsletters from the mailbox (see `newsletters` in the config). Use them to find stories, then open the linked original. A newsletter-only item can run only if it is clearly attributed ("Latent Space reports...") and contains no number you could not confirm.

### T4 social
X trending summaries and posts show what people are discussing. They are machine-generated or unvetted. Rules:
- Only in the **AI Trends on X** section, which always opens with the caveat note from the template.
- Describe the conversation ("posts argue...", "developers debate..."), never assert the underlying claim as fact.
- If a trend points to a real release or paper, find T1 and move the story to the proper section instead.
- List every X item on the could-not-verify list unless you confirmed it in T1.

## 2. Recency windows

Default windows (override in config `recency_hours`):
- Weekday issue: items published since the previous issue's research cutoff (normally ~24 h; Monday covers Fri cutoff to Mon cutoff, ~72 h).
- Budget/appropriations and S&T: up to 72 h if the item is still unreported in prior issues and still current (e.g. a markup scheduled for this week).
- Fitness science and learning: up to 7 days (slower beats).
- Outings: events happening Fri evening through Sunday of this weekend.

An item outside the window runs only as one line of **Context** inside a fresh story.

## 3. Date verification (do this for every story)

1. Find the publication date on the page itself (byline date, `datePublished` meta, release date, PDF cover date, notice posted date). Search snippets and aggregator pages often show the crawl date or a stale cached date.
2. If the page shows "updated", note both dates and use the newer only if the substance changed.
3. If you cannot find a date on the page, either find it in T1 or drop the item (or put it on the could-not-verify list with "date not confirmed").
4. Check the event date separately from the publication date ("announced Oct 29, takes effect Dec 1").
5. Watch the year. Annual items (budget cycles, conferences, "FY" numbers) recycle the same headlines every year.

## 4. Stale and cached search results

- Search tools can return pages from a cache or an index that is hours or days old. Open the live page before you rely on it.
- If the live page and the snippet disagree, the live page wins. If the live page is blocked, say so and do not quote the snippet as current.
- Search "site:<domain> <topic>" for primary sources, and re-run the query with the current month and year to push fresh results up.
- Never treat "no results" as "nothing happened". Check the primary source's own news page directly before writing "no new public news".

## 5. Cross-checking (two-source rule)

A story needs **two independent sources** before it can be stated as fact, unless one of them is T1.
- T1 alone: OK. State it as fact and cite it.
- Two independent T2 (different outlets, not one copying the other): OK as fact, attributed ("Breaking Defense and Defense News report...").
- One T2 only: run it with attribution ("Inside Defense reports..."), and add it to could-not-verify if it carries a number.
- Aggregators, SEO rewrite sites, and AI-written news sites are not independent sources. If an aggregator is the only source, leave the story out and list it under could-not-verify.
- Numbers: copy them from the most primary source, keep units and fiscal year, and say whether it is a ceiling, an obligation, a request, or an appropriation.

## 6. Paywalls

- Do not bypass paywalls. Do not paste paywalled text.
- If a paywalled article is the source, use only what is visible (headline, dek, first paragraph) plus a summary from another outlet that read it, and say so: "per a summary of the WSJ report". Add "full article not read (paywall)" to could-not-verify.
- Prefer the free primary document the article is based on.

## 7. Fact vs claim

- **Fact**: confirmed by T1 or two independent T2. Plain statement.
- **Claim**: what a person or organization says, not yet confirmed. Attribute it ("the company says", "officials said") and, for numbers, wrap it in `<span class="claim">`.
- **Vendor-reported**: any figure a company reports about itself (contract wins before DoD posts them, benchmark scores, user counts, revenue, "first", "best"). Always highlighted, always attributed, and listed in could-not-verify unless independently confirmed.
- Opinion and analysis: label the author ("a CSIS analyst argues...").
- Do not upgrade hedged language. If the source says "could", the paper says "could".

## 8. Dedupe against prior issues

Before writing, load the last 5 issues (`issues/*.html`, newest first) or the previous run's output (Hermes cron `continuity`).
- Drop any story whose core fact already ran, unless there is a real update. If there is, write only the update and add "(update)" to the headline.
- Compare on the underlying event, not the headline: the same contract, the same bill markup, the same model release.
- Keep a running list of "already covered" items in `issues/covered.txt` (one line per story: date, section, key, URL) and append to it after delivery.

## 9. Link checking

- Every cite must be a URL you opened during this run. Prefer canonical URLs, strip tracking parameters (`utm_*`, `ref`, `fbclid`).
- Check each link resolves (HTTP 200 or a normal redirect). If a link 404s, find the replacement or drop the cite.
- Do not cite search-result pages, Google AMP links, or link shorteners.
- Mailbox links (webmail message links) may be used in the Personal section only and must never contain message bodies.

## 10. Weather (NWS, US only)

Do not hand-write the weather block, and do not turn the forecast into a prose paragraph. `scripts/nws_weather.py --html` prints the finished `<div class="wx">...</div>`. Paste that stdout under the Weather header in place of the template's weather div. The agent's job is to pass the config flags and paste the block.

```bash
python3 scripts/nws_weather.py --html \
  --lat 38.8951 --lon -77.0364 --contact you@example.com \
  --tz America/New_York --tz-abbr ET \
  --commute 07:00-08:30 --commute-label "Commute" \
  --jacket-below 60 --umbrella-pop 30 \
  --running-window ~/morning-intel/running-window/YYYY-MM-DD.md
```

Omit `--running-window` when today's file is missing. Pass `--no-commute` when the config has no commute block. `--now` is a test clock for which periods fill the tiles; production runs omit it. The source note always uses the real fetch time.

The script calls `/points/{lat},{lon}`, then `forecast`, `forecastHourly`, and `forecastGridData` (gusts). The User-Agent comes from `--contact`. It does not print the place name from the points response.

Tiles, always four, use NWS period temperatures (never a guessed number):

- **Today's daytime period is still in the feed and has not ended** (a morning run, or any run before that period ends): high = that period, labeled `{Dow} high`; low = the following night, labeled `{Dow} night low`. Rain and wind cover that daytime period through the end of that night.
- **Today's daytime period has ended or is no longer in the feed** (an evening run): high = the next daytime period, labeled with that day (`Sat high`, not `Fri high`); low = the night period still ahead, labeled from the evening it starts (`Fri night low`). Rain and wind cover that night through the end of the next daytime period.
- Rain is the max hourly probability in that window, or the period probability if hourly pop is missing. An em dash means NWS did not send a number. The big wind number is the max grid gust in the window when those values exist, otherwise the max sustained speed. The label says `gusts` only when the number is a gust.
- The one-line forecast is the night period plus the next two daytime periods, using each period's NWS name and `shortForecast`. Do not substitute `detailedForecast`.

The commute verdict (the bold `.verdict` line) is included only on a weekday, and only when the commute window has not yet ended and the hourly forecast covers it. Jacket if the minimum air temperature in the window is at or below `--jacket-below` (default 60°F). Umbrella if any hour's rain chance is at or above `--umbrella-pop` (default 30%). NWS hourly has no feels-like temperature; the script does not invent wind chill. Weekend runs, and runs after the window ends, omit the verdict. They do not borrow the next morning's commute.

If the request fails, or the feed has no high and low period, `--html` prints only:

`<p class="note">Weather unavailable (NWS API error)</p>`

Paste that under the Weather header and list NWS in could-not-verify. Never estimate from memory, a nearby city, or an earlier day.

`qa.py` fails the issue when a Weather section does not contain exactly four `.stat` tiles and does not contain that unavailable note.

Outside NWS coverage the same note is the weather block. Do not write a second forecast from another service into this section.

## 11. Personal feed (email and calendar)

- Read only the feed file named in config (`personal_feed`). It is pre-summarized by another tool or agent.
- Never print passwords, one-time codes, account or card numbers, full addresses of private homes, or message bodies. Summarize ("bill posted, AutoPay on 11/20").
- Map groups to chips: Today → CLEAR (nothing) or UPCOMING (an event); Action needed → ACTION; Alerts → ALERT; Pointers → one plain line.
- If the file is missing or stale (date in the header is not today), print a one-line note and move on.

## 12. Weekend outings (Fridays only)

- Sources: official venue and event pages (museums, parks, city event calendars), the local transit agency's service alerts for the weekend, and one or two local "things to do this weekend" guides for discovery.
- Confirm on the venue's own page: date, time, price, and whether it needs timed passes. Confirm the nearest transit stop.
- Apply the config rules: price cap, transit-only, activity limits. Tag each pick **EASY** or **CHECK WITH DOCTOR** using the config's activity rules. List the exclusions you applied, then print the stop rule exactly as configured.
- Weekend weather in this intro: one short clause copied from the daytime periods already in the pasted weather one-liner. Do not write a separate forecast.

## 13. Citation format

Inline (end of the paragraph that carries the fact):
`<span class="src">domain.tld/path (Mon DD)</span>`
- Drop `https://` and `www.`. Keep enough path to find the page. Long paths are fine; the CSS breaks them.
- Several sources: separate with ` &middot; `.
- Papers: `doi.org/10.xxxx/yyyy` with first author et al. in parentheses when useful.
- Documents: short name plus identifier, e.g. `CRS R4xxxx`, `H. Rept. 119-xxx`, `SAM.gov notice FA8750-xx-S-xxxx`.

SOURCES block at the end (inside `.srcbox`): one line per section in issue order, `Section: cite; cite; cite.` Include weather (gridpoint, fetch time) and any file inputs (feed, running window).

## 14. Could-not-verify list

Inside `.cnv`, numbered `(1) ... (2) ...`. Include every:
- vendor-reported figure not independently confirmed,
- single-T2 number,
- X/social item,
- paywalled article you did not read in full,
- story you dropped because only an aggregator had it (one line, so the reader knows you saw it),
- input that was missing or late (newsletter not arrived, feed missing, NWS error).
If there is nothing to list, write "(none today)". Never delete the block.

## 15. Never fabricate

- No invented quotes, numbers, dates, URLs, DOIs, PE numbers, or names.
- If a section has nothing new that passes these rules, skip the section (or add it to the one-line "nothing new" note). An empty section beats a padded one.
- If you are unsure, it goes on the could-not-verify list, not in the story.
- Public, unclassified information only. Do not speculate about classified programs, and do not combine public facts into a sensitive picture.
