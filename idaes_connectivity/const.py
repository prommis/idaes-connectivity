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
from pathlib import Path

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


class Images:
    """Provide access to image files by a canonical name."""

    DIRNAME = "images"  # relative to location of this file

    def __init__(self, root: str | Path = None):
        # construct path to image directory
        if root is None:
            root = Path(__file__).parent
        elif not isinstance(Path, root):
            root = Path(root)
        image_dir = root / self.DIRNAME
        # check image directory
        if not image_dir.exists():
            raise FileNotFoundError(f"Directory {image_dir} does not exist")
        elif not image_dir.is_dir():
            raise FileNotFoundError(f"Path {image_dir} must be a directory")
        self._image_dir = image_dir
        # give names to files
        self._names = {}
        self._set_names()

    def list_names(self, img_type=None) -> list[str]:
        """List all of the names for which we have an image."""
        if img_type is None:
            img_type = "all"
        elif img_type not in self._names:
            raise KeyError("Bad image type")
        return list(self._names[img_type].keys())

    def get_file(self, name, as_url=True, img_type=None):
        """Get file (or file:// URL) corresponding to given
        image name and, optionally, type.
        """
        # choose mapping to search
        if img_type:
            if img_type in self._names:
                data = self._names[img_type]
        else:
            data = self._names["all"]
        # look for name in mapping
        if name not in data:
            raise KeyError(f"Unknown image name '{name}'")
        # get associated filename
        filename = data[name]
        filepath = str((self._image_dir / filename).absolute())
        # return filename as plain file or URL
        if as_url:
            result = f"file://{filepath}"
        else:
            result = filepath

        return result

    def _set_names(self):
        self._names = {"svg": {}, "png": {}, "all": {}}
        for filepath in self._image_dir.glob("*"):
            sfx = filepath.suffix
            img_type = sfx[1:] if sfx in (".svg", ".png") else None
            if img_type:
                name = self._name(filepath.stem)
                if name:
                    filename = str(filepath)
                    self._names[img_type][name] = filename
                    self._names["all"][name] = filename

    def _name(self, s: str) -> str:
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
            return s
        if s == "heat_exchanger_1.svg":
            return "heat_exchanger"
        if s == "heater_1.svg":
            return "heater"
