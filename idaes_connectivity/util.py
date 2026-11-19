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
from http.server import SimpleHTTPRequestHandler
import logging
import multiprocessing
import os
from pathlib import Path
import psutil
from re import compile, Pattern
import signal
import socketserver
import sys
import time
from typing import Dict, Iterable, Optional, Tuple, Union

# third-party
from pandas import DataFrame

_log = logging.getLogger(__name__)

re_prefix_chr = "~"


def get_stream_display_values(
    stream_table: DataFrame,
    value_map: Dict[Union[str, Pattern], Union[str, Tuple[str, str]]],
) -> Dict[str, Dict[str, str]]:
    """Select and format stream values in the `stream_table`.

    Args:
        stream_table: A pandas.DataFrame with streams in the columns and values
                      in the rows. The first column is the Units for the value.
                      This is the default format returned by the IDAES
                      flowsheet `stream_table()` method.
        value_map: Select and format values using this mapping from a stream value name
                   (or regular expression that will match names) to a tuple with the
                   units and format specifier.
                   For example::

                        { "temperature": ("K", ".3g"),
                        re.compile("conc_mass_comp.*"): ("kg/m^3", ".4g") }

                    If the units are None, the value from the "Units" column
                    in the stream table is used. Also, giving a string instead of a
                    tuple will set the units to None.
                    A shorthand for a Pattern is to make the first character in
                    the name of the value whatever `re_prefix_chr` is set to,
                    by default a tilde ("~") character.

                    Thus, the following is equivalent to the above::

                        {"temperature": ".3g",
                         "~conc.mass.comp.*": ".4g"}

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

    # convert bare strings to tuples with None units
    fill_units = {}
    for vm_key, vm_val in value_map.items():
        if isinstance(vm_val, str):
            fill_units[vm_key] = (None, vm_val)
    value_map.update(fill_units)

    # convert special keys to Patterns
    patterns = {}
    for vm_key, vm_val in value_map.items():
        if isinstance(vm_key, str) and vm_key.startswith(re_prefix_chr):
            expr = compile(vm_key[1:])
            patterns[expr] = (vm_key, vm_val)
    for p_key, p_val in patterns.items():
        del value_map[p_val[0]]
        value_map[p_key] = p_val[1]

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

    # put units, from input table, where not specified
    from_table = {}
    for sval, sdisplay in stream_map.items():
        unit, fmt = sdisplay
        if unit is None:
            table_unit = stream_table["Units"][sval]
            from_table[sval] = (table_unit, fmt)
    stream_map.update(from_table)

    # build display values map
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
