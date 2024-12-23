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
Create and process a connectivity matrix.

The main contents are the `Connectivity` class, which does all the
reading and parsing of connectivity information, and the
`Formatter` subclasses, which write out connectivity information
in various formats.
"""

import abc
import argparse
import csv
from dataclasses import dataclass, field
import enum
import importlib
from io import StringIO
import logging
from pathlib import Path
import re
import sys
from typing import TextIO, Union, Optional, List, Dict
import warnings

# third-party
try:
    import pyomo
    from pyomo.network import Arc
except ImportError as err:
    pyomo = None
    warnings.warn(f"Could not import pyomo: {err}")

from idaes.core import UnitModelBlockData

# package
from idaes_connectivity.util import IdaesPaths, UnitIcon
from idaes_connectivity.const import Direction

__author__ = "Dan Gunter (LBNL)"

# Logging
_log = logging.getLogger(__name__)


class ModelLoadError(Exception):
    def __init__(self, err):
        super(f"Could not load model: {err}")


class Connectivity:
    """Connectivity of a model

    Attributes:
        units (dict): Dictionary with keys being the unit name (in the model instance) and
            values being the unit abbreviation (for Mermaid, etc.)
        streams (dict): Dictionary with keys being the stream name (in the model instance) and
            values being the stream abbreviation (for Mermaid, etc.)
        connections (dict): Dictionary with keys being the stream abbreviation and values being a
            list of length 2, each element of which can contain a unit abbreviation
            or be empty. If the first item in the list has a unit abbreviation, then
            this stream connects to the outlet of that unit; similarly, if the 2nd
            item has a unit abbr then this stream connects to the inlet.
            Thus each item in this dict describes an arc, or a line in a diagram,
            with a stream connecting two units (usual case) or coming into or out of
            a unit as an unconnected feed or outlet for the flowsheet (possible).

    """

    def __init__(
        self,
        units: Dict = None,
        streams: Dict = None,
        connections: Dict = None,
        input_file: Union[str, Path, TextIO] = None,
        input_data: List[List[Union[str, int]]] = None,
        input_module: str = None,
        input_model=None,
        model_flowsheet_attr: str = "fs",
        model_build_func: str = "build",
    ):
        """Constructor.

        Either all three of units, streams, and connections must be given OR
        one of the `input_*` arguments must not be None. They will be looked
        at in the order `input_file` then `input_data` and the first one that is
        not None will be used.

        Args:
            units: See attributes description
            streams: See attributes description
            connections: See attributes description
            input_file: Input CSV file
            input_data: List of input rows.
            input_module: Module from which to load model
            input_model: Existing model object
            model_flowsheet_attr: Attribute on model object with flowsheet. If empty,
                use the model object as the flowsheet.
            model_build_func: Name of function in `input_module` to invoke to build
                and return the model object.
        """
        if units is not None and streams is not None and connections is not None:
            self.units = units
            self.streams = streams
            self.connections = connections
        else:
            if input_module is not None or input_model is not None:
                if input_model is None:
                    try:
                        _log.info("[begin] load and build model")
                        mod = importlib.import_module(input_module)
                        build_function = getattr(mod, model_build_func)
                        _log.debug(f"[begin] build model function={model_build_func}")
                        input_model = build_function()
                        _log.debug("[ end ] build model")
                        _log.info("[ end ] load and build model")
                    except Exception as err:
                        raise ModelLoadError(err)
                if model_flowsheet_attr == "":
                    flowsheet = input_model
                else:
                    flowsheet = getattr(input_model, model_flowsheet_attr)
                self._load_model(flowsheet)
            elif input_file is not None or input_data is not None:
                _log.info("[begin] load from file or data")
                if input_file is not None:
                    if isinstance(input_file, str) or isinstance(input_file, Path):
                        datafile = open(input_file, "r")
                    else:
                        datafile = input_file
                    reader = csv.reader(datafile)
                    self._header = next(reader)
                    self._rows = list(reader)
                else:
                    self._header = input_data[0]
                    self._rows = input_data[1:]
                _log.info("[end] load from file or data")
            else:
                raise ValueError("No inputs provided")
            self.units = self._build_units()
            self.streams = self._build_streams()
            self.connections = self._build_connections()

    def as_table(self) -> List[List[str]]:
        rows = [self._header.copy()]
        for r in self._rows:
            rows.append(r.copy())
        return rows

    def _build_units(self):
        units = {}
        c1, c2 = 1, -1
        for s in self._header[1:]:
            abbr = "Unit_"
            # Pick abbreviations that match spreadsheet column names,
            # for easier comparison and debugging: A-Z then AA-ZZ
            if c2 > -1:
                abbr += chr(ord("A") + c2)
            abbr += chr(ord("A") + c1)
            units[s] = abbr
            c1 += 1
            if c1 == 26:  # after Z, start on AA..ZZ
                c1 = 0
                c2 += 1
        return units

    def _build_streams(self):
        streams = {}
        n = 3  # pick numbers that match spreadsheet row numbers
        for row in self._rows:
            s = row[0]
            abbr = f"Stream_{n}"
            streams[s] = abbr
            n += 1
        return streams

    def _build_connections(self):
        units, streams = self.units, self.streams  # aliases
        n_cols = len(self._header)
        connections = {s: [None, None] for s in streams.values()}
        for i, row in enumerate(self._rows):
            stream_name = row[0]
            for col in range(1, n_cols):
                conn = row[col]
                # get integer connection value
                if isinstance(conn, str):
                    if conn.strip() == "":
                        conn_value = 0
                    else:
                        conn_value = int(float(conn))  # may raise ValueError
                elif isinstance(conn, int):
                    conn_value = conn
                elif isinstance(conn, float):
                    conn_value = int(conn)
                else:
                    raise ValueError(
                        f"Connection value type '{type(conn)}' not string or numeric"
                    )
                # check connection value
                if conn_value not in (-1, 0, 1):
                    raise ValueError(
                        f"Connection value '{conn_value}' not in {{-1, 0, 1}}"
                    )
                # process connection value
                if conn_value != 0:
                    conn_index = max(conn_value, 0)  # -1 -> 0
                    unit_name = self._header[col]
                    stream_abbr, unit_abbr = streams[stream_name], units[unit_name]
                    connections[stream_abbr][conn_index] = unit_abbr
        return connections

    def _load_model(self, fs):
        units_ord, units_idx = {}, 0
        units, streams = [], []
        streams_ord, streams_idx = {}, 0
        rows, empty = [], True
        arcs = fs.component_objects(Arc, descend_into=False)
        sorted_arcs = sorted(arcs, key=lambda arc: arc.getname())
        for comp in sorted_arcs:
            stream_name = comp.getname()
            src, dst = comp.source.parent_block(), comp.dest.parent_block()
            src_name, dst_name = self._model_unit_name(src), self._model_unit_name(dst)
            # print(f"{src_name} , {dst_name}")
            src_i, dst_i, stream_i = -1, -1, -1
            try:
                idx = streams_ord[stream_name]
            except KeyError:
                streams.append(stream_name)
                idx = streams_ord[stream_name] = streams_idx
                streams_idx += 1
                if empty:  # first entry in matrix
                    rows = [[]]
                    empty = False
                else:
                    rows.append([0] * len(rows[0]))
            stream_i = idx

            # build rows
            endpoints = [None, None]
            for ep, unit_name in enumerate(
                [
                    src_name,
                    dst_name,
                ]
            ):
                try:
                    idx = units_ord[unit_name]
                except KeyError:  # create new column
                    units.append(unit_name)
                    idx = units_ord[unit_name] = units_idx
                    units_idx += 1
                    for row in rows:
                        row.append(0)
                endpoints[ep] = idx
            rows[stream_i][endpoints[0]] = -1
            rows[stream_i][endpoints[1]] = 1

        self._header = ["Arcs"] + units
        self._rows = [[streams[i]] + r for i, r in enumerate(rows)]

    @staticmethod
    def _model_unit_name(block):
        """Get the unit name for a Pyomo/IDAES block."""
        name = block.getname()
        class_name = block.__class__.__name__
        # extract last part of the name
        m = re.search(r"[a-zA-Z]\w+$", class_name)
        if m is None:
            return name
        block_type = class_name[m.start() : m.end()]
        return f"{name}::{block_type}"


class Formatter(abc.ABC):
    """Base class for formatters, which write out the matrix in a way that can be
    more easily visualized or processed by other tools.
    """

    def __init__(self, connectivity: Connectivity, direction: str = None, **kwargs):
        self._conn = connectivity
        if direction is None:
            self._direction = Direction.RIGHT
        else:
            self._parse_direction(direction)

    def _parse_direction(self, d):
        if d.lower() == "lr":
            self._direction = Direction.RIGHT
        elif d.lower() == "td":
            self._direction = Direction.DOWN
        else:
            raise ValueError(f"Direction '{d}' not recognized")

    @abc.abstractmethod
    def write(
        self,
        output_file: Union[str, TextIO, None],
    ) -> Optional[str]:
        pass

    def _write_return(self, f):
        """Call this at the end of the write() methods."""
        if isinstance(f, StringIO):
            f.flush()
            return f.getvalue()
        else:
            return None

    @staticmethod
    def _get_output_stream(output_file):
        if output_file is None:
            f = StringIO()
        elif hasattr(output_file, "write"):
            f = output_file
        else:
            f = open(output_file, "w")
        return f


class CSV(Formatter):
    """Write out the data as CSV."""

    def write(self, output_file: Union[str, TextIO, None]) -> Optional[str]:
        f = self._get_output_stream(output_file)
        table = self._conn.as_table()
        writer = csv.writer(f, dialect="excel")
        for row in table:
            writer.writerow(row)
        return self._write_return(f)


class Mermaid(Formatter):
    """Create output in Mermaid syntax.

    See https://mermaid.js.org/
    """

    def __init__(
        self,
        connectivity: Connectivity,
        stream_labels: bool = False,
        indent="   ",
        **kwargs,
    ):
        super().__init__(connectivity, **kwargs)
        self.indent = indent
        self._stream_labels = stream_labels
        if self._direction == Direction.RIGHT:
            self._mm_dir = "LR"
        elif self._direction == Direction.DOWN:
            self._mm_dir = "TD"
        else:
            raise RuntimeError(f"Unknown parsed direction '{self._direction}'")

    def write(self, output_file: Union[str, TextIO, None]) -> Optional[str]:
        """Write Mermaid (plain or encapsulated) file

        Args:
            output_file (Union[str, TextIO, None]): Output file object, filename,
               or None meaning return a string

        Raises:
            ValueError: This output format is not handled (e.g., CSV)

        Returns:
            str | None: If `output_file` was None then return output as a string, otherwise None
        """
        f = self._get_output_stream(output_file)
        self._body(f)
        return self._write_return(f)

    def _body(self, outfile):
        i = self.indent
        outfile.write(f"flowchart {self._mm_dir}\n")
        # Get connections first, so we know which streams to show
        connections, show_streams = self._get_connections()
        # Units
        for s in self._get_mermaid_units():
            outfile.write(f"{i}{s}\n")
        # Streams
        for abbr, s in self._get_mermaid_streams():
            if abbr in show_streams:
                outfile.write(f"{i}{s}\n")
        # Connections
        for s in connections:
            outfile.write(f"{i}{s}\n")

    def _get_mermaid_units(self):
        for name, abbr in self._conn.units.items():
            yield f"{abbr}[{name}]"

    def _get_mermaid_streams(self):
        for name, abbr in self._conn.streams.items():
            yield abbr, f"{abbr}([{name}])"

    def _get_connections(self):
        connections = []
        show_streams = set()

        stream_name_map = {v: k for k, v in self._conn.streams.items()}
        for stream_abbr, values in self._conn.connections.items():
            stream_name = stream_name_map[stream_abbr]
            src, tgt = values[0], values[1]
            if values[0] is not None and values[1] is not None:
                if self._stream_labels:
                    label = self._clean_stream_label(stream_name)
                    connections.append(f"{src} --|{label}| -->{tgt}")
                else:
                    connections.append(f"{src} --> {tgt}")
            elif values[0] is not None:
                connections.append(f"{src} --> {stream_abbr}")
                show_streams.add(stream_abbr)
            elif values[1] is not None:
                connections.append(f" {stream_abbr} --> {tgt}")
                show_streams.add(stream_abbr)
        return connections, show_streams

    @staticmethod
    def _clean_stream_label(label):
        if label.endswith("_outlet"):
            label = label[:-7]
        elif label.endswith("_feed"):
            label = label[:-5]
        label = label.replace("_", " ")
        return label


class D2(Formatter):
    """Create output in Terraform D2 syntax.

    See https://d2lang.com
    """

    def __init__(
        self, connectivity: Connectivity, stream_labels: bool = False, **kwargs
    ):
        super().__init__(connectivity, **kwargs)
        self._labels = stream_labels
        if self._direction == Direction.RIGHT:
            self._d2_dir = "right"
        elif self._direction == Direction.DOWN:
            self._d2_dir = "down"
        else:
            raise RuntimeError(f"Unknown parsed direction '{self._direction}'")

    def write(self, output_file: Union[str, TextIO, None]) -> Optional[str]:
        unit_icon = UnitIcon(IdaesPaths().icons)
        feed_num, sink_num = 1, 1
        f = self._get_output_stream(output_file)
        f.write(f"direction: {self._d2_dir}\n")
        for unit_name, unit_abbr in self._conn.units.items():
            unit_str, unit_type = self._split_unit_name(unit_name)
            image_file = None if unit_type is None else unit_icon.get_icon(unit_type)
            if image_file is None:
                f.write(f"{unit_abbr}: {unit_str}\n")
            else:
                f.write(
                    f"{unit_abbr}: {unit_str} {{\n"
                    f"  shape: image\n"
                    f"  icon: {image_file}\n"
                    f"}}\n"
                )
        stream_rmap = {v: k for k, v in self._conn.streams.items()}
        for stream_abbr, conns in self._conn.connections.items():
            stream_name = stream_rmap[stream_abbr]
            if conns[0] is None:
                f.write(f"f{feed_num}: Feed {feed_num}\n")
                f.write(f"f{feed_num} -> {conns[1]}")
                if self._labels:
                    f.write(f": {stream_name}")
                f.write("\n")
                feed_num += 1
            elif conns[1] is None:
                f.write(f"s{sink_num}: Sink {sink_num}\n")
                f.write(f"f{sink_num} -> {conns[1]}")
                if self._labels:
                    f.write(f": {stream_name}")
                f.write("\n")
                sink_num += 1
            else:
                f.write(f"{conns[0]} -> {conns[1]}")
                if self._labels:
                    f.write(f": {stream_name}")
                f.write("\n")

        return self._write_return(f)

    @staticmethod
    def _split_unit_name(n):
        parts = n.split("::", 1)
        if len(parts) == 1:
            return None, n
        return parts
