"""Pull identifier-shaped tokens out of diff text.

This exists to answer one question: are this doc change and this code change
*about the same thing*, or did they merely land in the same commit? Sharing an
identifier is the cheapest available evidence that they are. It is evidence, not
proof -- two unrelated changes can both mention `config` -- which is why the
stoplist below matters more than the regex does.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = [
    "MIN_TOKEN_LENGTH",
    "delta",
    "extract",
    "extract_numbers",
    "extract_versions",
    "literal_spans",
    "strip_html_tags",
    "shared",
    "strip_comment_lines",
    "strip_urls",
]

# Deliberately loose: identifiers, dotted attribute paths, and the insides of
# backticked spans all reduce to runs of word characters.
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# camelCase and PascalCase boundaries, so `maxRetries` also yields `max` and
# `retries` -- docs and code often disagree about casing conventions for the
# same concept.
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

# Tokens shorter than this are noise at the scale we operate: `id`, `os`, `to`.
MIN_TOKEN_LENGTH = 4

# Language keywords and structural words. These co-occur in almost every
# code/doc pair, so leaving them in would make the overlap test always pass --
# which would look like a working heuristic while measuring nothing.
_KEYWORDS = frozenset(
    """
    self this null none true false void func function def class struct enum impl
    trait interface public private protected static final const let mut var
    return yield await async import export from require module package namespace
    while break continue elif else then case switch default goto
    try catch except finally raise throw throws assert with using
    type typeof instanceof new delete sizeof template typename extern inline
    string bool int long float double char byte short unsigned signed
    list dict set tuple array vector map slice option result
    print println echo log console error warn info debug trace fatal panic
    args kwargs argv params param arg
    """.split()
)

# High-frequency English that survives the length filter. Without this the
# overlap test fires on prose like "the following configuration options".
_ENGLISH = frozenset(
    """
    also although always because before being below between both cannot change
    changed changes could does doing done during each either else even every
    example examples first following from have here however into itself just
    like make makes many more most must need needs note only other others over
    same should since some such than that their them then there these they this
    those through under until using very were what when where which while will
    with within without would your
    added adding allow allows available call called calling case cases
    check code create created creates current data default defaults
    described description detail details different documentation does
    file files find found given help implementation include included includes
    information instead issue level line lines list local look makes
    method methods more name names need never number object objects
    onto option options order output page pages part pass passed
    project provide provided provides read reference release remove removed
    request requests require required requires response result results
    return returns same section see sent server service set sets setting
    settings should side simple single specified specify start started
    state step steps still support supported supports sure take taken
    test text than thing time true type types update updated updates
    usage use used user users uses value values version want warning
    way work working works write written
    """.split()
)

# Platform and packaging vocabulary. Added 2026-09-18 after hand-review: the
# single largest source of false positives was repo-wide mechanical sweeps
# (renaming the GitHub org, switching http:// to https:// everywhere), which touch
# a doc and some code and "share" exactly these tokens while misdescribing
# nothing.
_PLATFORM = frozenset(
    """
    github gitlab bitbucket https http readthedocs pypi conda npm
    python python2 python3 master main trunk branch commit repo repository
    issue issues pull request tracker badge shield travis appveyor circleci
    codecov coveralls jenkins actions workflow
    docs html index page site www com org net
    """.split()
)

_STOPWORDS = _KEYWORDS | _ENGLISH | _PLATFORM

# Version literals: 3.7, 3.14, 2.31.0, 1.0.0rc1. Emitted with a `ver:` prefix so
# they cannot collide with a real identifier and so they bypass MIN_TOKEN_LENGTH,
# which would otherwise discard "3.7" for being three characters long.
#
# This exists because of a measured failure, not a hunch. `_TOKEN_RE` requires a
# leading letter and `_normalise` drops anything numeric, so the entire identifier
# system was blind to version numbers. Two of the six true positives in the
# 2026-09-18 shape-A review were Python-version-support corrections, and both
# survived only as the bare token `python` -- which the platform stoplist then
# removed, making them look like stoplist casualties when the real cause was that
# the claim itself was never tokenisable.
#
# Deliberately narrow: at least one dot, so a bare `200` or `3` stays out. Known
# risk, stated rather than solved -- dependency-bump commits are dense in version
# literals and will now score as changed claims. `COSMETIC_SUBJECT_MARKERS`
# already catches "bump" and "version number", and changelogs are excluded by
# path, so there is some cover; whether it is enough is a question for the labels.
#
# Rewritten 2026-09-18 after reading the ten hand-judged shape-B cases whose only
# evidence was a `ver:` token. The first version was `\b\d+(?:\.\d+)+...` and it was
# wrong in two ways that the labels made visible and no test had:
#
#   `127.0.0.1`, `179.13.100.4`, and a MIME boundary `127.0.0.1.502.21746...` all
#   matched. A dotted numeric run is not a version. Hence at most three components
#   and the trailing `(?!\.?\d)`, which is what actually rejects an address: without
#   it the pattern happily matches the `127.0.0` prefix of a dotted quad.
#
#   A leading `v` truncated the match instead of being absorbed, because `\b` does
#   not fire between `v` and `0`. So `v0.5.0` yielded `5.0` -- and, far worse,
#   `v1.0.0` and `v2.0.0` BOTH yielded `0.0`. Two different versions collided on one
#   token, which means a doc corrected from one to the other registered as no change
#   at all. That is a fourth instance of this file's recurring bug: the token
#   carrying the claim is the one the tokeniser destroys. Found in the code written
#   to fix the first three.
#
# Four digits per component, so calendar versions like `2023.11.0` survive. Genuine
# four-component versions (`1.2.3.4`) are now missed; that is the price of rejecting
# IP addresses, and it is the cheaper of the two errors on documentation prose.
_VERSION_RE = re.compile(
    r"(?<![\w.])[vV]?(?P<version>\d{1,4}(?:\.\d{1,4}){1,2}"
    r"(?:\.?(?:a|b|rc|dev|post)\d*)?)(?!\.?\d)"
)

# Standalone integers, prefixed `num:` for the same reasons as `ver:`. The negative
# lookarounds keep this from shredding a version literal into its components, so
# `3.8` stays one `ver:` token and does not also yield `num:3` and `num:8`.
#
# Used inside marked-up code spans only. This is the third symptom of one root
# cause: the token that carries the claim keeps being the one the tokeniser throws
# away. Versions were unextractable, `True`/`False` were stoplisted, and a numeric
# default like ``timeout=30`` was dropped as a digit -- so "the default changed
# from None to 30" read as no change at all. In prose a bare `30` is noise; inside
# backticks it is a value someone is asserting.
_NUMBER_RE = re.compile(r"(?<![\d.\w])\d+(?![\d.]|\w)")

# A URL contributes its host and path segments as if they were identifiers:
# `https://github.com/kennethreitz/requests` yields `kennethreitz`, `github`,
# `requests`. None of that is a code symbol, and it was the top false-positive
# source in the 2026-09-18 review.
_URL_RE = re.compile(r"(?:https?://|www\.|mailto:)\S+", re.IGNORECASE)

# Comment markers across the languages we classify as code. Applied to the code
# side only -- prose is the entire content of the doc side.
_COMMENT_LINE_RE = re.compile(r"^\s*(?:#|//|/\*|\*/|\*(?!\w)|--|;;|<!--|\"\"\"|''')")


def strip_urls(text: str) -> str:
    return _URL_RE.sub(" ", text)


# Inline literal spans: ``x`` in RST, `x` in markdown, and RST roles like
# :class:`x`. This is how documentation marks the difference between a word and a
# symbol, and it is the only such signal available in prose.
_LITERAL_SPAN_RE = re.compile(r"``(?P<double>[^`\n]+)``|`(?P<single>[^`\n]+)`")
# Fenced code blocks. Content between fences is code, whatever the info string says.
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
# HTML/XML tags. Docs in markdown routinely inline anchors, and the attribute
# names -- href, target, class, external -- are identifier-shaped, survive URL
# stripping, and are pure markup. Removing a dead link therefore looked exactly
# like retracting a factual claim.
_HTML_TAG_RE = re.compile(r"<[^>\n]+>")


def strip_html_tags(text: str) -> str:
    return _HTML_TAG_RE.sub(" ", text)


def literal_spans(text: str) -> str:
    """Only the parts of prose that are marked up as code.

    Backticked spans plus the insides of fenced blocks. Everything else in a doc
    is English, and English is what drowned the doc-only signal: the first
    shape-B review scored 0/20, and the retained cases were firing on words like
    `guarantee` and `stability` because a reworded sentence changes its nouns.

    Lossy on purpose. A doc that names a function in bare prose without marking it
    up will not register here. That trade is deliberate: shape B has no
    demonstrated true positives and over a thousand candidates, so precision is
    the binding constraint and recall is not.
    """
    kept: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            kept.append(line)
            continue
        for match in _LITERAL_SPAN_RE.finditer(line):
            kept.append(match.group("double") or match.group("single") or "")
    return "\n".join(kept)


def strip_comment_lines(text: str) -> str:
    """Drop whole-line comments.

    Deliberately line-based and therefore incomplete: it will not catch a trailing
    comment on a code line, or prose inside a multi-line docstring whose opening
    quote is outside the diff fragment. It catches the case the review data
    actually showed -- a URL in a standalone `#` comment matching a URL in the
    docs -- and the residue is a known, stated limitation rather than a silent one.
    """
    return "\n".join(
        line for line in text.splitlines() if not _COMMENT_LINE_RE.match(line)
    )


def _normalise(raw: str, *, stopwords: bool = True) -> Iterable[str]:
    """Yield lowercase candidate tokens from one raw identifier."""
    pieces = [raw, *_CAMEL_SPLIT_RE.split(raw), *raw.split("_")]
    for piece in pieces:
        token = piece.strip("_").lower()
        if len(token) < MIN_TOKEN_LENGTH:
            continue
        if stopwords and token in _STOPWORDS:
            continue
        if token.isdigit():
            continue
        yield token


def extract(text: str, *, versions: bool = True, stopwords: bool = True) -> set[str]:
    """Identifier-shaped tokens in `text`, normalised and stopworded.

    `versions` is switchable because turning it on *admits* cases rather than
    removing them, so unlike the subtractive filters its effect cannot be scored
    against existing hand-labels -- the two corpora have to be mined both ways and
    compared.

    `stopwords` exists to be turned off inside marked-up code spans. The stoplist
    suppresses *prose* noise, and inside backticks that rationale does not hold:
    `True`, `False`, `None` and `return` are code there, not English. Leaving it on
    everywhere made `verify=True` -> `verify=False` -- a flag flip, and one of the
    plainest kinds of documentation drift there is -- register as no change at all.
    """
    tokens: set[str] = set()
    for match in _TOKEN_RE.finditer(text):
        tokens.update(_normalise(match.group(0), stopwords=stopwords))
    if versions:
        tokens |= extract_versions(text)
    return tokens


def extract_versions(text: str) -> set[str]:
    """Just the version literals. Separate because they are the one claim type
    that is legitimately made in bare prose -- "supports Python 3.8" needs no
    backticks to be a factual assertion -- so `literals_only` must not filter them
    out along with the surrounding English.

    Emits the numeric part only, so `v1.0.0` and `1.0.0` are the same token. A doc
    that switches between the two spellings is not asserting anything new.
    """
    return {f"ver:{match.group('version')}" for match in _VERSION_RE.finditer(text)}


def extract_numbers(text: str) -> set[str]:
    """Standalone integers as `num:` tokens. See `_NUMBER_RE`."""
    return {f"num:{match.group(0)}" for match in _NUMBER_RE.finditer(text)}


def delta(
    added_text: str,
    removed_text: str,
    *,
    drop_urls: bool = True,
    versions: bool = True,
    literals_only: bool = False,
) -> dict[str, list[str]]:
    """Identifiers that exist on only one side of a diff.

    The contrast available in a doc-only commit, where there is no code diff to
    compare against. The reasoning: rewording a sentence preserves its
    identifiers, because the nouns are the part that carries the claim. Replacing
    a false claim moves one -- `verify=False` becomes `verify=True`, `3.7`
    becomes `3.8`, a renamed function stops being named.

    The two directions are not the same defect and are returned separately:

      removed_only -- something the docs used to assert and no longer do. This is
        the signature of a *correction*, and the one that means drift.
      added_only -- something the docs now assert and did not before. On its own
        this is documentation that was *incomplete*, not documentation that was
        false. Real, worth finding, and not what this label claims.

    Collapsing the two would let every expanded paragraph in the repo enter the
    corpus as a positive.
    """
    if drop_urls:
        added_text = strip_urls(added_text)
        removed_text = strip_urls(removed_text)
    def tokens(text: str) -> set[str]:
        if not literals_only:
            return extract(text, versions=versions)
        body = strip_html_tags(text)
        spans = literal_spans(body)
        found = extract(spans, versions=False, stopwords=False) | extract_numbers(spans)
        if versions:
            found |= extract_versions(body)
        return found

    added_tokens = tokens(added_text)
    removed_tokens = tokens(removed_text)
    by_length = lambda token: (-len(token), token)  # noqa: E731
    return {
        "added_only": sorted(added_tokens - removed_tokens, key=by_length),
        "removed_only": sorted(removed_tokens - added_tokens, key=by_length),
    }


def shared(
    doc_text: str,
    code_text: str,
    *,
    drop_urls: bool = True,
    drop_code_comments: bool = True,
    versions: bool = True,
) -> list[str]:
    """Tokens appearing in both sides, sorted longest-first.

    Longest-first because a long shared token is much stronger evidence of a
    common subject than a short one, and the caller usually wants to eyeball the
    top few rather than all of them.

    Both cleaning steps are switchable rather than hardcoded so the miner can be
    run with and without them against the same hand-labels. A filter you cannot
    turn off is a filter whose contribution you cannot measure.
    """
    if drop_urls:
        doc_text = strip_urls(doc_text)
        code_text = strip_urls(code_text)
    if drop_code_comments:
        code_text = strip_comment_lines(code_text)
    overlap = extract(doc_text, versions=versions) & extract(code_text, versions=versions)
    return sorted(overlap, key=lambda token: (-len(token), token))
