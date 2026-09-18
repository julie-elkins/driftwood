"""The asymmetry that separates a correction from a new feature.

Both look identical to a plain overlap test: a doc and a code file change in one
commit and share an identifier. The difference is *direction*. A feature adds a
symbol to both sides. A correction takes the stale claim out of both.

This distinction is not theoretical. `new` was absent from the first 40
hand-labelled cases and was then the largest shape-A error class in the next 45,
at 8 of 25 -- so the first review's evidence actively argued against building the
gate these tests cover.
"""

from __future__ import annotations

import re

from driftwood.mining import identifiers
from driftwood.mining.gitio import changed_lines, changed_sides
from driftwood.mining.labels import _DOCS_BUILD_PATH_RE


def withdrawn(doc_diff: str, code_diff: str) -> list[str]:
    """What labels.py computes under `require_withdrawn_claim`."""
    _, doc_removed = changed_sides(doc_diff)
    _, code_removed = changed_sides(code_diff)
    return identifiers.shared(doc_removed, code_removed)


FEATURE_DOC = """\
@@ -10,3 +10,5 @@
+.. autofunction:: stream_template
+.. autofunction:: stream_template_string
"""

FEATURE_CODE = """\
@@ -20,3 +20,8 @@
+def stream_template(template_name, **context):
+    return _stream(template_name, context)
"""

CORRECTION_DOC = """\
@@ -10,3 +10,3 @@
-Set ``FLASK_ENV=development`` to enable the debugger.
+Set ``FLASK_DEBUG=1`` to enable the debugger.
"""

CORRECTION_CODE = """\
@@ -20,3 +20,3 @@
-    env = os.environ.get("FLASK_ENV")
+    debug = os.environ.get("FLASK_DEBUG")
"""


def test_new_feature_shares_identifiers_but_withdraws_none():
    """The false-positive class. Overlap is high; the gate must still reject it."""
    overlap = identifiers.shared(
        changed_lines(FEATURE_DOC), changed_lines(FEATURE_CODE)
    )
    assert "stream_template" in overlap, "precondition: the naive test does fire"
    assert withdrawn(FEATURE_DOC, FEATURE_CODE) == []


def test_correction_withdraws_an_identifier_from_both_sides():
    """The true-positive class. Must survive the gate."""
    assert "flask_env" in withdrawn(CORRECTION_DOC, CORRECTION_CODE)


def test_gate_is_strictly_subtractive():
    """Whatever the gate keeps, the naive overlap test kept too.

    Worth asserting rather than assuming: a subtractive filter can be scored
    against existing hand labels, and an additive one cannot. If this property
    ever broke, the retention tooling would silently start reporting nonsense.
    """
    for doc, code in ((FEATURE_DOC, FEATURE_CODE), (CORRECTION_DOC, CORRECTION_CODE)):
        naive = set(identifiers.shared(changed_lines(doc), changed_lines(code)))
        assert set(withdrawn(doc, code)) <= naive


def test_docs_build_renumbering_is_recognised():
    moved = changed_lines(
        "@@ -1,2 +1,2 @@\n"
        "-{!> ../../docs_src/dependencies/tutorial001.py!}\n"
        "+{!> ../../docs_src/dependencies/tutorial001_an.py!}\n"
    )
    assert _DOCS_BUILD_PATH_RE.search(moved)


def test_ordinary_api_correction_is_not_mistaken_for_a_docs_build_change():
    """The filter must not swallow the arm's real positives."""
    assert not _DOCS_BUILD_PATH_RE.search(changed_lines(CORRECTION_DOC))
    # A doc that merely says the word "tutorial" is prose, not a generated path.
    assert not _DOCS_BUILD_PATH_RE.search("See the tutorial for a worked example.")


def test_docs_build_pattern_needs_a_digit():
    """`tutorial` alone is prose; `tutorial001` is a generated filename.

    Guards the boundary directly, because widening this regex to bare `tutorial`
    would silently discard every doc page that mentions one.
    """
    assert isinstance(_DOCS_BUILD_PATH_RE, re.Pattern)
    assert not _DOCS_BUILD_PATH_RE.search("tutorial")
    assert _DOCS_BUILD_PATH_RE.search("tutorial7")
