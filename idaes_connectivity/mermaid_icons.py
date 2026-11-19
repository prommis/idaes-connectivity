"""
Icons for mermaid diagrams
"""

import logging

_log = logging.getLogger(__name__)


class Icons:
    """
    Icons for IDAES flowsheet nodes.
    """

    # Map of class suffixes to idaes icons
    suffix_map = {
        "Feed": "feed",
        "Flash": "flash",
        "Heater": "heater-1",
        "Mixer": "mixer",
        "HeatExchanger": "heat-exchanger-1",
    }

    def __init__(self):
        self._smap = self.suffix_map

    def get_icon_for_class(self, comp: str | object) -> str | None:
        """Get name of the IDAES icon for a given component class
        name.

        Returns: name, or None if no match is found
        """
        try:
            class_name = comp.local_name
        except AttributeError:
            class_name = str(comp)
        for k, v in self._smap.items():
            if class_name.endswith(k):
                return v
        _log.debug("No icon found for class '{class_name}': display with generic node")
        return None
