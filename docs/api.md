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

The Python API is contained in the {py:mod}`idaes_connectivity.base` module.
The basic workflow is:
- Create an instance of the [Connectivity](connectivity-class) class from a model.
- Format the connectivity information with one of the subclasses of the [Formatter](formatter-classes) class, writing to a file
or returning the value as a string.
- Optionally, show the results with an external tool:
  - For CSV tables, view as text or in Excel
  - For text-based diagrams, run the appropriate program
    to create the diagram from the output text.

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

