"""
designlab_core.prompts.loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Load Markdown prompt templates by ID and inject variables.

Usage:
    from designlab_core.prompts.loader import load_prompt

    prompt = load_prompt(
        "REQ-001-story-generation",
        variables={"feature_description": "Allow users to reset their password..."},
    )

The loader searches all subdirectories under designlab_core/prompts/ for a
matching .md file. Template IDs correspond to filenames without the extension.


Status: COMPLETE
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from designlab_core.utilities.logger import get_logger
from designlab_core.utilities.env import get_env

_logger = get_logger("prompts.loader")

# Root directory containing all prompt template subdirectories
_PROMPTS_DIR = Path(__file__).parent


# ── Template Discovery ────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _build_template_index() -> dict[str, Path]:
    """
    Build an index mapping template IDs to their file paths.

    Scans all subdirectories of the prompts/ directory for .md files.
    The template ID is the filename stem (without extension).

    Returns:
        Dictionary mapping template ID → absolute Path.

    Example:
        {"REQ-001-story-generation": Path(".../requirements/REQ-001-story-generation.md")}
    """
    index: dict[str, Path] = {}

    for md_file in _PROMPTS_DIR.rglob("*.md"):
        template_id = md_file.stem
        if template_id in index:
            _logger.warning(
                f"Duplicate template ID '{template_id}' found. "
                f"Using: {index[template_id]}, ignoring: {md_file}"
            )
        else:
            index[template_id] = md_file

    _logger.debug(f"Template index built: {len(index)} templates found")
    return index


def list_templates() -> list[str]:
    """
    Return a sorted list of all available template IDs.

    Useful for debugging and for API endpoints that need to enumerate
    available prompt templates.

    Returns:
        Sorted list of template ID strings.
    """
    return sorted(_build_template_index().keys())


# ── Template Loading ──────────────────────────────────────────────────────────


def load_prompt(
    template_id: str,
    variables: dict[str, str] | None = None,
) -> str:
    """
    Load a prompt template by ID and inject variables into placeholders.

    Searches all subdirectories under designlab_core/prompts/ for a .md file
    whose stem matches ``template_id``. Then replaces all ``{{variable_name}}``
    placeholders with the corresponding values from ``variables``.

    Args:
        template_id: The template identifier (filename without .md extension).
                     Examples: "REQ-001-story-generation", "ARC-001-system-architecture".
        variables:   Dictionary of placeholder names to replacement values.
                     Keys should NOT include the ``{{ }}`` delimiters.
                     Example: {"feature_description": "Allow users to reset..."}

    Returns:
        The fully assembled prompt string with all placeholders replaced.

    Raises:
        FileNotFoundError: If no template matches the given ID.
        ValueError: If the template contains unreplaced placeholders after injection.

    Example:
        prompt = load_prompt(
            "REQ-001-story-generation",
            variables={"feature_description": "User password reset via email link."},
        )
    """
    index = _build_template_index()

    if template_id not in index:
        limit = get_env().prompts_max_list_display
        available = ", ".join(sorted(index.keys())[:limit])
        raise FileNotFoundError(
            f"Prompt template '{template_id}' not found. "
            f"Available templates: {available}"
            + (" ..." if len(index) > limit else "")
        )

    template_path = index[template_id]
    content = template_path.read_text(encoding="utf-8")

    _logger.debug(f"Loaded template '{template_id}' from {template_path}")

    # Inject variables into {{placeholder}} patterns
    if variables:
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            if placeholder in content:
                content = content.replace(placeholder, value)
                _logger.debug(f"Injected variable '{key}' ({len(value)} chars)")
            else:
                _logger.warning(
                    f"Variable '{key}' provided but placeholder "
                    f"'{placeholder}' not found in template '{template_id}'"
                )

    # Check for any remaining unreplaced placeholders
    remaining = re.findall(r"\{\{(\w+)\}\}", content)
    if remaining:
        raise ValueError(
            f"Template '{template_id}' has unreplaced placeholders: "
            f"{', '.join(f'{{{{{p}}}}}' for p in remaining)}. "
            f"Provide values for these in the 'variables' argument."
        )

    return content
