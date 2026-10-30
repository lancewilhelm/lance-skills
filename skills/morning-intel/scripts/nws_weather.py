#!/usr/bin/env python3
"""Fetch an NWS forecast and, with --html, print the weather block to paste.

Usage:
  python3 nws_weather.py --html --lat 38.8951 --lon -77.0364 \\
      --contact you@example.com --tz America/New_York --tz-abbr ET \\
      --commute 07:00-08:30 --jacket-below 60 --umbrella-pop 30 \\
      [--commute-label Commute] [--running-window PATH] [--now ISO] [--save-raw DIR]

Paste --html stdout into the issue verbatim, in place of the template's
<div class="wx">. Do not hand-write weather prose and do not re-tile the numbers.

The block is four .stat tiles (high, low, rain chance, wind), a one-line
forecast, a weekday commute verdict when the window has not ended, the
running-window box if PATH exists, and the source note.

Tile rules, in --tz, using --now or the actual time:
  today   Today's daytime period is still in the feed and has not ended
          (morning, or any run before that period ends). High = that period.
          Low = the following night. Labels use those weekdays ("Fri high",
          "Fri night low").
  next    Today's daytime period has ended or dropped out of the feed
          (evening). High = the next daytime period, labeled as that day
          ("Sat high", never "Fri high"). Low = the night still ahead,
          labeled from the evening it starts ("Fri night low").

Rain and wind cover that same span. The big wind number is the max grid gust
when NWS sent gusts, otherwise the max sustained speed. The label says
"gusts" only when the number is a gust. Missing rain or wind is an em dash,
not a guess. The one-liner uses each period's NWS name and shortForecast,
not detailedForecast.

The commute verdict is omitted on Saturday and Sunday, after the window
ends, with --no-commute, or when hourly data does not cover the window.
Jacket uses the minimum air temperature in the window (NWS hourly has no
feels-like; this script does not invent wind chill). Umbrella uses the max
rain chance in the window. Defaults: jacket at or below 60°F, umbrella at
or above 30%.

If the API fails, or the feed has no high and low, --html prints only
<p class="note">Weather unavailable (NWS API error)</p> and exits 0 so that
note can be pasted. JSON mode (no --html) still exits 2 on failure.
--now changes which periods are selected; the source note always shows the
real fetch time. Never estimate.

NWS requires a User-Agent with an app name and a contact
(https://www.weather.gov/documentation/services-web-api). US locations only.
Python 3.9+, stdlib only.
"""
import argparse, datetime as dt, json, pathlib, re, sys, time, urllib.request
from html import escape as html_escape
from zoneinfo import ZoneInfo

API = "https://api.weather.gov"
# Keep this sentence identical to the check in qa.py.
UNAVAILABLE_NOTE = "Weather unavailable (NWS API error)"
UNAVAILABLE_HTML = f'<p class="note">{UNAVAILABLE_NOTE}</p>'
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return html_escape(str(s), quote=True)


def get(url, ua, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:  # NWS returns intermittent 500/503; retry with backoff
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"{url}: {last}")


def mph_nums(s):
    return [int(n) for n in re.findall(r"\d+", s or "")]


def as_int(n):
    if n is None:
        return None
    if isinstance(n, float):
        return int(n) if n.is_integer() else int(round(n))
    return int(n)


def aware(iso, tz):
    s = str(iso).replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=tz)
    return t.astimezone(tz)


def parse_now(value, tz):
    if not value:
        return dt.datetime.now(tz)
    s = value.strip().replace("Z", "+00:00")
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"--now must be an ISO datetime, got {value!r}") from e
    if t.tzinfo is None:
        t = t.replace(tzinfo=tz)
    return t.astimezone(tz)


def parse_hhmm(s):
    h, m = s.strip().split(":")
    return dt.time(int(h), int(m))


def parse_window(s):
    try:
        a, b = s.split("-")
        return parse_hhmm(a), parse_hhmm(b)
    except Exception as e:
        raise ValueError(f"--commute must be HH:MM-HH:MM, got {s!r}") from e


def parse_duration(s):
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", s or "")
    if not m:
        return dt.timedelta(hours=1)
    days, hours, minutes, seconds = (int(x or 0) for x in m.groups())
    span = dt.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return span if span.total_seconds() > 0 else dt.timedelta(hours=1)


