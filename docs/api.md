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
# Python API

The Python API is contained in the *idaes_connectivity.base* module.
The basic workflow is:
* Create an instance of the [Connectivity](connectivity-class) class from a model.
* Format the connectivity information with one of the subclasses of the [Formatter](formatter-classes) class, writing to a file
or returning the value as a string.
  - You can output CSV for viewing in a text editor or spreadsheet program.
  - You can also output a text-based diagram specification for viewing in a tool such as Mermaid or D2. Find more details on the [diagrams](diagrams.md) page.

The rest of this page documents the [Connectivity](connectivity-class) and [Formatter](formatter-classes) classes and then provides some [extended examples](api-examples) of API usage.

(connectivity-class)=
## Model connectivity
The `Connectivity` class represents the connectivity of the model.

```{eval-rst}
.. autoclass:: idaes_connectivity.base.Connectivity
    :class-doc-from: class
    :members: __init__, as_table
```

(formatter-classes)=
## Formatters

(api-examples)=
## Examples
