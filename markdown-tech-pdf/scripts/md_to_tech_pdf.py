#!/usr/bin/env python3
"""Convert Markdown into a restrained technical-document PDF using a local browser."""

from __future__ import annotations

import argparse
import html
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Optional Markdown library – full spec-compliant parsing when available
# ---------------------------------------------------------------------------
_HAS_MARKDOWN = importlib.util.find_spec("markdown") is not None


# ======================== BASE CSS ==========================================

_CSS_BASE = r"""
@page {
  size: A4;
  margin: 18mm 16mm;
}
* { box-sizing: border-box; }
html { color: #1f2933; background: #fff; }
body {
  margin: 0;
  font-family: "Segoe UI", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.62;
  orphans: 3;
  widows: 3;
}
@media screen {
  html { background: #eef2f6; }
  body {
    max-width: 980px;
    min-height: 1380px;
    margin: 32px auto;
    padding: 54px 60px;
    background: #fff;
    border: 1px solid #d7dde5;
    box-shadow: 0 18px 50px rgba(31, 41, 55, .14);
  }
}
.title-block {
  border-bottom: 2px solid #2f3a45;
  padding-bottom: 14px;
  margin-bottom: 18px;
}
.doc-title {
  margin: 0 0 7px;
  font-size: 24pt;
  line-height: 1.15;
  font-weight: 700;
  color: #111827;
}
.doc-meta { margin: 0; color: #667085; font-size: 9.5pt; }
.toc {
  border: 1px solid #d7dde5;
  background: #f8fafc;
  padding: 12px 14px;
  margin: 0 0 22px;
  break-inside: avoid;
}
.toc-title { margin: 0 0 8px; font-size: 12pt; color: #111827; }
.toc ol { margin: 0; padding-left: 20px; }
.toc li { margin: 2px 0; }
.toc a { color: #344054; text-decoration: none; }
h1, h2, h3, h4, h5, h6 {
  color: #111827;
  line-height: 1.28;
  margin: 1.25em 0 .45em;
  break-after: avoid;
}
h1 { font-size: 19pt; border-bottom: 1px solid #d7dde5; padding-bottom: 5px; }
h2 { font-size: 15.5pt; border-bottom: 1px solid #edf1f5; padding-bottom: 4px; }
h3 { font-size: 13pt; }
h4, h5, h6 { font-size: 11.5pt; }
p { margin: .45em 0 .8em; }
a { color: #175cd3; }
hr { border: 0; border-top: 1px solid #d7dde5; margin: 18px 0; }
ul, ol { margin: .35em 0 .85em 1.35em; padding: 0; }
li { margin: .18em 0; }
blockquote {
  margin: .9em 0;
  padding: 8px 12px;
  border-left: 4px solid #8aa4c2;
  background: #f7f9fb;
  color: #344054;
}
code {
  font-family: "Cascadia Mono", Consolas, Menlo, Monaco, monospace;
  font-size: .92em;
  background: #eef2f6;
  border: 1px solid #d9e1ea;
  border-radius: 3px;
  padding: 0 .22em;
}
pre {
  margin: .85em 0 1em;
  padding: 10px 12px;
  background: #f3f6f9;
  border: 1px solid #d7dde5;
  border-left: 4px solid #536b86;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  break-inside: avoid;
}
pre code {
  display: block;
  padding: 0;
  border: 0;
  background: transparent;
  font-size: 9.5pt;
}
.code-lang {
  display: block;
  margin-bottom: 5px;
  color: #667085;
  font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  font-size: 8.5pt;
  text-transform: uppercase;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: .9em 0 1.05em;
  font-size: 9.8pt;
  break-inside: avoid;
}
thead { display: table-header-group; }
th, td {
  border: 1px solid #d7dde5;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
th { background: #eef2f6; color: #111827; font-weight: 650; }
tr:nth-child(even) td { background: #fbfcfe; }
.task-box { font-family: "Cascadia Mono", Consolas, monospace; }
"""

_CSS_PAGE_NUMBERS = r"""
@page {
  @bottom-center {
    content: counter(page);
    font-size: 9pt;
    color: #667085;
    font-family: "Segoe UI", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
  }
}
"""

_CSS_NO_PAGE_NUMBERS = r"""
@page {
  @bottom-center { content: none; }
}
"""


