#!/usr/bin/env python3
"""Fetch today's forecast from the US National Weather Service (api.weather.gov) as JSON.

Usage:
  python3 nws_weather.py --lat 38.8951 --lon -77.0364 --contact you@example.com \
      [--commute 07:00-08:30] [--tz America/New_York] [--save-raw DIR]

Prints one JSON object with: gridpoint (office/x/y), forecast update time, today's
high, tonight's low, max rain chance today, wind range and gusts (from the hourly
forecast), the commute-window hours, tonight/tomorrow short forecasts, and the
exact URLs fetched (cite them in SOURCES). Fields that NWS did not return are null,
never guessed.

NWS asks every client to send a User-Agent that identifies the app and a contact
(https://www.weather.gov/documentation/services-web-api). US locations only.
Python 3.9+ stdlib only. Exit 2 on network/API errors (put weather on the
could-not-verify list and skip the weather block rather than inventing numbers).
"""
import argparse, datetime as dt, json, re, sys, time, urllib.request
from zoneinfo import ZoneInfo

API = "https://api.weather.gov"


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


def mph(s):
    nums = [int(n) for n in re.findall(r"\d+", s or "")]
    return nums


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--contact", required=True, help="email or URL for the NWS User-Agent")
    ap.add_argument("--commute", default="07:00-08:30", help="HH:MM-HH:MM local time")
    ap.add_argument("--tz", default="America/New_York")
    ap.add_argument("--save-raw", help="directory to save raw forecast JSON (fc.json, hourly.json)")
    a = ap.parse_args()
    ua = f"(morning-intel-skill, {a.contact})"
    tz = ZoneInfo(a.tz)
    try:
        pt = get(f"{API}/points/{a.lat:.4f},{a.lon:.4f}", ua)["properties"]
        fc_url, hr_url = pt["forecast"], pt["forecastHourly"]
        fc = get(fc_url, ua)
        hr = get(hr_url, ua)
        grid_url = pt.get("forecastGridData")
        grid = get(grid_url, ua) if grid_url else None
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(2)
    if a.save_raw:
        import pathlib
        d = pathlib.Path(a.save_raw); d.mkdir(parents=True, exist_ok=True)
        (d / "fc.json").write_text(json.dumps(fc)); (d / "hourly.json").write_text(json.dumps(hr))

    now = dt.datetime.now(tz)
    today = now.date()
    periods = fc["properties"]["periods"]
    day = next((p for p in periods if p["isDaytime"] and dt.datetime.fromisoformat(p["startTime"]).astimezone(tz).date() == today), None)
    night = next((p for p in periods if not p["isDaytime"]), None)
    nxt = [p for p in periods if p is not day and p is not night][:2]

    hours = []
    for h in hr["properties"]["periods"]:
        t = dt.datetime.fromisoformat(h["startTime"]).astimezone(tz)
        if t.date() == today and t.hour >= 6:
            hours.append((t, h))
    pops = [h.get("probabilityOfPrecipitation", {}).get("value") for _, h in hours]
    pops = [p for p in pops if p is not None]
    winds = [n for _, h in hours for n in mph(h.get("windSpeed"))]
    # Gusts are not in the hourly forecast; read them from the raw gridpoint layer (km/h).
    gusts = []
    if grid:
        g = grid["properties"].get("windGust", {})
        factor = 0.621371 if "km_h" in g.get("uom", "km_h") else 1.0
        for v in g.get("values", []):
            start = dt.datetime.fromisoformat(v["validTime"].split("/")[0]).astimezone(tz)
            if start.date() == today and start.hour >= 6 and v.get("value") is not None:
                gusts.append(round(v["value"] * factor))

    c0, c1 = [dt.time.fromisoformat(x) for x in a.commute.split("-")]
    commute = [{"time": t.strftime("%H:%M"), "temp_f": h["temperature"], "pop": (h.get("probabilityOfPrecipitation") or {}).get("value"),
                "wind": h.get("windSpeed"), "dir": h.get("windDirection"), "short": h.get("shortForecast"),
                "rh": (h.get("relativeHumidity") or {}).get("value")}
               for t, h in hours if c0 <= t.time() <= c1]

    def brief(p):
        return None if not p else {"name": p["name"], "temp_f": p["temperature"], "wind": p["windSpeed"], "dir": p["windDirection"],
                                   "pop": (p.get("probabilityOfPrecipitation") or {}).get("value"), "short": p["shortForecast"],
                                   "detailed": p["detailedForecast"]}

    out = {
        "ok": True,
        "fetched_at": now.strftime("%Y-%m-%d %H:%M %Z"),
        "gridpoint": {"office": pt["gridId"], "x": pt["gridX"], "y": pt["gridY"]},
        "forecast_updated": fc["properties"].get("updateTime") or fc["properties"].get("updated"),
        "high_f": day["temperature"] if day else None,
        "low_f": night["temperature"] if night else None,
        "rain_chance_max_pct": max(pops) if pops else (brief(day) or {}).get("pop"),
        "wind_sustained_mph": [min(winds), max(winds)] if winds else None,
        "wind_gust_max_mph": max(gusts) if gusts else None,
        "today": brief(day), "tonight": brief(night), "next": [brief(p) for p in nxt],
        "commute_window": commute,
        "sources": [f"{API}/points/{a.lat:.4f},{a.lon:.4f}", fc_url, hr_url] + ([grid_url] if grid else []),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