def to_mph(value, uom):
    u = (uom or "km_h").lower()
    if "km" in u:
        mph = value * 0.621371
    elif "m_s" in u or "m/s" in u:
        mph = value * 2.23694
    else:
        mph = float(value)
    return int(round(mph))


def unit_letter(p):
    return "C" if str(p.get("unit") or "F").upper().startswith("C") else "F"


def day_abbr(t):
    return DOW[t.weekday()]


def night_abbr(p):
    """Weekday of the evening a night period belongs to.

    A period that starts after noon is that calendar evening ("Friday Night"
    → Fri). One that starts after midnight is the tail of the previous night.
    """
    start = p["start"]
    if start.hour < 12:
        start = start - dt.timedelta(days=1)
    return day_abbr(start)


def clip_short(s):
    s = " ".join((s or "").split())
    i = s.lower().find(" then ")
    if i != -1:
        s = s[:i].rstrip(" ,;")
    return s


def fmt_stamp(t, tz_abbr):
    h = t.hour % 12 or 12
    ampm = "AM" if t.hour < 12 else "PM"
    return f"{DOW[t.weekday()]} {MON[t.month - 1]} {t.day} at {h}:{t.minute:02d} {ampm} {esc(tz_abbr)}"


def fmt_span(t0, t1):
    def clock(t):
        h = t.hour % 12 or 12
        suf = "AM" if t.hour < 12 else "PM"
        return f"{h}:{t.minute:02d}", suf
    a, sa = clock(t0)
    b, sb = clock(t1)
    if sa == sb:
        return f"{a}&ndash;{b} {sa}"
    return f"{a} {sa}&ndash;{b} {sb}"


def overlaps(a0, a1, b0, b1):
    return a0 < b1 and a1 > b0


def wind_bits(raw, direction):
    nums = mph_nums(raw)
    d = direction or ""
    if nums:
        lo, hi = min(nums), max(nums)
        plain_rng = f"{lo} mph" if lo == hi else f"{lo}–{hi} mph"
        html_rng = f"{lo} mph" if lo == hi else f"{lo}&ndash;{hi} mph"
    else:
        plain_rng = html_rng = ""
    plain = " ".join(x for x in (d, plain_rng) if x)
    html = " ".join(x for x in (esc(d) if d else "", html_rng) if x)
    return plain, html


def choose_periods(periods, now):
    """Return (mode, high, low). mode is 'today' or 'next'. See the module docstring."""
    today = now.date()
    today_day = next((p for p in periods if p["is_day"] and p["start"].date() == today and p["end"] > now), None)
    if today_day is not None:
        low = next((p for p in periods if (not p["is_day"]) and p["start"] >= today_day["start"] and p["end"] > now), None)
        return "today", today_day, low
    low = next((p for p in periods if (not p["is_day"]) and p["end"] > now), None)
    high = next((p for p in periods if p["is_day"] and p["end"] > now), None)
    return "next", high, low


def tile_window(mode, high, low):
    if mode == "today":
        start = high["start"]
        end = low["end"] if low else high["end"]
    else:
        start = low["start"] if low else high["start"]
        end = high["end"] if high else low["end"]
    if end <= start:
        end = start + dt.timedelta(hours=1)
    return start, end


def dominant_dir(hours):
    counts = {}
    for h in hours:
        if h.get("dir"):
            counts[h["dir"]] = counts.get(h["dir"], 0) + 1
    best = None
    chosen = None
    for d, count in counts.items():
        peak = 0
        for h in hours:
            if h.get("dir") == d and h.get("winds"):
                peak = max(peak, max(h["winds"]))
        key = (count, peak, d)
        if best is None or key > best:
            best = key
            chosen = d
    return chosen


def high_labels(p):
    abbr = day_abbr(p["start"])
    short = clip_short(p["short"])
    plain = f"{abbr} high" + (f" · {short}" if short else "")
    html = f"{abbr} high" + (f" &middot; {esc(short)}" if short else "")
    return plain, html


def low_labels(p):
    plain = f"{night_abbr(p)} night low"
    return plain, plain


