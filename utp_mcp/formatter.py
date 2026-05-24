"""UTP MCP Server — Compact formatter utilities.

Provides token-efficient output formatting for MCP tools.
When MCP_COMPACT=1 (env), tools return compact output instead of full JSON.
"""

import json
import os

COMPACT = os.getenv("MCP_COMPACT", "0") == "1"

# Fields that are internal IDs for tool chaining — shown compactly in compact mode
_INTERNAL_IDS = {"courseId", "sectionId", "activityId"}


def fmt(data) -> str:
    """Format data: compact or full JSON based on MCP_COMPACT env."""
    if not COMPACT:
        return json.dumps(data, ensure_ascii=False, indent=2)

    if isinstance(data, list):
        return _fmt_list(data)
    elif isinstance(data, dict):
        return _fmt_dict(data)
    else:
        return str(data)


def _fmt_list(items: list) -> str:
    if not items:
        return "_(sin resultados)_"

    lines = []
    for i, item in enumerate(items, 1):
        # Separate display fields from internal IDs
        display = {}
        ids = {}
        for k, v in item.items():
            if k in _INTERNAL_IDS:
                ids[k] = v
            else:
                display[k] = v

        # Build display fields
        fields = []
        for label, val in display.items():
            if isinstance(val, bool):
                val = "✅" if val else "❌"
            elif isinstance(val, list):
                val = ", ".join(str(v) for v in val[:3])
            elif isinstance(val, dict):
                val = " ".join(f"{k}:{v}" for k, v in list(val.items())[:3])
            val_str = str(val) if val is not None else ""
            fields.append(f"  {label}: {val_str}")

        # Add compact IDs line if any
        if ids:
            id_parts = " | ".join(f"{k[-3:]}:{v[:8]}..." for k, v in ids.items())
            fields.append(f"  IDs: {id_parts}")

        header = f"**[ {i} ]**" if len(items) > 1 else ""
        body = "\n".join(fields)
        if header and len(items) > 1:
            lines.append(f"{header}\n{body}")
        else:
            lines.append(body)

    return "\n".join(lines)


def _fmt_dict(d: dict) -> str:
    lines = []
    for k, v in d.items():
        if isinstance(v, list) and v:
            if isinstance(v[0], dict):
                lines.append(f"**{k}:** {len(v)} items")
                for item in v[:5]:
                    short = ", ".join(f"{kk}={vv}" for kk, vv in list(item.items())[:3])
                    lines.append(f"  - {short}")
                if len(v) > 5:
                    lines.append(f"  ... y {len(v) - 5} más")
            else:
                lines.append(f"**{k}:** {', '.join(str(x) for x in v[:10])}")
        elif isinstance(v, dict):
            inner = ", ".join(f"{kk}: {vv}" for kk, vv in v.items())
            lines.append(f"**{k}:** {inner}")
        else:
            lines.append(f"**{k}:** {v}")
    return "\n".join(lines)
