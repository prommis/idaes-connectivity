"""
This example shows how to use the Connectivity class with the University of Kentucky flowsheet model.
It prints out a table of the connectivity and a mermaid diagram of the flowsheet.
"""

# stdlib
import sys

# pkg
from idaes_connectivity.base import Connectivity
from idaes_connectivity.base import Mermaid

# prommis
try:
    from prommis.uky.uky_flowsheet import build

    uky_model = build()
except ImportError as err:
    uky_model = None
    uky_model_err = err

# other third-party
import pandas as pd

__author__ = "Dan Gunter"


def main():
    if uky_model is None:
        print(
            f"Import error, probably PrOMMiS is not installed. "
            f"See https://prommis.readthedocs.io/ for installation instructions.\n"
            f"Error message: {uky_model_err}"
        )
        return -1

    pd.set_option("display.max_columns", None)  # don't elide columns
    conn = Connectivity(input_model=uky_model)
    df = pd.DataFrame(conn.as_table())

    sep = "=" * 60

    # Print the tabular format
    print(sep)
    print("Table")
    print(sep)
    print(df)

    # Print the mermaid format, with stream labels
    print(sep)
    print("Mermaid diagram")
    print(sep)
    mmd = Mermaid(conn, stream_labels=True)
    print(mmd.write(None))

    # final separator
    print(sep)

    return 0


if __name__ == "__main__":
    sys.exit(main())
