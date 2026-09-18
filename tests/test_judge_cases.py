"""The join between hand-written verdicts and mined records.

Most of these test a way the eval could be wrong about its own denominator while
every number it prints still computes. That class of bug does not raise, so it has
to be pinned rather than caught.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftwood.judge.cases import (
    FALSE_AT_PARENT,
    JudgeCase,
    class_balance,
    format_case_report,
    load_cases,
    parse_verdicts,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _record(example_id: str, **overrides) -> dict:
    base = {
        "example_id": example_id,
        "repo": "pallets/flask",
        "label": "drift",
        "label_basis": "doc_only_commit_modified_existing_prose",
        "shape": "B",
        "doc_path": "docs/config.rst",
        "code_path": None,
        "at_sha": "a" * 40,
        "fix_sha": "b" * 40,
        "parent_sha": "a" * 40,
        "committed_at": 1780234504,
        "subject": "Tidy the config docs",
        "shared_identifiers": [],
    }
    base.update(overrides)
    return base


def _sheet(*cases: tuple[str, str | None]) -> str:
    """A review sheet, including the legend every real sheet carries."""
    out = [
        "# Drift label review — cases",
        "",
        "For each case, replace `VERDICT: ?` with one of:",
        "",
        "- `drift` — the doc said something untrue about the code",
        "- `new` — the doc was documenting something that did not exist yet",
        "- `cosmetic` — wording, formatting or a link",
        "- `unrelated` — not about the same thing",
        "- `unclear` — cannot tell from these diffs alone",
        "",
        "---",
        "",
    ]
    for index, (example_id, verdict) in enumerate(cases, start=1):
        out.append(f"## Case {index} — `{example_id}`")
        out.append("")
        out.append("- **repo** `pallets/flask` · **shape** B")
        out.append("")
        out.append(f"**VERDICT: `{verdict}`**" if verdict else "**VERDICT: `?`**")
        out.append("")
        out.append("---")
        out.append("")
    return "\n".join(out)


@pytest.fixture
def corpus(tmp_path: Path):
    """A review dir and a data dir that resolve against each other."""
    review = tmp_path / "review"
    data = tmp_path / "data"
    review.mkdir()
    data.mkdir()
    return review, data


class TestTheProspectiveTargetMapping:
    """`new` is a negative, and that is the single most load-bearing constant here."""

    def test_new_is_not_false_at_parent(self):
        # The legend's wording invites the opposite reading. Both sampled cases are
        # "Added support for X" -- feature and docs in one commit -- so at the
        # parent neither existed and nothing was false. Flipping this would
        # mislabel 10 of 105 cases and penalise a judge for being right.
        assert FALSE_AT_PARENT["new"] is False

    def test_only_drift_is_positive(self):
        positives = [v for v, t in FALSE_AT_PARENT.items() if t is True]
        assert positives == ["drift"]

    def test_unclear_is_held_out_rather_than_a_class(self):
        assert FALSE_AT_PARENT["unclear"] is None

    def test_a_case_knows_whether_it_can_be_scored(self):
        def case(verdict):
            return JudgeCase(
                example_id="x", repo="r", shape="B", basis="b", doc_path="d",
                code_path=None, at_sha="a", fix_sha="f", subject="s",
                shared_identifiers=(), verdict=verdict, sheet="s.md",
                resolved_from="labels.jsonl",
            )

        assert case("drift").target is True and case("drift").scoreable
        assert case("new").target is False and case("new").scoreable
        assert case("unclear").target is None
        assert not case("unclear").scoreable


class TestParsingASheetAPersonWrote:
    def test_a_verdict_binds_to_its_own_case(self):
        # The off-by-one that matters: an unlabelled case in the middle must not
        # shift every later verdict up by one. Shifted labels are worse than
        # missing ones because every downstream number still computes.
        sheet = _sheet(("aaa1", "cosmetic"), ("bbb2", None), ("ccc3", "drift"))
        found = parse_verdicts(sheet)
        assert found == {"aaa1": "cosmetic", "ccc3": "drift"}

    def test_the_legend_is_not_read_as_a_verdict(self):
        # Every real sheet names all five verdicts in prose above the first case and
        # shows the unfilled `VERDICT: ?` placeholder.
        sheet = _sheet(("aaa1", "drift"))
        assert parse_verdicts(sheet) == {"aaa1": "drift"}

    def test_an_unfilled_sheet_yields_nothing(self):
        assert parse_verdicts(_sheet(("aaa1", None), ("bbb2", None))) == {}

    def test_a_verdict_outside_the_vocabulary_is_ignored(self):
        sheet = _sheet(("aaa1", "probably")).replace("`probably`", "`probably`")
        assert parse_verdicts(sheet) == {}

    def test_no_cases_at_all(self):
        assert parse_verdicts("# just a heading\n\nsome prose\n") == {}

    def test_the_real_hex_id_format_parses(self):
        assert parse_verdicts(_sheet(("222912096e5bad9a", "cosmetic"))) == {
            "222912096e5bad9a": "cosmetic"
        }

    def test_an_id_that_is_not_a_hex_digest_still_parses(self):
        # The parser must not encode the id format. If the miner's digest scheme
        # changed, a stricter pattern would return {} and the eval would report zero
        # cases with nothing raising; an unrecognised id should instead reach the
        # join and be counted there as unresolvable.
        assert parse_verdicts(_sheet(("not-a-digest", "drift"))) == {
            "not-a-digest": "drift"
        }


class TestResolvingAgainstTheMinedRecords:
    def test_a_verdict_with_no_record_is_counted_not_dropped_quietly(self, corpus):
        review, data = corpus
        (review / "b.md").write_text(_sheet(("aaa1", "drift"), ("ghost", "cosmetic")))
        (data / "labels.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")

        cases, tally = load_cases(review, data)

        assert [c.example_id for c in cases] == ["aaa1"]
        assert tally["verdicts"] == 2
        assert tally["unresolvable"] == 1

    def test_every_label_version_is_searched(self, corpus):
        # Three of the real 125 exist only in v3/v4/v5, having been filtered out of
        # every later version. Reading one file finds 122 and looks complete.
        review, data = corpus
        (review / "b.md").write_text(_sheet(("aaa1", "drift"), ("old1", "cosmetic")))
        (data / "labels.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")
        (data / "labels-v3.jsonl").write_text(json.dumps(_record("old1")) + "\n")

        cases, tally = load_cases(review, data)

        assert {c.example_id for c in cases} == {"aaa1", "old1"}
        assert tally.get("unresolvable", 0) == 0
        assert {c.resolved_from for c in cases} == {"labels.jsonl", "labels-v3.jsonl"}

    def test_the_tracked_v1_file_wins_when_several_have_the_case(self, corpus):
        review, data = corpus
        (review / "b.md").write_text(_sheet(("aaa1", "drift")))
        (data / "labels.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")
        (data / "labels-v3.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")

        cases, _ = load_cases(review, data)

        assert cases[0].resolved_from == "labels.jsonl"

    def test_versions_that_disagree_are_counted_rather_than_silently_picked(self, corpus):
        # Mining is deterministic, so a case in two versions should carry identical
        # fields. If it does not, the corpus moved under a judgement and choosing a
        # version quietly would bury that.
        review, data = corpus
        (review / "b.md").write_text(_sheet(("aaa1", "drift")))
        (data / "labels.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")
        (data / "labels-v3.jsonl").write_text(
            json.dumps(_record("aaa1", doc_path="docs/OTHER.rst")) + "\n"
        )

        _, tally = load_cases(review, data)

        assert tally["version_disagreements"] == 1

    def test_the_miners_own_label_disagreeing_is_not_a_disagreement(self, corpus):
        # `label` is the miner's proposed verdict. It moved as the filters changed
        # and is never used -- the ground truth is the sheet's. Counting it would
        # flag most of the corpus.
        review, data = corpus
        (review / "b.md").write_text(_sheet(("aaa1", "drift")))
        (data / "labels.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")
        (data / "labels-v3.jsonl").write_text(
            json.dumps(_record("aaa1", label="cosmetic")) + "\n"
        )

        _, tally = load_cases(review, data)

        assert tally.get("version_disagreements", 0) == 0

    def test_fields_the_judge_needs_survive_the_join(self, corpus):
        review, data = corpus
        (review / "b.md").write_text(_sheet(("aaa1", "drift")))
        (data / "labels.jsonl").write_text(
            json.dumps(
                _record(
                    "aaa1",
                    shape="A",
                    code_path="src/flask/app.py",
                    shared_identifiers=["Flask", "config"],
                )
            )
            + "\n"
        )

        cases, _ = load_cases(review, data)
        case = cases[0]

        assert case.code_path == "src/flask/app.py"
        assert case.at_sha == "a" * 40
        assert case.shared_identifiers == ("Flask", "config")
        assert case.sheet == "b.md"

    def test_the_same_case_judged_twice_is_counted_not_averaged(self, corpus):
        review, data = corpus
        (review / "a.md").write_text(_sheet(("aaa1", "drift")))
        (review / "z.md").write_text(_sheet(("aaa1", "cosmetic")))
        (data / "labels.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")

        cases, tally = load_cases(review, data)

        assert len(cases) == 1
        assert cases[0].verdict == "drift"  # first sheet alphabetically
        assert tally["duplicate_verdicts"] == 1


class TestTheFloorComesFromTheLabels:
    def _cases(self, **counts) -> list[JudgeCase]:
        out = []
        for verdict, n in counts.items():
            for i in range(n):
                out.append(
                    JudgeCase(
                        example_id=f"{verdict}{i}", repo="r", shape="B", basis="b",
                        doc_path="d", code_path=None, at_sha="a", fix_sha="f",
                        subject="s", shared_identifiers=(), verdict=verdict,
                        sheet="s.md", resolved_from="labels.jsonl",
                    )
                )
        return out

    def test_unclear_is_outside_the_denominator(self):
        balance = class_balance(self._cases(drift=3, cosmetic=7, unclear=5))
        assert balance["scoreable"] == 10
        assert balance["held_out_unclear"] == 5

    def test_new_counts_as_a_negative_in_the_floor(self):
        balance = class_balance(self._cases(drift=2, new=8))
        assert balance["negative"] == 8
        assert balance["majority_class"] == "not-false"
        assert balance["majority_accuracy"] == pytest.approx(0.8)

    def test_the_floor_is_the_larger_class(self):
        balance = class_balance(self._cases(drift=30, cosmetic=70))
        assert balance["majority_accuracy"] == pytest.approx(0.7)
        assert balance["positive_rate"] == pytest.approx(0.3)

    def test_no_scoreable_cases_does_not_divide_by_zero(self):
        balance = class_balance(self._cases(unclear=4))
        assert balance["scoreable"] == 0
        assert balance["majority_accuracy"] == 0.0


@pytest.fixture(scope="module")
def real():
    """The actual corpus. Skipped rather than failed if the labels are absent."""
    data = REPO_ROOT / "data"
    if not (data / "labels.jsonl").exists():
        pytest.skip("mined labels not present")
    return load_cases(REPO_ROOT / "review", data)


class TestAgainstTheRealCorpus:
    """Pins the pre-registered numbers, so a corpus change cannot pass unnoticed."""

    def test_every_verdict_resolves_to_a_record(self, real):
        _, tally = real
        assert tally["verdicts"] == 125
        assert tally["cases"] == 125
        assert tally.get("unresolvable", 0) == 0

    def test_no_case_differs_between_the_versions_holding_it(self, real):
        _, tally = real
        assert tally.get("version_disagreements", 0) == 0

    def test_the_preregistered_balance_holds(self, real):
        cases, _ = real
        balance = class_balance(cases)
        assert balance["scoreable"] == 105
        assert balance["positive"] == 30
        assert balance["negative"] == 75
        assert balance["majority_accuracy"] == pytest.approx(0.714, abs=0.001)

    def test_shape_b_has_no_code_side_at_all(self, real):
        # The reason retrieval is load-bearing in stage 3 rather than optional.
        cases, _ = real
        assert all(c.code_path for c in cases if c.shape == "A")
        assert not any(c.code_path for c in cases if c.shape == "B")

    def test_the_report_states_the_floor_and_the_holdout(self, real):
        cases, tally = real
        report = format_case_report(cases, tally)
        assert "71.4% accuracy" in report
        assert "F1 0.00" in report
        assert "held out 20" in report
