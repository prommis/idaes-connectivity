"""
Create and process a connectivity matrix.

This module can be run as a script or used programmatically, using the
public functions `create_from_matrix` and `create_from_model`.
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
from typing import TextIO, Union, Optional, List
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
from idaes_connectivity.const import OutputFormats, Direction

__author__ = "Dan Gunter (LBNL)"

# Logging
# This variable is reassigned if run as script
_log = logging.getLogger(__name__)


class Formatter(abc.ABC):
    """Base class for formatters, which write out the matrix in a way that can be
    more easily visualized or processed by other tools.
    """

    def __init__(self, connectivity, direction: str = None, **kwargs):
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
        output_format: Union[OutputFormats, str] = None,
    ) -> Optional[str]:
        pass

    @staticmethod
    def _get_output_stream(output_file):
        if output_file is None:
            f = StringIO()
        elif hasattr(output_file, "write"):
            f = output_file
        else:
            f = open(output_file, "w")
        return f


class Mermaid(Formatter):
    """Create output in Mermaid syntax.

    See https://mermaid.js.org/
    """

    def __init__(
        self,
        connectivity,
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

    def write(
        self,
        output_file: Union[str, TextIO, None],
        output_format: Union[OutputFormats, str] = None,
    ) -> Optional[str]:
        """Write Mermaid (plain or encapsulated) file

        Args:
            output_file (Union[str, TextIO, None]): Output file object, filename,
               or None meaning return a string
            output_format (Union[OutputFormats, str], optional): Output format. Defaults to None.

        Raises:
            ValueError: This output format is not handled (e.g., CSV)

        Returns:
            str | None: If `output_file` was None then return output as a string, otherwise None
        """
        f = self._get_output_stream(output_file)

        output_format = _output_format(output_format)
        if output_format == OutputFormats.MERMAID:
            self._body(f)
        else:  # !! should not get here
            raise ValueError(f"Output format not handled: {output_format}")

        if output_file is None:
            return f.getvalue()

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

    def __init__(self, connectivity, stream_labels: bool = False, **kwargs):
        super().__init__(connectivity, **kwargs)
        self._labels = stream_labels
        if self._direction == Direction.RIGHT:
            self._d2_dir = "right"
        elif self._direction == Direction.DOWN:
            self._d2_dir = "down"
        else:
            raise RuntimeError(f"Unknown parsed direction '{self._direction}'")

    def write(
        self,
        output_file: Union[str, TextIO, None],
        output_format: Union[OutputFormats, str] = None,
    ) -> Optional[str]:
        unit_icon = UnitIcon(Paths().icons)
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

        if output_file is None:
            f.flush()
            return f.getvalue()

    @staticmethod
    def _split_unit_name(n):
        parts = n.split("::", 1)
        if len(parts) == 1:
            return None, n
        return parts


@dataclass
class Connectivity:
    """Connectivity of a model."""

    #: Dictionary with keys being the unit name (in the model instance) and
    #: values being the unit abbreviation (for Mermaid, etc.)
    units: dict = field(default_factory=dict)
    #: Dictionary with keys being the stream name (in the model instance) and
    #: values being the stream abbreviation (for Mermaid, etc.)
    streams: dict = field(default_factory=dict)
    #: Dictionary with keys being the stream abbreviation and values being a
    #: list of length 2, each element of which can contain a unit abbreviation
    #: or be empty. If the first item in the list has a unit abbreviation, then
    #: this stream connects to the outlet of that unit; similarly, if the 2nd
    #: item has a unit abbr then this stream connects to the inlet.
    #: Thus each item in this dict describes an arc, or a line in a diagram,
    #: with a stream connecting two units (usual case) or coming into or out of
    #: a unit as an unconnected feed or outlet for the flowsheet (possible).
    connections: dict = field(default_factory=dict)


class ConnectivityBuilder:
    """Build connectivity information, as an instance of :class:`Connectivity`,
    from input data."""

    def __init__(
        self,
        input_file: Union[str, Path, TextIO] = None,
        input_data: List[List[Union[str, int]]] = None,
    ):
        """Constructor.

        One of the `input_*` arguments must not be None. They will be looked
        at in the order `input_file` then `input_data` and the first one that is
        not None will be used.

        Args:
            input_file: Input CSV file
            input_data: List of input rows.
        """
        if input_file is not None:
            if isinstance(input_file, str) or isinstance(input_file, Path):
                datafile = open(input_file, "r")
            else:
                datafile = input_file
            reader = csv.reader(datafile)
            self._header = next(reader)
            self._rows = list(reader)
        elif input_data is not None:
            self._header = input_data[0]
            self._rows = input_data[1:]
        else:
            raise ValueError("Either 'input_file' or 'input_data' must not be None")
        self._c = None

    @property
    def connectivity(self) -> Connectivity:
        if self._c is None:
            units = self._build_units()
            streams = self._build_streams()
            connections = self._build_connections(units, streams)
            self._c = Connectivity(
                units=units, streams=streams, connections=connections
            )
        return self._c

    def _build_units(self):
        units = {}
        c1, c2 = 1, -1
        for s in self._header[1:]:
            abbr = "Unit_"
            # Pick abbreviations that match spreadsheet column names,
            # for easier comparison and debugging.
            # i.e. A-Z then AA-ZZ. chr(x) returns ASCII character at x,
            # and ord(x) is the reverse function. e.g., chr(ord("A") + 1) == "B"
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

    def _build_connections(self, units, streams):
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


class ModelConnectivity:
    """Extract connectivity information from a model."""

    def __init__(self, model, flowsheet_attr: str = "fs"):
        """Constructor

        Args:
            model: Pyomo ConcreteModel instance with an attribute, ".fs"
                   that is (or acts like) an IDAES flowsheet

        Raises:
            NotImplementedError: If Pyomo isn't installed
        """
        if pyomo is None:
            raise NotImplementedError(
                "Trying to build from a Pyomo model, but Pyomo is not installed"
            )
        fa = flowsheet_attr.strip("'").strip('"').strip()
        if not re.match(r"[a-zA-Z_]+", fa):
            raise ValueError("Flowsheet attribute can only be letters and underscores")
        self._fs = eval(f"model.{fa}")
        self._units = []
        self._streams = []
        self._build()

    def _build(self):
        fs = self._fs  # alias
        units_ord, units_idx = {}, 0
        streams_ord, streams_idx = {}, 0
        rows, empty = [], True
        for comp in self._arcs_sorted_by_name(fs):
            stream_name = comp.getname()
            src, dst = comp.source.parent_block(), comp.dest.parent_block()
            src_name, dst_name = self.unit_name(src), self.unit_name(dst)
            # print(f"{src_name} , {dst_name}")
            src_i, dst_i, stream_i = -1, -1, -1
            try:
                idx = streams_ord[stream_name]
            except KeyError:
                self._streams.append(stream_name)
                idx = streams_ord[stream_name] = streams_idx
                streams_idx += 1
                if empty:
                    rows = [[]]
                    empty = False
                else:
                    rows.append([0] * len(rows[0]))
            stream_i = idx

            for unit_name, is_src in (src_name, True), (dst_name, False):
                try:
                    idx = units_ord[unit_name]
                except KeyError:
                    self._units.append(unit_name)
                    idx = units_ord[unit_name] = units_idx
                    units_idx += 1
                    for row in rows:
                        row.append(0)
                if is_src:
                    src_i = idx
                else:
                    dst_i = idx

            rows[stream_i][src_i] = -1
            rows[stream_i][dst_i] = 1

        self._rows = rows

    @staticmethod
    def unit_name(block):
        name = block.getname()
        class_name = block.__class__.__name__
        m = re.search(r"[a-zA-Z]\w+$", class_name)
        if m is None:
            return name
        block_type = class_name[m.start() : m.end()]
        return f"{name}::{block_type}"

    @staticmethod
    def _arcs_sorted_by_name(fs):
        """Try and make the output stable by looping through the Pyomo
        Arcs in alphabetical order, by their name.
        """
        arcs = fs.component_objects(Arc, descend_into=False)
        return sorted(arcs, key=lambda arc: arc.getname())

    def write(self, f: TextIO):
        """Write the CSV file."""
        header = self._units.copy()
        header.insert(0, "Arcs")
        f.write(",".join(header))
        f.write("\n")
        for row_idx, row in enumerate(self._rows):
            row.insert(0, self._streams[row_idx])
            f.write(",".join((str(value) for value in row)))
            f.write("\n")

    def get_data(self):
        """Get rows of CSV file as data."""
        data = [["Arcs"] + self._units.copy()]
        for row_idx, row in enumerate(self._rows):
            data.append([self._streams[row_idx]] + row)
        return data


############
# Utility
############


def _get_model(module_name, build_func):
    _log.info("[begin] load and build model")
    mod = importlib.import_module(module_name)
    build_function = getattr(mod, build_func)
    _log.debug(f"[begin] build model function={build_func}")
    model = build_function()
    _log.debug("[ end ] build model")
    _log.info("[ end ] load and build model")
    return model


##################
# Public interface
##################


def create_from_matrix(
    ifile: Union[str, TextIO],
    ofile: Optional[str] = None,
    to_format: Union[OutputFormats, str] = None,
    formatter_options: dict = None,
) -> Union[Connectivity, None]:
    """Programmatic interface to create a graph of the model from a connectivity matrix.

    Args:
        ifile: Input file (name or path)
        ofile: Output file name. If this is the special value defined by `AS_STRING`, then
               The output will go to the console. If None, then no output will
               be created and the connectivity will be returned as an object.
        to_format: Output format, which should match one of the values in `OutputFormat`
        formatter_options: Keyword arguments to pass to the output formatter

    Returns:
        Connectivity instance, if ofile is None

    Raises:
        RuntimeError: For all errors captured during Mermaid processing
        ValueError: Bad output format
    """
    conn_file = ConnectivityBuilder(ifile)
    output_format = _output_format(to_format)

    if ofile is None:
        return conn_file.connectivity

    try:
        conn = conn_file.connectivity
    except Exception as err:
        err_msg = f"Could not parse connectivity information: {err}. "
        # err_msg += f"Stack trace:\n{format_stack()}"
        raise RuntimeError(err_msg)

    formatter_kw = formatter_options or {}

    if output_format == OutputFormats.MERMAID:
        formatter = Mermaid(conn_file.connectivity, **formatter_kw)
    elif output_format == OutputFormats.D2:
        formatter = D2(conn_file.connectivity, **formatter_kw)
    else:
        raise RuntimeError(f"No processing defined for output format: {output_format}")

    if ofile == AS_STRING:
        print(formatter.write(None, output_format=output_format))
    else:
        formatter.write(ofile, output_format=output_format)


def create_from_model(
    model: object = None,
    module_name: str = None,
    ofile: Union[str, TextIO] = None,
    to_format: Union[OutputFormats, str] = None,
    build_func: str = "build",
    flowsheet_attr: str = "fs",
    formatter_options: dict = None,
) -> Union[Connectivity, None]:
    """Programmatic interface to create the connectivity or mermaid output from a python model.

    Arguments:
        model: If present, the model to use
        module_name: Dotted Python module name (absolute, e.g. package.subpackage.module).
                     The protocol is to call the `build()` function in the module to get
                     back a model.
        ofile: Output file name. If this is the special value defined by `AS_STRING`, then
               The output will go to the console. If None, then no output will
               be created and the connectivity will be returned as an object.
        to_format: Output format
        formatter_options: Keyword arguments to pass to the output formatter

    Returns:
        Connectivity instance, if ofile is None

    Raises:
        RuntimeError: For all errors captured while building the model, or internal errors
        ValueError: Bad output format
    """
    output_format = _output_format(to_format)

    if model is None:
        try:
            model = _get_model(module_name, build_func)
        except Exception as err:
            # XXX: create custom Exception subclass for this
            raise RuntimeError(f"Could not load model: {err}")
    else:
        pass  # assume it's already loaded into this variable

    model_conn = ModelConnectivity(model, flowsheet_attr=flowsheet_attr)

    if ofile == AS_STRING:
        output_stream = sys.stdout
    else:
        output_stream = ofile
    data = model_conn.get_data()
    # No output: return connectivity
    if ofile is None:
        cb = ConnectivityBuilder(input_data=data)
        return cb.connectivity
    # CSV output
    elif output_format == OutputFormats.CSV:
        if isinstance(output_stream, str):
            output_stream = open(output_stream, "w")
        model_conn.write(output_stream)
    else:
        cb = ConnectivityBuilder(input_data=data)
        formatter_kw = formatter_options or {}

        # Mermaid output
        if output_format == OutputFormats.MERMAID:
            formatter = Mermaid(cb.connectivity, **formatter_kw)
        # D2 output
        elif output_format == OutputFormats.D2:
            formatter = D2(cb.connectivity, **formatter_kw)
        else:
            raise RuntimeError(f"No processing defined for output format: {to_format}")

        formatter.write(output_stream, output_format=output_format)


def _output_format(fmt):
    if fmt is None or isinstance(fmt, OutputFormats):
        return fmt
    try:
        return OutputFormats(fmt)
    except ValueError:
        raise ValueError(f"Bad output format: {fmt}")
