# Markdown Tech PDF Skill

Codex skill for converting AI-generated Markdown summaries into polished technical PDF documents.

## Install With npx

```bash
npx @zartt/markdown-tech-pdf
```

This copies the `markdown-tech-pdf` skill into your Codex skills directory and overwrites the previous local copy if one exists.

## Install With Vercel Skills

This repository is compatible with the Vercel `skills` CLI:

```bash
npx skills add zarttic/markdown-tech-pdf-skill
```

The CLI detects the `markdown-tech-pdf` skill from this repository and can install it for supported agents.

## What It Does

- Converts Markdown into a restrained technical-document HTML layout.
- Prints the HTML to PDF through a local Chromium-family browser such as Microsoft Edge, Google Chrome, or Chromium.
- Supports common technical Markdown: headings, lists, checklists, links, blockquotes, fenced code blocks, and pipe tables.
- Includes print-oriented CSS for A4 pages, readable code blocks, table styling, a title block, and a generated table of contents.
- Uses Chinese-capable system font fallbacks for mixed English and Chinese documentation.

## Manual Install

Copy the skill folder into your Codex skills directory:

```powershell
Copy-Item -Recurse -Force `
  ".\markdown-tech-pdf" `
  "$env:USERPROFILE\.codex\skills\markdown-tech-pdf"
```

Restart Codex after copying the folder.

## Direct Script Usage

```powershell
python ".\markdown-tech-pdf\scripts\md_to_tech_pdf.py" ".\sample.md" ".\sample.pdf" --title "Technical Report"
```

Optional HTML output:

```powershell
python ".\markdown-tech-pdf\scripts\md_to_tech_pdf.py" ".\sample.md" ".\sample.pdf" --html-output ".\sample.html"
```

## Requirements

- Python 3.10+
- Microsoft Edge, Google Chrome, or Chromium available on the machine

No Pandoc dependency is required.
