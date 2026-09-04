"""Embed latest report markdown into index.html for GitHub Pages."""
import json
from pathlib import Path

REPORT_DIR = Path("reports")
HTML_PATH = Path("index.html")

def main():
    md_files = sorted(REPORT_DIR.glob("*.md"))
    if not md_files:
        print("No report files found, skipping HTML build.")
        return
    reports = {}
    for f in md_files:
        reports[f.name] = f.read_text(encoding="utf-8")
    embedded_json = json.dumps(reports, ensure_ascii=False)

    html = HTML_PATH.read_text(encoding="utf-8")
    marker_start = "const EMBEDDED_REPORTS = "
    marker_end = ";\n\nfunction loadReports()"
    start = html.find(marker_start)
    end = html.find(marker_end)
    if start == -1 or end == -1:
        print("ERROR: could not find EMBEDDED_REPORTS markers in index.html")
        return
    new_html = html[:start + len(marker_start)] + embedded_json + html[end:]
    HTML_PATH.write_text(new_html, encoding="utf-8")
    print(f"index.html updated with {len(md_files)} report(s), {len(embedded_json)} bytes")

if __name__ == "__main__":
    main()
