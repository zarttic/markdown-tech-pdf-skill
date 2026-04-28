#!/usr/bin/env python3
"""Convert Markdown into a restrained technical-document PDF using a local browser."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


CSS = r"""
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
html { color: #1f2933; background: #fff; }
body {
  margin: 0;
  font-family: "Segoe UI", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.62;
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Markdown to a technical PDF.")
    parser.add_argument("input", type=Path, help="Source Markdown file")
    parser.add_argument("output", type=Path, help="Output PDF path")
    parser.add_argument("--title", help="Document title override")
    parser.add_argument("--html-output", type=Path, help="Also write the generated HTML")
    parser.add_argument("--keep-html", action="store_true", help="Keep temporary HTML next to the PDF")
    parser.add_argument("--browser", type=Path, help="Path to Chrome, Edge, or Chromium executable")
    return parser.parse_args()


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


def slugify(text: str, used: set[str]) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.lower()).strip("-")
    slug = slug or "section"
    base = slug
    counter = 2
    while slug in used:
        slug = f"{base}-{counter}"
        counter += 1
    used.add(slug)
    return slug


def inline_md(text: str) -> str:
    placeholders: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\u0000{len(placeholders) - 1}\u0000"

    text = re.sub(r"`([^`]+)`", stash_code, html.escape(text))
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", text)
    for index, value in enumerate(placeholders):
        text = text.replace(f"\u0000{index}\u0000", value)
    return text


def is_table(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return "|" in lines[index] and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]) is not None


def parse_table(lines: list[str], index: int) -> tuple[str, int]:
    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    headers = cells(lines[index])
    rows: list[list[str]] = []
    index += 2
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        rows.append(cells(lines[index]))
        index += 1
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{inline_md(cell)}</th>" for cell in headers)
    out.append("</tr></thead>")
    if rows:
        out.append("<tbody>")
        for row in rows:
            out.append("<tr>")
            padded = row + [""] * (len(headers) - len(row))
            out.extend(f"<td>{inline_md(cell)}</td>" for cell in padded[: len(headers)])
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table>")
    return "".join(out), index


def markdown_to_html(markdown: str) -> tuple[str, list[tuple[int, str, str]]]:
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
            out.append(f"<p>{inline_md(' '.join(paragraph).strip())}</p>")
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

        if is_table(lines, index):
            flush_paragraph()
            close_lists()
            table_html, index = parse_table(lines, index)
            out.append(table_html)
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            ident = slugify(re.sub(r"`([^`]+)`", r"\1", text), used)
            headings.append((level, ident, re.sub(r"<.*?>", "", inline_md(text))))
            out.append(f'<h{level} id="{ident}">{inline_md(text)}</h{level}>')
            index += 1
            continue

        if re.match(r"^\s*---+\s*$", line):
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
            out.append(f"<blockquote>{inline_md(' '.join(quote_lines).strip())}</blockquote>")
            continue

        unordered = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$", line)
        if unordered:
            flush_paragraph()
            if not list_stack or list_stack[-1] != "ul":
                close_lists()
                out.append("<ul>")
                list_stack.append("ul")
            checked = "x" if unordered.group(1).lower() == "x" else " "
            out.append(f'<li><span class="task-box">[{checked}]</span> {inline_md(unordered.group(2))}</li>')
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
            out.append(f"<li>{inline_md(item)}</li>")
            index += 1
            continue

        paragraph.append(line.strip())
        index += 1

    flush_paragraph()
    close_lists()
    if in_code:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(out), headings


def choose_title(markdown: str, metadata: dict[str, str], path: Path, override: str | None) -> str:
    if override:
        return override
    if metadata.get("title"):
        return metadata["title"]
    match = re.search(r"^#\s+(.+)$", markdown, re.M)
    if match:
        return re.sub(r"[`*_]", "", match.group(1)).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def build_toc(headings: list[tuple[int, str, str]], title: str) -> str:
    toc_items = [(level, ident, text) for level, ident, text in headings if not (level == 1 and text == title)]
    if len(toc_items) < 2:
        return ""
    items = "\n".join(
        f'<li class="toc-l{level}"><a href="#{ident}">{html.escape(text)}</a></li>'
        for level, ident, text in toc_items
        if level <= 3
    )
    return f'<nav class="toc"><h2 class="toc-title">Table of Contents</h2><ol>{items}</ol></nav>'


def build_html(markdown: str, title: str, source_name: str) -> str:
    body, headings = markdown_to_html(markdown)
    toc = build_toc(headings, title)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
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


def find_browser(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit if explicit.exists() else None
    for command in ("msedge", "chrome", "chromium", "google-chrome", "chrome.exe", "msedge.exe"):
        found = shutil.which(command)
        if found:
            return Path(found)
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    return next((path for path in candidates if path.exists()), None)


def render_pdf(browser: Path, html_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    user_data_dir = Path(tempfile.mkdtemp(prefix="md-tech-pdf-browser-"))
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--user-data-dir={user_data_dir}",
        f"--print-to-pdf={output_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    finally:
        shutil.rmtree(user_data_dir, ignore_errors=True)
    if result.returncode != 0 or not output_path.exists():
        message = (result.stderr or result.stdout or "Browser PDF rendering failed.").strip()
        raise RuntimeError(message)


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
    rendered = build_html(markdown, title, input_path.name)

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
        render_pdf(browser, html_path, output_path)
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
