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
Tests for `util` module.
"""
from pathlib import Path

import pytest
import pandas as pd

from idaes_connectivity.util import IdaesPaths, UnitIcon, get_stream_display_values


@pytest.mark.unit
def test_idaespaths():
    IdaesPaths.reset_home()
    home1 = IdaesPaths.home()
    icons1 = IdaesPaths.icons()
    with pytest.raises(ValueError):
        IdaesPaths.set_home(Path("/a"))
    IdaesPaths.set_home(Path("~").expanduser())
    home2 = IdaesPaths.home()
    assert home1 != home2
    icons2 = IdaesPaths.icons()
    assert icons1 != icons2
    IdaesPaths.reset_home()
    assert IdaesPaths.home() == home1


@pytest.mark.unit
def test_uniticon():
    IdaesPaths.reset_home()

    ui = UnitIcon()
    sfeed = ui.get_icon("ScalarFeed")
    expect_sfeed = (IdaesPaths.icons() / "feed.svg").absolute()
    assert sfeed == expect_sfeed

    myhome = Path("~").expanduser()
    ui = UnitIcon(icon_dir=myhome / "iconsss")
    sfeed = ui.get_icon("ScalarFeed")
    expect_sfeed = myhome / "iconsss" / "feed.svg"
    assert sfeed == expect_sfeed


@pytest.fixture
def stream_table():
    return pd.DataFrame(
        {
            "Units": ["K", "Pa", "m"],
            "s1": [1.2, 1.3, "-"],
            "s2": [1.4, "-", 1.5],
        },
        index=["metric1", "metric2", "metric3"],
    )


@pytest.mark.unit
def test_get_stream_display_values(stream_table):
    def gsdv(m):
        return get_stream_display_values(stream_table, m)

    # empty mapping
    assert gsdv({}) == {}

    # metric1
    r = gsdv({"metric1": ("K", ".1f")})
    assert r == {"s1": {"metric1": "1.2 K"}, "s2": {"metric1": "1.4 K"}}

    # unknown metric => KeyError
    with pytest.raises(KeyError):
        gsdv({"foo": {"x", ".1f"}})

    # regex + use units from table
    r = gsdv({r"~metric[23]": ".1f"})
    assert r == {"s1": {"metric2": "1.3 Pa"}, "s2": {"metric3": "1.5 m"}}
