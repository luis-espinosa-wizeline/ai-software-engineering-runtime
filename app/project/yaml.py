"""Small YAML parsing helpers shared by discovery loaders."""

from collections.abc import Set
from pathlib import Path
from typing import Any, cast

import yaml
from yaml import YAMLError
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


def _duplicate_mapping_key(node: Node) -> str | None:
    """Return the first duplicate scalar mapping key in document order."""
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            if isinstance(key_node, ScalarNode):
                key = cast(str, key_node.value)
                if key in seen:
                    return key
                seen.add(key)
            duplicate = _duplicate_mapping_key(value_node)
            if duplicate is not None:
                return duplicate
    elif isinstance(node, SequenceNode):
        for item in node.value:
            duplicate = _duplicate_mapping_key(item)
            if duplicate is not None:
                return duplicate
    return None


def load_yaml_mapping(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load a YAML document, returning either a mapping or an error detail."""
    try:
        content = path.read_text(encoding="utf-8")
        document = yaml.compose(content)
        if document is not None:
            duplicate = _duplicate_mapping_key(document)
            if duplicate is not None:
                return None, f"duplicate field: {duplicate}"
        value = yaml.safe_load(content)
    except (OSError, UnicodeError, YAMLError) as error:
        return None, str(error)

    if not isinstance(value, dict):
        return None, "document must be a mapping"
    if not all(isinstance(key, str) for key in value):
        return None, "all field names must be strings"
    return value, None


def require_exact_fields(
    data: dict[str, Any],
    *,
    required: Set[str],
    optional: Set[str] = frozenset(),
) -> str | None:
    """Validate the fields of a parsed mapping."""
    missing = sorted(required - data.keys())
    if missing:
        return f"missing required field(s): {', '.join(missing)}"
    unknown = sorted(data.keys() - required - optional)
    if unknown:
        return f"unknown field(s): {', '.join(unknown)}"
    return None
