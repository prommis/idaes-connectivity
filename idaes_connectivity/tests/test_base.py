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
import pytest

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


@pytest.mark.unit
def test_example_data(example_csv, example_mermaid, example_d2):
    model = example_flowsheet.build()
    conn = Connectivity(input_model=model)
    # loop over each output format
    for text, ref in (
        (CSV(conn).write(None), example_csv),
        (Mermaid(conn).write(None), example_mermaid),
        (D2(conn).write(None), example_d2),
    ):
        # normalize ws and remove blank lines at end, if any
        items = [t.rstrip() for t in text.split("\n")]
        while items[-1] == "":
            items = items[:-1]
        # compare line by line
        for i, item in enumerate(items):
            assert item == ref[i]
