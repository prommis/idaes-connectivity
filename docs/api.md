# Python API

The Python API is contained in the *idaes_connectivity.base* module.
The basic workflow is:
* Create an instance of the [Connectivity](connectivity-class) class from a model.
* Format the connectivity information with one of the subclasses of the [Formatter](formatter-classes) class, writing to a file
or returning the value as a string.
  - You can output CSV for viewing in a text editor or spreadsheet program.
  - You can also output a text-based diagram specification for viewing in a tool such as Mermaid or D2. Find more details on the [diagrams](diagrams.md) page.

The rest of this page provides some [examples](api-examples) of API usage and details of the [Connectivity](connectivity-class) and [Formatter](formatter-classes) classes.

(api-examples)=
## Examples

In these examples, we will assume we have an instance of Connectivity for a given model. 
```
from idaes_connectivity.tests.example_flowsheet import build
model = build()
conn = Connectivity(input_model=model)
```

Thenm, to create a CSV file:
```
from idaes_connectivity.base import Connectivity, CSV
# get connectivity
conn = 
# format as CSV
csv_fmt = CSV(conn)
csv_fmt.write("myfile.csv")
```

Creating D2 and Mermaid diagrams follows the same pattern:
```
from idaes_connectivity.base import Mermaid, D2
mermaid_fmt = Mermaid(conn)
mermaid_fmt.write("myfile.mmd")
d2_fmt = D2(conn)
d2_fmt.write("myfile.d2")
```

Returning as a string requires `None` as the file argument (full example to show output):
```
from idaes_connectivity.base import D2, Connectivity
from idaes_connectivity.tests.example_flowsheet import build

conn = Connectivity(input_model=build())

print(D2(conn).write(None))
```
Ouput:
```
direction: right
Unit_B: M01
Unit_C: H02
Unit_D: F03
Unit_B -> Unit_C
Unit_C -> Unit_D
```

A convenience method, `display_connectivity`, displays the Mermaid diagram inline in a Jupyter Notebook. 
This requires JupyterLab 4.1 or Notebook 7.1, or later.
```
from idaes_connectivity.base import Connectivity
from idaes_connectivity.jupyter import display_connectivity

conn = Connectivity(input_module="idaes_connectivity.tests.example_flowsheet")

display_connectivity(conn)
```
Results are output in the next cell, in Markdown, like:
```{image} ex.svg
:height: 75px
```


(connectivity-class)=
## Model connectivity
The `Connectivity` class represents the connectivity of the model.
It also provides some methods to add key/value pairs to the streams or units in the model.
You can fetch values from the model itself using the utility function {py:func}`idaes_connectivity.util.get_stream_display_values`.

```{eval-rst}
.. autoclass:: idaes_connectivity.base.Connectivity
    :class-doc-from: class
    :members: __init__, as_table, stream_values, set_stream_value, set_stream_values_map, clear_stream_values,    
              unit_values, set_unit_value, set_unit_values_map, clear_unit_values
    :member-order: bysource
```

(formatter-classes)=
## Formatters

All formatters have a `write` method, defined in their base class, `Formatter`.

The basic usage is:
* Create the formatter, passing an instance of [](connectivity-class).
* Call `formatter.write()` to generate the text.

### Formatter base class

```{eval-rst}
.. autoclass:: idaes_connectivity.base.Formatter
  :class-doc-from: class
  :members: write
```

### CSV formatter

The CSV formatter writes out text as comma-separated values.
It ignores the `direction` argument in the `Formatter` base class constructor.

```{eval-rst}
.. autoclass:: idaes_connectivity.base.CSV
  :class-doc-from: class
  :members: __init__, write
```

### Mermaid formatter

The Mermaid formatter writes out a Mermaid text description.

```{eval-rst}
.. autoclass:: idaes_connectivity.base.Mermaid
  :class-doc-from: class
  :members: __init__, write
```

#### Jupyter

Mermaid is supported by newer versions of Jupyter Notebooks and Jupyter Lab.
The *display_connectivity* function allows one to easily display a diagram in a Jupyter notebook.
This function is also shown in the [Jupyter Notebook example](./example.md).

```{eval-rst}
.. autofunction:: idaes_connectivity.jupyter.display_connectivity
```

This function

### D2 formatter

The D2 formatter writes out a D2 text description.

```{eval-rst}
.. autoclass:: idaes_connectivity.base.D2
  :class-doc-from: class
  :members: __init__, write
```

(utility-functions)=
## Utility

Utility functions.

```{eval-rst}
.. automodule:: idaes_connectivity.util
   :members: get_stream_display_values
```