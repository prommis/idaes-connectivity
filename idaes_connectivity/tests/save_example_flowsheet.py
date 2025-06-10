"""
Simple example flowsheet.

Self-contained with generated data and ability to
re-generate data by running itself(!)
"""

# stdlib
import logging
from tempfile import NamedTemporaryFile
from shutil import copyfile
import sys

# third-party
import pytest
from idaes.models.unit_models import Heater
from pyomo.environ import TransformationFactory, ConcreteModel
from pyomo.network import Arc
from idaes.core import FlowsheetBlock
from idaes.models.properties.activity_coeff_models.BTX_activity_coeff_VLE import (
    BTXParameterBlock,
)
from idaes.models.unit_models import Flash, Mixer

# package
from idaes_connectivity.tests import example_flowsheet
from idaes_connectivity.base import Connectivity, CSV, Mermaid, D2

TAB = "    "

_log = logging.getLogger(__name__)
_h = logging.StreamHandler()
_h.setFormatter(logging.Formatter("{asctime} {levelname} - {message}", style="{"))
_log.addHandler(_h)


def build():
    """Build example flowsheet."""
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.BT_props = BTXParameterBlock()
    m.fs.M01 = Mixer(property_package=m.fs.BT_props)
    m.fs.H02 = Heater(property_package=m.fs.BT_props)
    m.fs.F03 = Flash(property_package=m.fs.BT_props)
    m.fs.s01 = Arc(source=m.fs.M01.outlet, destination=m.fs.H02.inlet)
    m.fs.s02 = Arc(source=m.fs.H02.outlet, destination=m.fs.F03.inlet)
    TransformationFactory("network.expand_arcs").apply_to(m.fs)
    return m


@pytest.fixture
def example_csv():
    return []


@pytest.fixture
def example_mermaid():
    return []


@pytest.fixture
def example_d2():
    return []


# Regenerate the data returned by fixtures
# by rewriting this file.


def main() -> int:
    _log.setLevel(logging.DEBUG)

    model = example_flowsheet.build()
    conn = Connectivity(input_model=model)
    data = {
        "csv": CSV(conn).write(None),
        "mermaid": Mermaid(conn).write(None),
        "d2": D2(conn).write(None),
    }

    filename = "connectivity_data.py"
    outfile = NamedTemporaryFile("w", encoding="utf-8")
    with open(filename, "r") as infile:
        fixture_name, in_fixture, wrote_data = None, False, False
        for line in infile:
            if in_fixture and line.startswith(f"{TAB}return"):
                outfile.write(f"{TAB}return [\n")
                for row in data[fixture_name].split("\n"):
                    row = row.rstrip()
                    if row:
                        outfile.write(f'{TAB}{TAB}"{row}",\n')
                outfile.write(f"{TAB}]\n")
                wrote_data = True
            else:
                if in_fixture and wrote_data:
                    if line.rstrip().endswith("]"):
                        in_fixture, wrote_data = False, False
                else:
                    outfile.write(line)
                    if line.startswith("@pytest.fixture"):
                        in_fixture = True
                    elif in_fixture and line.startswith("def"):
                        func = line.split(" ")[1].split("(")[0]
                        fixture_name = func.split("_")[-1]
    outfile.flush()
    outfile.seek(0)
    _log.debug(f"copyfile({outfile.name}, {infile.name})")
    copyfile(outfile.name, infile.name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
