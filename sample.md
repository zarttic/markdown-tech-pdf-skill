# API Integration Summary

This document summarizes an AI-generated Markdown report and exports it as a PDF.

## Goals

- Produce a standard technical document.
- Keep code blocks readable.
- Support Chinese text：这是一个技术文档导出测试。

## Endpoint Table

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/v1/reports` | `POST` | Create report |
| `/v1/reports/{id}` | `GET` | Fetch report status |

## Example

```python
def create_report(client, payload):
    return client.post("/v1/reports", json=payload)
```

> Use a restrained print layout rather than a marketing-style page.