def period_line(p, wind=False, with_high=False):
    plain_bits, html_bits = [], []
    if p["short"]:
        plain_bits.append(p["short"])
        html_bits.append(esc(p["short"]))
    if with_high and p["is_day"] and p["temp"] is not None:
        n = as_int(p["temp"])
        unit = unit_letter(p)
        plain_bits.append(f"high {n}°{unit}")
        html_bits.append(f"high {n}&deg;{unit}")
    if wind:
        plain_w, html_w = wind_bits(p["wind"], p["dir"])
        if plain_w:
            plain_bits.append(plain_w)
            html_bits.append(html_w)
    pop = as_int(p["pop"]) if p["pop"] is not None else None
    if pop is not None and pop > 0:
        plain_bits.append(f"{pop}% rain")
        html_bits.append(f"{pop}% rain")
    if not plain_bits:
        return p["name"], esc(p["name"])
    return f"{p['name']}: {', '.join(plain_bits)}", f"{esc(p['name'])}: {', '.join(html_bits)}"


def forecast_lines(periods, low):
    chosen = []
    if low:
        chosen.append((low, True, False))
        follow = [p for p in periods if p["is_day"] and p["start"] >= low["end"]][:2]
        chosen.extend((p, False, True) for p in follow)
    parts = [period_line(p, wind=wind, with_high=with_high) for p, wind, with_high in chosen]
    if not parts:
        return "", ""
    plain = ". ".join(p for p, _ in parts) + "."
    html = ". ".join(h for _, h in parts) + "."
    return plain, html


def wind_tile_label(direction, sustained, gust):
    d = esc(direction) if direction else ""
    if sustained:
        lo, hi = min(sustained), max(sustained)
        rng = f"{lo} mph sust." if lo == hi else f"{lo}&ndash;{hi} sust."
    else:
        rng = ""
    if gust is not None and rng:
        body = f"{d} gusts &middot; {rng}".strip()
    elif gust is not None:
        body = (f"{d} gusts".strip() or "Gusts")
    elif rng:
        body = f"{d} wind &middot; {rng}".strip()
    else:
        body = "Wind"
    plain_rng = ""
    if sustained:
        lo, hi = min(sustained), max(sustained)
        plain_rng = f"{lo} mph sust." if lo == hi else f"{lo}–{hi} sust."
    if gust is not None and plain_rng:
        plain = f"{direction} gusts · {plain_rng}".strip() if direction else f"gusts · {plain_rng}"
    elif gust is not None:
        plain = f"{direction} gusts".strip() if direction else "Gusts"
    elif plain_rng:
        plain = f"{direction} wind · {plain_rng}".strip() if direction else f"wind · {plain_rng}"
    else:
        plain = "Wind"
    return " ".join(plain.split()), " ".join(body.split())


def stat(number_html, label_html):
    return f'<div class="stat"><div class="n">{number_html}</div><div class="l">{label_html}</div></div>'


def temp_html(value, unit):
    if value is None:
        return "&mdash;"
    return f"{as_int(value)}<small>&deg;{esc(unit)}</small>"


def suffixed(value, suffix):
    if value is None:
        return "&mdash;"
    return f"{as_int(value)}<small>{suffix}</small>"


def commute_bounds(now, tz, start_t, end_t):
    start = dt.datetime.combine(now.date(), start_t, tzinfo=tz)
    end = dt.datetime.combine(now.date(), end_t, tzinfo=tz)
    if end <= start:
        end += dt.timedelta(days=1)
    return start, end


def running_window_html(path):
    if not path:
        return ""
    file = pathlib.Path(path)
    if not file.is_file():
        print(f"nws_weather: running window not found ({file}); omitted", file=sys.stderr)
        return ""
    items = []
    for line in file.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s[:2] in ("- ", "* "):
            s = s[2:].strip()
        if s:
            items.append(esc(s))
    if not items:
        return ""
    lis = "".join(f"<li>{item}</li>" for item in items)
    return f'<div class="rw"><div class="t">Running window</div><ul>{lis}</ul></div>'


def source_note(grid, fetched, updated, tz_abbr):
    gp = f"{esc(grid['office'])}/{grid['x']},{grid['y']}"
    text = f"Source: NWS API, gridpoint {gp} (forecast and hourly), fetched {fmt_stamp(fetched, tz_abbr)}."
    if updated is not None:
        text += f" NWS last updated the forecast at {fmt_stamp(updated, tz_abbr)}."
    return f'<div class="note">{text}</div>'


