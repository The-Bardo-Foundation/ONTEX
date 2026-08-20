from app.services.ai.schemas import PromptEdit
from app.services.prompt_merge import apply_prompt_edits


def test_apply_replace():
    base = "Rule A.\n\nRule B stays."
    edits = [PromptEdit(action="replace", find="Rule A.", content="Rule A (revised).")]
    assert apply_prompt_edits(base, edits) == "Rule A (revised).\n\nRule B stays."


def test_apply_insert_after():
    base = "## REJECT TRAPS\n- existing trap"
    edits = [
        PromptEdit(
            action="insert_after",
            find="- existing trap",
            content="\n- Kaposi sarcoma in title is a false positive",
        )
    ]
    result = apply_prompt_edits(base, edits)
    assert "existing trap\n- Kaposi sarcoma" in result
    assert result.startswith("## REJECT TRAPS")


def test_apply_append():
    base = "Line one."
    edits = [PromptEdit(action="append", content="\n\nNew section.")]
    assert apply_prompt_edits(base, edits) == "Line one.\n\nNew section."


def test_unmatched_find_skipped():
    base = "Unchanged prompt."
    edits = [PromptEdit(action="replace", find="missing text", content="nope")]
    assert apply_prompt_edits(base, edits) == base


def test_empty_edits_returns_base():
    base = "CRITICAL PRINCIPLE: line one\nline two\nline three"
    assert apply_prompt_edits(base, []) == base


def test_strips_duplicate_section_header_from_insert():
    base = '## LABEL: "unsure"\n\nUse "unsure" if uncertain. Examples:\n- Example one'
    edits = [
        PromptEdit(
            action="insert_after",
            find="- Example one",
            content='## LABEL: "unsure"- Broad sarcoma with osteosarcoma eligibility → confident',
        )
    ]
    result = apply_prompt_edits(base, edits)
    assert '## LABEL: "unsure"-' not in result
    assert "- Broad sarcoma with osteosarcoma eligibility" in result


def test_insert_after_adds_bullet_prefix_in_bullet_section():
    base = "## LABEL: \"confident\"\n\nRules:\n- Existing bullet"
    edits = [
        PromptEdit(
            action="insert_after",
            find="- Existing bullet",
            content="New rule without dash",
        )
    ]
    result = apply_prompt_edits(base, edits)
    assert "- Existing bullet\n- New rule without dash" in result


def test_preserves_structure_around_edit():
    base = (
        "CRITICAL PRINCIPLE: When uncertain, use \"unsure\" — do NOT reject.\n"
        "Osteosarcoma is a rare cancer.\n\n"
        "## REJECT TRAPS\n- trap one"
    )
    edits = [
        PromptEdit(
            action="insert_after",
            find="- trap one",
            content="\n- new trap from statistics",
        )
    ]
    result = apply_prompt_edits(base, edits)
    assert "CRITICAL PRINCIPLE: When uncertain" in result
    assert "Osteosarcoma is a rare cancer." in result
    assert "- trap one\n- new trap from statistics" in result
