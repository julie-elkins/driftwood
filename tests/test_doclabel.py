"""Tests for the stage 2c hand-labelling harness.

The sheet round-trip is the thing under test. Everything downstream -- the rankers,
the floor, the macro-averaging -- is already covered; what is new here is a Markdown
file a person edits by hand, which means the parser will meet blank boxes, reordered
lines, deleted candidates and paths typed by hand. A parser that silently loses a
judgement would cost an hour of work and report a clean number anyway.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from driftwood.mining.gitio import local_name_for
from driftwood.retrieval import doclabel
from driftwood.retrieval.doclabel import (
    DocCase,
    SheetSpec,
    eligible_docs,
    parse_sheet,
    render_sheet,
    sample_cases,
    splits_from_sheet,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A tiny real repository. The sampler shells out to git, so a stub would test
    the stub."""
    work = tmp_path / "work"
    work.mkdir()
    _git(work.parent, "init", "-q", "work")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    (work / "src").mkdir()
    (work / "docs").mkdir()
    for name in ("alpha", "beta", "gamma"):
        (work / "src" / f"{name}.py").write_text(f"def {name}():\n    return 1\n")
        (work / "docs" / f"{name}.md").write_text(f"# {name}\n\n" + "prose. " * 200)
    (work / "docs" / "stub.md").write_text("# too short\n")
    _git(work, "add", "src", "docs")
    _git(work, "commit", "-qm", "init")
    return work


class TestEligibility:
    def test_a_doc_too_short_to_assert_anything_is_not_a_case(self):
        texts = {"docs/a.md": "x" * 500, "docs/b.md": "short"}
        assert eligible_docs(list(texts), texts) == ["docs/a.md"]

    def test_process_docs_are_excluded_here_not_in_the_classifier(self):
        """A PR template makes no claim about a module, but `classify` calls it a DOC.

        Excluded in the sampler rather than in `classify` on purpose: the classifier
        decides what the miner produces, so changing it would move the mined corpus
        and make every label file already on disk incomparable with the next one. A
        review sheet must not be able to do that as a side effect.
        """
        texts = {
            ".github/PULL_REQUEST_TEMPLATE.md": "x" * 900,
            "docs/real.md": "x" * 900,
        }
        assert eligible_docs(list(texts), texts) == ["docs/real.md"]


class TestSampling:
    def test_the_pool_is_code_and_the_cases_are_docs(self, repo: Path):
        spec = sample_cases("t/t", repo, per_repo=2, seed=1)
        assert len(spec.cases) == 2
        assert all(c.doc_path.startswith("docs/") for c in spec.cases)
        assert spec.cases[0].pool == (
            "src/alpha.py",
            "src/beta.py",
            "src/gamma.py",
        )

    def test_the_same_seed_gives_the_same_sample(self, repo: Path):
        first = sample_cases("t/t", repo, per_repo=2, seed=7)
        second = sample_cases("t/t", repo, per_repo=2, seed=7)
        assert [c.doc_path for c in first.cases] == [c.doc_path for c in second.cases]

    def test_a_larger_sample_contains_the_smaller_one(self, repo: Path):
        """The nesting property, which is why the draw is a shuffled prefix.

        A sheet gets extended when too many sampled docs turn out to make no claim
        about any module. If extending redrew the sample, judgements already made
        would fall outside it -- so the work would either be discarded or the old
        sheet kept for reasons that have nothing to do with the measurement.
        """
        small = {c.doc_path for c in sample_cases("t/t", repo, 1, seed=3).cases}
        large = {c.doc_path for c in sample_cases("t/t", repo, 3, seed=3).cases}
        assert small < large

    def test_asking_for_more_docs_than_exist_is_not_an_error(self, repo: Path):
        spec = sample_cases("t/t", repo, per_repo=99, seed=1)
        assert len(spec.cases) == 3  # the three long docs; the stub is ineligible

    def test_the_short_doc_never_enters_the_sample(self, repo: Path):
        spec = sample_cases("t/t", repo, per_repo=99, seed=1)
        assert "docs/stub.md" not in {c.doc_path for c in spec.cases}


def _spec() -> SheetSpec:
    pool = ("src/alpha.py", "src/beta.py")
    return SheetSpec(
        repo="t/t",
        sha="abc123def4567",
        cases=(
            DocCase("t/t", "abc123def4567", "docs/alpha.md", 900, pool),
            DocCase("t/t", "abc123def4567", "docs/beta.md", 900, pool),
        ),
    )


