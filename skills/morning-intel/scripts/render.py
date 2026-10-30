#!/usr/bin/env python3
"""Render a Morning Intel issue: HTML -> PDF (headless Chrome) -> page PNGs (pdftoppm).

Usage:
  python3 render.py issues/2026-10-30.html            # writes issues/2026-10-30.pdf and -page-N.png
  python3 render.py in.html --pdf out.pdf --dpi 110 --no-png

Same method as the original issues: Chrome/Chromium --headless --print-to-pdf with
--no-pdf-header-footer (CSS @page sets US Letter and margins), then poppler's pdftoppm
at 110 dpi (935x1210 px per Letter page).

Needs: Google Chrome or Chromium (or set CHROME=/path/to/binary), poppler-utils
(pdftoppm, pdfinfo), and the fonts from install_fonts.sh. Python 3.8+, stdlib only.
Exit codes: 0 ok, 2 missing dependency, 3 render failed.
"""
import argparse, glob, os, pathlib, shutil, subprocess, sys

CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium"]
FONTS = ["Inter", "IBM Plex Serif", "IBM Plex Mono"]


def find_chrome():
    env = os.environ.get("CHROME")
    if env and (shutil.which(env) or os.path.exists(env)):
        return shutil.which(env) or env
    for c in CANDIDATES:
        p = shutil.which(c) or (c if os.path.exists(c) else None)
        if p:
            return p
    # Playwright's bundled Chromium, if present
    for p in sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")), reverse=True):
        return p
    return None


def check_fonts():
    if not shutil.which("fc-list"):
        return []
    out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    fams = {f.strip() for line in out.splitlines() for f in line.split(",")}
    return [f for f in FONTS if f not in fams]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("--pdf", help="output PDF (default: same stem as the HTML)")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()

    html = pathlib.Path(a.html).resolve()
    if not html.exists():
        sys.exit(f"render: {html} not found")
    pdf = pathlib.Path(a.pdf).resolve() if a.pdf else html.with_suffix(".pdf")

    chrome = find_chrome()
    if not chrome:
        print("render: no Chrome/Chromium found. Install google-chrome or chromium, or set CHROME=/path.", file=sys.stderr)
        sys.exit(2)
    if not a.no_png and not shutil.which("pdftoppm"):
        print("render: pdftoppm missing (apt install poppler-utils / brew install poppler).", file=sys.stderr)
        sys.exit(2)
    missing = check_fonts()
    if missing:
        print(f"render: WARNING fonts not installed: {', '.join(missing)}. Run install_fonts.sh, "
              "or the page will fall back to Georgia/sans-serif and will not match the design.", file=sys.stderr)

    # Headless Chrome uses a throwaway profile by default. Do not pass --user-data-dir:
    # with a fresh custom profile Chrome 156 hung until timeout in testing.
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if pdf.exists():
        pdf.unlink()
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
           "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000",
           "--no-pdf-header-footer", f"--print-to-pdf={pdf}", html.as_uri()]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        print("render: Chrome timed out (is another Chrome holding a lock? try CHROME=chromium)", file=sys.stderr)
        sys.exit(3)
    if not pdf.exists() or pdf.stat().st_size == 0:
        print("render: Chrome produced no PDF\n" + r.stderr[-2000:], file=sys.stderr)
        sys.exit(3)
    print(f"pdf  {pdf}")

    if not a.no_png:
        stem = pdf.with_suffix("")
        for old in glob.glob(f"{glob.escape(str(stem))}-page-*.png"):
            os.remove(old)
        subprocess.run(["pdftoppm", "-png", "-r", str(a.dpi), str(pdf), f"{stem}-page"], check=True)
        # pdftoppm pads page numbers (page-01) for 10+ pages; normalize to -page-N.png
        for p in sorted(glob.glob(f"{glob.escape(str(stem))}-page-*.png")):
            n = int(p.rsplit("-", 1)[1].split(".")[0])
            dst = f"{stem}-page-{n}.png"
            if p != dst:
                os.replace(p, dst)
            print(f"png  {dst}")


if __name__ == "__main__":
    main()
