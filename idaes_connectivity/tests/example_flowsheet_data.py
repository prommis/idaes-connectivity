import pytest


@pytest.fixture
def example_csv():
    return [
        "Arcs,M01,H02,F03",
        "fs.s01,-1,1,0",
        "fs.s02,0,-1,1",
    ]


@pytest.fixture
def example_mermaid():
    return [
        "flowchart LR",
        "    Unit_B["M01"]",
        "    Unit_C["H02"]",
        "    Unit_D["F03"]",
        "    Unit_B --> Unit_C",
        "    Unit_C --> Unit_D",
    ]


@pytest.fixture
def example_d2():
    return [
        "direction: right",
        "Unit_B: M01 {",
        "  shape: image",
        "  icon: /home/dang/.idaes/icon_shapes/mixer.svg",
        "}",
        "Unit_C: H02",
        "Unit_D: F03",
        "Unit_B -> Unit_C",
        "Unit_C -> Unit_D",
    ]
