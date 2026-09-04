"""Authoritative action metadata for constructed agents."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from tau2.environment.tool import Tool
from tau2.environment.toolkit import ToolType


@dataclass(frozen=True)
class ActionDefinition:
    """Serializable metadata describing one executable action."""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    return_schema: Mapping[str, Any]
    tool_type: ToolType
    mutates_state: bool

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible metadata without the execution handler."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": dict(self.input_schema),
            "return_schema": dict(self.return_schema),
            "tool_type": self.tool_type.value,
            "mutates_state": self.mutates_state,
        }


class ActionCatalog:
    """A validated catalog joining action metadata to runtime handlers."""

    def __init__(self, tools: Sequence[Tool]):
        tools_by_name = {tool.name: tool for tool in tools}
        if len(tools_by_name) != len(tools):
            raise ValueError("Action names must be unique")

        self._tools_by_name = MappingProxyType(tools_by_name)
        self._definitions = tuple(self._definition_for(tool) for tool in tools)

    @staticmethod
    def _definition_for(tool: Tool) -> ActionDefinition:
        schema = tool.openai_schema["function"]
        tool_type = ToolType(tool.info.get("tool_type", ToolType.GENERIC.value))
        return ActionDefinition(
            name=tool.name,
            description=schema["description"],
            input_schema=MappingProxyType(schema["parameters"]),
            return_schema=MappingProxyType(tool.returns.model_json_schema()),
            tool_type=tool_type,
            mutates_state=bool(tool.info.get("mutates_state", True)),
        )

    @property
    def definitions(self) -> tuple[ActionDefinition, ...]:
        """Return stable metadata in source-tool order."""
        return self._definitions

    @property
    def names(self) -> tuple[str, ...]:
        """Return action names in source-tool order."""
        return tuple(definition.name for definition in self._definitions)

    def tools(self, names: Sequence[str] | None = None) -> tuple[Tool, ...]:
        """Resolve all tools or an explicitly ordered subset by name."""
        if names is None:
            return tuple(self._tools_by_name[name] for name in self.names)
        unknown = set(names) - self._tools_by_name.keys()
        if unknown:
            raise ValueError(
                f"Unknown action names {sorted(unknown)}; available: {list(self.names)}"
            )
        return tuple(self._tools_by_name[name] for name in names)
