# Technical Document Style

Use this reference when adjusting the HTML/CSS or when judging whether the PDF looks like a standard technical document.

## Page

- Paper: A4.
- Margins: about 18 mm top/bottom and 16 mm left/right.
- Page numbers: centered at the bottom of each page (can be toggled via `--no-page-number`).
- Background: white.
- Body width: use the printable page naturally; do not center content in a narrow web-page column.

## Typography

- Body: system sans-serif stack with Chinese fallbacks such as Microsoft YaHei and Noto Sans CJK.
- Code: Consolas, Cascadia Mono, Menlo, Monaco, monospace.
- Body size: 10.5-11 pt equivalent for print.
- Line height: 1.55-1.65.
- Letter spacing: normal.

## Structure

- Include a title block at the start.
- Include a generated table of contents when the document has two or more headings below the title.
- Use visible but restrained heading hierarchy.
- Keep headings with following content when possible.
- Avoid web landing-page composition, decorative cards, and large colored hero areas.

## Technical Elements

- Code blocks: light neutral background, subtle border, wrapping enabled, language label optional.
- Inline code: small neutral background and monospace font.
- Tables: full width, collapsed borders, shaded header row, vertical top alignment.
- Blockquotes: left border, neutral background, no oversized quote marks.
- Links: dark blue, underlined only when helpful for print legibility.

## Common Fixes

- If tables are too wide, reduce font size slightly and allow word wrapping.
- If code clips, enforce `white-space: pre-wrap` and `overflow-wrap: anywhere`.
- If CJK text is missing, switch to system CJK fonts before considering embedded fonts.
- If a section starts at the bottom of a page, apply `break-after: avoid` on headings.
- If page numbers overlap content, adjust `@page` margins in `_CSS_PAGE_NUMBERS` in the script.
- If a large table or code block is split awkwardly across pages, ensure `break-inside: avoid` is applied to its container.
- For custom branding, pass `--extra-css` with your own styles (they append after defaults).
