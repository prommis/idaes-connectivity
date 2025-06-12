"""
Simple example flowsheet.

Run as a script to regenerate the data in
`example_flowsheet_data.py`
"""

# stdlib
import argparse
import logging
from pathlib import Path
import sys

# third-party
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
from idaes_connectivity.tests.util import generate, init_logger
from idaes_connectivity.base import Connectivity, CSV


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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()
    log = logging.getLogger(Path(__file__).name[:-3])
    init_logger(log)
    if args.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.WARNING)
    model = example_flowsheet.build()
    conn = Connectivity(input_model=model.fs)
    try:
        csv_file = "example_flowsheet.csv"
        log.info("Writing connectivity data to CSV: %s", csv_file)
        CSV(conn).write(csv_file)
        print(f"Connectivity data written to: {csv_file}")
    except Exception as e:
        log.warning("Failed to write connectivity data to CSV: %s", e)
    try:
        data_script = Path(__file__).parent / "example_flowsheet_data.py"
        log.info("Generating example flowsheet data: %s", data_script)
        generate(conn=conn, filename=str(data_script), log=log)
    except Exception as e:
        log.warning("Failed to generate example flowsheet data: %s", e)


if __name__ == "__main__":
    sys.exit(main())
