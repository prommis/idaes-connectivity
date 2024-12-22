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
import pytest


IDAES_MARKERS = {
    "build": "Test of model build methods",
    "unit": "Quick tests that do not require a solver, must run in < 2 s",
    "component": "Quick tests that may require a solver",
    "integration": "Long duration tests",
    "solver": "Test requires a solver",
}


def pytest_configure(config: pytest.Config):
    for spec, descr in IDAES_MARKERS.items():
        config.addinivalue_line("markers", f"{spec}: {descr}")
