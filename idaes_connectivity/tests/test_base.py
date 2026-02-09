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
from typing import List

# third-party
import pytest
from PIL import Image, ImageChops
import numpy as np
from pathlib import Path

# package
from idaes_connectivity.base import Connectivity, CSV, Mermaid, D2
from idaes_connectivity.tests import example_flowsheet
from idaes_connectivity.tests.example_flowsheet_data import (
    example_csv,
    example_mermaid,
    example_d2,
)

# avoid warnings about unused imports
_1, _2, _3 = example_csv, example_d2, example_mermaid

# Constants
STREAM_1 = "fs.s01"
UNIT_1 = "M01"


def setup():
    model = example_flowsheet.build()
    conn = Connectivity(input_model=model)
    return model, conn


def list_rstrip(x: List) -> List:
    """Return list (copy) with empty items at end removed"""
    i = len(x) - 1
    while i > -1 and len(x[i]) == 0:
        i -= 1
    return x[: i + 1]


@pytest.mark.unit
def test_example_data(example_csv, example_mermaid, example_d2):
    model, conn = setup()
    # loop over each output format
    for name, text, ref in (
        ("CSV", CSV(conn).write(None), example_csv),
        ("Mermaid", Mermaid(conn).write(None), example_mermaid),
        ("D2", D2(conn).write(None), example_d2),
    ):
        print(f"@ Start {name} {text},{ref}")
        # normalize ws and remove blank lines at end (if any)

        items = list_rstrip([t.rstrip() for t in text.split("\n")])
        assert len(items) == len(ref)
        # compare line by line
        for i, item in enumerate(items):
            # special processing for icon paths (which will differ)
            if "icon:" in item:
                assert "icon:" in ref[i]
            else:
                assert item == ref[i]
        print(f"@ End   {name}")


@pytest.mark.unit
@pytest.mark.parametrize("klass", (Mermaid, D2))
def test_defaults_formatters(klass):
    _, conn = setup()

    klass.defaults["stream_labels"] = True

    # not given (use default)
    fmt = klass(conn)
    assert fmt._stream_labels == True

    # given, but None (use default)
    fmt = klass(conn, stream_labels=None)
    assert fmt._stream_labels == True

    # different value (use value)
    fmt = klass(conn, stream_labels=False)
    assert fmt._stream_labels == False


@pytest.mark.unit
def test_show(tmpdir_factory):
    _, conn = setup()
    fn = tmpdir_factory.mktemp("data").join("img.png")

    # conn.show()
    conn.save(save_file=fn)
    test_data_dir = Path(__file__).parent.absolute() / "test_image.png"

    Image.open(test_data_dir).convert("RGB")
    Image.open(fn).convert("RGB")


@pytest.mark.unit
@pytest.mark.parametrize("klass", (Mermaid, D2))
def test_stream_values_formatter(klass):
    _, conn = setup()
    test_key, test_val = "test_value", 123
    conn.set_stream_value(STREAM_1, test_key, test_val)
    for stream_labels in (True, False):
        found_key = False
        print(f"class={klass.__name__} stream_labels={stream_labels}")
        mmd = klass(conn, stream_values=True, stream_labels=stream_labels)
        for line in mmd.write(None).split("\n"):
            print(line)
            if test_key in line:
                assert str(test_val) in line
                found_key = True
        assert found_key


@pytest.mark.unit
@pytest.mark.parametrize("klass", (Mermaid, D2))
def test_unit_values_formatter(klass):
    _, conn = setup()
    test_key, test_val, test_unit_class = "test_value", 123, "foobar"
    conn.set_unit_value(UNIT_1, test_key, test_val)
    conn.set_unit_class(UNIT_1, test_unit_class)
    for uc_flag in (False, True):
        print(f"class={klass.__name__} unit_class={uc_flag}")
        mmd = klass(conn, unit_values=True, unit_class=uc_flag)
        found_key, found_class = False, False
        for line in mmd.write(None).split("\n"):
            print(line)
            if test_key in line:
                assert str(test_val) in line
                found_key = True
            if test_unit_class in line:
                found_class = True
        assert found_key


@pytest.mark.unit
@pytest.mark.parametrize("klass", (Mermaid, D2))
def test_unit_and_stream_values_formatter(klass):
    _, conn = setup()
    s_test_key, s_test_val = "s_test_value", 123
    conn.set_stream_value(STREAM_1, s_test_key, s_test_val)
    u_test_key, u_test_val, u_test_unit_class = "u_test_value", 123, "foobar"
    conn.set_unit_value(UNIT_1, u_test_key, u_test_val)
    conn.set_unit_class(UNIT_1, u_test_unit_class)
    for stream_labels in (True, False):
        for uc_flag in (False, True):
            s_found_key, u_found_key, u_found_class = 0, 0, 0
            print(
                f"class={klass.__name__} stream_labels={stream_labels} unit_class={uc_flag}"
            )
            mmd = klass(
                conn,
                stream_values=True,
                unit_values=True,
                stream_labels=stream_labels,
                unit_class=uc_flag,
            )
            for line in mmd.write(None).split("\n"):
                print(line)
                if s_test_key in line:
                    assert str(s_test_val) in line
                    s_found_key += 1
                if u_test_key in line:
                    assert str(u_test_val) in line
                    # print(f"found unit key={u_test_key}={u_test_val} in '{line}'")
                    u_found_key += 1
                if "::" + u_test_unit_class in line:
                    u_found_class += 1

            assert s_found_key == 1
            assert u_found_key == 1
            assert u_found_class == (1 if uc_flag else 0)
