"""
Tests for idaes_connectivity.jupyter module
"""

import pytest
import warnings
from idaes_connectivity.jupyter import display_connectivity
from idaes_connectivity.tests.example_flowsheet import build
from idaes_connectivity.base import Connectivity


def test_display_connectivity():
    # temporarily suppress the warning about 'Nothing to display'
    warnings.filterwarnings(message=r".*display.*", action="ignore")
    assert display_connectivity() is None
    del warnings.filters[0]

    m = (build()).fs
    conn = Connectivity(input_model=m)
    md_obj1 = display_connectivity(conn=conn)
    assert md_obj1 is not None
    md_obj2 = display_connectivity(input_model=m)
    assert md_obj2 is not None
    # TODO: compare contents of 1/2 (should be same)
