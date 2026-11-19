"""
Tests for const module.
"""

from idaes_connectivity import const


def test_output_formats():
    assert {item.name: item.value for item in const.OutputFormats} == {
        "MERMAID": "mermaid",
        "CSV": "csv",
        "HTML": "html",
    }


def test_direction():
    assert const.Direction.RIGHT.value == 0
    assert const.Direction.DOWN.value == 1


def test_console():
    assert const.CONSOLE == "-"
