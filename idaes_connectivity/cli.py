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
Command-line program
"""

import argparse
from importlib.resources import files as imp_files
import logging
from pathlib import Path
import re
import sys

# package
import idaes_connectivity.base as ic
from idaes_connectivity.const import OutputFormats, CONSOLE, DEFAULT_IMAGE_DIR
from idaes_connectivity.version import VERSION
from idaes_connectivity.util import FileServer


__author__ = "Dan Gunter (LBNL)"


SCRIPT_NAME = "idaes-conn"
_log = logging.getLogger(SCRIPT_NAME)


class MermaidHtml(ic.Formatter):
    def __init__(self, conn, **mmd_opt):
        self._mmd = ic.Mermaid(conn, **mmd_opt)

    def write(self, output_file):
        """Write MermaidJS HTML to output file.

        Args:
            output_file (str or file-like): Output file path or file-like object
        """
        f = self._get_output_stream(output_file)
        self._write_html(f)

    def _write_html(self, f):
        """Write MermaidJS HTML to file-like object.

        Args:
            f (file-like): Output file-like object
        """
        if _log.isEnabledFor(logging.DEBUG):
            filename = f.name if hasattr(f, "name") else str(f)
            _log.debug(f"_begin_ write MermaidJS HTML to '{filename}'")
        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n<head>\n")
        f.write(
            "<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>\n"
        )
        f.write("</head>\n<body>\n")
        f.write("<div class='mermaid'>\n")
        f.write(self._mmd.write(None))
        f.write("\n</div>\n")
        f.write("</body>\n</html>\n")
        if _log.isEnabledFor(logging.DEBUG):
            _log.debug(f"_end_ write MermaidJS HTML to '{filename}'")


def infer_output_file(ifile: str, to_, input_file=None):
    to_fmt = OutputFormats(to_)  # arg checked already
    ext = {
        OutputFormats.MERMAID: "mmd",
        OutputFormats.CSV: "csv",
        OutputFormats.D2: "d2",
    }[to_fmt]
    i = ifile.rfind(".")
    if i > 0:
        filename = ifile[:i] + "." + ext
    else:
        filename = ifile + +"." + ext
    _log.info(f"No output file specified, using '{filename}'")
    return filename


def csv_main(args) -> int:
    """CLI function for creating a graph from connectivity matrix specifying units and streams.

    Args:
        args: Parsed args from ArgumentParser

    Returns:
        int: Code for sys.exit()
    """
    _log.info(f"_begin_ create from matrix. args={args}")

    if args.ofile is None:
        args.ofile = infer_output_file(args.source, args.to)
        print(f"Output in: {args.ofile}")
    elif args.ofile == CONSOLE:
        args.ofile = sys.stdout

    fmt_opt = {"stream_labels": args.labels, "direction": args.direction}

    try:
        conn = ic.Connectivity(input_file=args.source)
        formatter = get_formatter(conn, args.to)
        formatter.write(args.ofile)
    except (RuntimeError, ic.DataLoadError) as err:
        _log.info("_end_ create from matrix (1)")
        _log.error(f"{err}")
        return 1
    _log.info("_end_ create from matrix")

    return 0


def module_main(args) -> int:
    """CLI function for creating connectivity/graph from a Python model.

    Args:
        args: Parsed args from ArgumentParser

    Returns:
        int: Code for sys.exit()
    """
    _log.info("_begin_ create from Python model")
    options, conn_kw = _code_main(args)
    try:
        conn = ic.Connectivity(input_module=args.source, **conn_kw)
        formatter = get_formatter(conn, args.to, options)
        formatter.write(args.ofile)
    except (RuntimeError, ic.ModelLoadError) as err:
        _log.info("_end_ create from Python model (1)")
        _log.error(f"{err}")
        return 1
    _log.info("_end_ create from Python model")

    return 0


def py_main(args) -> int:
    """CLI function for creating connectivity/graph from a Python module.

    Args:
        args: Parsed args from ArgumentParser
    Returns:
        int: Code for sys.exit()
    """
    _log.info("_begin_ create from Python script")
    options, conn_kw = _code_main(args)
    script_globals = {}
    try:
        with open(args.source, "r") as f:
            exec(f.read(), script_globals)
    except Exception as err:
        _log.info("_end_ create from Python module (1)")
        _log.error("Error executing Python file: %s", str(err))
        return -1
    try:
        model = eval(args.build, script_globals)()
    except Exception as err:
        _log.info("_end_ create from Python module (1)")
        _log.error("Error evaluating Python file: %s", str(err))
        return -1
    try:
        conn = ic.Connectivity(input_model=model, **conn_kw)
        formatter = get_formatter(conn, args.to, options)
        formatter.write(args.ofile)
    except (RuntimeError, ic.ModelLoadError) as err:
        _log.info("_end_ create from Python model (1)")
        _log.error(f"{err}")
        return 1
    _log.info("_end_ create from Python script")

    return 0


def _code_main(args):
    if args.ofile is None or args.ofile == CONSOLE:
        args.ofile = sys.stdout

    options = {"stream_labels": args.labels, "direction": args.direction}
    conn_kw = {}
    if args.fs is not None:
        conn_kw["model_flowsheet_attr"] = args.fs
    if args.build:
        conn_kw["model_build_func"] = args.build
    return options, conn_kw


def get_formatter(conn: object, fmt: str, options=None) -> ic.Formatter:
    options = {} if options is None else options
    fmt = fmt.lower().strip()
    if fmt == OutputFormats.CSV.value:
        clazz = ic.CSV
    elif fmt == OutputFormats.D2.value:
        clazz = ic.D2
    elif fmt == OutputFormats.MERMAID.value:
        clazz = ic.Mermaid
    elif fmt == OutputFormats.HTML.value:
        clazz = MermaidHtml
    else:
        raise ValueError(f"Unrecognized output format: {fmt}")
    return clazz(conn, **options)


USAGE = f"""
This script generates connectivity information from models,
or graphs of the model structure from connectivity information,
or both together -- i.e. graphs of the model structure from the model.

