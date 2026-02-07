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
from importlib.resources import files
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


class ImageType(Enum):
    SVG = "svg"
    PNG = "png"
    ALL = "all"


class HttpImages:
    """Provide access to image files by a standard name."""

    DIRNAME = "images"  # relative to location of this file

    def __init__(self, host="localhost", port=8000, protocol="http"):
        """Get list of images and associate with standard names."""
        # use importlib so this works on installed wheels, too
        self._image_path = files("idaes_connectivity.images")
        # give names to files
        self._names = {}
        self._set_names()
        self._base_url = f"{protocol}://{host}:{port}"
        self.host, self.port = host, port

    def list_names(self, img_type: ImageType = ImageType.ALL) -> list[str]:
        """List all of the names for which we have an image."""
        return list(self._names[img_type].keys())

    def get_url(self, name, img_type: ImageType = None) -> str:
        """Get image URL (local server)"""
        # choose mapping to search
        if img_type is not None:
            if img_type in self._names:
                data = self._names[img_type]
        else:
            data = self._names[ImageType.ALL]
        # look for name in mapping
        if name not in data:
            raise KeyError(f"Unknown image name '{name}'")
        # get associated filename
        filename = data[name]

        return f"{self._base_url}/{filename}"

    def _set_names(self):
        """Find images in a directory and match them with names."""
        self._names = {ImageType.SVG: {}, ImageType.PNG: {}, ImageType.ALL: {}}
        for filepath in self._image_path.iterdir():
            sfx = filepath.suffix
            img_type = ImageType(sfx[1:]) if sfx in (".svg", ".png") else None
            if img_type:
                name = self._name(filepath.stem)
                if name:
                    filename = filepath.name
                    self._names[img_type][name] = filename
                    self._names[ImageType.ALL][name] = filename

    def _name(self, s: str) -> str:
        result = ""
        s = s.lower()

        if s in (
            "compressor",
            "cooler",
            "expander",
            "fan",
            "feed",
            "flash",
            "mixer",
            "product",
            "pump",
            "splitter",
        ):
            result = s
        elif s == "heat_exchanger_1":
            result = "heat_exchanger"
        elif s == "heater_1":
            result = "heater"

        return result
