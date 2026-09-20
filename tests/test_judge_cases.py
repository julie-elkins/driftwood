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
    FROZEN_NAME,
    JudgeCase,
    class_balance,
    format_case_report,
    freeze_records,
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
        # mislabel 19 of 130 cases and penalise a judge for being right.
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
        # 79 of the real 125 exist only in gitignored versions, having been filtered
        # out of `labels.jsonl`. Reading one file finds 46 and prints a warning.
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


class TestTheCorpusIsSelfContained:
    """The test that was missing, and the bug it would have caught.

    79 of the 125 verdicts joined only to `labels-v3` and `labels-v10`, both
    gitignored as derived data. A clean checkout rebuilt 46 cases, reported a
    different class balance and a different floor, and raised nothing -- it printed one
    warning and then computed every number correctly against the wrong corpus. The
    machine that wrote the pre-registration could not see it, because that machine had
    all the versions.
    """

    def test_the_frozen_file_alone_rebuilds_every_case(self, tmp_path):
        source = REPO_ROOT / "data" / FROZEN_NAME
        if not source.exists():
            pytest.skip("frozen join table not present")
        lonely = tmp_path / "data"
        lonely.mkdir()
        (lonely / FROZEN_NAME).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        cases, tally = load_cases(REPO_ROOT / "review", lonely)

        assert tally["verdicts"] == 150
        assert tally["cases"] == 150, (
            "a checkout with only the tracked files must rebuild the whole corpus"
        )
        assert tally.get("unresolvable", 0) == 0
        assert class_balance(cases)["scoreable"] == 130

    def test_the_frozen_file_is_the_preferred_source_everywhere(self, real):
        # So `resolved_from` is identical on a machine holding every mined version and
        # on a clean checkout holding none. Otherwise the provenance block in the
        # results JSON differs by machine, and two people comparing results are
        # comparing their checkouts.
        cases, tally = real
        if not (REPO_ROOT / "data" / FROZEN_NAME).exists():
            pytest.skip("frozen join table not present")
        assert {c.resolved_from for c in cases} == {FROZEN_NAME}
        assert tally["from_ignored_versions"] == 0

    def test_each_frozen_record_remembers_which_mine_produced_it(self):
        path = REPO_ROOT / "data" / FROZEN_NAME
        if not path.exists():
            pytest.skip("frozen join table not present")
        sources = {
            json.loads(line)["frozen_from"]
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        # Freezing must not erase provenance: which mining run produced a case is the
        # field needed to explain it, and a naive concatenation drops exactly that.
        assert sources == {"labels.jsonl", "labels-v3.jsonl", "labels-v10.jsonl"}

    def test_freezing_is_idempotent(self, tmp_path):
        source = REPO_ROOT / "data" / FROZEN_NAME
        if not source.exists():
            pytest.skip("frozen join table not present")
        data = tmp_path / "data"
        data.mkdir()
        (data / FROZEN_NAME).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        out = tmp_path / "again.jsonl"

        written, unresolvable = freeze_records(REPO_ROOT / "review", data, out)

        assert (written, unresolvable) == (150, 0)
        assert out.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")

    def test_a_verdict_resolving_nowhere_is_reported_as_a_failure(self, tmp_path):
        # A freeze that quietly omits a case is worse than no freeze: it would make
        # the gap permanent and invisible on every machine.
        review = tmp_path / "review"
        data = tmp_path / "data"
        review.mkdir()
        data.mkdir()
        (review / "b.md").write_text(_sheet(("aaa1", "drift"), ("ghost", "cosmetic")))
        (data / "labels.jsonl").write_text(json.dumps(_record("aaa1")) + "\n")

        written, unresolvable = freeze_records(review, data, tmp_path / "out.jsonl")

        assert (written, unresolvable) == (1, 1)


class TestAgainstTheRealCorpus:
    """Pins the corpus, so a change to it cannot pass unnoticed.

    These fired as seven failures the moment `review/batch.md` was filled in, which is
    the control working: the sheets are globbed, so the corpus grows whenever one is
    labelled, and every stage-3 number is measured against a denominator that just
    moved. Updating the literal is the *last* step of absorbing a new batch, not the
    first -- `driftwood judge-freeze` comes before it, or a clean checkout rebuilds the
    old corpus and these keep passing while the real one has grown.

    **Only the 125-case numbers were pre-registered.** `review/batch.md` added 25 shape-A
    cases with no prediction recorded beforehand, so the 150/130 literals below are a pin
    on an observed corpus and not a prediction that survived. Noted here rather than
    smoothed over, because the class used to say "pre-registered" about all of it.
    """

    def test_every_verdict_resolves_to_a_record(self, real):
        _, tally = real
        assert tally["verdicts"] == 150
        assert tally["cases"] == 150
        assert tally.get("unresolvable", 0) == 0

    def test_no_case_differs_between_the_versions_holding_it(self, real):
        _, tally = real
        assert tally.get("version_disagreements", 0) == 0

    def test_the_class_balance_holds(self, real):
        # Batch 01's 30/75 WAS pre-registered and held. The 25 cases in `review/batch.md`
        # were not predicted, and they came in at 4 positive / 21 negative -- 16% against
        # the established 28.6%. That gap is not readable at n=25 (1.4 sd on a binomial
        # at p=0.286), so it is recorded, not interpreted.
        cases, _ = real
        balance = class_balance(cases)
        assert balance["scoreable"] == 130
        assert balance["positive"] == 34
        assert balance["negative"] == 96
        assert balance["majority_accuracy"] == pytest.approx(0.738, abs=0.001)

    def test_the_new_batch_held_out_nothing_and_that_has_a_mechanism(self, real):
        # Batch 01 held out 20 of 125 as `unclear` (16%); `review/batch.md` held out 0 of
        # 25. Under a binomial at p=0.16 that is p≈0.013, which would be suspicious if it
        # had no mechanism -- and it has one: all 25 are shape A, so the reviewer had a
        # code file to read. Shape B is doc-only and every `unclear` in the corpus comes
        # from a shape-B sheet. Asserted so that a future all-shape-A batch producing
        # `unclear` cases is a finding rather than a shrug.
        cases, _ = real
        unclear = [c for c in cases if c.verdict == "unclear"]
        assert len(unclear) == 20
        assert all(c.code_path is None for c in unclear)

    def test_shape_b_has_no_code_side_at_all(self, real):
        # The reason retrieval is load-bearing in stage 3 rather than optional.
        cases, _ = real
        assert all(c.code_path for c in cases if c.shape == "A")
        assert not any(c.code_path for c in cases if c.shape == "B")

    def test_the_report_states_the_floor_and_the_holdout(self, real):
        cases, tally = real
        report = format_case_report(cases, tally)
        assert "73.8% accuracy" in report
        assert "F1 0.00" in report
        assert "held out 20" in report
