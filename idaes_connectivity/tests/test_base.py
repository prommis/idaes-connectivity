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
Tests for `base` module.
"""
# stdlib
from io import StringIO
import re
import pytest

# third-party
try:
    from prommis.uky.uky_flowsheet import build
except:
    build = None
# package
from idaes_connectivity.base import Connectivity, CSV, Mermaid, D2
from idaes_connectivity.const import OutputFormats as OF
from idaes_connectivity.tests import connectivity_data as cdata


@pytest.fixture
def example_conn():
    #
    # Connectivity for this little loop:
    #
    # UnitA -- Stream1 --> UnitB ---+
    #  ^                            |
    #  +----- Stream 2 -----<-------+
    #
    u = {"Unit A": "U-A", "Unit B": "U-B"}
    s = {"Stream 1": "S-1", "Stream 2": "S-2"}
    c = {"S-1": ["U-A", "U-B"], "S-2": ["U-B", "U-A"]}
    conn = Connectivity(units=u, streams=s, connections=c)
    yield conn


@pytest.mark.unit
def test_mermaid(example_conn):
    mmd = Mermaid(example_conn)
    s = mmd.write(None)
    unit_patterns = [r"U-A..?Unit A..?", r"U-B..?Unit B..?"]
    connection_patterns = [r"U-A\s*-->\s*U-B", r"U-B\s*-->\s*U-A"]

    def find_and_remove(text, patterns):
        match_idx, match_item = -1, None
        for j, pat in enumerate(patterns):
            m = re.search(pat, line)
            if m:
                match_idx, match_item = j, pat
                break
        if match_idx >= 0:
            patterns.remove(match_item)
        return match_idx

    for i, line in enumerate(s.split("\n")):
        line = line.strip()
        if not line:
            continue
        if i == 0:
            assert line.startswith("flowchart")
        else:
            patterns = unit_patterns if i < 3 else connection_patterns
            match_idx = find_and_remove(line, patterns)
            assert match_idx >= 0
    # everything was found
    assert len(unit_patterns) == 0
    assert len(connection_patterns) == 0


@pytest.mark.unit
def test_mermaid_options(example_conn):
    kwargs_list = [{}, {"direction": "TD"}, {"direction": "TD", "stream_labels": True}]
    for kwargs in kwargs_list:
        mmd = Mermaid(example_conn, **kwargs)
        _ = mmd.write(None)


@pytest.mark.unit
def test_ordering():
    # is the ordering consistent?
    if build is None:
        return

    model = build()
    conn1 = Connectivity(model_object=model)
    conn2 = Connectivity(model_object=model)

    for attribute in "units", "streams", "connections":
        keys1 = getattr(conn1, attribute).keys()
        keys2 = getattr(conn2, attribute).keys()
        assert list(keys1) == list(keys2)


# this roundabout method avoids pylint warnings
uky_csv_data, uky_mermaid_data = cdata.uky_csv, cdata.uky_mermaid


@pytest.mark.unit
def test_uky_data(uky_csv_data, uky_mermaid_data):
    if build is None:
        return
    model = build()
    for fmt, ref_lines in (("csv", uky_csv_data), ("mermaid", uky_mermaid_data)):
        print(f"Format={fmt}")
        conn = Connectivity(model_object=model)
        data = CSV(conn).write(output_file=None)
        lines = data.split("\n")
        for line, ref_line in zip(lines, ref_lines):
            assert line == ref_line


# With a parametrized fixture, create a set of CSV files
# representing different connectivities.
# First element is expected exception (None if OK)
matrix_list = [
    (None, [[1, 0], [-1, 1], [0, -1]]),  # (S1) -> U1 -(S2)-> U2 -> (S3)
    (None, [[1, 0], [-1, 1], [0, -1, 1]]),  # Bad rowlen / ignored
    (None, [[1, 0], [-1, 1], [0, -1.0]]),  # Float OK
    (ValueError, [[1, 9], [-1, 1], [0, -1]]),  # Bad value
    (ValueError, [[1, "?"], [-1, 1], [0, -1]]),  # Bad value
]


@pytest.fixture(scope="function", params=matrix_list)
def connectivity_info(tmp_path, request):
    exc, m = request.param
    n_streams = len(m)
    n_units = len(m[0])
    csv_file = tmp_path / f"matrix.csv"
    with open(csv_file, "w") as f:
        unit_list = ",".join((f"Unit {n + 1}" for n in range(n_units)))
        f.write(f"Arcs,{unit_list}\n")
        for i in range(n_streams):
            f.write(f"Stream {i + 1},")
            values = ",".join((f"{v}" for v in m[i]))
            f.write(values)
            f.write("\n")
    yield (exc, csv_file)


@pytest.mark.unit
def test_connectivity(connectivity_info):
    expect_exc, csv = connectivity_info
    # csv_dump = "".join(csv.open())
    # print(f"exc={expect_exc}; csv={csv_dump}")
    if expect_exc is None:
        conn = Connectivity(input_file=csv)
    else:
        with pytest.raises(expect_exc):
            conn = Connectivity(input_file=csv)