def brief(p):
    if not p:
        return None
    return {"name": p["name"], "temp_f": p["temp"], "temp_unit": unit_letter(p), "wind": p["wind"],
            "dir": p["dir"], "pop": p["pop"], "short": p["short"]}


def assemble(now, fetched, tz, tz_abbr, periods, hours, gusts, grid, updated, updated_raw,
             commute, commute_label, jacket_below, umbrella_pop, no_commute, rw_html, sources):
    """Build the weather block. Returns None when a high and a low cannot both be filled."""
    mode, high, low = choose_periods(periods, now)
    if high is None or low is None or high.get("temp") is None or low.get("temp") is None:
        return None
    w0, w1 = tile_window(mode, high, low)
    win_hours = [h for h in hours if overlaps(h["start"], h["end"], w0, w1)]
    pops = [h["pop"] for h in win_hours if h["pop"] is not None]
    if not pops:
        pops = [p["pop"] for p in (high, low) if p["pop"] is not None]
    rain = as_int(max(pops)) if pops else None
    sustained = [n for h in win_hours for n in h["winds"]]
    if not sustained:
        sustained = mph_nums(high["wind"]) + mph_nums(low["wind"])
    direction = dominant_dir(win_hours) or high.get("dir") or low.get("dir") or ""
    gust_vals = [g["mph"] for g in gusts if overlaps(g["start"], g["end"], w0, w1)]
    gust = max(gust_vals) if gust_vals else None
    wind_number = gust if gust is not None else (max(sustained) if sustained else None)
    high_plain, high_html = high_labels(high)
    low_plain, low_html = low_labels(low)
    wind_plain, wind_html = wind_tile_label(direction, sustained, gust)
    fc_plain, fc_html = forecast_lines(periods, low)
    high_unit = unit_letter(high)
    low_unit = unit_letter(low)

    verdict_html = ""
    verdict_plain = None
    status = "included"
    commute_rows = []
    if no_commute:
        status = "omitted: disabled"
    elif now.weekday() >= 5:
        status = "omitted: weekend"
    else:
        c0, c1 = commute_bounds(now, tz, commute[0], commute[1])
        if now >= c1:
            status = "omitted: window passed"
        else:
            ch = [h for h in hours if overlaps(h["start"], h["end"], c0, c1) and h["temp"] is not None]
            if not ch:
                status = "omitted: no hourly coverage"
            else:
                temps = [h["temp"] for h in ch]
                cpops = [h["pop"] for h in ch if h["pop"] is not None]
                cwinds = [n for h in ch for n in h["winds"]]
                cdir = dominant_dir(ch) or ""
                lo, hi = as_int(min(temps)), as_int(max(temps))
                temp_plain = f"{lo}°F" if lo == hi else f"{lo}–{hi}°F"
                commute_temp = f"{lo}&deg;F" if lo == hi else f"{lo}&ndash;{hi}&deg;F"
                if not cpops:
                    rain_p, rain_h = "rain chance not reported", "rain chance not reported"
                    umbrella = "umbrella not reported"
                elif max(cpops) <= 0:
                    rain_p = rain_h = "dry"
                    umbrella = "umbrella no"
                else:
                    pct = as_int(max(cpops))
                    rain_p = rain_h = f"rain {pct}%"
                    umbrella = "umbrella yes" if pct >= umbrella_pop else "umbrella no"
                if cwinds:
                    wlo, whi = min(cwinds), max(cwinds)
                    wind_p = f"{cdir} {wlo} mph".strip() if wlo == whi else f"{cdir} {wlo}–{whi} mph".strip()
                    wind_h = f"{esc(cdir)} {wlo} mph".strip() if wlo == whi else f"{esc(cdir)} {wlo}&ndash;{whi} mph".strip()
                else:
                    wind_p, wind_h = "wind not reported", "wind not reported"
                jacket = "Jacket yes" if min(temps) <= jacket_below else "Jacket no"
                span = f"{jacket}, {umbrella}."
                when = fmt_span(commute[0], commute[1])
                label = esc(commute_label)
                verdict_plain = f"{commute_label}, {when.replace('&ndash;', '–')}: {temp_plain}, {rain_p}, {wind_p}. {span}"
                verdict_html = (f'<div class="verdict">{label}, {when}: {commute_temp}, {rain_h}, {wind_h}. '
                                f"<span>{esc(span)}</span></div>")
                for h in ch:
                    commute_rows.append({
                        "time": h["start"].strftime("%H:%M"), "temp_f": h["temp"], "pop": h["pop"],
                        "wind": h["wind"], "dir": h["dir"], "short": h["short"],
                    })

    tiles = [
        stat(temp_html(high["temp"], high_unit), high_html),
        stat(temp_html(low["temp"], low_unit), low_html),
        stat(suffixed(rain, "%"), "Rain chance"),
        stat(suffixed(wind_number, "mph"), wind_html),
    ]
    comment_body = (f"nws-weather tile_mode={mode} as_of={now.isoformat(timespec='minutes')}"
                    f" | {high_plain} | {low_plain} | commute={status}")
    comment_body = comment_body.replace("--", " ").replace(">", " ")
    comment = f"<!-- {comment_body} -->"
    parts = [comment, '<div class="wx">', '<div class="stats">', *tiles, "</div>", f'<div class="fc">{fc_html}</div>']
    if verdict_html:
        parts.append(verdict_html)
    if rw_html:
        parts.append(rw_html)
    parts.append(source_note(grid, fetched, updated, tz_abbr))
    parts.append("</div>")
    follow = [p for p in periods if low and p["is_day"] and p["start"] >= low["end"]][:2]
    payload = {
        "ok": True,
        "fetched_at": fetched.strftime("%Y-%m-%d %H:%M %Z"),
        "as_of": now.strftime("%Y-%m-%d %H:%M %Z"),
        "tile_mode": mode,
        "gridpoint": {"office": grid["office"], "x": grid["x"], "y": grid["y"]},
        "forecast_updated": updated_raw,
        "high_f": high["temp"],
        "low_f": low["temp"],
        "high_label": high_plain,
        "low_label": low_plain,
        "rain_chance_max_pct": rain,
        "wind_sustained_mph": [min(sustained), max(sustained)] if sustained else None,
        "wind_gust_max_mph": gust,
        "wind_number_mph": wind_number,
        "wind_label": wind_plain,
        "forecast_line": fc_plain,
        "today": brief(high) if mode == "today" else None,
        "tonight": brief(low),
        "next": [brief(p) for p in follow],
        "commute_status": status,
        "commute_line": verdict_plain,
        "commute_window": commute_rows,
        "sources": sources,
    }
    return {"html": "\n".join(parts), "json": payload}


