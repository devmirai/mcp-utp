"""UTP MCP Server — Compact formatter utilities.

Provides token-efficient output formatting for MCP tools.
When MCP_COMPACT=1 (env), tools return compact output instead of full JSON.
"""

import json
import os

# Fields that are internal IDs for tool chaining — shown in compact form
_INTERNAL_IDS = {"courseId", "sectionId", "activityId"}


def _is_compact() -> bool:
    """Read MCP_COMPACT dynamically so .env is loaded before first use."""
    return os.getenv("MCP_COMPACT", "0") == "1"


def fmt(data) -> str:
    """Format data: compact or full JSON based on MCP_COMPACT env."""
    if not _is_compact():
        return json.dumps(data, ensure_ascii=False, indent=2)

    if isinstance(data, list):
        return _fmt_list(data)
    elif isinstance(data, dict):
        return _fmt_dict(data)
    elif isinstance(data, str):
        return data
    else:
        return str(data)


def fmt_error(message: str) -> str:
    """Format an error message consistently in both modes."""
    if not _is_compact():
        return json.dumps({"error": message}, ensure_ascii=False, indent=2)
    return f"**Error:** {message}"


def _fmt_list(items: list) -> str:
    if not items:
        return "_(sin resultados)_"

    # Handle non-dict items (scalars, None)
    if items and not isinstance(items[0], dict):
        return "\n".join(f"- {item}" for item in items)

    lines = []
    for i, item in enumerate(items, 1):
        display = {}
        ids = {}
        for k, v in item.items():
            if k in _INTERNAL_IDS:
                ids[k] = v
            else:
                display[k] = v

        fields = []
        for label, val in display.items():
            if isinstance(val, bool):
                val = "✅" if val else "❌"
            elif isinstance(val, list) and val:
                if isinstance(val[0], dict):
                    # Summarize list of dicts: show count + key fields
                    count = len(val)
                    # Extract up to 3 most relevant fields from first item
                    first = val[0]
                    priority_keys = [k for k in ("courseName", "name", "title", "cycle", "grade", "status", "approvalStatus") if k in first]
                    if priority_keys:
                        summaries = []
                        for item in val[:5]:
                            parts = f"{priority_keys[0]}={item.get(priority_keys[0], '?')}"
                            if len(priority_keys) > 1:
                                parts += f" ({priority_keys[1]}={item.get(priority_keys[1], '?')})"
                            summaries.append(parts)
                        val = "; ".join(summaries)
                        if count > 5:
                            val += f" ...y {count - 5} más"
                    else:
                        val = f"{count} items"
                else:
                    val = ", ".join(str(v) for v in val[:3])
            elif isinstance(val, dict):
                val = " ".join(f"{k}:{v}" for k, v in list(val.items())[:3])
            val_str = str(val) if val is not None else ""
            fields.append(f"  {label}: {val_str}")

        # Full IDs for tool chaining (not truncated)
        if ids:
            id_parts = " | ".join(f"{k}: {v}" for k, v in ids.items())
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
