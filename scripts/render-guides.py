"""Build browser-readable guides. Requires the Python markdown package."""
from pathlib import Path
import html
import re
import markdown
from markdown.extensions.toc import slugify_unicode
import os

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "asset-guide"
sources = list(GUIDE.rglob("*.md"))
outputs = {p: p.with_name("hands-on.html") if p.name == "HANDS_ON.md" else p.with_suffix(".html") for p in sources}
for source, output in outputs.items():
    document = markdown.markdown(source.read_text(), extensions=["tables", "fenced_code", "toc"],
                                 extension_configs={"toc": {"slugify": slugify_unicode}})
    def link(match):
        target = match.group(1)
        if target.startswith(("https:", "http:", "#")):
            return match.group(0)
        path, separator, anchor = target.partition("#")
        resolved = (source.parent / path).resolve()
        if resolved in outputs:
            target = os.path.relpath(outputs[resolved], output.parent) + (separator + anchor if separator else "")
        return 'href="' + html.escape(target, quote=True) + '"'
    document = re.sub(r'href="([^"]+)"', link, document)
    title = source.read_text().splitlines()[0].lstrip("# ")
    hands_on = os.path.relpath(GUIDE / "hands-on.html", output.parent)
    start = os.path.relpath(GUIDE / "README.html", output.parent)
    css = """body{font:16px/1.8 system-ui,sans-serif;color:#232f3e;background:#fff;max-width:1120px;margin:auto;padding:32px}a{color:#0972d3}h1,h2,h3{line-height:1.4}h2{margin-top:44px;border-top:1px solid #d5dbdb;padding-top:24px}pre{background:#f2f3f3;padding:18px;overflow:auto;border-radius:6px}code{font-size:.9em}table{display:block;overflow:auto;border-collapse:collapse;width:100%}th,td{text-align:left;border-bottom:1px solid #d5dbdb;padding:10px}img{max-width:100%;height:auto}blockquote{border-left:4px solid #ec7211;padding-left:20px;margin-left:0}.nav{font-size:14px}"""
    output.write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
                      + html.escape(title) + '</title><style>' + css + '</style></head><body><p class="nav"><a href="/">'
                      + f'데모 앱</a> · <a href="{hands_on}">핸즈온</a> · <a href="{start}">가이드 시작</a></p>'
                      + document + '</body></html>')
print(f"Rendered {len(sources)} guides.")
