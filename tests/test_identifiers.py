"""Cases that caught real bugs, kept so they stay caught.

Every parametrised case below was found by reading actual mined output or an actual
review sheet, not by imagining what might break. Three of them correspond to
defects that shipped: version literals were unextractable, `True`/`False` were
stoplisted as prose, and bare integers were discarded as digits. All three had the
same shape -- the token carrying the factual claim was the one the tokeniser threw
away -- and all three made a genuine documentation correction register as no change
at all.

The `drop` cases matter as much as the `keep` ones. The filter's whole job is to
separate a factual correction from a rewording, and a filter that keeps everything
would pass every `keep` case here while being worthless.
"""

from __future__ import annotations

import pytest

from driftwood.mining import identifiers as ids

# (name, added_text, removed_text, should_be_kept)
DELTA_CASES = [
    # --- rewordings and markup churn: must NOT look like a claim change ---
    (
        "dead_link_removal_html",
        'See the <a href="https://example.com" class="external-link" target="_blank">docs</a>.',
        'See <a href="http://callbackhell.com" class="external-link" target="_blank">callback hell</a>.',
        False,
    ),
    (
        "prose_rewording",
        "There are no stability guarantees for these recommendations.",
        "We give no guarantee of stability and requirements much may happen.",
        False,
    ),
    (
        "code_block_reindent",
        "```py\n  x = 1\n```",
        "```py\nx = 1\n```",
        False,
    ),
    (
        "pure_addition_is_incompleteness_not_falsity",
        "There is also a ``stream`` parameter for large responses.",
        "",
        False,
    ),
    # --- genuine factual corrections: must survive ---
    (
        "version_claim_in_bare_prose",
        "Requests officially supports Python 3.8+.",
        "Requests officially supports Python 3.7+.",
        True,
    ),
    (
        "symbol_renamed",
        "Use the ``charset_normalizer`` package to detect encodings.",
        "Use the ``chardet`` package to detect encodings.",
        True,
    ),
    (
        "boolean_flag_flipped",
        "Pass ``verify=True`` to check certificates.",
        "Pass ``verify=False`` to check certificates.",
        True,
    ),
    (
        "numeric_default_changed",
        "The default is ``timeout=None``.",
        "The default is ``timeout=30``.",
        True,
    ),
    (
        "import_changed_inside_fence",
        "```py\nimport charset_normalizer\n```",
        "```py\nimport chardet\n```",
        True,
    ),
]


@pytest.mark.parametrize(
    ("added", "removed", "kept"),
    [pytest.param(a, r, k, id=name) for name, a, r, k in DELTA_CASES],
)
def test_delta_literals_only(added: str, removed: str, kept: bool) -> None:
    result = ids.delta(added, removed, literals_only=True)
    assert bool(result["removed_only"]) is kept


def test_pure_addition_reports_added_but_not_removed() -> None:
    """The two directions are different defects and must stay distinguishable.

    Collapsing them would let every expanded paragraph in a repo enter the corpus
    as a positive, because prose gets longer far more often than it gets corrected.
    """
    result = ids.delta("Also takes a ``stream`` argument.", "", literals_only=True)
    assert result["added_only"]
    assert not result["removed_only"]


def test_version_literal_is_not_shredded_into_integers() -> None:
    """`3.8` must stay one version token.

    If `_NUMBER_RE` swallowed the components, `3.8` and `3.9` would share `num:3`
    and differ only in the minor -- still detectable, but `2.0` vs `3.0` would look
    like a claim change in a doc that merely renumbered a list.
    """
    assert ids.extract_versions("3.8") == {"ver:3.8"}
    assert ids.extract_numbers("3.8") == set()
    assert ids.extract_numbers("timeout=30") == {"num:30"}


def test_stoplist_applies_to_prose_but_not_to_literal_spans() -> None:
    """The stoplist suppresses prose noise; inside backticks these words are code."""
    assert "false" not in ids.extract("The value is false.")
    assert "false" in ids.extract("verify=False", stopwords=False)


def test_literal_spans_ignores_unmarked_prose() -> None:
    text = "Call charset_normalizer, or better ``chardet``, to sniff encodings."
    spans = ids.literal_spans(text)
    assert "chardet" in spans
    assert "charset_normalizer" not in spans


def test_html_attributes_do_not_survive_as_identifiers() -> None:
    """Removing a dead link was reading as retracting a factual claim."""
    html = '<a href="https://x.com" class="external-link" target="_blank">text</a>'
    stripped = ids.strip_html_tags(html)
    for attribute in ("href", "target", "external", "class"):
        assert attribute not in stripped


def test_shared_finds_version_overlap_between_doc_and_packaging_metadata() -> None:
    """The pair that was being lost: a docs version claim against setup.py.

    Before version literals were extractable this returned nothing at all, so the
    pair survived on the single generic token `python` -- and stoplisting `python`
    then removed the last trace of it.
    """
    assert ids.shared("Supports Python 3.8+.", 'python_requires=">=3.8"') == ["ver:3.8"]
    assert ids.shared("Supports Python 3.8+.", 'python_requires=">=3.8"', versions=False) == []


def test_extract_counts_agrees_with_extract_on_which_tokens_exist() -> None:
    """The two functions share `_TOKEN_RE`, `_normalise` and `_VERSION_RE` but not a
    body, because `extract` mined `data/labels.jsonl` and that label set cannot be
    replayed. This is what keeps the duplication from becoming a divergence -- and it
    runs over real source text rather than a fixture, because the shapes that break a
    tokeniser (dotted paths, camelCase, version literals, `__dunder__`) are exactly
    what a hand-written sample leaves out.
    """
    from pathlib import Path

    for path in sorted(Path("src/driftwood").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert set(ids.extract_counts(text)) == ids.extract(text), path
        assert set(ids.extract_counts(text, versions=False)) == ids.extract(
            text, versions=False
        ), path


def test_one_mention_counts_once_however_many_pieces_it_splits_into() -> None:
    """`_normalise` yields the raw identifier, its camel pieces and its underscore
    pieces from a SINGLE match, so counting the yield directly inflates a count -- and
    inflates it unevenly, by identifier shape rather than by frequency.

    `retries` has no internal boundary, so it arrives three times from one occurrence.
    `max_retries` yields `max_retries`, `max` and `retries`. Without the per-match
    `set()`, one mention of `retries` would outweigh one mention of `max_retries` on
    the token they share, which is backwards.
    """
    assert ids.extract_counts("retries") == {"retries": 1}
    assert ids.extract_counts("maxRetries") == {"maxretries": 1, "retries": 1}
    assert ids.extract_counts("max_retries") == {"max_retries": 1, "retries": 1}
    assert ids.extract_counts("retries retries retries")["retries"] == 3


def test_version_literals_are_counted_and_not_merely_present() -> None:
    counts = ids.extract_counts("Needs 3.8. Tested on 3.8 and 3.12.")
    assert counts["ver:3.8"] == 2
    assert counts["ver:3.12"] == 1
