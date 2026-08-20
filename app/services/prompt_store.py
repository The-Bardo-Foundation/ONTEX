"""Storage and resolution of the active classifier system prompt.

The classifier prompt is versioned in the ``classifier_prompt_versions`` table
with exactly one active row. The hardcoded ``CLASSIFICATION_SYSTEM_PROMPT``
constant becomes a seed + fallback only: if the table is empty (e.g. before the
seeding migration has run, or in a fresh test DB) we lazily insert it as the
first active version so the classifier always has something to use.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClassifierPromptVersion
from app.services.ai.prompts import CLASSIFICATION_SYSTEM_PROMPT


async def _seed_default(db: AsyncSession) -> ClassifierPromptVersion:
    version = ClassifierPromptVersion(
        content=CLASSIFICATION_SYSTEM_PROMPT,
        source="seed",
        note="Initial prompt seeded from CLASSIFICATION_SYSTEM_PROMPT.",
        is_active=True,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


async def get_active_version(db: AsyncSession) -> ClassifierPromptVersion:
    """Return the active prompt version, lazily seeding the default if none."""
    result = await db.execute(
        select(ClassifierPromptVersion).where(ClassifierPromptVersion.is_active.is_(True))
    )
    version = result.scalars().first()
    if version is None:
        # No active row — fall back to any existing row, else seed the default.
        any_row = (
            await db.execute(
                select(ClassifierPromptVersion).order_by(
                    ClassifierPromptVersion.id.desc()
                )
            )
        ).scalars().first()
        if any_row is not None:
            any_row.is_active = True
            await db.commit()
            await db.refresh(any_row)
            return any_row
        return await _seed_default(db)
    return version


async def get_active_prompt(db: AsyncSession) -> str:
    """Return the active classifier prompt text (with seed/fallback)."""
    version = await get_active_version(db)
    return version.content or CLASSIFICATION_SYSTEM_PROMPT


async def list_versions(db: AsyncSession) -> list[ClassifierPromptVersion]:
    """Return all prompt versions, newest first."""
    result = await db.execute(
        select(ClassifierPromptVersion).order_by(
            ClassifierPromptVersion.created_at.desc(),
            ClassifierPromptVersion.id.desc(),
        )
    )
    return list(result.scalars().all())


async def _deactivate_all(db: AsyncSession) -> None:
    result = await db.execute(
        select(ClassifierPromptVersion).where(ClassifierPromptVersion.is_active.is_(True))
    )
    for row in result.scalars().all():
        row.is_active = False


async def create_version(
    db: AsyncSession,
    *,
    content: str,
    source: str = "manual",
    note: str | None = None,
    created_by: str | None = None,
    advice_run_id: int | None = None,
    activate: bool = True,
) -> ClassifierPromptVersion:
    """Insert a new prompt version. When ``activate`` is true, deactivate the
    previously active row(s) so exactly one version is active."""
    if activate:
        await _deactivate_all(db)
    version = ClassifierPromptVersion(
        content=content,
        source=source,
        note=note,
        created_by=created_by,
        advice_run_id=advice_run_id,
        is_active=activate,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


async def activate_version(db: AsyncSession, version_id: int) -> ClassifierPromptVersion | None:
    """Make an existing version the active one (rollback). Returns None if the
    version does not exist."""
    target = (
        await db.execute(
            select(ClassifierPromptVersion).where(ClassifierPromptVersion.id == version_id)
        )
    ).scalars().first()
    if target is None:
        return None
    await _deactivate_all(db)
    target.is_active = True
    await db.commit()
    await db.refresh(target)
    return target
