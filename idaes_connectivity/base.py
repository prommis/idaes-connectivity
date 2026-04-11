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
import shutil
import subprocess
from tempfile import NamedTemporaryFile
import time
from typing import TextIO, Tuple, Union, Optional, List, Dict, Any
import warnings

from PIL import Image as im
import base64
import io, requests

# third-party
from IPython.display import Markdown

try:
    import pyomo
    from pyomo.network import Arc
except ImportError as err:
    pyomo = None
    warnings.warn(f"Could not import pyomo: {err}")

# package
from idaes_connectivity.util import IdaesPaths, UnitIcon, FileServer
from idaes_connectivity.const import Direction, ComponentNames, DEFAULT_SERVER_ROOT

__author__ = "Dan Gunter (LBNL)"

# Logging
_log = logging.getLogger(__name__)


class ModelLoadError(Exception):
    def __init__(self, err):
        super().__init__(f"Could not load model: {err}")


class DataLoadError(Exception):
    def __init__(self, path, err):
        super().__init__(f"Could not load from file '{path}': {err}")


class MermaidServerError(Exception):
    def __init__(self, err):
        super().__init__(f"Error contacting Mermaid server to render diagram: {err}")


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

    #: Mermaid server URL for rendering diagrams over HTTP
    default_mermaid_server_url = "https://mermaid.ink/img/"

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
                self._create_from_model(flowsheet)
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

    # TODO: Add support for D2 display as well and maker it an option

    def _get_mermaid_image(self, mermaid_server_url: str, timeout: float = 10.0):
        """Get image for Mermaid diagram.

        Args:
            mermaid_server_url: URL of the Mermaid server to use for rendering
            timeout: Timeout in seconds for contacting the server

        Raises:
            MermaidServerError: if there is a problem contacting `mermaid_server_url` to render the image
        """
        str_mm = Mermaid(self).write(None)
        graphbytes = str_mm.encode("utf8")
        base64_bytes = base64.urlsafe_b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")
        try:
            img = im.open(
                io.BytesIO(
                    requests.get(
                        mermaid_server_url + base64_string, timeout=timeout
                    ).content
                )
            )
        except Exception as e:
            _log.error(f"Error displaying Mermaid diagram: {e}")
            raise MermaidServerError(e)
        return img

    def save(
        self,
        save_file=None,
        mermaid_server_url=default_mermaid_server_url,
    ):
        """Save the Mermaid diagram

        Args:
            save_name: Optional path to save the diagram as a text file
            mermaid_server_url: URL of the Mermaid server to use for rendering

        """
        try:
            img = self._get_mermaid_image(mermaid_server_url)
        except MermaidServerError as err:
            _log.error(f"save() failed because of a mermaid server error: {err}")
            raise

        img.save(save_file)

    def show(
        self,
        mermaid_server_url=default_mermaid_server_url,
    ):
        """Display the Mermaid diagram
        Args:
            mermaid_server_url: URL of the Mermaid server to use for rendering
        """
        try:
            img = self._get_mermaid_image(mermaid_server_url)
        except MermaidServerError as err:
            _log.error(f"show() failed because of a mermaid server error: {err}")
            raise

        img.show()

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
            _log.debug(f"_build_connections: row {i}: {row}")
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

    def _create_from_model(self, fs):
        _log.info("begin:_create_from_model")

        units_ord, units_idx = {}, 0
        units, streams = [], []
        streams_ord, streams_idx = {}, 0
        rows = []
        arcs = fs.component_objects(Arc, descend_into=self._arc_descend)

        sorted_arcs = sorted(arcs, key=lambda arc: arc.name)
        if _log.isEnabledFor(logging.DEBUG):
            _log.debug(f"arc short names: {[a.getname() for a in sorted_arcs]}")
            _log.debug(f"arc full names : {[a.name for a in sorted_arcs]}")
        # create `self._name_map`: arc names to shortened names
        # with common prefixes stripped
        self._build_name_map(sorted_arcs)

        # Main loop, each arc builds one row in `rows`
        for comp in sorted_arcs:
            # Create list of arcs (streams), whether indexed or no
            if comp.is_indexed:
                stream_set = list(comp.values())
            else:
                stream_set = [comp]
            # Loop through list of streams
            for comp_stream in stream_set:
                stream_name = comp_stream.name
                src, dst = (
                    comp_stream.source.parent_block(),
                    comp_stream.dest.parent_block(),
                )
                src_name, dst_name = self._model_unit_name(src), self._model_unit_name(
                    dst
                )
                # record the class of the source and dest
                self._unit_classes[src_name] = self._model_unit_class(src)
                self._unit_classes[dst_name] = self._model_unit_class(dst)
                # add the stream to the rows
                streams_idx, units_idx = self._add_model_stream(
                    streams_idx,
                    units_idx,
                    stream_name,
                    src_name,
                    dst_name,
                    streams,
                    streams_ord,
                    units,
                    units_ord,
                    rows,
                )

        # ["Arcs", "<Unit-name1>", "<Unit-name2>", ...]
        self._header = ["Arcs"] + units
        # ["<stream name>", 0|1|-1, 0|1|-1, ...]
        self._rows = [[streams[i]] + r for i, r in enumerate(rows)]

        _log.info("end:_create_from_model")

    @staticmethod
    def _add_model_stream(
        streams_idx,  # current num streams, modified and returned
        units_idx,  # current num units, modified and returned
        stream_name,  # name of stream being added
        src_name,  # source unit name
        dst_name,  # destination unit name
        streams,  # current list of streams
        streams_ord,  # list of streams, ordered
        units,  # current list of units
        units_ord,  # list of units, ordered
        rows,  # resulting rows of connectivity info
    ) -> Tuple[int, int]:
        """Encapsulate logic of adding a stream from the model."""
        dbg = _log.isEnabledFor(logging.DEBUG)
        stream_row = -1
        # get row for stream
        try:
            idx = streams_ord[stream_name]
        except KeyError:
            # create new row
            streams.append(stream_name)
            idx = streams_ord[stream_name] = streams_idx
            streams_idx += 1
            if len(rows) == 0:  # first entry in matrix
                rows.append([])
            else:
                rows.append([0] * len(rows[0]))
        stream_row = idx

        # build rows
        endpoints = [None, None]
        for ep, unit_name in enumerate([src_name, dst_name]):
            try:
                idx = units_ord[unit_name]
                if dbg:
                    _log.debug(f"add_streams {unit_name}[{ep}]={idx}")
            except KeyError:  # create new column
                if dbg:
                    _log.debug(f"add_streams {unit_name}[{ep}]= {units_idx}/New column")
                units.append(unit_name)
                idx = units_ord[unit_name] = units_idx
                units_idx += 1
                for row in rows:
                    row.append(0)
            endpoints[ep] = idx
        if dbg:
            _log.debug(f"add streams: row[{stream_row}][{endpoints[0]}] => -1")
        rows[stream_row][endpoints[0]] = -1
        if dbg:
            _log.debug(f"add streams: row[{stream_row}][{endpoints[1]}] => 1")
        rows[stream_row][endpoints[1]] = 1

        return streams_idx, units_idx

    def _build_name_map(self, arcs):
        """Mapping to strip off any prefixes common to all unit names.
        This mapping is used by :func:`_model_unit_name`.
        """
        self._name_map = None
        if len(arcs) < 2:
            return
        # split names by "." into tuples
        name_tuples = set()
        for comp in arcs:
            if comp.is_indexed():
                for comp_item in comp.values():
                    for p in comp_item.source, comp_item.dest:
                        parent_name = p.parent_block().name
                        nm = tuple(parent_name.split("."))
                        name_tuples.add(nm)
            else:
                for p in comp.source, comp.dest:
                    nm = p.parent_block().name.split(".")
                    name_tuples.add(tuple(nm))

        # abort if empty!
        if not name_tuples:
            _log.warning("No arcs found in model")
            self._name_map = {}
            return

        # Find and strip common prefixes
        prefix_len = self._find_common_prefix_len(name_tuples)
        # Strip common prefixes (if any)
        if prefix_len > 0:
            self._name_map = {
                ".".join(k): ".".join(k[prefix_len:]) for k in name_tuples
            }

    @staticmethod
    def _find_common_prefix_len(tuple_list) -> int:
        """Get common prefix length (to strip) from a list of tuples."""
        if len(tuple_list) < 1:
            return 0  # for len=1, we still don't want to strip it
        shortest_tuple = min(map(len, tuple_list))
        n = 1
        while n <= shortest_tuple:
            # continue only if the set of prefixes is length 1,
            # which means they are all the same
            if len({tuple(nm[:n]) for nm in tuple_list}) > 1:
                return n - 1
            n += 1
        return shortest_tuple

    def _model_unit_name(self, block):
        """Get the unit name for a Pyomo/IDAES block."""
        name = block.name

        if self._name_map is None:
            return name

        return self._name_map.get(name, name)

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

    def __init__(self, connectivity: Connectivity | Any, **kwargs):
        """Constructor.

        Arguments:
            connectivity: Either a Connectivity instance or any valid value
                          for `input_*` arguments that could be passed to
                          create a Connectivity instance.

        Raises:
            ValueError: Unable to construct Connectivity instance from provided arg
        """
        if isinstance(connectivity, Connectivity):
            self._conn = connectivity
        else:
            self._conn = self._connectivity_factory(connectivity)

    def _connectivity_factory(self, arg) -> Connectivity:
        kwargs = {}
        # a string can be many things:
        # path, CSV, module name
        if isinstance(arg, Connectivity):
            return arg
        if isinstance(arg, str):
            try:
                # is this a path?
                path = Path(arg)
                if not path.exists():
                    raise ValueError()
                kwargs["input_file"] = path
            except ValueError:
                # not a path. is it a CSV blob?
                csv_data = arg.split("\n")
                if len(csv_data) > 1:
                    hdr = csv_data[0].split(",")
                    if len(hdr) > 1:
                        kwargs["input_data"] = arg
                else:
                    # not CSV. is it a module name?
                    kwargs["input_module"] = arg
        # things that are specifically file paths
        elif isinstance(arg, TextIO) or isinstance(arg, Path):
            kwargs["input_file"] = arg
        # otherwise it is probably a model
        elif hasattr(arg, "component_objects"):
            kwargs["input_model"] = arg

        if not kwargs:  # nothing matched!
            raise ValueError(
                "Argument is not an input file, Pyomo/IDAES model, "
                "module name, or CSV text data"
            )

        return Connectivity(**kwargs)

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

    # For theming the output
    # See: https://mermaid.js.org/config/theming.html#theme-variables
    theme_variables = {"primaryColor": "#ffffff", "background": "#f4f4f4"}

    def __init__(
        self,
        connectivity: Connectivity,
        dark_mode: bool = False,
        component_images=False,
        image_css: str | None = None,
        server_root_dir: Optional[Path] = None,
        server_img_dir: Optional[Path] = None,
        server_var_dir: Optional[Path] = None,
        **kwargs,
    ):
        """Constructor. See class `defaults` for default values.

        Args:
            connectivity (Connectivity): Model connectivity
            dark: If true, change styles for dark mode display
            component_images: If true, run a server for images
            image_css: Use provided string as CSS class for images, otherwise create one internally
            server_root_dir: Server root for images
            server_img_dir: Server image subdir, should be below server_root_dir
            server_var_dir: Server var (bookkeeping) subdir, should be below server_var_dir
            kwargs: Keyword arguments passed through to parent's constructor

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
        self._img_css = image_css
        self._dark_mode = dark_mode
        # invert selected theme variables in dark mode
        if dark_mode:
            for key in "primaryColor", "background":
                self.theme_variables[key] = self._invert_color(
                    self.theme_variables[key]
                )

        # If component images are desired, start image server, etc.
        if component_images:
            self._images = self._start_image_server(
                server_root_dir, server_img_dir, server_var_dir
            )
            if self._images:
                self._comp_names = ComponentNames()
                self._host = self._image_server.HOST
                self._port = self._image_server.port
        else:
            self._images = False

    @staticmethod
    def _invert_color(color):
        if isinstance(color, str):
            color = color.strip()
            if color[0] == "#":
                hex_color = color.lstrip("#")
                if len(hex_color) == 3:
                    r = int(hex_color[0], 16) * 16
                    g = int(hex_color[1], 16) * 16
                    b = int(hex_color[2], 16) * 16
                elif len(hex_color) == 6:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                else:
                    raise ValueError(
                        f"Hexadecimal RGB must be #rgb or #rrggbb: '{color}'"
                    )
        else:
            raise ValueError(f"Invalid color format: {color}")
        return f"#{255 - r:02X}{255 - g:02X}{255 - b:02X}"

    def _start_image_server(self, root_dir, img_dir, var_dir) -> bool:
        started = False
        # set up arguments
        if root_dir is None:
            root_dir = Path(DEFAULT_SERVER_ROOT)
        kwargs = {"root_dir": root_dir}
        if img_dir is not None:
            if img_dir.is_absolute():
                kwargs["file_dir"] = str(img_dir.relative_to(root_dir))
            else:
                kwargs["file_dir"] = str(img_dir)
        if var_dir is not None:
            if var_dir.is_absolute():
                kwargs["var_dir"] = str(var_dir.relative_to(root_dir))
            else:
                kwargs["var_dir"] = str(var_dir)
        # create file server
        self._image_server = FileServer(**kwargs)
        # try to start file server
        try:
            _log.info(
                f"Starting image server (root_dir={root_dir}, image_dir={img_dir}, var_dir={var_dir})"
            )
            self._image_server.start()
            started = True
            self._port = self._image_server.port
            _log.info(
                f"Successfully started image server "
                f"(root_dir={root_dir}, image_dir={img_dir}, var_dir={var_dir})"
            )
        except (FileExistsError, ValueError) as err:
            _log.error(
                f"Could not start image server (root_dir={root_dir}, image_dir={img_dir}, var_dir={var_dir}): {err}"
            )

        return started

    def _repr_markdown_(self):
        """Display using Markdown in a Jupyter Notebook."""
        graph_str = self.write(None)
        return f"```mermaid\n{graph_str}\n```"

    def write(self, output_file: Union[str, TextIO, None]) -> Optional[str]:
        """Write Mermaid text description."""
        f = self._get_output_stream(output_file)
        self._frontmatter(f)
        self._body(f)
        return self._write_return(f)

    def _frontmatter(self, outfile):
        outfile.write("---\n")
        outfile.write("config:\n    theme: 'base'\n    themeVariables:\n")
        i = " " * 8  # indent
        if self._dark_mode:
            outfile.write(f"{i}darkMode: true\n")
        for name, value in self.theme_variables.items():
            outfile.write(f"{i}{name}: '{value}'\n")
        outfile.write("---\n\n")

    def _body(self, outfile):
        i = self.indent
        mm_dir = "LR" if self._direction == Direction.RIGHT else "TD"
        outfile.write(f"flowchart {mm_dir}\n")
        # Stream values
        if self._stream_values:
            outfile.write(
                f"{i}classDef streamValue fill:#fff,stroke:#666,stroke-width:1px,font-size:80%;\n"
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
            outfile.write(f"{i}class {all_streams} streamValue;\n")
        if self._images:  # add imgNode class for styling images
            if self._img_css:
                img_class = self._img_css
            else:
                outfile.write(
                    f"{i}classDef imgNode stroke-width:0,fill:none,background-color:transparent;\n"
                )
                img_class = "imgNode"
        # Get connections and which streams to show
        connections, show_streams = self._get_connections()
        # Units. Handle variations:
        #   1) plain = abbr["name"]
        #   2) image = abbr@{ img: url, ... }
        #   3) key/value = abbr["name"\n key="value:\n...]
        #   4) key/value but no values, like (1)
        for name, abbr in self._conn.units.items():
            node_name, node_class = self._get_node_info(name)
            if self._images and (img_url := self._get_url(node_class)):
                # image. images don't add key=value pairs (yet)
                # note: spaces after/before curly braces are *essential*
                node_str = f'{abbr}:::{img_class}@{{ img: "{img_url}", label: {node_name}, h: 50, constraint: "on" }}'
            else:
                # plain or key/value
                nclass = f"::{node_class}" if self._unit_class else ""
                node_str_base = f"{abbr}{nclass}[{node_name}"
                if self._unit_values:
                    # key/value
                    if values := self._conn.unit_values[name]:
                        # key/value with values
                        values_str = "\n".join((f"{k}={v}" for k, v in values.items()))
                        node_str = f"{node_str_base}\n{values_str}]"
                    else:
                        # key/value without values
                        node_str = node_str_base + "]"
                else:
                    # plain
                    node_str = node_str_base + "]"
            outfile.write(f"{i}{node_str}\n")
        # Streams
        for abbr, s in self._get_mermaid_streams():
            if abbr in show_streams:
                outfile.write(f"{i}{s}\n")
        # Connections
        for s in connections:
            outfile.write(f"{i}{s}\n")

    def _get_url(self, node_class):
        return (  # returns None if filename=None
            filename := self._comp_names.get_filename(
                node_class, dark_mode=self._dark_mode
            )
        ) and f"http://{self._host}:{self._port}/{filename}"

    @staticmethod
    def _format_stream_values(data):
        text_list = []
        for k, v in data.items():
            text_list.append(f"{k} = {v}")
        return "\n".join(text_list)

    def _get_node_info(self, name):
        return self._quote_name(name), self._conn.get_unit_class(name)

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


class MermaidImage(Formatter):
    """Formatter that calls mermaid-cli command line program (mmdc) in order to
    generate the diagram as an aimage file.

    For more information about mermaid-cli, see https://github.com/mermaid-js/mermaid-cli

    Example usage::

        from idaes_connectivity.base import Connectivity, MermaidImage
        # somehow create connectivity object, e.g. from a CSV file
        conn = Connectivity(input_file="idaes_connectivity/tests/example_flowsheet.csv")
        # create an image
        MermaidImage(conn).write("flowsheet_diagram.png")
    """

    def __init__(self, conn: Connectivity, **kwargs):
        """Constructor.

        Args:
            conn: Connectivity to graph
            kwargs: Same as for the `Mermaid` class, except for an additional
                    section for (optional) keywords related to the mmdc program::
                    { "mmdc":
                        "bin": "<path>", # path to the binary
                        "options": ["<opt>", "<opt2>", ..]  # extra CLI opts
                    }
        """
        if "mmdc" in kwargs:
            self._bin = kwargs["mmdc"].get("bin", self.find_mmdc())
            self._opt = kwargs["mmdc"].get("options", [])
            del kwargs["mmdc"]
        else:
            self._bin = self.find_mmdc()
            self._opt = []
        self._formatter = Mermaid(conn, **kwargs)

    def write(self, output_file: Path | str):
        """Write to image file.

        Arguments:
            output_file: Image file name. Extension determines image type, as decided
                         by the mermaid-cli program.
        """
        _log.info(f"Use 'mmdc' to create output in '{output_file}'")
        # write mermaid output to a named temporary file
        tmpfile = NamedTemporaryFile(mode="w")
        self._formatter.write(tmpfile)
        tmpfile.flush()
        if _log.isEnabledFor(logging.DEBUG):
            with open(tmpfile.name, "r") as f:
                buf = f.read()
            _log.debug(f"Contents of temporary file ({tmpfile.name}):\n{buf}")
        time.sleep(1)  # lame, but safer
        # run mmdc on temporary file, writing its image output to user-provided file
        args = [self._bin, "-i", tmpfile.name]
        if not hasattr(output_file, "close"):  # e.g. stdout
            args.extend(["-o", output_file])
        args += self._opt
        _log.info(f"running: {' '.join(args)}")
        try:
            subprocess.check_call(args, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError) as err:
            raise RuntimeError(err)

    @staticmethod
    def find_mmdc() -> str | None:
        """Find CLI program for mermaid-cli (mmdc)."""
        return shutil.which("mmdc")


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
