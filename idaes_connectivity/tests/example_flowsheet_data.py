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
        '    Unit_B@{icon: "idaes:mixer", form: "square", label: "M01", pos: "B", h: 50}',
        '    Unit_C@{icon: "idaes:heater-1", form: "square", label: "H02", pos: "B", h: 50}',
        '    Unit_D@{icon: "idaes:flash", form: "square", label: "F03", pos: "B", h: 50}',
        "    Unit_B --> Unit_C",
        "    Unit_C --> Unit_D",
        "classDef idaesUnit fill:#cdf;",
        "class Unit_B,Unit_C,Unit_D idaesUnit;",
    ]
