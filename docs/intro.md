---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# IDAES Connectivity Tool

## Overview

The IDAES connectivity tool provides a Python API and a command-line script to extract and display the connectivity within [IDAES](https://idaes.org) and [Pyomo](https://pyomo.org) models.

It can output simple comma-separated value (CSV) files for looking at in a spreadsheet and it can post-process the information into input for the diagramming tools [Mermaid](https://mermaid.js.org/) or [D2](https://d2lang.com).

## Installation

You can install the latest version of the tool using *pip*:
```shell
pip install git+https://github.com/prommis/idaes-connectivity.git
```

To verify the installation and see which version of the tool was installed, you can run the command-line program:
```shell
$ idaes-conn --version
0.0.1
```

You can also run test suite with `pytest`:
```shell
pytest --pyargs idaes_connectivity
```

## Example

This section shows a small example of the both the Python and command-line interface.
The example formats the connectivity information in
its simplest form as a comma-separated value (CSV table with model units in each row and arcs for each column, where non-zero cell values indicate an arc entering (1) or leaving (-1) the unit. 

### Python

```{code-cell}
# Import the main class, "Connectivity", and 
# a formatter class (CSV)
from idaes_connectivity.base import Connectivity, CSV

# Build the simple example flowsheet
from idaes_connectivity.tests.example_flowsheet import build
model = build()

# Extract and format connectivity
conn = Connectivity(input_model=model)
csv = CSV(conn)

# Print out the connectivity CSV
print(csv.write(None))
```

### Command-line

```{code-block} shell

# generate the CSV output, for the simple
# included flowsheet, as a file
$ idaes-conn idaes_connectivity.tests.example_flowsheet --to csv --output-file ex.csv
# show the output
$ cat ex.csv
```
```none
Arcs,M01,H02,F03
s01,-1,1,0
s02,0,-1,1
```

## Contents

```{tableofcontents}
```
