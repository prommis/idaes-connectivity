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
import os
from pathlib import Path
import psutil
from re import compile, Pattern
import socketserver
import time
from typing import Dict, Iterable, Optional, Tuple, Union

# third-party
from pandas import DataFrame

_log = logging.getLogger(__name__)


class IdaesPaths:
    """IDAES paths, relative to a home directory."""

    _idaes_home = Path("~/.idaes").expanduser()

    @classmethod
    def set_home(cls, path: Path) -> Path:
        cls._idaes_home = path
        return cls._home()

    @classmethod
    def reset_home(cls):
        cls._idaes_home = Path("~/.idaes").expanduser()

    @classmethod
    def home(cls):
        return cls._home()

    @classmethod
    def _home(cls):
        if not cls._idaes_home.exists():
            raise ValueError(f"IDAES  directory '{cls._idaes_home}' not found")
        if not cls._idaes_home.is_dir():
            raise ValueError(f"IDAES path '{cls._idaes_home}' is not a directory")
        return cls._idaes_home

    @classmethod
    def icons(cls, group: str = None):
        """Path to the directory of SVG icons

        Args:
          group: Currently ignored, but in the future can be used to retrieve different groups of icons.
        """
        return cls._home() / "icon_shapes"


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
        if icon_dir is None:
            icon_dir = IdaesPaths.icons()
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

    # build display vales map
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


class FileServer:
    """Serve files from a directory over HTTP.

    This is used to server Mermaid images in a local installation,
    since Mermaid will not load them from a local file.
    """

    #: Server host
    HOST = "localhost"

    #: Base server port
    PORT = 8800

    def __init__(self, run_dir: str | Path = None):
        # logging
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s"))
        self._log = logging.Logger("idaes_connectivity-FileServer")
        self._log.addHandler(sh)
        self._log.setLevel(logging.INFO)
        sh.setLevel(logging.INFO)
        # check and set run directory
        if run_dir is None:
            self._run_dir = Path.home() / ".idaes"
        else:
            self._run_dir = Path(run_dir)
        if not self._run_dir.exists():
            raise FileExistsError(
                f"Directory to store server state does not exist: {self._run_dir}"
            )
        self._port = -1

    @property
    def port(self):
        return self._port

    def start(self, file_dir: str | Path, client_key: str = "default"):
        """Run a simple HTTP server that serves files from `file_dir`.

        By choosing different values for `client_key` you can run different servers (to different dirs)
        on different ports. Put another way, there is one server running per value of `client_key`.
        """
        # check and set directory for files served
        file_dir = Path(file_dir)
        if not file_dir.exists():
            raise FileExistsError(
                f"Directory from which to serve files does not exist: {file_dir}"
            )

        pid_file = self._run_dir / f"idaes_connectivity_image_server-{client_key}.pid"
        port_file = self._run_dir / f"idaes_connectivity_image_server-{client_key}.port"

        if pid_file.exists():
            # see if some process is really running at this PID
            with open(pid_file, "r") as f:
                pid_str = f.readline().strip()
            try:
                pid = int(pid_str)
            except ValueError:
                raise ValueError(
                    f"Cannot parse PID from first line of {pid_file}: '{pid_str}'"
                )
            pid_running = psutil.pid_exists(pid)
            # if running, stop
            if pid_running:
                self._log.info(f"Server is already running PID={pid}")
                self._port = self._server_port(port_file)
                return
            # otherwise, we are going to start a new server
            else:
                self._log.warning(f"Server has PID file, but is not running PID={pid}")
        else:
            # no server, start a new one
            self._log.info("No existing server found")
        # start new server, in a new process
        host = self.HOST
        server_log = self._run_dir / f"idaes_connectivity_image_server-{client_key}.log"
        if pid := os.fork():
            # parent, write PID
            with open(pid_file, "w") as f:
                f.write(f"{pid}\n")
            self._log.info(f"Started server PID={pid}. Log file={server_log}")
            self._port = self._server_port(port_file)
            # done with parent process
        else:
            log = logging.getLogger("idaes_connectivity.image_server")
            handler = logging.FileHandler(server_log)
            handler.setLevel(logging.INFO)
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
            )
            log.addHandler(handler)
            log.setLevel(logging.INFO)

            log.info("Starting server")
            Handler = SimpleHTTPRequestHandler
            os.chdir(file_dir)  # serve from this directory
            port, ran_server = self.PORT, False
            while not ran_server and port < self.PORT + 32:
                try:
                    with socketserver.TCPServer((host, port), Handler) as httpd:
                        ran_server = True
                        with open(port_file, "w") as f:
                            f.write(f"{port}\n")
                        log.info(f"Serving from dir {file_dir} at {host}:{port}")
                        try:
                            httpd.serve_forever()
                        except Exception as err:
                            log.info(f"Server stopped with error: {err}")
                except OSError:
                    # assume port is used
                    _log.warning(f"Port {port} in use, trying {port + 1}")
                    port += 1
            if not ran_server:
                _log.error(
                    f"Could not find open port between {self.PORT} and {port - 1}"
                )
            # done with child process

    def _server_port(self, port_file) -> int:
        # read port from file
        port_value, tries = -1, 0
        while port_value < 0 and tries < 5:
            try:
                with open(port_file, "r") as f:
                    port_str = f.readline().strip()
                try:
                    port_value = int(port_str)
                except ValueError:
                    raise RuntimeError(
                        f"Unexpected value for port in {port_file}: {port_str}"
                    )
            except FileExistsError:
                tries += 1
                _log.warning(f"Waiting for port file to exist ({tries})")
            # wait a bit
            time.sleep(1)

        if port_value < 0:
            raise RuntimeError(f"Could not read server port from {port_file}")
        return port_value

    def kill_all(self):
        """Kill all image servers found in the run directory."""
        for filename in self._run_dir.glob("idaes_connectivity_image_server-*.pid"):
            pid_file = self._run_dir / filename
            with open(pid_file, "r") as f:
                pid_str = f.readline().strip()
            try:
                pid = int(pid_str)
            except ValueError:
                raise ValueError(
                    f"Cannot parse PID from first line of {pid_file}: '{pid_str}'"
                )
            self._log.info(f"Found server PID={pid} in file {pid_file}")
            pid_running = psutil.pid_exists(pid)
            if pid_running:
                self._log.info(f"Killing server PID={pid}")
                try:
                    os.kill(pid, 9)
                except OSError as err:
                    self._log.error(f"Could not kill PID={pid}: {err}")
                self._log.info(f"Deleting PID file {pid_file}")
                try:
                    os.unlink(pid_file)
                except OSError as err:
                    self._log.error(f"Could not delete PID file: {err}")
            else:
                self._log.warning("Server at PID={pid} not running")


# crude test framework for the image_server functions

if __name__ == "__main__":
    import sys
    from idaes_connectivity import const

    arg = sys.argv[-1]

    server = FileServer()

    if arg == "kill":
        server.kill_all()
    else:
        port = server.start(arg)
        img = const.ImageNames(arg)
        unit = "compressor"
        url = img.get_url(unit, port)
        print(f"URL for {unit} = {url}")
