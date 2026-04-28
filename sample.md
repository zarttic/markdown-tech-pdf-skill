# API Integration Technical Summary

This sample shows the kind of AI-generated Markdown report that the skill converts into a standard technical PDF. It includes section hierarchy, a generated table of contents, tables, code blocks, blockquotes, and mixed English/Chinese content.

## Goals

- Produce a restrained engineering document instead of a marketing-style page.
- Keep code blocks readable in print.
- Preserve tables, inline code, links, lists, and blockquotes.
- Support Chinese text: 这是一个技术文档导出测试。

## Architecture Notes

The report API accepts a normalized request payload, stores the job metadata, and returns a polling URL. Workers process the report asynchronously and update job status.

> The PDF output should prioritize scanability, stable layout, and readable technical details over visual decoration.

## Endpoint Table

| Endpoint | Method | Purpose | Response |
| --- | --- | --- | --- |
| `/v1/reports` | `POST` | Create report | `202 Accepted` |
| `/v1/reports/{id}` | `GET` | Fetch report status | `200 OK` |
| `/v1/reports/{id}/download` | `GET` | Download generated PDF | `302 Found` |

## Example Request

```json
{
  "title": "Weekly Engineering Summary",
  "range": {
    "from": "2026-04-20",
    "to": "2026-04-27"
  },
  "format": "pdf",
  "audience": "manager"
}
```

## Client Helper

```python
def create_report(client, payload):
    response = client.post("/v1/reports", json=payload, timeout=20)
    response.raise_for_status()
    return response.json()["id"]
```

## Release Checklist

- [x] Generate HTML with print-oriented CSS.
- [x] Render PDF through a Chromium-family browser.
- [x] Keep generated screenshots in the repository for README previews.
- [ ] Add project-specific branding if needed.
