"""Stage 3: does a document make a false claim about the code, judged at one commit.

Stages 1 and 2 built ground truth and found the code a document talks about. This
stage answers the question the project is actually named after, and it is scored
against labels that already exist: 125 verdicts Julie wrote by hand across six
review sheets.

The target is deliberately *not* the five verdict classes. Three of the five are
defined in terms of the correcting commit rather than the state being judged, so a
judge that sees only the parent state cannot separate them even in principle. See
`cases.FALSE_AT_PARENT` for the mapping and why `new` is a negative.

Nothing here calls a model at import time, and the whole harness runs with no
credentials: the floors and the stub judges are the parts that make a real judge's
number mean anything, and they are free.
"""

from __future__ import annotations

# Sonnet 5 rather than the cheapest or the strongest. The eval is re-run often
# enough that Opus is wasteful for iteration, and a judge that fails on Haiku
# leaves "would a better model fix it" unanswered -- which is the question this
# stage exists to settle with a measurement rather than an assumption. Overridable.
DEFAULT_JUDGE_MODEL = "claude-sonnet-5"

__all__ = ["DEFAULT_JUDGE_MODEL"]
