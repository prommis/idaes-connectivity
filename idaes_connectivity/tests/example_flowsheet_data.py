import pytest


@pytest.fixture
def example_csv():
    return [
        "Arcs,M01,H02,F03",
        "fs.s01,-1,1,0",
        "fs.s02,0,-1,1",
        #        "f01,1,0,0",
        #        "k01,0,0,-1",
    ]


@pytest.fixture
def example_csv_with_user_names():
    return [
        "Arcs,user_M01,user_H02,user_F03",
        "fs.s01,-1,1,0",
        "fs.s02,0,-1,1",
        #        "f01,1,0,0",
        #        "k01,0,0,-1",
    ]


@pytest.fixture
def example_mermaid():
    return [
        "flowchart LR",
        '    Unit_B["M01"]',
        '    Unit_C["H02"]',
        '    Unit_D["F03"]',
        "    Unit_B --> Unit_C",
        "    Unit_C --> Unit_D",
    ]


@pytest.fixture
def example_mermaid_user_names():
    return [
        "flowchart LR",
        '    Unit_B["user_M01"]',
        '    Unit_C["user_H02"]',
        '    Unit_D["user_F03"]',
        "    Unit_B --> Unit_C",
        "    Unit_C --> Unit_D",
    ]


@pytest.fixture
def example_d2():
    return [
        "direction: right",
        "Unit_B: M01 {",
        "  shape: image",
        "  icon: /home/<user>/.idaes/icon_shapes/mixer.svg",
        "}",
        "Unit_C: H02",
        "Unit_D: F03",
        "Unit_B -> Unit_C",
        "Unit_C -> Unit_D",
    ]


@pytest.fixture
def example_d2_user_names():
    return [
        "direction: right",
        "Unit_B: user_M01 {",
        "  shape: image",
        "  icon: /home/<user>/.idaes/icon_shapes/mixer.svg",
        "}",
        "Unit_C: user_H02",
        "Unit_D: user_F03",
        "Unit_B -> Unit_C",
        "Unit_C -> Unit_D",
    ]
