#####################################################################################################
# “PrOMMiS” was produced under the DOE Process Optimization and Modeling for Minerals Sustainability
# (“PrOMMiS”) initiative, and is copyright (c) 2023-2024 by the software owners: The Regents of the
# University of California, through Lawrence Berkeley National Laboratory, et al. All rights reserved.
# Please see the files COPYRIGHT.md and LICENSE.md for full copyright and license information.
#####################################################################################################
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
