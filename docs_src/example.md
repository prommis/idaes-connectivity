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

# Example

This section shows a small example of the both the [Python API](./api.md) and [command-line interface](./cli.md).
The example formats the connectivity information in
its simplest form as a comma-separated value (CSV table with model units in each row and arcs for each column, where non-zero cell values indicate an arc entering (1) or leaving (-1) the unit. 

## Python API

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

# Display diagram as an image, this will load it using system image viewer
conn.show()

# Save diagram to disk
conn.save(save_name='example.jpg')
```

## Command-line interface

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