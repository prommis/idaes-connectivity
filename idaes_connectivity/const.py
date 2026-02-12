###############################################################################
# PrOMMiS was produced under the DOE Process Optimization and Modeling
# for Minerals Sustainability (“PrOMMiS”) initiative, and is
# Copyright © 2024-2025 by the software owners: The Regents of the
# University of California, through Lawrence Berkeley National
# Laboratory, National Technology & Engineering Solutions of Sandia, LLC,
# Carnegie Mellon University, West Virginia University Research
# Corporation, University of Notre Dame, and Georgia Institute of
# Technology. All rights reserved.
###############################################################################
"""
Shared constants for idaes_connectivity
"""
# stdlib
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import threading

# third-party
from idaes.models import unit_models as um

__author__ = "Dan Gunter (LBNL)"


class OutputFormats(Enum):
    MERMAID = "mermaid"
    CSV = "csv"
    D2 = "d2"
    HTML = "html"


class Direction(Enum):
    RIGHT = 0
    DOWN = 1


CONSOLE = "-"

DEFAULT_IMAGE_DIR = Path.home() / ".idaes" / "images"


class ComponentNames:
    """Get a standardized name for a component.

    Basic usage:

        ```
        comp_names = ComponentNames()
        filename = comp_names.get_filename(component)
        ```
    """

    NAMES = (
        "compressor",
        "cooler",
        "cstr",  #
        "expander",
        "fan",
        "feed",  #
        "flash",  #
        "gibbs_reactor",
        "heater",  #
        "heat_exchanger",  #
        "mixer",  #
        "product",
        "pump",
        "splitter",
    )

    def __init__(self):
        """Constructor."""
        self._filenames = {n: f"{n}.svg" for n in self.NAMES}

    def get_filename(self, component) -> str | None:
        """Get (image) filename associated with component

        Args:
            component: Name of component class, component object,
                       or standardized name in `self.NAMES`

        Returns:
            str | None: Filename, or None if no match

        Raises:
            AttributeError: if component was an object
                            without a `local_name` attribute
        """
        try:
            name = self._comp_name(component)
            result = self._filenames[name]
        except KeyError:
            result = None
        return result

    def _comp_name(self, component):
        # extract the component's name
        if isinstance(component, str):
            comp = component.lower()
            if comp in self.NAMES:
                return comp  # already have standard name
            name = component
        else:
            name = component.local_name
        # map to standardized name
        if name.endswith("CSTR"):
            return "cstr"
        elif name.endswith("Feed"):
            return "feed"
        elif name.endswith("Flash"):
            return "flash"
        elif name.endswith("Heater"):
            return "heater"
        elif name.endswith("Mixer"):
            return "mixer"
        elif name.endswith("HeatExchanger"):
            return "heat_exchanger"
        raise KeyError(name)
