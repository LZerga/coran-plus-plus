"""The Markdown the command line prints, turned into HTML for the web page.

One rendering for both (the page shows exactly what the command prints). Only the
subset the harness writes is handled: headings, lists, tables, paragraphs, **bold**,
`code` and [links](path). Everything is escaped first; the only HTML kept is the <br> of table cells.
"""

from __future__ import annotations

import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`(.+?)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def _inline(text: str) -> str:
    text = html.escape(text, quote=False).replace("&lt;br&gt;", "<br>")
    text = _CODE.sub(r"<code>\1</code>", text)
    text = _LINK.sub(lambda m: f'<a href="{html.escape(m.group(2))}" data-file="{html.escape(m.group(2))}">{m.group(1)}</a>', text)
    return _BOLD.sub(r"<strong>\1</strong>", text)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def to_html(markdown: str) -> str:
    out: list[str] = []
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("#"):
            level = min(len(line) - len(line.lstrip("#")), 4)
            out.append(f"<h{level + 1}>{_inline(line.lstrip('#').strip())}</h{level + 1}>")
            i += 1
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{_inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            head, body = block[0], [row for row in block[1:] if not set(row) <= set("|-: ")]
            rows = ["<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in _cells(head)) + "</tr>"]
            rows += ["<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in _cells(row)) + "</tr>" for row in body]
            out.append('<div class="scroll"><table>' + "".join(rows) + "</table></div>")
        else:
            out.append(f"<p>{_inline(line)}</p>")
            i += 1
    return "\n".join(out)
