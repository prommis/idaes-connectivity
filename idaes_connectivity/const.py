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


class ImageNames:
    """Provide access to image files by a standard name.

    Basic usage:

        ```
        # assuming server in util.FileServer running on localhost and some port
        #     server = FileServer(); port = server.start()
        img_names = ImageNames(port=port)
        # this will return a URL usable in a Mermaid diagram:
        url = img_names.get_url("component-name")
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

    def __init__(self, port: int = -1, host: str = "localhost"):
        """Get list of images and associate with standard names.

        Args:
            port: Port of image server
            host: Host of image server. Defaults to "localhost".
        """
        self._images = {n: f"{n}.svg" for n in self.NAMES}
        self._port = port
        self._host = host

    def list_filenames(self) -> list[str]:
        """List all possible image filenames."""
        return list(self._images.values())

    def get_url(self, component) -> str | None:
        """Get image URL.

        Args:
            component: Name of component class or component object

        Raises:
            KeyError: No component found by this name

        Returns:
            Full URL, usable by Mermaid, or None if component has no image
        """
        filename = self._filename(component)
        if filename is None:
            return None
        return f"http://{self._host}:{self._port}/{filename}"

    def get_filename(self, component) -> str | None:
        """Get image filename

        Args:
            component: Name of component class or component object

        Returns:
            str | None: Filename, or None if not found
        """
        return self._filename(component)

    def _filename(self, component) -> str | None:
        name = self._component_name(component)
        if name is None:
            return None

        if name not in self._images:
            # should be there, if not None
            raise RuntimeError(f"Unknown image name '{name}'")

        return self._images[name]

    def _component_name(self, component):
        if isinstance(component, str):
            comp = component.lower()
            if comp in self.NAMES:
                return comp  # already have standard name
            name = component
        else:
            try:
                name = component.local_name
            except AttributeError:
                raise AttributeError(
                    "Cannot get image for object without `.local_name` attribute"
                )

        std_name = None

        if name.endswith("CSTR"):
            std_name = "cstr"
        elif name.endswith("Feed"):
            std_name = "feed"
        elif name.endswith("Flash"):
            std_name = "flash"
        elif name.endswith("Heater"):
            std_name = "heater"
        elif name.endswith("Mixer"):
            std_name = "mixer"
        elif name.endswith("HeatExchanger"):
            std_name = "heat_exchanger"

        return std_name
