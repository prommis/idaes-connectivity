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

# stdlib
import logging
from pathlib import Path
from re import compile, Pattern
from typing import Dict, Iterable, Optional, Tuple, Union
import warnings

# third-party
from pandas import DataFrame

_log = logging.getLogger(__name__)


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


def get_stream_display_values(
    stream_table: DataFrame,
    value_map: Dict[Union[str, Pattern], Tuple[str, str]],
) -> Dict[str, Dict[str, str]]:
    """Select and format stream values in the `stream_table`.

    Args:
        stream_table: A pandas.DataFrame with streams in the columns and values
                      in the rows. This is the default format returned by the IDAES
                      flowsheet `stream_table()` method.
        value_map: Select and format values using this mapping from a stream value name
                   (or regular expression that will match names) to a tuple with the
                   units and format specifier.
                   For example::

                        { "temperature": ("K", ".3g"),
                        re.compile("conc_mass_comp.*"): ("kg/m^3", ".4g") }

    Returns:
        Mapping with keys being stream names and values being another
        mapping of stream value names to the formatted display value.
        For example::

            {"stream1": {
                "temperature": "305.128 K",
                 "conc_mass_comp HSO4": "2.71798 kg/m^3" },
             "stream2": {
                "temperature": "305.128 K",
                 "conc_mass_comp HSO4": "2.71798 kg/m^3" },
              ...
            }
    Raises:
        KeyError: Stream name given as a string is not found
    """
    # Table keys should be ['Units', '<stream1>', '<stream2>', ... ]
    if len(stream_table.keys()) < 2:
        return

    stream_names = list(stream_table.keys())[1:]
    stream0 = stream_names[0]

    stream_map = {}

    # set regular expressions first
    for vm_key, vm_val in value_map.items():
        if isinstance(vm_key, Pattern):
            for stream_val_name in stream_table[stream0].keys():
                if vm_key.match(stream_val_name):
                    stream_map[stream_val_name] = vm_val

    # set string matches next (will override regex)
    for vm_key, vm_val in value_map.items():
        if not isinstance(vm_key, Pattern):
            if vm_key not in stream_table[stream0].keys():
                raise KeyError(f"Stream value '{vm_key}' not found in stream table")
            stream_map[vm_key] = vm_val

    result = {}
    for stream_name in stream_names:
        display_values = {}
        for key, value in stream_table[stream_name].items():
            if value == "-" or key not in stream_map:
                continue
            unit, spec = stream_map[key]
            display_value = f"{{v:{spec}}}".format(v=value)
            if unit:
                display_value = f"{display_value} {unit}"
            display_values[key] = display_value
        if display_values:
            result[stream_name] = display_values

    return result
