#!/usr/bin/env python3
"""QA a rendered Morning Intel issue. Run after render.py; fix and re-render until it passes.

Usage:
  python3 qa.py issues/2026-10-30.pdf [--html issues/2026-10-30.html] [--max-pages 3] [--json]

Checks (FAIL = exit 1, WARN = printed only):
  pages        FAIL if the PDF has more than --max-pages pages (default 3) or none.
  placeholders FAIL if any {{TEMPLATE_PLACEHOLDER}} survived into the PDF text.
  margins      FAIL if any word's box sits outside the page or more than 3pt into the
               left/right margin, or a left-column line spills across the gutter
               into right-column text (long URLs, wide tables, unbroken code).
  coverage     FAIL if words from the HTML's visible text are missing from the PDF
               text (clipped or hidden content). Needs --html (defaults to the PDF's
               sibling .html).
  orphans      FAIL if a section label or story headline is the last line in its
               column (its text starts in the next column or page).
  weather      FAIL if a Weather section does not contain exactly 4 .stat tiles
               and does not contain "Weather unavailable (NWS API error)".
               The fix is to re-run nws_weather.py --html and paste its block.
  last-page    WARN if the last page is less than 15% filled (consider tightening to
               save a page).
Needs poppler-utils (pdfinfo, pdftotext). Python 3.8+, stdlib only.
"""
import argparse, html as htmlmod, json, pathlib, re, subprocess, sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

NS = "{http://www.w3.org/1999/xhtml}"
MARGIN_X_PT = 0.46 * 72   # default; overridden by the last @page margin found in the HTML
MARGIN_Y_PT = 0.42 * 72
TOL = 3.0


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


