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

DEFAULT_SERVER_ROOT = Path.home() / ".idaes"

# For dark/light images
LIGHT = "light"
DARK = "dark"


class ComponentNames:
    """Get a standardized name for a component.

    Basic usage:

        ```
        comp_names = ComponentNames()
        filename = comp_names.get_filename(component)
        ```
    """

    filenames = {
        "compressor": "compressor.svg",
        "cooler": "cooler.svg",
        "cstr": "cstr.svg",  #
        "expander": "expander.svg",
        "fan": "fan.svg",
        "feed": "feed.svg",  #
        "flash": "flash.svg",  #
        "gibbs_reactor": "gibbs_reactor.svg",
        "heater": "heater_1.svg",  #
        "heat_exchanger": "heat_exchanger.svg",  #
        "mixer": "mixer.svg",  #
        "product": "product.svg",
        "pump": "pump.svg",
        "splitter": "splitter.svg",
        "stoichiometric_reactor": "reactor_s.svg",
    }

    def get_filename(self, component, dark_mode: bool = False) -> str | None:
        """Get (image) filename associated with component

        Args:
            component: Name of component class, component object,
                       or standardized name in `self.NAMES`
            dark_moe: Get inverted images if dark mode is true

        Returns:
            str | None: Filename, or None if no match

        Raises:
            AttributeError: if component was an object
                            without a `local_name` attribute
        """
        try:
            result = self.filenames[self._comp_name(component)]
        except KeyError:
            result = None

        # add dark/light mode marker
        mode = DARK if dark_mode else LIGHT
        spos = result.rfind(".")
        result = result[:spos] + "_" + mode + result[spos:]

        return result

    def _comp_name(self, component):
        """ "Get canonical name, for matching to image files"""
        # extract the component's name
        if isinstance(component, str):
            # check if matches canonical name, then stop
            if (cname := component.lower()) in self.filenames:
                return self.filenames[cname]
            # assume it's the name of class
            name = component
        else:
            name = component.local_name
        # map to canonical name
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
        elif name.endswith("Separator"):
            return "splitter"
        elif name.endswith("HeatExchanger"):
            return "heat_exchanger"
        elif name.endswith("StoichiometricReactor"):
            return "stoichiometric_reactor"
        elif name.endswith("PressureChanger"):
            return "compressor"
        raise KeyError(name)