# ======================== CLI ===============================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Markdown to a technical PDF.")
    parser.add_argument("input", type=Path, help="Source Markdown file")
    parser.add_argument("output", type=Path, help="Output PDF path")
    parser.add_argument("--title", help="Document title override")
    parser.add_argument("--html-output", type=Path, help="Also write the generated HTML")
    parser.add_argument("--keep-html", action="store_true", help="Keep temporary HTML next to the PDF")
    parser.add_argument("--browser", type=Path, help="Path to Chrome, Edge, or Chromium executable")
    parser.add_argument("--page-number", action="store_true", default=True,
                        help="Include page numbers (default: on)")
    parser.add_argument("--no-page-number", action="store_false", dest="page_number",
                        help="Omit page numbers")
    parser.add_argument("--extra-css", type=Path, help="Path to extra CSS file to inject")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Browser render timeout in seconds (default: 60)")
    parser.add_argument("--author", help="Document author (stored in HTML meta)")
    parser.add_argument("--subject", help="Document subject (stored in HTML meta)")
    return parser.parse_args()


# ======================== YAML FRONTMATTER ==================================

def strip_frontmatter(text: str) -> tuple[str, dict[str, str]]:
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return text, {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not match:
        return text, {}
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip().lower()] = value.strip().strip('"').strip("'")
    return text[match.end() :], metadata


def choose_title(markdown: str, metadata: dict[str, str], path: Path, override: str | None) -> str:
    if override:
        return override
    if metadata.get("title"):
        return metadata["title"]
    match = re.search(r"^#\s+(.+)$", markdown, re.M)
    if match:
        return re.sub(r"[`*_]", "", match.group(1)).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


# ======================== MARKDOWN → HTML ===================================

