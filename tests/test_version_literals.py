"""What counts as a version literal, and what a withdrawn one is worth.

Every string in this file was taken from one of the ten hand-judged shape-B cases
whose only evidence was a `ver:` token -- cases that scored 0/10 where the rest of
the arm scored 44%. Reading them is what produced both fixes below; no test written
from the design would have found either, because the design was not wrong about what
a version is. The regex was.
"""

from __future__ import annotations

import pytest

from driftwood.mining import identifiers as I
from driftwood.mining.labels import MineConfig


def vers(text: str) -> set[str]:
    return I.extract_versions(text)


class TestNotEveryDottedNumberIsAVersion:
    """The corpus supplied these. All three were mined as withdrawn claims."""

    @pytest.mark.parametrize(
        "text",
        [
            'boundary=127.0.0.1.502.21746.1321131593.786.1',  # a MIME boundary
            '"origin": "179.13.100.4",',  # an IP in example output
            '"Host": "127.0.0.1:7077",',  # localhost, with a port
            'see 1.2.3.4 for the quad',  # four components
        ],
    )
    def test_addresses_and_boundaries_are_not_versions(self, text: str):
        assert vers(text) == set()

    def test_a_dotted_quad_does_not_match_via_its_own_prefix(self):
        """The component cap alone is not enough, and this is the subtle half.

        `127.0.0.1` has four components, but `127.0.0` has three -- so a pattern that
        only caps the count still matches the prefix and yields `ver:127.0.0`. The
        trailing `(?!\\.?\\d)` is what actually rejects it.
        """
        assert "ver:127.0.0" not in vers('"Host": "127.0.0.1"')

    def test_a_version_glued_to_a_word_is_not_extracted(self):
        assert vers("x1.2 glued") == set()


class TestALeadingVDoesNotTruncateTheVersion:
    def test_the_v_is_absorbed_not_skipped(self):
        assert vers("available is  v0.5.0.") == {"ver:0.5.0"}

    def test_two_versions_that_used_to_collide_are_now_distinct(self):
        """The reason this matters more than the cosmetics of `v`.

        `\\b` does not fire between `v` and `0`, so the old pattern started matching
        at the second component: `v1.0.0` and `v2.0.0` both produced `ver:0.0`. A doc
        corrected from one to the other therefore withdrew nothing and added nothing,
        and registered as no change at all -- a false negative manufactured by the
        tokeniser, which is this module's recurring bug.
        """
        one, two = vers("reached v1.0.0."), vers("reached v2.0.0.")
        assert one == {"ver:1.0.0"}
        assert two == {"ver:2.0.0"}
        assert one != two  # the point: these must not be the same token

    def test_prefixed_and_bare_spellings_are_one_token(self):
        """`v1.0.0` -> `1.0.0` is a reformat, not a retracted claim."""
        assert vers("v1.0.0") == vers("1.0.0")


class TestRealVersionsStillMatch:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("HTTPX requires Python 3.6+", {"ver:3.6"}),
            ("supports Python 2.6-2.7 & 3.3-3.5", {"ver:2.6", "ver:2.7", "ver:3.3", "ver:3.5"}),
            ("a version of FastAPI before 0.106.0 used", {"ver:0.106.0"}),
            ("requests 2.31.0", {"ver:2.31.0"}),
            ("1.0.0rc1", {"ver:1.0.0rc1"}),
            ("1.0.0.post1", {"ver:1.0.0.post1"}),
            ("* PyPy-c 1.7", {"ver:1.7"}),
            ("released 2023.11.0", {"ver:2023.11.0"}),  # calendar versioning
        ],
    )
    def test_extracted(self, text: str, expected: set[str]):
        assert vers(text) == expected

    def test_an_incidental_version_in_example_output_still_matches(self):
        """Not a bug, and deliberately left alone.

        `python-requests/0.13.1` in a `User-Agent` header is a well-formed version
        literal that happens not to be a claim about anything. The regex cannot tell;
        only the arm it appears in can. That is what
        `require_symbol_beyond_version` is for, and keeping the two concerns apart is
        why the regex fix does not try to guess intent.
        """
        assert vers("'User-Agent': 'python-requests/0.13.1'") == {"ver:0.13.1"}


class TestRequireSymbolBeyondVersion:
    """The filter, at the level it actually operates: the withdrawn-token list."""

    def keep(self, tokens: list[str], *, on: bool) -> bool:
        cfg = MineConfig(require_symbol_beyond_version=on)
        return not (
            cfg.require_symbol_beyond_version
            and not any(not t.startswith("ver:") for t in tokens)
        )

    def test_off_by_default(self):
        assert MineConfig().require_symbol_beyond_version is False

    def test_version_only_evidence_is_dropped_when_on(self):
        assert self.keep(["ver:0.13.1"], on=True) is False
        assert self.keep(["ver:1.4", "ver:1.5"], on=True) is False

    def test_the_same_case_survives_when_off(self):
        assert self.keep(["ver:0.13.1"], on=True) != self.keep(["ver:0.13.1"], on=False)
        assert self.keep(["ver:0.13.1"], on=False) is True

    def test_one_real_symbol_is_enough_to_keep_it(self):
        assert self.keep(["ver:3.6", "timeout"], on=True) is True

    def test_no_withdrawn_tokens_at_all_is_also_dropped(self):
        """Reachable only with --no-require-removed-identifier, and consistent:
        no tokens means no symbol."""
        assert self.keep([], on=True) is False