class Visible(HTMLParser):
    """Collect visible body text plus the text of .sec and h3 headings."""
    SKIP = {"style", "script", "head", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.text = []
        self.heads = []
        self.cur = None   # [tag, depth, buffer]
        self.depth = 0

    INLINE = {"b", "strong", "i", "em", "span", "a", "code", "small", "sup", "sub"}

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag not in self.INLINE:
            self.text.append(" ")
        if tag in ("br", "img", "meta", "link", "hr", "input"):
            return
        self.depth += 1
        cls = dict(attrs).get("class", "") or ""
        if self.cur is None and (tag == "h3" or (tag == "div" and "sec" in cls.split())):
            self.cur = [tag, self.depth, []]

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        if tag not in self.INLINE:
            self.text.append(" ")
        if self.cur and self.depth == self.cur[1] and tag == self.cur[0]:
            t = " ".join("".join(self.cur[2]).split())
            if t:
                self.heads.append(t)
            self.cur = None
        self.depth -= 1

    def handle_data(self, data):
        if self.skip:
            return
        self.text.append(data)
        if self.cur:
            self.cur[2].append(data)


# Keep this sentence identical to UNAVAILABLE_NOTE in nws_weather.py.
WEATHER_NOTE = "Weather unavailable (NWS API error)"


class WeatherSections(HTMLParser):
    """Split the issue on div.sec headers and count .stat tiles in each section.

    A section runs from its header through the siblings that follow it, up to
    the next div.sec. The weather header is not a wrapper around the tiles.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = []
        self.cur = None

    def handle_starttag(self, tag, attrs):
        cls = (dict(attrs).get("class") or "").split()
        if tag == "div" and "sec" in cls:
            self.cur = {"text": [], "stats": 0}
            self.sections.append(self.cur)
            return
        if self.cur is not None and "stat" in cls:
            self.cur["stats"] += 1

    def handle_data(self, data):
        if self.cur is not None:
            self.cur["text"].append(data)


def weather_block_problems(html_text):
    """FAIL messages for a Weather section that is neither 4 tiles nor the NWS note."""
    parser = WeatherSections()
    parser.feed(html_text)
    problems = []
    for sec in parser.sections:
        flat = " ".join("".join(sec["text"]).split())
        if not flat.lower().startswith("weather"):
            continue
        if sec["stats"] == 4 or WEATHER_NOTE in flat:
            continue
        problems.append(
            "weather: the Weather section has "
            f"{sec['stats']} .stat tile(s), not 4, and does not contain "
            f"\"{WEATHER_NOTE}\". Re-run python3 scripts/nws_weather.py --html "
            "and paste its block verbatim. Do not hand-write weather prose."
        )
    return problems


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def pdf_lines(pdf):
    xml = run(["pdftotext", "-bbox-layout", str(pdf), "-"])
    xml = re.sub(r"<!DOCTYPE[^>]*>", "", xml)
    root = ET.fromstring(xml)
    pages = []
    for pg in root.iter(NS + "page"):
        w, h = float(pg.get("width")), float(pg.get("height"))
        lines = []
        for ln in pg.iter(NS + "line"):
            words = [(float(x.get("xMin")), float(x.get("yMin")), float(x.get("xMax")), float(x.get("yMax")), x.text or "")
                     for x in ln.iter(NS + "word")]
            if words:
                lines.append({"x0": float(ln.get("xMin")), "y0": float(ln.get("yMin")),
                              "x1": float(ln.get("xMax")), "y1": float(ln.get("yMax")),
                              "text": " ".join(t for *_, t in words), "words": words})
        pages.append({"w": w, "h": h, "lines": lines})
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--html")
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    pdf = pathlib.Path(a.pdf)
    html_path = pathlib.Path(a.html) if a.html else pdf.with_suffix(".html")
    fails, warns, info = [], [], {}

    try:
        meta = run(["pdfinfo", str(pdf)])
    except FileNotFoundError:
        sys.exit("qa: pdfinfo not found. Install poppler-utils.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"qa: pdfinfo could not read {pdf} (missing or not a PDF): {e}")
    n = int(re.search(r"^Pages:\s+(\d+)", meta, re.M).group(1))
    info["pages"] = n
    if n < 1 or n > a.max_pages:
        fails.append(f"pages: {n} pages (limit {a.max_pages})")

    mx, my = MARGIN_X_PT, MARGIN_Y_PT
    if html_path.exists():
        m = re.findall(r"@page\s*\{[^}]*margin:\s*([\d.]+)in(?:\s+([\d.]+)in)?", html_path.read_text(encoding="utf-8"))
        if m:
            top, side = m[-1]
            my, mx = float(top) * 72, float(side or top) * 72
    pages = pdf_lines(pdf)
    all_text = "\n".join(l["text"] for p in pages for l in p["lines"])
    ph = sorted(set(re.findall(r"\{\{[^}]*\}\}?", all_text)))
    if ph:
        fails.append(f"placeholders: {len(ph)} left, e.g. {ph[:5]}")

    # margins / overflow
    bad = []
    for i, p in enumerate(pages, 1):
        for l in p["lines"]:
            for x0, y0, x1, y1, t in l["words"]:
                if (x0 < mx - TOL or x1 > p["w"] - mx + TOL or y0 < 0 or y1 > p["h"]
                        or y1 > p["h"] - my + 6):
                    bad.append(f"p{i} '{t[:30]}' x={x0:.0f}-{x1:.0f} y={y0:.0f}-{y1:.0f}")
        # Column intrusion: a line that starts in the left column, crosses the gutter, and
        # shares its height with right-column text (an unbreakable string spilling over).
        mid = p["w"] / 2
        for l in p["lines"]:
            if l["x0"] < mid - 10 and l["x1"] > mid + 10:
                for r in p["lines"]:
                    if r is l or r["x0"] < mid - 5:
                        continue
                    ov = min(l["y1"], r["y1"]) - max(l["y0"], r["y0"])
                    if ov > 0.3 * (l["y1"] - l["y0"]):
                        bad.append(f"p{i} spills across the gutter: '{l['text'][:40]}'")
                        break
    if bad:
        fails.append(f"margins: {len(bad)} item(s) outside the text area, e.g. {bad[:4]}")

    # coverage + orphans need the HTML
    heads = []
    if html_path.exists():
        v = Visible()
        v.feed(html_path.read_text(encoding="utf-8"))
        heads = v.heads
        html_words = [w for w in re.split(r"\s+", htmlmod.unescape("".join(v.text))) if norm(w)]
        stream = norm(all_text.replace("-\n", ""))
        # A word broken across lines/columns (hyphens, dashes, URLs) may be split in the PDF
        # text, so a word counts as present if each of its alphanumeric parts is present.
        missing = [w for w in html_words
                   if norm(w) not in stream and not all(part in stream for part in re.findall(r"[a-z0-9]+", w.lower()))]
        info["html_words"] = len(html_words)
        info["missing_words"] = len(missing)
        if missing:
            fails.append(f"coverage: {len(missing)} of {len(html_words)} HTML words not in the PDF (clipped or hidden?), e.g. {missing[:8]}")
        fails.extend(weather_block_problems(html_path.read_text(encoding="utf-8")))
    else:
        warns.append(f"coverage/orphans/weather skipped: {html_path} not found (pass --html)")

    # orphaned headings: heading text that ends a column
    flat = []  # (page_idx, col, line)
    for pi, p in enumerate(pages):
        mid = p["w"] / 2
        for l in p["lines"]:
            full = (l["x1"] - l["x0"]) > p["w"] * 0.6
            col = "full" if full else ("L" if l["x0"] < mid else "R")
            flat.append((pi, col, l))
    orphans = []
    for h in heads:
        target = norm(h)
        if not target:
            continue
        for i, (pi, col, l) in enumerate(flat):
            t = norm(l["text"])
            if not t or not target.startswith(t) or len(t) < min(6, len(target)):
                continue
            acc, j = t, i
            while acc != target and j + 1 < len(flat) and target.startswith(acc + norm(flat[j + 1][2]["text"])):
                j += 1
                acc += norm(flat[j][2]["text"])
            if acc != target:
                continue
            lpi, lcol, last = flat[j]
            below = [l2 for (pi2, c2, l2) in flat if pi2 == lpi and c2 == lcol and l2["y0"] > last["y1"] - 0.5]
            split = any(flat[k][0] != pi or flat[k][1] != col for k in range(i, j + 1))
            if (not below and lcol != "full") or split:
                orphans.append(f"p{lpi + 1} col {lcol}: '{h[:50]}'")
            break
    if orphans:
        fails.append(f"orphans: {len(orphans)} heading(s) stranded at a column/page end: {orphans}")

    if pages:
        lp = pages[-1]
        if lp["lines"]:
            fill = (max(l["y1"] for l in lp["lines"]) - my) / (lp["h"] - 2 * my)
            info["last_page_fill"] = round(fill, 2)
            if fill < 0.15 and n > 1:
                warns.append(f"last-page: only {fill:.0%} filled; tighten copy to drop a page")

    result = {"ok": not fails, "fails": fails, "warns": warns, "info": info}
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        for f in fails:
            print("FAIL", f)
        for w in warns:
            print("WARN", w)
        print(("PASS" if not fails else "FAIL"), json.dumps(info))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