def norm_periods(fc, tz):
    out = []
    for p in fc["properties"]["periods"]:
        out.append({
            "name": p.get("name") or "",
            "start": aware(p["startTime"], tz),
            "end": aware(p["endTime"], tz),
            "is_day": bool(p.get("isDaytime")),
            "temp": p.get("temperature"),
            "unit": p.get("temperatureUnit") or "F",
            "wind": p.get("windSpeed") or "",
            "dir": p.get("windDirection") or "",
            "pop": (p.get("probabilityOfPrecipitation") or {}).get("value"),
            "short": p.get("shortForecast") or "",
        })
    out.sort(key=lambda p: p["start"])
    return out


def norm_hours(hr, tz):
    out = []
    for h in hr["properties"]["periods"]:
        out.append({
            "start": aware(h["startTime"], tz),
            "end": aware(h["endTime"], tz),
            "temp": h.get("temperature"),
            "unit": h.get("temperatureUnit") or "F",
            "wind": h.get("windSpeed") or "",
            "winds": mph_nums(h.get("windSpeed")),
            "dir": h.get("windDirection") or "",
            "pop": (h.get("probabilityOfPrecipitation") or {}).get("value"),
            "short": h.get("shortForecast") or "",
        })
    out.sort(key=lambda h: h["start"])
    return out


def norm_gusts(grid, tz):
    if not grid:
        return []
    layer = (grid.get("properties") or {}).get("windGust") or {}
    uom = layer.get("uom") or "km_h"
    out = []
    for v in layer.get("values") or []:
        if v.get("value") is None:
            continue
        spec = v.get("validTime") or ""
        start_s, _, dur = spec.partition("/")
        if not start_s:
            continue
        start = aware(start_s, tz)
        out.append({"start": start, "end": start + parse_duration(dur), "mph": to_mph(v["value"], uom)})
    return out


