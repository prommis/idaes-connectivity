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
Utility functions and classes.
"""

from pathlib import Path
from typing import Optional
import warnings


class IdaesPaths:
    """IDAES paths, relative to a home directory.

    This class is a singleton.

    Example: `icons_path = IdaesPaths().icons`

    By default, the home directory is `~/.idaes`, however
    a non-standard directory can be set by directly
    setting the class-level attribute `idaes_home`, e.g.::

        IdaesPaths.idaes_home = Path("~/.foobar").expanduser()

    """

    _shared_state = {}  # for singleton pattern

    def __new__(cls, *args, **kwargs):
        """Singleton pattern"""
        obj = super(IdaesPaths, cls).__new__(cls, *args, **kwargs)
        obj.__dict__ = cls._shared_state
        return obj

    def __init__(self):
        """Constructor.

        On first call, tries to set attribute `idaes_home` to `~/.idaes`.
        If this fails, nothing else will work.
        """
        if not hasattr(self, "idaes_home"):
            self.idaes_home = None
            idaes_home = Path("~/.idaes").expanduser()
            if not idaes_home.exists():
                warnings.warn("IDAES  directory '~/.idaes' not found")
            elif not idaes_home.is_dir():
                warnings.warn("IDAES path '~/.idaes' is not a directory")
            else:
                self.idaes_home = idaes_home

    @property
    def icons(self, group: str = None):
        """Path to the directory of SVG icons

        Args:
          group: Currently ignored, but in the future can be used to retrieve different groups of icons.
        """
        if self.idaes_home is None:
            raise ValueError("Cannot get icon path, IDAES home not found")
        return self.idaes_home / "icon_shapes"


class UnitIcon:
    _map = {
        "name1": "compressor",
        "name2": "cooler",
        "name3": "default",
        "name4": "expander",
        "name5": "fan",
        "ScalarFeed": "feed",
        "name7": "flash",
        "name8": "heater_1_flipped",
        "name9": "heater_1",
        "namea": "heater_2",
        "nameb": "heat_exchanger_1",
        "namec": "heat_exchanger_3",
        "named": "horizontal_flash",
        "namee": "mixer_flipped",
        "ScalarMixer": "mixer",
        "nameg": "packed_column_1",
        "nameh": "packed_column_2",
        "namei": "packed_column_3",
        "namej": "packed_column_4",
        "ScalarProduct": "product",
        "namel": "pump",
        "namem": "reactor_c",
        "namen": "reactor_e",
        "nameo": "reactor_g",
        "namep": "reactor_pfr",
        "nameq": "reactor_s",
        "namer": "splitter_flipped",
        "names": "splitter",
        "namet": "tray_column_1",
        "nameu": "tray_column_2",
        "namev": "tray_column_3",
        "namew": "tray_column_4",
    }

    def __init__(self, icon_dir=None, ext="svg"):
        self._path = icon_dir
        self._ext = ext

    def get_icon(self, unit_class_name: str, absolute=True) -> Optional[Path]:
        name = self._map.get(unit_class_name, None)
        if name is not None:
            p = self._path / f"{name}.{self._ext}"
            if absolute:
                p = p.absolute()
        else:
            p = None
        return p