class TestTheSheetIsHandedOverEmpty:
    def test_no_box_is_ticked(self):
        """The whole corpus is worthless if anything pre-fills it.

        A sheet arriving with plausible boxes already ticked is not a time-saver: a
        reviewer confirms an anchor far more readily than they generate an answer, and
        if the anchor came from a ranker the ranker is then graded on its own output.
        """
        sheet = render_sheet([_spec()], Path("review/2c"), seed=5)
        # Asserted through the parser rather than by grepping for `- [x]`: the header
        # shows a ticked box as an inline example of the syntax, so a raw substring
        # check would fail on the instructions. What has to be empty is what the parser
        # can read, which is exactly what this asks.
        assert all(not case.answered for case in parse_sheet(sheet))
        assert not any(case.marked for case in parse_sheet(sheet))
        assert "**NONE:** [ ]" in sheet

    def test_every_pool_file_appears_under_every_case(self):
        sheet = render_sheet([_spec()], Path("review/2c"), seed=5)
        assert sheet.count("- [ ] src/alpha.py") == 2
        assert sheet.count("- [ ] src/beta.py") == 2

    def test_the_seed_and_the_tree_are_on_the_sheet(self):
        sheet = render_sheet([_spec()], Path("review/2c"), seed=5)
        assert "seed 5" in sheet
        assert "abc123def456" in sheet


class TestParsingWhatAPersonActuallyWrote:
    def _filled(self) -> str:
        sheet = render_sheet([_spec()], Path("review/2c"), seed=5)
        # Case 1: one box ticked, uppercase X, plus a hand-typed extra path.
        sheet = sheet.replace("- [ ] src/alpha.py", "- [X] src/alpha.py", 1)
        return sheet.replace("**EXTRA:**", "**EXTRA:** src/gamma.py", 1)

    def test_a_ticked_box_is_read_whatever_its_case(self):
        cases = parse_sheet(self._filled())
        assert cases[0].marked == ["src/alpha.py"]

    def test_a_hand_typed_path_is_read_from_the_extra_line(self):
        cases = parse_sheet(self._filled())
        assert cases[0].extra == ["src/gamma.py"]

    def test_marks_do_not_leak_between_cases(self):
        """Case blocks are split on their headings, not scanned as one document.

        Worth a test because the failure is invisible: every case would inherit the
        previous one's answers, scores would rise, and the sheet would look filled in.
        """
        cases = parse_sheet(self._filled())
        assert cases[1].marked == []
        assert cases[1].extra == []

    def test_an_untouched_case_is_a_skip_and_not_an_answer_of_nothing(self):
        cases = parse_sheet(render_sheet([_spec()], Path("review/2c"), seed=5))
        assert [c.answered for c in cases] == [False, False]

    def test_an_explicit_none_is_an_answer(self):
        sheet = render_sheet([_spec()], Path("review/2c"), seed=5)
        sheet = sheet.replace("**NONE:** [ ]", "**NONE:** [x]", 1)
        cases = parse_sheet(sheet)
        assert cases[0].answered is True
        assert cases[0].marked == []
        assert cases[1].answered is False

    def test_a_reviewer_may_delete_candidate_lines_instead_of_leaving_them(self):
        """Some people tidy. Deleting the unticked lines must not change the answer."""
        sheet = self._filled()
        kept = [
            line
            for line in sheet.splitlines()
            if not line.startswith("- [ ] ")
        ]
        cases = parse_sheet("\n".join(kept))
        assert cases[0].marked == ["src/alpha.py"]
        assert cases[1].answered is False


class TestScoringTheFilledSheet:
    def test_a_skipped_case_contributes_no_query(self, repo: Path, tmp_path: Path):
        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        sha = _git(repo, "rev-parse", "--short=12", "HEAD").strip()
        cases = parse_sheet(
            f"## Case 1 — `t/t` · `docs/alpha.md`\n"
            f"- **tree** `{sha}`\n"
            f"- [x] src/alpha.py\n"
            f"\n"
            f"## Case 2 — `t/t` · `docs/beta.md`\n"
            f"- **tree** `{sha}`\n"
            f"- [ ] src/alpha.py\n"
        )
        splits, tally = splits_from_sheet(cases, root)
        assert tally["skipped"] == 1
        assert tally["queries"] == 1
        assert [q.doc_path for q in splits[0].queries] == ["docs/alpha.md"]

    def test_a_none_case_is_answered_but_is_not_a_query(self, repo: Path, tmp_path: Path):
        """A doc that makes no claim about any module has no correct retrieval result.

        Scoring it would add a query every ranker necessarily loses, dragging recall
        down by an amount set by how many such docs the sample happened to draw -- a
        number about the corpus reported as a number about the rankers.
        """
        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        cases = parse_sheet(
            "## Case 1 — `t/t` · `docs/alpha.md`\n"
            "- [ ] src/alpha.py\n"
            "\n**NONE:** [x]\n"
        )
        splits, tally = splits_from_sheet(cases, root)
        assert tally["answered"] == 1
        assert tally["none"] == 1
        assert tally["queries"] == 0
        assert splits == []

    def test_a_path_not_in_the_tree_is_dropped_and_counted(self, repo: Path, tmp_path: Path):
        """A typo on the EXTRA line must not silently cap recall at less than one.

        An unreachable relevant path is a positive no ranker can return, so recall for
        that query tops out below 1.0 for a reason nothing in the table mentions.
        """
        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        cases = parse_sheet(
            "## Case 1 — `t/t` · `docs/alpha.md`\n"
            "- [x] src/alpha.py\n"
            "\n**EXTRA:** src/typo.py\n"
        )
        splits, tally = splits_from_sheet(cases, root)
        assert tally["unknown_paths"] == 1
        assert splits[0].queries[0].relevant == frozenset({"src/alpha.py"})

    def test_every_query_carries_empty_evidence_so_ablation_is_a_no_op(
        self, repo: Path, tmp_path: Path
    ):
        """No mining rule chose these pairs, so there are no evidence tokens to strike.

        Pinned rather than assumed because `evaluate_split` always runs an ablated arm:
        if `evidence` were ever populated here, the 2c table would grow a row that
        looked like a circularity bound on labels that have no circularity channel.
        """
        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        cases = parse_sheet(
            "## Case 1 — `t/t` · `docs/alpha.md`\n- [x] src/alpha.py\n"
        )
        splits, _ = splits_from_sheet(cases, root)
        assert splits[0].queries[0].evidence == frozenset()


