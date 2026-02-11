"""
Simple example flowsheet that has a bunch of different units.

Don't try to solve it, it is engineering garbage.
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
from idaes.models.properties.interrogator.reactions_interrogator import (
    ReactionInterrogatorBlock,
)
from idaes.models.unit_models import Flash, Mixer, HeatExchanger, CSTR, Feed

# package
from idaes_connectivity.tests.util import init_logger
from idaes_connectivity.base import Connectivity, CSV, Mermaid


def build():
    """Build example flowsheet."""
    m = ConcreteModel()

    m.fs = FlowsheetBlock(dynamic=False)

    m.fs.BT_props = BTXParameterBlock()
    m.fs.BT_rxn = ReactionInterrogatorBlock(property_package=m.fs.BT_props)

    kw = dict(property_package=m.fs.BT_props)

    # units
    m.fs.FDa = Feed(**kw)
    m.fs.FDb = Feed(**kw)
    m.fs.MX = Mixer(**kw)
    m.fs.HT = Heater(**kw)
    m.fs.FL = Flash(**kw)
    m.fs.HX = HeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": m.fs.BT_props},
        tube={"property_package": m.fs.BT_props},
    )
    m.fs.CSTR = CSTR(**kw, reaction_package=m.fs.BT_rxn)

    # arcs
    m.fs.s01 = Arc(source=m.fs.FDa.outlet, destination=m.fs.HT.inlet)
    m.fs.s02 = Arc(source=m.fs.HT.outlet, destination=m.fs.FL.inlet)
    m.fs.s03 = Arc(source=m.fs.FL.vap_outlet, destination=m.fs.MX.inlet_1)
    m.fs.s04 = Arc(source=m.fs.FL.liq_outlet, destination=m.fs.MX.inlet_2)
    m.fs.s05 = Arc(source=m.fs.MX.outlet, destination=m.fs.HX.tube_inlet)
    # m.fs.s06 = Arc(source=m.fs.FDa, destination=m.fs.HX.shell_inlet)
    # m.fs.s06 = Arc(source=m.fs.HX.tube_outlet, destination=m.fs.MX.inlet_2)
    # m.fs.s06 = Arc(source=m.fs.HX.shell_outlet, destination=m.fs.CSTR.inlet)

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
    model = build()
    conn = Connectivity(input_model=model.fs)
    try:
        csv_file = "example_flowsheet_2.csv"
        log.info("Writing connectivity data to CSV: %s", csv_file)
        CSV(conn).write(csv_file)
        print(f"Connectivity data written to: {csv_file}")
    except Exception as e:
        log.warning("Failed to write connectivity data to CSV: %s", e)
    mmd = Mermaid(conn, component_images=True)
    with open("example_flowsheet_2.mmd", "w") as f:
        mmd.write(f)


if __name__ == "__main__":
    sys.exit(main())
