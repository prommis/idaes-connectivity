"""
Tests for 'Connectivity' module in the context of IDAES models.
"""

__author__ = "Dan Gunter (LBNL)"

# third-party
import pytest
from pyomo.environ import ConcreteModel, Var, Set, RangeSet, TransformationFactory
from pyomo.network import Arc, Port
from idaes.core import FlowsheetBlock
from idaes.models.unit_models import Feed, Product, Pump
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.core.base.process_base import useDefault

from idaes.models.properties import iapws95

# pkg
from idaes_connectivity.base import Connectivity, Mermaid


class AlwaysAvailableIapws95ParameterBlock(iapws95.Iapws95ParameterBlock):
    def available(self):
        return True


def idaes_model(use_rangeset=False):
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.water_properties = AlwaysAvailableIapws95ParameterBlock()
    m.fs.feed = Feed(property_package=m.fs.water_properties)
    m.fs.product = Product(property_package=m.fs.water_properties)

    if use_rangeset:
        number_of_pumps = 2
        m.fs.pump_list = RangeSet(1, number_of_pumps)
        m.fs.pump = Pump(m.fs.pump_list, property_package=m.fs.water_properties)
        m.fs.feed_to_p1 = Arc(source=m.fs.feed.outlet, destination=m.fs.pump[1].inlet)
        m.fs.p1_to_p2 = Arc(source=m.fs.pump[1].outlet, destination=m.fs.pump[2].inlet)
        m.fs.p2_to_product = Arc(
            source=m.fs.pump[2].outlet, destination=m.fs.product.inlet
        )
    else:
        m.fs.pump_01 = Pump(property_package=m.fs.water_properties)
        m.fs.pump_02 = Pump(property_package=m.fs.water_properties)
        m.fs.feed_to_p1 = Arc(source=m.fs.feed.outlet, destination=m.fs.pump_01.inlet)
        m.fs.p1_to_p2 = Arc(source=m.fs.pump_01.outlet, destination=m.fs.pump_02.inlet)
        m.fs.p2_to_product = Arc(
            source=m.fs.pump_02.outlet, destination=m.fs.product.inlet
        )

    TransformationFactory("network.expand_arcs").apply_to(m)

    return m


@pytest.mark.parametrize("with_sets", [True, False])
def test_build_idaes_connectivity(with_sets):
    model = idaes_model(use_rangeset=with_sets)
    conn = Connectivity(input_model=model.fs)

    # Check that the connectivity object has been created
    assert conn is not None

    # Check that the model has been processed correctly
    pumps = ["pump[1]", "pump[2]"] if with_sets else ["pump_01", "pump_02"]
    table = conn.as_table()
    assert table is not None
    print(table)
    expected_table = [
        ["Arcs", "feed", pumps[0], pumps[1], "product"],
        ["feed_to_p1", -1, 1, 0, 0],
        ["p1_to_p2", 0, -1, 1, 0],
        ["p2_to_product", 0, 0, -1, 1],
    ]
    assert table == expected_table

    # Check that Mermaid output is generated correctly
    mermaid_formatter = Mermaid(conn)
    mermaid_output = mermaid_formatter.write(None)
    print(mermaid_output)
    assert mermaid_output is not None
