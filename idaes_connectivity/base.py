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
from collections.abc import MutableMapping
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

# package
from idaes_connectivity.util import IdaesPaths, UnitIcon
from idaes_connectivity.const import Direction

__author__ = "Dan Gunter (LBNL)"

# Logging
_log = logging.getLogger(__name__)


class ModelLoadError(Exception):
    def __init__(self, err):
        super().__init__(f"Could not load model: {err}")


class DataLoadError(Exception):
    def __init__(self, path, err):
        super().__init__(f"Could not load from file '{path}': {err}")


class ValueContainer:
    def __init__(self, obj):
        self.value = obj


class Connectivity:
    """Represent connectivity of a Pyomo/IDAES model.

    Once built, the connectivity is represented by
    three attributes, `units`, `streams`, and `connections`.

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

    #: Default class for a unit
    DEFAULT_UNIT_CLASS = "Component"

    def __init__(
        self,
        units: Dict = None,
        streams: Dict = None,
        connections: Dict = None,
        input_file: Union[str, Path, TextIO] = None,
        input_data: List[List[Union[str, int]]] = None,
        input_module: str = None,
        input_model=None,
        model_flowsheet_attr: str = "",
        model_build_func: str = "build",
    ):
        """Create from existing data or one of the valid input types.

        Either all three of units, streams, and connections must be given OR
        one of the `input_*` arguments must not be None. They will be looked
        at in the order: model, module, file, data.

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

        Raises:
            ModelLoadError: Couldn't load the model/module
            ValueError: Invalid inputs
        """
        self._unit_classes = {}
        self._arc_descend = True  # XXX: Maybe make this an option later?
        if units is not None and streams is not None and connections is not None:
            self.units = units
            self._unit_classes = {k: self.DEFAULT_UNIT_CLASS for k in self.units}
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
                    try:
                        flowsheet = getattr(input_model, model_flowsheet_attr)
                    except AttributeError as err:
                        raise ModelLoadError(err)
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
                if len(self._rows) == 0:  # e.g., when loading from CSV
                    raise DataLoadError(datafile.name, "Empty file")
                _log.info("[end] load from file or data")
            else:
                raise ValueError("No inputs provided")
            self.units = self._build_units()
            if len(self._unit_classes) == 0:
                self._unit_classes = {k: self.DEFAULT_UNIT_CLASS for k in self.units}
            self._unit_values = {k: {} for k in self.units}
            self.streams = self._build_streams()
            self._stream_values = {k: {} for k in self.streams}
            self.connections = self._build_connections()

    @property
    def stream_values(self):
        """Get current stream values.

        This returns a copy, that can be modified without changing the underlying
        values in the class.
        """
        return {
            k1: {k2: v2.value for k2, v2 in v1.items()}
            for k1, v1 in self._stream_values.items()
        }

    def set_stream_value(self, stream_name: str, key: str, value):
        """Set a value for a stream.

        Args:
            stream_name: Name of the stream
            key: Name of the value
            value: The value. Accepts Pyomo value objects with a `.value` attribute, or
                   "plain" values (string or numeric).

        Raises:
            KeyError: If the `stream_name` is not a valid stream.
        """
        if stream_name not in self._stream_values:
            raise KeyError(f"No stream with name '{stream_name}'")
        values = self._stream_values[stream_name]
        values[key] = value if hasattr(value, "value") else ValueContainer(value)

    def set_stream_values_map(self, stream_values_map: Dict[str, Dict[str, str]]):
        """Set multiple stream values using a mapping.

        Args:
            stream_values_map: Mapping with keys being stream names and values being
                               another mapping of stream value names to the value.

        Raises:
            KeyError: If any of the stream names is not a valid stream.
        """
        for stream_name, set_values in stream_values_map.items():
            for key, value in set_values.items():
                self.set_stream_value(stream_name, key, value)

    def clear_stream_values(self):
        """Remove all stream values."""
        self._stream_values = {}

    @property
    def unit_values(self):
        """Get current unit values.

        This returns a copy, that can be modified without changing the underlying
        values in the class.
        """
        return {
            k1: {k2: v2.value for k2, v2 in v1.items()}
            for k1, v1 in self._unit_values.items()
        }

    def set_unit_value(self, unit_name: str, key: str, value):
        """Set a value for a unit.
        This method has the same semantics as :meth:`set_stream_value`.
        """
        if unit_name not in self._unit_values:
            raise KeyError(f"No unit with name '{unit_name}'")
        values = self._unit_values[unit_name]
        values[key] = value if hasattr(value, "value") else ValueContainer(value)

    def set_unit_values_map(self, unit_values_map: Dict[str, Dict[str, str]]):
        """Set multiple unit values using a mapping.
        This method has the same semantics as :meth:`set_stream_values_map`.
        """
        for unit_name, set_values in unit_values_map.items():
            for key, value in set_values.items():
                self.set_unit_value(unit_name, key, value)

    def clear_unit_values(self):
        """Remove all unit values."""
        self._unit_values = {}

    def set_unit_class(self, unit_name: str, class_name: str):
        """Set name of the unit class.

        This will override the class inferred from the model, if any.

        Args:
            unit_name: Name of the unit
            class_name: Arbitrary name of unit's class (or type)

        Raises:
            KeyError: If `unit_name` does not correspond to a unit.
        """
        self._unit_classes[unit_name] = class_name

    def get_unit_class(self, name: str):
        """Get class for a unit.

        Args:
            name: Name of the unit

        Raises:
            KeyError: If the unit is not valid
        """
        # if len(self._unit_classes) == 0:
        #     self._unit_classes = {k: self.DEFAULT_UNIT_CLASS for k in self.units}
        return self._unit_classes[name]

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
            if not row:
                continue
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
            if not row:
                continue
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
        _log.info("_begin_ load model")
        units_ord, units_idx = {}, 0
        units, streams = [], []
        streams_ord, streams_idx = {}, 0
        rows, empty = [], True
        arcs = fs.component_objects(Arc, descend_into=self._arc_descend)
        sorted_arcs = sorted(arcs, key=lambda arc: arc.getname())
        if _log.isEnabledFor(logging.DEBUG):
            _log.debug(f"Arc short names: {[a.getname() for a in sorted_arcs]}")
            _log.debug(f"Arc full names : {[a.name for a in sorted_arcs]}")
        self._build_name_map(sorted_arcs)

        for comp in sorted_arcs:
            stream_name = comp.getname()
            src, dst = comp.source.parent_block(), comp.dest.parent_block()
            src_name, dst_name = self._model_unit_name(src), self._model_unit_name(dst)
            self._unit_classes[src_name] = self._model_unit_class(src)
            self._unit_classes[dst_name] = self._model_unit_class(dst)
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
        _log.info("_end_ load model")

    def _build_name_map(self, arcs):
        """Mapping to strip off any prefixes common to all unit names.
        This mapping is used by :func:`_model_unit_name`.
        """
        self._name_map = None
        if len(arcs) < 2:
            return
        # split names by "." into tuples
        name_tuples = []
        for comp in arcs:
            for p in comp.source, comp.dest:
                nm = p.parent_block().name.split(".")
                name_tuples.append(nm)
        # iteratively look if all prefixes of length n are the same
        n = 1
        while True:
            prefixes = {tuple(nm[:n]) for nm in name_tuples}
            if len(prefixes) > 1:  # not common to all = stop
                n -= 1
                break
            n += 1
        if n > 0:
            self._name_map = {".".join(k): ".".join(k[n:]) for k in name_tuples}

    def _build_name_map(self, arcs):
        """Mapping to strip off any prefixes common to all unit names.
        This mapping is used by :func:`_model_unit_name`.
        """
        self._name_map = None
        if len(arcs) < 2:
            return
        # split names by "." into tuples
        name_tuples = []
        for comp in arcs:
            for p in comp.source, comp.dest:
                nm = p.parent_block().name.split(".")
                name_tuples.append(nm)
        # iteratively look if all prefixes of length n are the same
        n = 1
        while True:
            prefixes = {tuple(nm[:n]) for nm in name_tuples}
            if len(prefixes) > 1:  # not common to all = stop
                n -= 1
                break
            n += 1
        if n > 0:
            self._name_map = {".".join(k): ".".join(k[n:]) for k in name_tuples}

    def _model_unit_name(self, block):
        """Get the unit name for a Pyomo/IDAES block."""
        return block.name if self._name_map is None else self._name_map[block.name]

    def _model_unit_class(self, block):
        class_name = block.__class__.__name__
        # extract last part of the name
        m = re.search(r"[a-zA-Z]\w+$", class_name)
        if m is None:
            return self._model_unit_name(block)
        return class_name[m.start() : m.end()]


class Formatter(abc.ABC):
    """Base class for formatters, which write out the matrix in a way that can be
    more easily visualized or processed by other tools.
    """

    defaults = {}  # extend in subclasses

    def __init__(self, connectivity: Connectivity, **kwargs):
        self._conn = connectivity

    @staticmethod
    def _parse_direction(d):
        if not hasattr(d, "lower"):
            raise ValueError(f"Direction '{d}' must be a string")
        if d.lower() == "lr":
            return Direction.RIGHT
        elif d.lower() == "td":
            return Direction.DOWN
        raise ValueError(f"Direction '{d}' not recognized")

    @abc.abstractmethod
    def write(
        self,
        output_file: Union[str, TextIO, None],
    ) -> Optional[str]:
        """Write the formatted output.

        Args:
            output_file: The output file. It can be a filename or file object.
                         The special value `None` means return the text as a string.

        Returns:
            If `None` was given as the *output_file*, return the text as a string.
            Otherwise, return None.
        """
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

    @classmethod
    def _use_defaults(cls, kwargs):
        for k, v in cls.defaults.items():
            if k not in kwargs or kwargs[k] is None:
                kwargs[k] = v


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

    #: Default values.
    #  Use these values if no value is given to the
    #: corresponding keyword in the constructor.
    #: For example::
    #:
    #:   Mermaid.defaults.update(dict(stream_labels=True, stream_values=True))
    #:
    #: - direction (str): Diagram direction
    #: - stream_labels (bool): If true, add stream labels
    #: - stream_values (bool): If True, show stream values
    #: - unit_values (bool): If True, show unit values
    #: - unit_class (bool): If True, include name of unit's class in its name
    #: - indent (str): Indent (spaces) in output text

    defaults = {
        "direction": "LR",
        "stream_labels": False,
        "stream_values": False,
        "unit_values": False,
        "unit_class": False,
        "indent": "    ",
    }

    def __init__(self, connectivity: Connectivity, **kwargs):
        """Constructor. See class `defaults` for default values.

        Args:
            connectivity (Connectivity): Model connectivity
            kwargs (dict): See `Mermaid.defaults` for keywords

        Raises:
            ValueError: Invalid `direction` argument.
        """
        super().__init__(connectivity, **kwargs)
        self._use_defaults(kwargs)
        self.indent = kwargs["indent"]
        self._stream_labels = kwargs["stream_labels"]
        self._stream_values = kwargs["stream_values"]
        self._unit_values = kwargs["unit_values"]
        self._unit_class = kwargs["unit_class"]
        self._direction = self._parse_direction(kwargs["direction"])
        if self._stream_values:
            self._streams_with_values = set()

    def write(self, output_file: Union[str, TextIO, None]) -> Optional[str]:
        """Write Mermaid text description."""
        f = self._get_output_stream(output_file)
        self._body(f)
        return self._write_return(f)

    def _body(self, outfile):
        i = self.indent
        mm_dir = "LR" if self._direction == Direction.RIGHT else "TD"
        outfile.write(f"flowchart {mm_dir}\n")
        # Stream values
        if self._stream_values:
            outfile.write(
                f"{i}classDef streamval fill:#fff,stroke:#666,stroke-width:1px,font-size:80%;\n"
            )
            for name, values in self._conn.stream_values.items():
                if values:
                    abbr = self._conn.streams[name]
                    sv_name = f"{abbr}_V"
                    sv_text = self._format_stream_values(values)
                    if self._stream_labels:
                        sv_text = f"{name}\n" + sv_text
                    outfile.write(f'{i}{sv_name}("{sv_text}")\n')
                    self._streams_with_values.add(sv_name)
            all_streams = ",".join(self._streams_with_values)
            outfile.write(f"{i}class {all_streams} streamval;\n")
        # Get connections and which streams to show
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

    @staticmethod
    def _format_stream_values(data):
        text_list = []
        for k, v in data.items():
            text_list.append(f"{k} = {v}")
        return "\n".join(text_list)

    def _get_mermaid_units(self):
        for name, abbr in self._conn.units.items():
            qname = self._quote_name(name)
            if self._unit_class:
                klass = self._conn.get_unit_class(name)
                display_name = f"{qname}::{klass}"
            else:
                display_name = qname
            if self._unit_values:
                values = self._conn.unit_values[name]
                if values:
                    values_str = "\n".join((f"{k}={v}" for k, v in values.items()))
                    display_name = f"{display_name}\n{values_str}"
            yield f"{abbr}[{display_name}]"

    def _get_mermaid_streams(self):
        """Get (possibly cleaned up) stream abbr. and names"""
        for name, abbr in self._conn.streams.items():
            yield abbr, f"{abbr}([{self._quote_name(name)}])"

    def _quote_name(self, name):
        return '"' + name + '"'

    def _get_connections(self):
        connections = []
        show_streams = set()

        stream_name_map = {v: k for k, v in self._conn.streams.items()}
        for stream_abbr, values in self._conn.connections.items():
            stream_name = stream_name_map[stream_abbr]
            src, tgt = values[0], values[1]
            if src is not None and tgt is not None:
                if self._stream_values:
                    sv_name = f"{stream_abbr}_V"
                    if sv_name in self._streams_with_values:
                        connections.append(f"{src} --- {sv_name}")
                        connections.append(f"{sv_name} --> {tgt}")
                    else:
                        connections.append(f"{src} --> {tgt}")
                elif self._stream_labels:
                    label = self._clean_stream_label(stream_name)
                    connections.append(f"{src} -- {label} -->{tgt}")
                else:
                    connections.append(f"{src} --> {tgt}")
            elif src is not None:
                connections.append(f"{src} --> {stream_abbr}")
                show_streams.add(stream_abbr)
            elif tgt is not None:
                connections.append(f"{stream_abbr} --> {tgt}")
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

    #: Default values.
    #  Use these values if no value is given to the
    #: corresponding keyword in the constructor.
    #: For example::
    #:
    #:   D2.defaults.update(dict(stream_labels=True, stream_values=True))
    #:
    #: - direction (str): Diagram direction
    #: - stream_labels (bool): If true, add stream labels
    #: - stream_values (bool): If True, show stream values
    #: - unit_values (bool): If True, show unit values
    #: - unit_class (bool): If True, include name of unit's class in its name
    #: - indent (str): Indent (spaces) in output text

    defaults = {
        "direction": "LR",
        "stream_labels": False,
        "stream_values": False,
        "unit_values": False,
        "unit_class": False,
    }

    def __init__(
        self,
        connectivity: Connectivity,
        **kwargs,
    ):
        """Constructor.

        Args:
            connectivity (Connectivity): Model connectivity
            kwargs (dict): See `D2.defaults` for keywords

        Raises:
            ValueError: Invalid direction.
        """
        super().__init__(connectivity, **kwargs)
        self._use_defaults(kwargs)
        self._stream_labels = kwargs["stream_labels"]
        self._stream_values = kwargs["stream_values"]
        self._unit_values = kwargs["unit_values"]
        self._unit_class = kwargs["unit_class"]
        self._direction = self._parse_direction(kwargs["direction"])

    STREAM_VALUE_CLASS = (
        "{style: {font-color: '#666'; stroke: '#ccc'; fill: 'white'; border-radius: 8}}"
    )

    def write(self, output_file: Union[str, TextIO, None]) -> Optional[str]:
        """Write D2 text description."""
        unit_icon = UnitIcon(IdaesPaths.icons())
        feed_num, sink_num = 1, 1
        f = self._get_output_stream(output_file)
        d2_dir = "right" if self._direction == Direction.RIGHT else "down"
        f.write(f"direction: {d2_dir}\n")
        if self._stream_values or self._unit_values:
            f.write("classes:{\n")
            if self._stream_values:
                f.write(f"  stream_value: {self.STREAM_VALUE_CLASS}\n")
            f.write("}\n")
        for unit_name, unit_abbr in self._conn.units.items():
            unit_type = self._conn.get_unit_class(unit_name)
            if self._unit_class:
                unit_str = f"{unit_name}::{unit_type}"
            else:
                unit_str = unit_name
            if self._unit_values:
                values_to_show = self._get_unit_values(unit_name)
                if values_to_show is None:
                    unit_display_str = unit_str
                else:
                    unit_display_str = '"' + unit_str + "\\n" + values_to_show + '"'
            else:
                unit_display_str = unit_str
            image_file = None if unit_type is None else unit_icon.get_icon(unit_type)
            if image_file is None:
                f.write(f"{unit_abbr}: {unit_display_str}\n")
            else:
                f.write(
                    f"{unit_abbr}: {unit_display_str} {{\n"
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
                if self._stream_labels:
                    f.write(f": {stream_name}")
                f.write("\n")
                feed_num += 1
            elif conns[1] is None:
                f.write(f"s{sink_num}: Sink {sink_num}\n")
                f.write(f"f{sink_num} -> {conns[1]}")
                if self._stream_labels:
                    f.write(f"{sink_num}: {stream_name}")
                f.write("\n")
                sink_num += 1
            else:
                if self._stream_labels and not self._stream_values:
                    f.write(f"{conns[0]} -> {conns[1]}: {stream_name}")
                elif self._stream_values:
                    v = self._conn.stream_values[stream_name]
                    if v:
                        values_text = self._format_values(v)
                        if self._stream_labels:
                            values_text = f"{stream_name}\\n" + values_text
                        stream_node = f"S_{stream_name}"
                        f.write(f'{stream_node}: "{values_text}"\n')
                        f.write(f"{stream_node}.class: stream_value\n")
                        f.write(f"{conns[0]} -> {stream_node} -> {conns[1]}\n")
                    elif self._stream_labels:
                        f.write(f"{conns[0]} -> {conns[1]}: {stream_name}")
                    else:
                        f.write(f"{conns[0]} -> {conns[1]}")
                else:
                    f.write(f"{conns[0]} -> {conns[1]}")
                f.write("\n")

        return self._write_return(f)

    @staticmethod
    def _format_values(data):
        text_list = []
        for k, v in data.items():
            text_list.append(f"{k} = {v}")
        return "\\n".join(text_list)

    def _get_unit_values(self, unit_name):
        values = self._conn.unit_values[unit_name]
        if not values:
            return None
        return "\\n".join((f"{k} = {v}" for k, v in values.items()))
