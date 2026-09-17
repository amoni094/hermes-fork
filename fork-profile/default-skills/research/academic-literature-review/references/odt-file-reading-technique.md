# Reading .odt Files on This Host
Date: 2026-07-28

## Problem
`read_file` and `mcp__read_file` cannot read binary `.odt` files.
`officecli` does not handle `.odt`.
`pip` is not on the host PATH.

## Solution: toolbox run python3 with odfpy

`odfpy` is pre-installed in the toolbox container (not on the host).
Always use `toolbox run python3`, never bare `python3` or `pip install odfpy`.

```bash
toolbox run python3 -c "
from odf.opendocument import load
from odf.text import P
doc = load('/path/to/file.odt')
text = ''
for para in doc.body.getElementsByType(P):
    parts = []
    for node in para.childNodes:
        if hasattr(node, 'data'):
            parts.append(node.data)
        elif hasattr(node, 'childNodes'):
            for n in node.childNodes:
                if hasattr(n, 'data'):
                    parts.append(n.data)
    text += ''.join(parts) + '\n'
print(text)
"
```

## Verification
Confirmed working July 2026 on /var/home/rainbow/Documents/research.odt — extracted
full plain-text content of a multi-section research document.

## Notes
- The nested childNode loop is needed because odfpy text content can be inside span
  elements (e.g. formatted runs) rather than directly in paragraph nodes.
- For very large ODT files, pipe output through `head -c 30000` or similar.
