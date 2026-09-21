# -*- coding: utf-8 -*-
"""arcpy.da test double: cursors and the edit session."""

from __future__ import unicode_literals

#: feature class name -> list of row tuples
_TABLES = {}

#: Domains and describe metadata the tests inject.
_DOMAINS = []


def _reset():
    _TABLES.clear()
    del _DOMAINS[:]


def _rows_of(feature_class):
    return list(_TABLES.get(feature_class, []))


def _register_table(feature_class, rows=None):
    _TABLES[feature_class] = list(rows or [])


class Domain(object):
    """Mirrors the shape of arcpy's Domain object for the fields the agent reads."""

    def __init__(self, name, domainType="CodedValue", codedValues=None, range=None):
        self.name = name
        self.domainType = domainType
        self.codedValues = codedValues or {}
        self.range = range


def ListDomains(workspace):  # noqa: N802
    """Mirrors arcpy.da.ListDomains."""
    return list(_DOMAINS)


class InsertCursor(object):
    """Mirrors arcpy.da.InsertCursor, including its failure on network classes.

    The real cursor raises ``SystemError('error return without exception set')`` when
    the feature class participates in a geometric network (H13). Reproducing that is
    the whole point of this double: it is what makes the agent's staging path testable.
    """

    def __init__(self, feature_class, field_names):
        import arcpy

        if feature_class in arcpy._NETWORK_CLASSES:
            raise SystemError("error return without exception set")
        self.feature_class = feature_class
        self.field_names = list(field_names)
        _TABLES.setdefault(feature_class, [])

    def insertRow(self, row):  # noqa: N802
        _TABLES[self.feature_class].append(tuple(row))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SearchCursor(object):
    """Mirrors arcpy.da.SearchCursor."""

    def __init__(self, feature_class, field_names, where_clause=None):
        self.field_names = list(field_names)
        self._rows = iter(_rows_of(feature_class))

    def __iter__(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class Editor(object):
    """Mirrors arcpy.da.Editor.

    Tracks whether an edit session is open, because geometric-network and topology
    classes cannot be modified outside one ("Objects in this class cannot be updated
    outside an edit session").
    """

    #: True while any Editor has an operation open.
    session_open = False

    def __init__(self, workspace):
        self.workspace = workspace
        self._operation = False

    def startEditing(self, with_undo=False, multiuser_mode=True):  # noqa: N802
        Editor.session_open = True

    def startOperation(self):  # noqa: N802
        self._operation = True

    def stopOperation(self):  # noqa: N802
        self._operation = False

    def stopEditing(self, save_changes=True):  # noqa: N802
        Editor.session_open = False

    def __enter__(self):
        self.startEditing()
        self.startOperation()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stopOperation()
        self.stopEditing(save_changes=exc_type is None)
        return False
