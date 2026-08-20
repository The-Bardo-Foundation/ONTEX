"""Apply surgical prompt edits onto the active classifier prompt.

The advice LLM returns content-only deltas (find/replace, insertions) so unchanged
sections stay byte-identical — no reformatting or structural churn.
"""

from __future__ import annotations

import logging

from app.services.ai.schemas import PromptEdit

logger = logging.getLogger(__name__)

_SECTION_HEADERS = (
    '## LABEL: "confident"',
    '## LABEL: "unsure"',
    '## LABEL: "reject"',
    "REJECT TRAPS",
    "## CONCRETE EXAMPLES",
)


def _normalize_insert_content(content: str, anchor: str, action: str) -> str:
    """Ensure inserted text flows naturally after the anchor."""
    if action not in {"insert_after", "insert_before"}:
        return content

    text = content
    # Strip accidental duplicate section headers glued to new rules.
    for header in _SECTION_HEADERS:
        if text.lstrip().startswith(header):
            rest = text.lstrip()[len(header) :].lstrip(" -:\u2014")
            text = rest if rest.startswith("-") else f"- {rest}" if rest else text
            break

    if action == "insert_after":
        if not text.startswith("\n"):
            text = f"\n{text}"
        # New list items inside a bullet section should start with "- ".
        stripped = text.lstrip("\n")
        if anchor.strip().startswith("-") and stripped and not stripped.startswith("-"):
            text = f"\n- {stripped}"
    elif action == "insert_before" and not text.endswith("\n"):
        text = f"{text}\n"

    return text


def _find_anchor(text: str, needle: str) -> tuple[int, int] | None:
    """Return (start, length) for an exact or whitespace-normalised anchor match."""
    if not needle:
        return None
    idx = text.find(needle)
    if idx != -1:
        return idx, len(needle)
    # Fallback: single-line anchor with collapsed whitespace.
    if "\n" not in needle:
        for line in text.split("\n"):
            if " ".join(line.split()) == " ".join(needle.split()):
                pos = text.find(line)
                if pos != -1:
                    return pos, len(line)
    return None


def apply_prompt_edits(base: str, edits: list[PromptEdit]) -> str:
    """Apply edits in order onto ``base``. Unmatched edits are skipped with a warning."""
    result = base
    for i, edit in enumerate(edits):
        if not edit.content.strip():
            logger.warning("prompt_edit[%d]: empty content; skipped", i)
            continue

        if edit.action == "append":
            addition = edit.content
            if result and not result.endswith("\n") and not addition.startswith("\n"):
                result += "\n"
            result += addition
            continue

        needle = edit.find or ""
        if not needle.strip():
            logger.warning("prompt_edit[%d]: %s requires non-empty find; skipped", i, edit.action)
            continue

        located = _find_anchor(result, needle)
        if located is None:
            logger.warning(
                "prompt_edit[%d]: find string not found (%r); skipped", i, needle[:80]
            )
            continue

        idx, length = located
        anchor = result[idx : idx + length]
        content = _normalize_insert_content(edit.content, anchor, edit.action)

        if edit.action == "replace":
            result = result[:idx] + content + result[idx + length :]
        elif edit.action == "insert_after":
            insert_at = idx + length
            result = result[:insert_at] + content + result[insert_at:]
        elif edit.action == "insert_before":
            result = result[:idx] + content + result[idx:]

    return result
