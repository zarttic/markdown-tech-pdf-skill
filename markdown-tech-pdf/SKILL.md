---
name: markdown-tech-pdf
description: Convert Markdown technical documentation into polished PDF files with a standard engineering-document style. Use when the user asks to export, render, print, or convert Markdown or AI-generated Markdown summaries into PDF technical documents, including docs with headings, tables, code blocks, checklists, images, Chinese or English text, and predictable page layout.
---

# Markdown Tech PDF

## Overview

Use this skill to turn Markdown into a professional technical PDF. Prefer the bundled script for repeatable output, then inspect the generated PDF when visual fidelity matters.

The script auto-detects the `markdown` Python library (install via `pip install markdown`) for full spec-compliant parsing, and falls back to a zero-dependency built-in parser if the library is not available.

## Workflow

1. Identify the source Markdown file or create one from the user's provided content.
2. Decide the title from, in order: the user's requested title, the first `# H1`, YAML frontmatter `title`, or the file name.
3. Run the bundled converter:

```powershell
python <skill-folder>\scripts\md_to_tech_pdf.py input.md output.pdf --title "Document Title"
```

4. If the user needs reviewable intermediate output, add `--html-output output.html`.
5. Open or render-check the PDF if the task depends on layout quality, tables, page breaks, CJK font rendering, or code block wrapping.
6. If conversion fails because no Chromium-family browser is available, install Microsoft Edge, Google Chrome, or Chromium, then rerun the script. The script auto-detects the browser on Windows, macOS, and Linux.

## Script Options

| Flag | Default | Description |
| --- | --- | --- |
| `--title` | (auto) | Document title override |
| `--html-output PATH` | — | Also write the generated HTML to PATH |
| `--keep-html` | off | Keep the intermediate HTML next to the PDF |
| `--browser PATH` | (auto) | Path to Chrome/Edge/Chromium binary |
| `--page-number` | on | Include page numbers in PDF footer |
| `--no-page-number` | — | Omit page numbers |
| `--extra-css PATH` | — | Inject a custom CSS file |
| `--timeout SECS` | 60 | Browser render timeout in seconds |
| `--author TEXT` | — | Document author (HTML meta) |
| `--subject TEXT` | — | Document subject (HTML meta) |

## Style Standard

Default to a restrained technical-document style:

- A4 pages with comfortable print margins and page numbers.
- Clear title block, generated table of contents, and section hierarchy.
- System sans-serif body font with CJK fallbacks.
- Monospace code blocks with wrapping, subtle background, and left accent.
- Bordered tables with shaded headers, cross-page header repeat, and print-friendly spacing.
- Callout-like styling for blockquotes.
- Avoid decorative gradients, oversized hero sections, and marketing-page styling.
- Orphan/widow control for clean paragraph breaks across pages.

For exact style guidance, read `references/technical-document-style.md` before changing CSS or layout behavior.

## Markdown Expectations

The script uses **two parsing modes**:

**Mode A — `markdown` library** (recommended, `pip install markdown`): full CommonMark spec compliance supporting all Markdown below plus images (`![alt](src)`), definition lists, nested lists, auto-links (`<url>`), footnotes, and more.

**Mode B — Built-in fallback** (zero dependencies): supports common AI-generated technical Markdown:

- `#` through `######` headings
- paragraphs, bold, italic, inline code, and links
- fenced code blocks with optional language labels
- unordered and ordered lists, including checklist markers
- blockquotes
- pipe tables
- horizontal rules

If using the fallback parser, install `markdown` (`pip install markdown`) for full capability.

## Output Checks

Before considering a PDF done, check:

- the title and table of contents match the document,
- code blocks are readable and do not clip horizontally,
- tables fit the page (cross-page headers repeat automatically),
- Chinese text renders with a real font,
- page numbers are present and not overlapping content,
- page breaks do not leave major headings stranded at the bottom of a page.
