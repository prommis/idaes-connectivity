"""
Tests for const module.
"""

import pytest
from idaes_connectivity import const
from pyomo.environ import Component


def test_component_names():
    c = const.ComponentNames()

    with pytest.raises(AttributeError):
        c.get_filename(None)

    comp = Component(name="mystery", ctype="T")
    assert c.get_filename(comp) is None

    comp = Component(name="Mixer", ctype="T")
    assert "mixer" in c.get_filename(comp)

    assert "mixer" in c.get_filename("mixer")