def markdown_to_html_fast(text: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Convert Markdown to HTML using the python-markdown library (full spec)."""
    import markdown

    md = markdown.Markdown(extensions=[
        "tables",
        "fenced_code",
        "toc",
        "sane_lists",
        "nl2br",
        "def_list",
    ])
    body_html = md.convert(text)

    # --- build heading list from toc_tokens ---
    headings: list[tuple[int, str, str]] = []

    def walk_toc(items: list[dict], depth: int = 0) -> None:
        for item in items:
            headings.append((item["level"], item["id"], item["name"]))
            if item.get("children"):
                walk_toc(item["children"], depth + 1)

    if hasattr(md, "toc_tokens"):
        walk_toc(md.toc_tokens)

    # --- add language labels to code blocks ---
    body_html = re.sub(
        r'<pre><code class="(?:language-)?([\w+-]+)">',
        r'<pre><span class="code-lang">\1</span><code class="\1">',
        body_html,
    )

    return body_html, headings


# ======================== FALLBACK HAND-WRITTEN PARSER ======================

def _slugify(text: str, used: set[str]) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.lower()).strip("-")
    slug = slug or "section"
    base = slug
    counter = 2
    while slug in used:
        slug = f"{base}-{counter}"
        counter += 1
    used.add(slug)
    return slug


def _inline_md(text: str) -> str:
    placeholders: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\u0000{len(placeholders) - 1}\u0000"

    text = re.sub(r"`([^`]+)`", stash_code, html.escape(text))
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    # Bold/italic: *italic* but not **bold** (already handled above)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    # Underscore italic: _italic_ but only when surrounded by word boundaries
    # to avoid matching e.g. some_var or __dunder__
    text = re.sub(r"(?<!\w)_(\w[^_]*\w)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)__([^_]+)__(?!_)", r"<strong>\1</strong>", text)
    for index, value in enumerate(placeholders):
        text = text.replace(f"\u0000{index}\u0000", value)
    return text


def _is_table(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return "|" in lines[index] and re.match(
        r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]
    ) is not None


def _parse_table(lines: list[str], index: int) -> tuple[str, int]:
    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    headers = cells(lines[index])
    rows: list[list[str]] = []
    index += 2
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        rows.append(cells(lines[index]))
        index += 1
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{_inline_md(cell)}</th>" for cell in headers)
    out.append("</tr></thead>")
    if rows:
        out.append("<tbody>")
        for row in rows:
            out.append("<tr>")
            padded = row + [""] * (len(headers) - len(row))
            out.extend(f"<td>{_inline_md(cell)}</td>" for cell in padded[: len(headers)])
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table>")
    return "".join(out), index


def markdown_to_html_fallback(markdown: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Fallback hand-written Markdown → HTML converter (zero dependencies)."""
    lines = markdown.splitlines()
    used: set[str] = set()
    headings: list[tuple[int, str, str]] = []
    out: list[str] = []
    paragraph: list[str] = []
    list_stack: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{_inline_md(' '.join(paragraph).strip())}</p>")
            paragraph.clear()

    def close_lists() -> None:
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    index = 0
    while index < len(lines):
        line = lines[index]
        fence = re.match(r"^\s*```([\w.+-]*)\s*$", line)
        if fence:
            if in_code:
                language = html.escape(code_lang)
                label = f'<span class="code-lang">{language}</span>' if language else ""
                out.append(f"<pre>{label}<code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                code_lang = ""
                in_code = False
            else:
                flush_paragraph()
                close_lists()
                in_code = True
                code_lang = fence.group(1)
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not line.strip():
            flush_paragraph()
            close_lists()
            index += 1
            continue

        if _is_table(lines, index):
            flush_paragraph()
            close_lists()
            table_html, index = _parse_table(lines, index)
            out.append(table_html)
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            ident = _slugify(re.sub(r"`([^`]+)`", r"\1", text), used)
            headings.append((level, ident, re.sub(r"<.*?>", "", _inline_md(text))))
            out.append(f'<h{level} id="{ident}">{_inline_md(text)}</h{level}>')
            index += 1
            continue

        if re.match(r"^\s*---+$", line) and not re.match(r"^\s*-{5,}$", line.strip("-").strip()):
            flush_paragraph()
            close_lists()
            out.append("<hr>")
            index += 1
            continue

        quote = re.match(r"^\s*>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            close_lists()
            quote_lines = [quote.group(1)]
            index += 1
            while index < len(lines):
                next_quote = re.match(r"^\s*>\s?(.*)$", lines[index])
                if not next_quote:
                    break
                quote_lines.append(next_quote.group(1))
                index += 1
            out.append(f"<blockquote>{_inline_md(' '.join(quote_lines).strip())}</blockquote>")
            continue

        unordered = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$", line)
        if unordered:
            flush_paragraph()
            if not list_stack or list_stack[-1] != "ul":
                close_lists()
                out.append("<ul>")
                list_stack.append("ul")
            checked = "x" if unordered.group(1).lower() == "x" else " "
            out.append(f'<li><span class="task-box">[{checked}]</span> {_inline_md(unordered.group(2))}</li>')
            index += 1
            continue

        unordered = re.match(r"^\s*[-*+]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if unordered or ordered:
            flush_paragraph()
            tag = "ul" if unordered else "ol"
            item = (unordered or ordered).group(1)
            if not list_stack or list_stack[-1] != tag:
                close_lists()
                out.append(f"<{tag}>")
                list_stack.append(tag)
            out.append(f"<li>{_inline_md(item)}</li>")
            index += 1
            continue

        paragraph.append(line.strip())
        index += 1

    flush_paragraph()
    close_lists()
    if in_code:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(out), headings


# ======================== CONVERSION DISPATCH ===============================

def markdown_to_html(text: str) -> tuple[str, list[tuple[int, str, str]]]:
    if _HAS_MARKDOWN:
        return markdown_to_html_fast(text)
    return markdown_to_html_fallback(text)


# ======================== TOC & HTML ASSEMBLY ===============================

def build_toc(headings: list[tuple[int, str, str]], title: str) -> str:
    toc_items = [
        (level, ident, text)
        for level, ident, text in headings
        if not (level == 1 and text == title)
    ]
    if len(toc_items) < 2:
        return ""
    items = "\n".join(
        f'<li class="toc-l{level}"><a href="#{ident}">{html.escape(text)}</a></li>'
        for level, ident, text in toc_items
        if level <= 3
    )
    return f'<nav class="toc"><h2 class="toc-title">Table of Contents</h2><ol>{items}</ol></nav>'


def build_css(page_number: bool, extra_css_path: Path | None) -> str:
    css = _CSS_BASE
    if page_number:
        css += _CSS_PAGE_NUMBERS
    else:
        css += _CSS_NO_PAGE_NUMBERS
    if extra_css_path and extra_css_path.exists():
        css += "\n" + extra_css_path.read_text(encoding="utf-8")
    return css


def build_html(markdown: str, title: str, source_name: str,
               page_number: bool = True, extra_css_path: Path | None = None,
               author: str | None = None, subject: str | None = None) -> str:
    body, headings = markdown_to_html(markdown)
    toc = build_toc(headings, title)
    css = build_css(page_number, extra_css_path)

    meta_parts = [f'  <meta charset="utf-8">\n  <title>{html.escape(title)}</title>']
    if author:
        meta_parts.append(f'  <meta name="author" content="{html.escape(author)}">')
    if subject:
        meta_parts.append(f'  <meta name="subject" content="{html.escape(subject)}">')

    return f"""<!doctype html>
<html>
<head>
{chr(10).join(meta_parts)}
  <style>{css}</style>
</head>
<body>
  <header class="title-block">
    <h1 class="doc-title">{html.escape(title)}</h1>
    <p class="doc-meta">Source: {html.escape(source_name)}</p>
  </header>
  {toc}
  <main>
{body}
  </main>
</body>
</html>
"""


# ======================== BROWSER DETECTION =================================

_FIND_BROWSER_COMMANDS = (
    "msedge",
    "chrome",
    "chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium-browser",
    "chrome.exe",
    "msedge.exe",
)

_FIND_BROWSER_PATHS = [
    # Windows
    lambda: Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
    lambda: Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
    lambda: Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    lambda: Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
    lambda: Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    # macOS
    lambda: Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    lambda: Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    lambda: Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    lambda: Path(os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")),
    # Linux – snap / flatpak / standard
    lambda: Path("/snap/bin/chromium"),
    lambda: Path("/var/lib/flatpak/exports/bin/com.google.Chrome"),
    lambda: Path("/usr/bin/google-chrome"),
    lambda: Path("/usr/bin/chromium"),
    lambda: Path("/usr/bin/chromium-browser"),
]


def find_browser(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit if explicit.exists() else None
    for command in _FIND_BROWSER_COMMANDS:
        found = shutil.which(command)
        if found:
            return Path(found)
    for path_builder in _FIND_BROWSER_PATHS:
        try:
            path = path_builder()
            if path.exists():
                return path
        except (OSError, ValueError):
            continue
    return None


# ======================== PDF RENDER ========================================

def render_pdf(browser: Path, html_path: Path, output_path: Path, timeout: int = 60) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Use persistent user-data-dir so first-run setup happens only once,
    # and orphaned child processes don't interfere with new sessions.
    user_data_dir = Path.home() / ".cache" / "md-tech-pdf-browser" / "headless-profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--no-first-run",
        "--disable-features=ChromeWhatsNewUI,PrivacySandboxSettings4",
        f"--user-data-dir={user_data_dir}",
        f"--print-to-pdf={output_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 or not output_path.exists():
        message = (result.stderr or result.stdout or "Browser PDF rendering failed.").strip()
        raise RuntimeError(message)


# ======================== MAIN ==============================================

def main() -> int:
    args = parse_args()
    input_path = args.input
    output_path = args.output

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    raw = input_path.read_text(encoding="utf-8-sig")
    markdown, metadata = strip_frontmatter(raw)
    title = choose_title(markdown, metadata, input_path, args.title)

    rendered = build_html(
        markdown,
        title,
        input_path.name,
        page_number=args.page_number,
        extra_css_path=args.extra_css,
        author=args.author or metadata.get("author"),
        subject=args.subject or metadata.get("subject"),
    )

    html_path = args.html_output
    temp_html: Path | None = None
    if html_path is None:
        if args.keep_html:
            html_path = output_path.with_suffix(".html")
        else:
            temp_file = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
            temp_html = Path(temp_file.name)
            html_path = temp_html
            temp_file.close()
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(rendered, encoding="utf-8")

    browser = find_browser(args.browser)
    if browser is None:
        print(
            "No Chromium-family browser found. Install Microsoft Edge, Google Chrome, or Chromium, "
            "or pass --browser <path-to-browser>.",
            file=sys.stderr,
        )
        return 3

    try:
        render_pdf(browser, html_path, output_path, timeout=args.timeout)
    except Exception as exc:
        print(f"PDF rendering failed: {exc}", file=sys.stderr)
        return 4
    finally:
        if temp_html is not None:
            temp_html.unlink(missing_ok=True)

    print(f"Wrote PDF: {output_path}")
    if args.html_output or args.keep_html:
        print(f"Wrote HTML: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