It has two main 'modes': csv and module.

The *csv* mode starts from a connectivity matrix stored in a file, and 
generates input for a graph drawing program that can be
rendered as a simple diagram of the flowsheet. Available graph outputs are:

- mermaid: Produce the graph in Mermaid format (see http://mermaid.js.org/)
- d2: Produce the graph in D2 format (see https://d2lang.com/)

The *module* mode starts from a Python module, calls its 'build()' function to
build a model, then either (a) writes out the connectivity CSV for that model, or
(b) generates graph drawing input as in the csv mode above. The (b) option
is a convenience and is equivalent to generating the CSV file then running again
in 'csv' mode with that file as input, which will be shown below.

You can explicitly indicate the mode with the --type/-t argument, though the
program will try to infer it as well (anything ending in ".csv" will be assumed to
be a CSV file, for example).

Example command-lines (showing the two modes):

    # Generate the connectivity matrix in uky_conn.csv
    {SCRIPT_NAME} prommis.uky.uky_flowsheet -O uky_conn.csv --to csv

    # Print the MermaidJS diagram to the console instead of to a file
    {SCRIPT_NAME}  uky_conn.csv --to mermaid --output-file "-"

    # Print input for D2 to default file, with streams labeled
    {SCRIPT_NAME} uky_conn.csv --to d2 --labels
    # (console)> Output in: uky_conn.d2

The connectivity matrix format is:

    |Arcs |Unit 1|Unit 2|...|Unit N|
    |-----|------|------|---|------|
    |Arc1 |-1    |0     |...|0     |
    |Arc2 | 0    |1     |...|0     |
    |...  | ...  |...   |...|...   |
    |ArcN | 0    |1     |...|0     |

Where each cell at the intersection of an Arc (row i) and Unit (column j)
is either:
  *  -1 meaning Arc(i) is an outlet of Unit(j), 
  *  1 meaning Arc(i) is an inlet for Unit(j),
  *  0 meaning there is no connection

"""


def _add_log_options(parser: argparse.ArgumentParser) -> None:
    """Add logging-specific options to the argument parser

    Args:
        parser (argparse.ArgumentParser): Parser to modify
    """
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal logging")
    parser.add_argument(
        "-v",
        action="count",
        dest="vb",
        default=0,
        help="Increase verbosity (repeatable)",
    )


def _process_log_options(module_name: str, args: argparse.Namespace) -> logging.Logger:
    log = logging.getLogger(module_name)
    if not log.handlers:
        h = logging.StreamHandler()
        fmt = "[{levelname}] {asctime} ({name}) {message}"
        h.setFormatter(logging.Formatter(fmt, style="{"))
        log.addHandler(h)
        log.propagate = False  # otherwise we get 2 copies
    if args.quiet:
        log.setLevel(logging.CRITICAL)
    else:
        log.setLevel(
            (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
                min(args.vb, 3)
            ]
        )
    return log


import shutil


def _copy_images():
    # use importlib so this works on installed wheels, too
    image_path = imp_files("idaes_connectivity.images")
    n = 0
    dst_dir = DEFAULT_IMAGE_DIR
    suffixes = (".svg", ".png")
    for filename in image_path.iterdir():
        if filename.suffix not in suffixes:
            continue
        src = image_path / filename
        dst = dst_dir / filename.name
        _log.info(f"Copying image from {src} -> {dst}")
        shutil.copy(src, dst)
        n += 1
    _log.info(f"Copied {n} images from {image_path} -> {dst_dir}")
    return n


def main(command_line=None):
    global _log

    p = argparse.ArgumentParser(
        description="Process and/or generate model connectivity information"
    )
    p.add_argument("--usage", action="store_true", help="Print usage with examples")
    # Mermaid-image related
    p.add_argument(
        "--copy-images",
        action="store_true",
        help="Copy images to standard IDAES image directory (for Mermaid)",
    )
    p.add_argument(
        "--kill-image-server",
        action="store_true",
        help="Kill all running image servers (for Mermaid)",
    )
    # set nargs=? so --usage works without any other argument; though
    # this will require more checks later
    p.add_argument(
        "source",
        help="Source file or module",
        metavar="FILE.csv or SCRIPT.py or MODULE",
        nargs="?",
    )
    p.add_argument(
        "--type",
        "-t",
        choices=("csv", "module", "py"),
        help="Build source type: csv=CSV file, module=Python module, py=Python script",
        default=None,
    )
    p.add_argument(
        "-O",
        "--output-file",
        dest="ofile",
        help=f"Output file",
        default=None,
    )
    output_format_choices = sorted((f.value for f in OutputFormats))
    p.add_argument(
        "--to",
        help="Output format for graph (default=csv)",
        choices=output_format_choices,
        default=None,
    )
    p.add_argument(
        "--fs",
        help="Name of flowsheet attribute on model object (default=fs)",
        default="fs",
    )
    p.add_argument(
        "--build",
        help="Name of build function in module (default=build)",
        default="build",
    )
    p.add_argument(
        "--labels", "-L", help="Add stream labels to diagram", action="store_true"
    )
    p.add_argument(
        "--direction",
        "-D",
        help="Direction of diagram",
        choices=("LR", "TD"),
        default="LR",
    )
    p.add_argument(
        "--version", help="Print version number and quit", action="store_true"
    )
    _add_log_options(p)
    if command_line:
        args = p.parse_args(args=command_line)
    else:
        args = p.parse_args()

    # Initialize the logger
    _log = _process_log_options("idaes_connectivity", args)

    # Do something besides the diagram
    if args.version:
        print(VERSION)
        return 0
    if args.usage:
        print(USAGE)
        return 0

    # For Mermaid images
    # See util.FileServer, const.ImageNames, and base.Mermaid
    if args.copy_images:
        n = _copy_images()
        print(f"Copied {n} images")
        return 0
    if args.kill_image_server:
        server = FileServer()
        server.kill_all()
        return 0

    # Generate the mermaid diagram
    if args.source is None:
        print("File or module source is required. Try --usage for details.\n")
        p.print_help()
        return 2
    if args.type is None:
        main_method = None
        if args.source.lower().endswith(".csv"):
            path = Path(args.source)
            if not path.exists():
                print(
                    f"Source looks like a CSV file, but does not exist: "
                    f"{args.source}"
                )
                return 2
            main_method = csv_main
        elif args.source.lower().endswith(".py"):
            path = Path(args.source)
            if not path.exists():
                print(
                    f"Source looks like a Python file, but does not exist: "
                    f"{args.source}"
                )
                return 2
            main_method = py_main
        elif "/" in args.source:
            path = Path(args.source)
            if path.exists():
                _log.warning(
                    "File path given, but suffix is not .csv; assuming CSV mode"
                )
                main_method = csv_main
            else:
                print(f"Source looks like file path, but does not exist: {args.source}")
                return 2
        else:
            m = re.match(
                r"[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*", args.source
            )
            if (m is None) or m.span() != (0, len(args.source)):
                print(
                    f"Source looks like a module name, but is not valid: {args.source}"
                )
                return 2
            main_method = module_main
    else:
        if args.type == "csv":
            if not Path(args.source).exists():
                print(f"Source file path does not exist: {args.source}")
                return 2
            main_method = csv_main
        elif args.type == "py":
            main_method = py_main
        elif args.type == "module":
            main_method = module_main

    if args.to is None:
        if main_method is csv_main:
            args.to = OutputFormats.MERMAID.value
        else:
            args.to = OutputFormats.CSV.value

    return main_method(args)


if __name__ == "__main__":
    sys.exit(main())
