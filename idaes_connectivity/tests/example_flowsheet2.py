"""
Simple flowsheet
"""

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


def build():
    """Build example flowsheet."""
    m = ConcreteModel()

    m.fs = FlowsheetBlock(dynamic=False)

    m.fs.BT_props = BTXParameterBlock()
    m.fs.BT_rxn = ReactionInterrogatorBlock(property_package=m.fs.BT_props)

    kw = dict(property_package=m.fs.BT_props)

    # units
    m.fs.FD = Feed(**kw)
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
    m.fs.s01 = Arc(source=m.fs.FD.outlet, destination=m.fs.CSTR.inlet)
    m.fs.s02 = Arc(source=m.fs.CSTR.outlet, destination=m.fs.HT.inlet)
    m.fs.s03 = Arc(source=m.fs.HT.outlet, destination=m.fs.FL.inlet)
    m.fs.s04a = Arc(source=m.fs.FL.vap_outlet, destination=m.fs.MX.inlet_1)
    m.fs.s04b = Arc(source=m.fs.FL.liq_outlet, destination=m.fs.MX.inlet_2)
    m.fs.s05 = Arc(source=m.fs.MX.outlet, destination=m.fs.HX.tube_inlet)

    TransformationFactory("network.expand_arcs").apply_to(m.fs)

    return m
