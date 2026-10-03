# -*- coding: utf-8 -*-
"""Minimal arcpy test double — see ../README.md.

Reproduces only the behaviours the agent's design depends on, including the failures.
Written to parse on Python 2.7 and 3.x, like the agent itself.
"""

from __future__ import unicode_literals

from . import da  # noqa: F401  (re-exported as arcpy.da, mirroring the real package)

#: Registry the tests populate: feature class name -> participates in geometric network.
_NETWORK_CLASSES = set()

#: Rows appended per feature class, so tests can assert on the result.
_APPENDED = {}


def _reset():
    """Clear double state between tests."""
    _NETWORK_CLASSES.clear()
    _APPENDED.clear()
    da._reset()


def _register_network_class(feature_class):
    """Mark a feature class as participating in the geometric network."""
    _NETWORK_CLASSES.add(feature_class)


class ExecuteError(Exception):
    """Mirrors arcpy.ExecuteError."""


def Append_management(inputs, target, schema_type="TEST"):  # noqa: N802
    """Mirrors arcpy.Append_management.

    Unlike InsertCursor, Append does work against geometric-network classes — which is
    exactly why the agent routes every insert through staging plus Append (H13).
    """
    if isinstance(inputs, (list, tuple)):
        sources = list(inputs)
    else:
        sources = [inputs]
    rows = []
    for source in sources:
        rows.extend(da._rows_of(source))
    _APPENDED.setdefault(target, []).extend(rows)
    return target


def Exists(name):  # noqa: N802
    return name in da._TABLES or name in _APPENDED


def Delete_management(name):  # noqa: N802
    da._TABLES.pop(name, None)
    _APPENDED.pop(name, None)
