#!/usr/bin/env python3
"""Inline data/seed.js, assets/styles.css and assets/app.js into standalone.html."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text()
css = (ROOT / "assets" / "styles.css").read_text()
seed = (ROOT / "data" / "seed.js").read_text().replace("</", "<\\/")
app = (ROOT / "assets" / "app.js").read_text().replace("</", "<\\/")
html = html.replace('<link rel="stylesheet" href="assets/styles.css">', f"<style>\n{css}</style>")
html = html.replace('<script src="data/seed.js"></script>', f"<script>\n{seed}</script>")
html = html.replace('<script src="assets/app.js"></script>', f"<script>\n{app}</script>")
assert "assets/" not in html.split("<body>")[0], "stylesheet was not inlined"
(ROOT / "standalone.html").write_text(html)
print(f"wrote standalone.html ({len(html) // 1024} KB)")
