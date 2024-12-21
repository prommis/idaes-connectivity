"""
Shared constants for idaes_connectivity
"""

from enum import Enum

__author__ = "Dan Gunter (LBNL)"


class OutputFormats(Enum):
    MERMAID = "mermaid"
    CSV = "csv"
    D2 = "d2"


class Direction(Enum):
    RIGHT = 0
    DOWN = 1
