import dagster as dg
from dataclasses import dataclass
import re

_FIELD_LINE_RE = re.compile(r'^( *)(\S+)\s*(.*)$')

@dataclass
class DocChunk:
    resource: str
    field_path: str
    content: str


def _parse_field_line(line: str):
    """Return (indent_level, field_name, type_annotation) or None."""
    match = _FIELD_LINE_RE.match(line)
    if not match:
        return None
    indent = len(match.group(1))
    level = indent // 2
    name = match.group(2)
    type_ann = match.group(3).strip()
    return level, name, type_ann


def _chunk_explain(resource: str, text: str) -> list[dict]:
    """Split one resource's explain output into chunks by field-path hierarchy.

    Strategy:
    * A *preamble* chunk holds KIND / VERSION / DESCRIPTION (everything before
      the FIELDS: section).
    * Each **top-level field** (indent level 1 under FIELDS:) starts a new
      chunk.  All deeper nested fields are included in their parent
      top-level field's chunk.
    * Every chunk carries a ``field_path`` breadcrumb, e.g.
      ``pods.spec`` or ``pods.metadata``, so retrieval can scope on it.
    """
    lines = text.splitlines()
    chunks: list[dict] = []

    # -- locate FIELDS: header -------------------------------------------------
    fields_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "FIELDS:":
            fields_idx = i
            break

    # Preamble: everything before (and including) the FIELDS: header line
    preamble_lines = lines[: fields_idx + 1] if fields_idx is not None else lines
    preamble_text = "\n".join(preamble_lines).strip()
    if preamble_text:
        chunks.append({
            "resource": resource,
            "field_path": resource,
            "content": preamble_text,
        })

    if fields_idx is None:
        # No FIELDS section – return just the preamble
        return chunks

    # -- walk the FIELDS block and split on top-level fields -------------------
    current_field: str | None = None
    current_lines: list[str] = []

    def _flush():
        nonlocal current_field, current_lines
        if current_field is not None and current_lines:
            breadcrumb = f"{resource}.{current_field}"
            chunks.append({
                "resource": resource,
                "field_path": breadcrumb,
                "content": f"{resource} > {current_field}\n" + "\n".join(current_lines),
            })
        current_field = None
        current_lines = []

    for line in lines[fields_idx + 1:]:
        parsed = _parse_field_line(line)
        if parsed is None:
            # blank / unparseable – attach to current chunk if any
            if current_field is not None:
                current_lines.append(line)
            continue

        level, name, type_ann = parsed

        if level == 1:
            # New top-level field → flush previous
            _flush()
            current_field = name
            header = f"  {name}"
            if type_ann:
                header += f"  {type_ann}"
            current_lines.append(header)
        else:
            # Nested field – include in current top-level chunk
            if current_field is not None:
                current_lines.append(line)

    _flush()
    return chunks


@dg.asset
def chunked_docs(k8s_explain_docs: dict[str, str]) -> list[dict]:
    """Chunk explain output by field-path hierarchy.

    Each resource is split into:
      * one preamble chunk (KIND / VERSION / DESCRIPTION)
      * one chunk per top-level field under FIELDS:, containing that
        field and all its nested children.

    The ``field_path`` on every chunk encodes the breadcrumb
    (e.g. ``deployments.apps.spec``), which downstream retrieval can
    filter on.
    """
    chunks: list[dict] = []

    for resource, content in k8s_explain_docs.items():
        chunks.extend(_chunk_explain(resource, content))

    return chunks