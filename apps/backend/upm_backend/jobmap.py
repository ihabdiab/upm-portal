"""Re-export the job<->definition mapping (canonical home: control_plane.mapping)."""

from upm_control_plane.mapping import definition_to_kwargs, row_to_definition

__all__ = ["definition_to_kwargs", "row_to_definition"]
