"""The claims on a documentation page, as units a judge can be asked about one at a time.

Why this module exists at all is a measured finding rather than a design preference. The
per-page judge was asked one question about a 38,830-character page, returned `not-false`
with an empty `claim` field, and reasoned only about the opening -- never reaching the
sentence under test at character 22,461. Raising the document budget put that sentence on
screen and flipped none of the three cases it was cut from. The page being in the prompt
is not the same as the page being read, so the unit of work has to change rather than the
budget.

A "claim unit" here is a PROXY and not a definition: a sentence of the page's prose that
marks up at least one identifier, via the same `literal_spans` signal `select_relevant`
selects code with. Two deliberate choices in that:

- It does not use the miner's `shared_identifiers`. Those are evidence derived from the
  fixing commit, so a judge that saw them would be told which sentence to look at. The
  count here is one that can be computed at inference time on a page nobody has labelled,
  which is what a deployed version would have to do.
- A directive block, a table or a fenced example counts as no unit. That undercounts a
  page making claims entirely inside a table, and the direction of the error is named
  here so it is a known bias rather than a surprise. Measured against the 45 shape-A
  pages it is good to about 20%, which is the precision the decisions it feeds need.

  That sentence was false about this code when it was first written, which is the failure
  this repository is for. `_NOT_PROSE` dropped a fence's ``` markers and kept the lines
  between them, so a markdown example arrived as a prose sentence marking up every
  identifier it called. `_outside_fences` is the fix and a test pins it; `scripts/
  claim_units.py` was re-run afterwards and its unit counts are the corrected ones.

One of those 45 pages yields no unit at all, so a per-claim judge abstains on it by
construction rather than by judgement. That is a cost of the design, reported in
`scripts/claim_units.py`, and it is the one respect in which the per-page judge is
strictly better: it at least sees such a page.
"""

from __future__ import annotations

import re

from driftwood.mining.identifiers import extract, literal_spans

# Claims per call. 8 is not tuned -- it is the value the pricing diagnostic was read at,
# and it lands the seeded arm at 168 calls and 3.5x the input of one per-page pass. The
# alternative at the same input price, one call per claim with a cached prefix, needs 1,195
# replies against these 168 and needs every call to land inside the prompt cache's TTL to
# hit its advertised number; this needs neither. See `scripts/claim_units.py` section 3,
# including the correction to the first version of that argument.
DEFAULT_BATCH = 8

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# Lines that are not prose: rst directives, fenced code, indented blocks, table rules,
# underlines, shell and repl prompts.
_NOT_PROSE = re.compile(
    r"^\s*(?:\.\.\s|```|~~~|\||[-=~^\"'+*#]{3,}\s*$|>>>|\$\s)|^\s{4,}\S"
)

_FENCE = re.compile(r"^\s*(?:```|~~~)")


def _outside_fences(text: str) -> str:
    """The text with fenced blocks removed, fence markers and contents alike.

    A separate pass because fencing is the one structure here that is not a property of a
    LINE. `_NOT_PROSE` drops the ``` markers, and the first version of this module stopped
    there: the body between them is neither indented nor a directive, so
    `result = some_call(timeout=3)` came through as a prose sentence marking up two
    identifiers, and became a claim a judge was then asked to rule on. Worse, an example is
    precisely where an identifier that no longer exists is MEANT to appear literally, so
    those units would have been the arm's most confident false positives.

    Nor does the blank-line split isolate them: a fence usually opens on the line straight
    after its introducing sentence, so the fence and the prose share a block.

    A fence line toggles the state, and an unclosed fence therefore swallows the rest of the
    page. That is the right direction for a proxy whose errors are supposed to undercount:
    losing the tail of a malformed page costs some units, where the alternative costs
    invented claims.
    """
    kept: list[str] = []
    inside = False
    for line in text.splitlines():
        if _FENCE.match(line):
            inside = not inside
            kept.append("")
            continue
        kept.append("" if inside else line)
    return "\n".join(kept)


def claim_units(text: str) -> list[str]:
    """The page's prose sentences that mark up at least one identifier, in page order.

    Order matters and is preserved: the batches handed to a judge are contiguous runs of
    the page, so a reply that drifts onto a neighbouring sentence is at least drifting
    onto a nearby one, and a per-claim verdict can be located on the page by index.
    """
    units: list[str] = []
    for block in re.split(r"\n\s*\n", _outside_fences(text)):
        lines = [ln for ln in block.splitlines() if not _NOT_PROSE.match(ln)]
        if not lines:
            continue
        prose = " ".join(ln.strip() for ln in lines).strip()
        if not prose:
            continue
        for sentence in _SENTENCE_END.split(prose):
            sentence = sentence.strip()
            if not sentence:
                continue
            if extract(literal_spans(sentence), versions=False):
                units.append(sentence)
    return units


def batch(units, size: int = DEFAULT_BATCH) -> list[tuple[str, ...]]:
    """Group units into calls, in page order, without reordering or dropping any.

    A size below 1 would silently produce no batches and a run that looks like a judge
    with nothing to say, so it is refused rather than clamped.
    """
    if size < 1:
        raise ValueError(f"batch size must be at least 1, got {size}")
    units = list(units)
    return [tuple(units[i : i + size]) for i in range(0, len(units), size)]


def locates(claim: str | None, identifiers) -> bool:
    """Does this quoted claim name at least one of these identifiers?

    Used only when SCORING, and only by the location-strict variant, where the
    identifiers are the miner's `shared_identifiers` for the case -- the ones the fixing
    commit and the drifted prose have in common. That is evidence about the label, so it
    may reach a scorer and must never reach a prompt. Nothing in this module's other
    functions touches it.

    A plain word-boundary search rather than `literal_spans`, and that is the whole
    subtlety here: the judge is asked to quote the claim verbatim and frequently quotes it
    with the backticks stripped, so requiring marked-up text would score a correctly
    located claim as unlocated. Matching bare words is the looser test, which is the right
    direction -- this exists to catch a verdict about a DIFFERENT part of the page, and it
    should not also fail on formatting.
    """
    if not claim:
        return False
    for identifier in identifiers:
        if not identifier:
            continue
        if re.search(rf"(?<![\w.]){re.escape(identifier)}(?![\w])", claim):
            return True
    return False