class TestTheRecordedTreeIsTheTreeScored:
    def test_a_judgement_is_scored_at_the_sha_the_sheet_pinned(
        self, repo: Path, tmp_path: Path
    ):
        """Not at the clone's current HEAD, which moves when a repo is re-fetched.

        Constructed as the failure it prevents: the labelled file is renamed in a later
        commit, so scoring at HEAD would drop the positive and cap that query's recall
        at zero while reporting nothing unusual. Both projects in this corpus really did
        move to a `src/` layout inside the mining window, so this is the observed shape
        of the problem rather than a hypothetical one.
        """
        old_sha = _git(repo, "rev-parse", "--short=12", "HEAD").strip()
        _git(repo, "mv", "src/alpha.py", "src/renamed.py")
        _git(repo, "commit", "-qm", "move it")

        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        cases = parse_sheet(
            f"## Case 1 — `t/t` · `docs/alpha.md`\n"
            f"- **tree** `{old_sha}`\n"
            f"- [x] src/alpha.py\n"
        )
        splits, tally = splits_from_sheet(cases, root)
        assert tally["unknown_paths"] == 0
        assert splits[0].queries[0].relevant == frozenset({"src/alpha.py"})
        assert splits[0].queries[0].at_sha.startswith(old_sha)

    def test_an_unresolvable_tree_drops_the_case_rather_than_falling_back_to_head(
        self, repo: Path, tmp_path: Path
    ):
        """Recovery by re-pointing at HEAD would be worse than dropping the case.

        It would produce a plausible score from a judgement scored against a tree it
        was not made on, and nothing downstream would look wrong. A dropped case shows
        up as a gap between `answered` and `queries`, which is visible.
        """
        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        cases = parse_sheet(
            "## Case 1 — `t/t` · `docs/alpha.md`\n"
            "- **tree** `deadbeefcafe`\n"
            "- [x] src/alpha.py\n"
        )
        splits, tally = splits_from_sheet(cases, root)
        assert tally["unresolved"] == 1
        assert tally["answered"] == 1
        assert tally["queries"] == 0

    def test_a_case_with_its_tree_line_deleted_is_counted_not_hidden(
        self, repo: Path, tmp_path: Path
    ):
        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        cases = parse_sheet(
            "## Case 1 — `t/t` · `docs/alpha.md`\n- [x] src/alpha.py\n"
        )
        _, tally = splits_from_sheet(cases, root)
        assert tally["unpinned"] == 1


class TestTheBundleIsSelfContained:
    def test_the_docs_and_the_whole_pool_are_written_out(self, repo: Path, tmp_path: Path):
        """The clones are bare, so a reviewer has no working tree to open.

        The pool is written as well as the docs because "does this document make a
        claim about this module" is usually not answerable from the document alone.
        """
        root = tmp_path / "clones"
        root.mkdir()
        (root / local_name_for("t/t")).symlink_to(repo)
        bundle = tmp_path / "2c"
        sheet = doclabel.write_bundle(
            [sample_cases("t/t", repo, per_repo=2, seed=1)], bundle, 1, root
        )
        assert sheet.exists()
        code = sorted(p.name for p in (bundle / "text" / "t-t" / "code").iterdir())
        assert code == ["src-alpha.py", "src-beta.py", "src-gamma.py"]
        assert len(list((bundle / "text" / "t-t" / "doc").iterdir())) == 2