def fetch(lat, lon, ua, save_raw):
    pt = get(f"{API}/points/{lat:.4f},{lon:.4f}", ua)["properties"]
    fc_url, hr_url = pt["forecast"], pt["forecastHourly"]
    fc = get(fc_url, ua)
    hr = get(hr_url, ua)
    grid_url = pt.get("forecastGridData")
    grid = get(grid_url, ua) if grid_url else None
    if save_raw:
        d = pathlib.Path(save_raw)
        d.mkdir(parents=True, exist_ok=True)
        (d / "fc.json").write_text(json.dumps(fc))
        (d / "hourly.json").write_text(json.dumps(hr))
        if grid is not None:
            (d / "grid.json").write_text(json.dumps(grid))
    sources = [f"{API}/points/{lat:.4f},{lon:.4f}", fc_url, hr_url] + ([grid_url] if grid_url else [])
    updated_raw = fc["properties"].get("updateTime") or fc["properties"].get("updated")
    return {
        "fc": fc,
        "hr": hr,
        "grid": grid,
        "gridpoint": {"office": pt["gridId"], "x": pt["gridX"], "y": pt["gridY"]},
        "sources": sources,
        "updated_raw": updated_raw,
    }


def fail_html(message):
    print(UNAVAILABLE_HTML)
    print(f"nws_weather: {message}", file=sys.stderr)
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--contact", required=True, help="email or URL for the NWS User-Agent")
    ap.add_argument("--commute", default="07:00-08:30", help="HH:MM-HH:MM local time")
    ap.add_argument("--commute-label", default="Commute", help="words in front of the commute verdict")
    ap.add_argument("--no-commute", action="store_true", help="omit the commute verdict")
    ap.add_argument("--jacket-below", type=float, default=60, help="jacket if commute air temp is at or below this °F")
    ap.add_argument("--umbrella-pop", type=float, default=30, help="umbrella if commute rain chance is at or above this")
    ap.add_argument("--running-window", help="optional running-window markdown file to embed")
    ap.add_argument("--tz", default="America/New_York")
    ap.add_argument("--tz-abbr", help="abbreviation in the source note (default: the zone's own, e.g. EDT)")
    ap.add_argument("--now", help="ISO datetime used only to choose periods (default: actual now)")
    ap.add_argument("--html", action="store_true", help="print the <div class=wx> block instead of JSON")
    ap.add_argument("--save-raw", help="directory to save raw forecast JSON")
    a = ap.parse_args()
    try:
        tz = ZoneInfo(a.tz)
        now = parse_now(a.now, tz)
        commute = parse_window(a.commute)
    except Exception as e:
        print(f"nws_weather: {e}", file=sys.stderr)
        sys.exit(2)
    fetched = dt.datetime.now(tz)
    tz_abbr = a.tz_abbr or fetched.strftime("%Z") or "UTC"
    ua = f"(morning-intel-skill, {a.contact})"
    try:
        bundle = fetch(a.lat, a.lon, ua, a.save_raw)
        periods = norm_periods(bundle["fc"], tz)
        hours = norm_hours(bundle["hr"], tz)
        gusts = norm_gusts(bundle["grid"], tz)
        updated = aware(bundle["updated_raw"], tz) if bundle["updated_raw"] else None
    except Exception as e:
        if a.html:
            fail_html(e)
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(2)
    built = assemble(
        now, fetched, tz, tz_abbr, periods, hours, gusts, bundle["gridpoint"], updated, bundle["updated_raw"],
        commute, a.commute_label, a.jacket_below, a.umbrella_pop, a.no_commute,
        running_window_html(a.running_window), bundle["sources"],
    )
    if built is None:
        msg = "NWS forecast did not include both a high period and a low period; not estimating"
        if a.html:
            fail_html(msg)
        print(json.dumps({"ok": False, "error": msg}))
        sys.exit(2)
    if a.html:
        print(built["html"])
    else:
        print(json.dumps(built["json"], indent=2))


if __name__ == "__main__":
    main()
