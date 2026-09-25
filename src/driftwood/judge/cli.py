"""The `driftwood judge-cases` and `driftwood judge-eval` subcommands.

Registered from the top-level parser the same way stage 2 is, and for the same
reason: the mining package is the ground truth everything else is graded against, so
it does not import the things grading it.

Two commands rather than one, because the useful thing to do first costs nothing.
`judge-cases` prints what the eval is about to be run on -- the class balance, the
floors, the shape split -- and touches neither a clone nor a model. Reading that
before spending anything is the whole point of having built the floors first.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from . import DEFAULT_JUDGE_MODEL
from .cases import (
    FROZEN_NAME,
    class_balance,
    format_case_report,
    freeze_records,
    load_cases,
)
from .context import (
    ARMS,
    CODE_BUDGET,
    DEFAULT_K,
    DOC_BUDGET,
    ContextBuilder,
    render,
    render_claim_batch,
)
from .evaluate import (
    dump_json,
    estimate_spend,
    format_results,
    format_spend,
    measured_spend,
    noise_range,
    restrict_to_located,
    to_json,
)
from .claims import DEFAULT_BATCH, batch as claim_batch, claim_units
from .judge import (
    CLAIM_SYSTEM_PROMPT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_TOKENS,
    PAID_PREFIXES,
    SYSTEM_PROMPT,
    AlwaysJudge,
    AnthropicJudge,
    LexicalJudge,
    PerClaimJudge,
    is_paid,
)
from .nullrun import (
    DEFAULT_TRIALS,
    format_null_run,
    null_run_json,
    summarise_trial,
    trial_cache,
)

__all__ = ["add_parser"]

# Every judge that needs no key and no network. The default, so that `judge-eval`
# with no flags produces the half of the result that is free -- and so that a missing
# key is a smaller command rather than an error.
FREE_JUDGES = ("always-not-false", "always-false", "lexical-absence")

# `floors` names all three at once. A group value rather than three words, for two
# reasons. It is the vocabulary the reports and the README already use, so the flag
# reads the way the result does. And the alternative is a 150-character command line,
# which wraps in a terminal and silently truncates when pasted -- the failure that
# produced `--out` with no argument followed by a stray path being run as a command.
JUDGE_GROUPS = {"floors": FREE_JUDGES}
JUDGE_CHOICES = ("floors", "model", "per-claim", *FREE_JUDGES)

# `PAID_PREFIXES` and the predicate over it moved to `judge.py`, next to the classes whose
# names they match, once stage 4 needed the complementary question -- which judges cannot
# vary between two identical runs. Re-exported here under the name this module's callers
# and tests already use, rather than copied: one prefix list, two readers.
_is_paid = is_paid


def _judge_arg(value: str) -> str:
    """Validate one `--judges` word, accepting the form the REPORTS print.

    `choices=` cannot do this job. The reports and the score files name the paid judge
    `model:claude-sonnet-5`, because a judge whose model is not in its name cannot be
    compared across runs -- and that string is then the obvious thing to paste back into
    a command line, where `choices=` rejected it with a list that does not explain the
    difference. A whole probe was typed, run and lost that way: argparse exited before
    the preflight, so it looked exactly like a run that had happened.

    So `model:<id>` is accepted and means `--judges model --model <id>`. Same trap as the
    error message in `8a25e79` that named a flag which did not exist.
    """
    if value in JUDGE_CHOICES:
        return value
    for prefix in ("model:", "per-claim:"):
        if value.startswith(prefix):
            model = value.split(":", 1)[1]
            if not model:
                raise argparse.ArgumentTypeError(
                    f"`{prefix}` needs an id after the colon, e.g. "
                    f"`{prefix}claude-sonnet-5`"
                )
            return value
    raise argparse.ArgumentTypeError(
        f"invalid judge {value!r}. Choose from {', '.join(JUDGE_CHOICES)}, or name the "
        f"model inline as `model:<id>` the way the reports print it"
    )


def _expand_groups(names) -> set[str]:
    """`--judges floors model` -> the four judge names it stands for."""
    out: set[str] = set()
    for name in names:
        if name in JUDGE_GROUPS:
            out.update(JUDGE_GROUPS[name])
        elif name.startswith("per-claim"):
            out.add("per-claim")
        elif name.startswith("model:"):
            out.add("model")
        else:
            out.add(name)
    return out


def _model_from_judges(names, fallback: str) -> str:
    """The model id an inline `model:<id>` names, else `--model`.

    Refuses two different inline ids rather than picking one: a run whose score file says
    one model and whose cache keys say another is unreadable later, and that is the whole
    reason the model is in the judge's name.
    """
    inline = {
        n.split(":", 1)[1]
        for n in names
        if n.startswith(("model:", "per-claim:"))
    }
    if len(inline) > 1:
        raise SystemExit(
            f"--judges names more than one model inline: {sorted(inline)}. "
            "Run them as separate scores; one score file describes one model."
        )
    return inline.pop() if inline else fallback


def _expand_only_cases(values) -> set[str]:
    """`--only-cases a b @ids.txt` -> the set of `example_id`s it names.

    `@path` reads ids from a file, one per line, `#` comments and blanks ignored. That
    exists because the useful selections come out of a diagnostic script -- the nine
    recall-costing cases, say -- and retyping nine sha-shaped ids by hand is how one of
    them silently becomes a different case.
    """
    out: set[str] = set()
    for value in values:
        if not value.startswith("@"):
            out.add(value)
            continue
        for line in Path(value[1:]).read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                out.add(line)
    return out


def _cmd_cases(args: argparse.Namespace) -> int:
    cases, tally = load_cases(args.review, args.data)
    print(format_case_report(cases, tally))
    return 0


def _cmd_freeze(args: argparse.Namespace) -> int:
    out = args.out or (args.data / FROZEN_NAME)
    written, unresolvable = freeze_records(args.review, args.data, out)
    print(f"wrote {written} record(s) to {out}")
    if unresolvable:
        print(
            f"WARNING: {unresolvable} verdict(s) resolved against nothing on this "
            "machine and are NOT in the freeze -- they will be missing from every "
            "checkout, including this one",
            file=sys.stderr,
        )
        return 1
    return 0


def _build_judges(
    args: argparse.Namespace, *, cache: Path | None = None
) -> dict[str, object]:
    """The judges `--judges` names. `cache` overrides where replies are read and written.

    The override exists for stage 4 and for nothing else. A null run has to give every
    trial a cache directory of its own -- otherwise trial 2 is served trial 1's reply and
    reports a run-to-run width of zero from a run that made no calls -- and the judges are
    otherwise identical between trials, so rebuilding them per trial with a different
    directory is the whole of the difference. `None` means `args.cache`, which is what
    every other caller wants.
    """
    judges: dict[str, object] = {}
    cache = args.cache if cache is None else cache
    wanted = _expand_groups(args.judges)
    if "always-not-false" in wanted:
        judges["always-not-false"] = AlwaysJudge(False)
    if "always-false" in wanted:
        judges["always-false"] = AlwaysJudge(True)
    if "lexical-absence" in wanted:
        for threshold in args.lexical_thresholds:
            judge = LexicalJudge(min_missing=threshold)
            # The threshold is in the name because the eval sweeps it. A baseline
            # reported at one arbitrary setting is a baseline chosen to lose.
            judge.name = f"lexical-absence(>={threshold})"
            judges[judge.name] = judge
    if "model" in wanted:
        judge = AnthropicJudge(
            model=_model_from_judges(args.judges, args.model),
            cache_dir=cache, max_tokens=args.max_tokens,
            retry_max_tokens=args.retry_max_tokens, effort=args.effort,
            max_retries=args.max_retries,
        )
        # Keyed by the judge's own name, which carries the effort setting when one was
        # chosen. Two efforts in one results file must not collide under `model:<model>`.
        judges[judge.name] = judge
    if "per-claim" in wanted:
        judge = PerClaimJudge(
            model=_model_from_judges(args.judges, args.model),
            cache_dir=cache, max_tokens=args.max_tokens,
            retry_max_tokens=args.retry_max_tokens, effort=args.effort,
            max_retries=args.max_retries,
            batch_size=args.claim_batch,
        )
        judges[judge.name] = judge
    return judges


def _build_contexts(builder: ContextBuilder, arm_cases, arm: str) -> dict:
    """Build one context per case, reporting the ones that cannot be judged.

    Shared by the eval and the null run, and shared rather than written twice because the
    reporting is the load-bearing half. A case with no readable doc or no code side is a
    case the judge was never asked about, and it has to come off the denominator VISIBLY
    or every rate downstream is computed against a corpus size that is not the one
    measured. Two copies of that would be two chances to drop the message.
    """
    contexts = {}
    unusable = []
    for case in arm_cases:
        context = builder.build(case, arm)
        if not context.usable:
            unusable.append(context)
            continue
        contexts[case.example_id] = context
    if unusable:
        print(
            f"arm {arm}: {len(unusable)} case(s) had no readable document or no "
            f"code file at their parent commit and were not judged: "
            + ", ".join(sorted(c.example_id for c in unusable))
        )
    return contexts


def _estimate_judge(judge, contexts, *, max_tokens: int) -> dict:
    """What one paid judge will cost over these contexts, in tokens.

    Per judge, never one figure for the arm. The per-claim judge sends a different prompt a
    different number of times -- 168 calls to the per-page judge's 45 on the seeded arm --
    so a single estimate would under-read it by 3.5x, in the cheap-looking direction, which
    is the one direction an estimate must not be wrong in. That mistake has already been
    made twice in this project: once by omitting the system prompt from the count, once by
    guessing chars-per-token high.

    One function rather than one per command, for the same reason. Stage 4 multiplies this
    by a trial count, and a second pricing path that forgot the per-claim case would
    under-read a null run by the same 3.5x with the multiplier on top of it.
    """
    contexts = list(contexts)
    if isinstance(judge, PerClaimJudge):
        prompts = [
            render_claim_batch(context, group)
            for context in contexts
            for group in claim_batch(
                claim_units(context.doc_full or context.doc_text), judge.batch_size
            )
        ]
        return estimate_spend(
            prompts, system=CLAIM_SYSTEM_PROMPT, max_tokens=max_tokens
        )
    return estimate_spend(
        [render(c) for c in contexts], system=SYSTEM_PROMPT, max_tokens=max_tokens
    )


def _select_cases(cases: list, args: argparse.Namespace) -> list | None:
    """Apply `--repos`, `--only-cases` and `--limit`. `None` means the run is refused.

    Extracted so the null run cannot select its corpus by a second set of rules. The
    refusal below is the reason: a mistyped id has to stop the run in both commands, and a
    null run over a silently smaller set would report a width for a corpus nobody chose.
    """
    if args.repos:
        cases = [c for c in cases if c.repo in set(args.repos)]
    if args.only_cases:
        wanted = _expand_only_cases(args.only_cases)
        known = {c.example_id for c in cases}
        missing = sorted(wanted - known)
        if missing:
            # Refused, not warned. A mistyped `example_id` silently selects fewer cases
            # than asked for, and the run then reports a confident number over a set
            # nobody chose -- the same shape as the `retried` bug, a false claim about
            # the run printed by the tool for finding false claims about code.
            print(
                f"--only-cases: {len(missing)} id(s) match no loaded case: "
                + ", ".join(missing[:5])
                + (" ..." if len(missing) > 5 else ""),
                file=sys.stderr,
            )
            return None
        cases = [c for c in cases if c.example_id in wanted]
        # Louder than --limit's note, because a DELIBERATELY CHOSEN subset is the more
        # dangerous of the two. A prefix is merely unrepresentative; a set picked because
        # those cases previously failed is selected on the outcome being measured, so its
        # F1 is guaranteed to flatter or damn a change and generalises to nothing. The
        # only sound reading is per-case: did these named cases flip, and which ones.
        print(
            f"NOTE: --only-cases -- {len(cases)} case(s) chosen by id.\n"
            "      This is NOT A RESULT and its F1 must not be quoted or compared to a\n"
            "      floor: the cases were selected on the outcome being measured. Read it\n"
            "      per case -- which named cases changed answer -- and nothing else.\n"
        )
    if args.limit:
        # A prefix of the sorted cases, not a sample. A sample would need a seed
        # recorded in the provenance block to mean anything, and --limit exists for
        # smoke-testing the harness rather than for producing a number.
        cases = cases[: args.limit]
        print(f"NOTE: --limit {args.limit} -- this is a smoke test, not a result\n")
    return cases


def _cmd_eval(args: argparse.Namespace) -> int:
    cases, tally = load_cases(args.review, args.data)
    if not cases:
        print("no labelled cases found; nothing to score", file=sys.stderr)
        return 1
    print(format_case_report(cases, tally))
    print()

    selected = _select_cases(cases, args)
    if selected is None:
        return 1
    cases = selected

    judges = _build_judges(args)
    if not judges:
        print("no judges selected", file=sys.stderr)
        return 1

    builder = ContextBuilder(
        args.clone_root, k=args.k,
        code_budget=args.code_budget, doc_budget=args.doc_budget,
    )
    by_arm: dict[str, dict[str, dict]] = {}
    noise: dict[str, dict] = {}

    for arm in args.arms:
        # The oracle and seeded arms cover shape A only. Filtered here rather than
        # raising, because the interesting comparison is the three arms *on the same 45
        # cases*, and that is what `--arms oracle seeded retrieved` with this filter
        # gives.
        needs_code_side = arm in ("oracle", "seeded")
        arm_cases = [c for c in cases if c.code_path] if needs_code_side else cases
        if not arm_cases:
            print(f"arm {arm}: no cases carry a code_path; skipped\n")
            continue

        contexts = _build_contexts(builder, arm_cases, arm)

        truncated_docs = sum(1 for c in contexts.values() if c.doc_truncated)
        # Reported because it was not, and 29 of the 45 oracle contexts were in it. The
        # line below said "18 document(s) ... were cut" and said nothing about the code
        # side, so the most common truncation in the run was the invisible one -- and a
        # cut code file is what produces "the file shown is truncated and does not
        # include the definitions", scored as an abstention. 10 of the 45 cached replies
        # gave truncation as their own stated reason for abstaining.
        #
        # Still counted after the switch to `select_relevant`, and the count still means
        # something: windowing spends the same budget better, it does not abolish it. A
        # 70,000-character module is still mostly elided, and the marker saying so is the
        # only thing separating "no claim is made here" from "the claim was cut out".
        truncated_code = sum(
            1 for c in contexts.values() if any(f.truncated for f in c.code_files)
        )
        coverage = [c.marked_identifier_coverage for c in contexts.values()]
        found_oracle = [c.oracle_rank for c in contexts.values() if c.oracle_rank]
        print(
            f"arm {arm}: {len(contexts)} contexts built; "
            f"{truncated_docs} document(s) and {truncated_code} code file set(s) hit the "
            f"character budget and were cut; "
            f"median candidate pool {_median([c.pool_size for c in contexts.values()]):.0f}"
        )
        # Printed before the spend, because it is the number that says whether the run
        # can produce a readable answer at all. A judge shown code that does not contain
        # what the document talks about can only abstain, and 68.9% of the first oracle
        # arm did exactly that -- correctly, and at full price.
        #
        # The denominator is the WHOLE DOCUMENT, so a low figure means "one file cannot
        # cover this page", not "this is the wrong file". The stronger claim was made off
        # this number once and was wrong: measured against the drifted sentence instead,
        # the commit's own file is the best-covering file in its pool in 37 of 45 cases.
        thin = sum(1 for v in coverage if v < 0.20)
        print(
            f"  answerability: the code shown contains a median "
            f"{_median(coverage):.0%} of the identifiers the document marks up; "
            f"{thin} of {len(coverage)} context(s) are under 20%, where a judge has "
            "almost nothing to check the prose against. Denominator is the whole page "
            "(median 52 identifiers), so read a low number as `one file is not enough`"
        )
        if found_oracle:
            hit_at_k = sum(1 for r in found_oracle if r <= args.k) / len(found_oracle)
            print(
                f"  retrieval check: the commit's own code file is in the top "
                f"{args.k} for {hit_at_k:.0%} of the {len(found_oracle)} shape-A cases "
                f"(median rank {_median(found_oracle):.0f}). Agreement between two "
                "selectors, not a ceiling: it says how often Lexical finds the file the "
                "fix touched, and `scripts/oracle_file_audit.py` is what establishes that "
                "that file is a defensible target in the first place"
            )
        print()

        if args.dump_prompt:
            first = next(iter(contexts.values()))
            print(f"--- rendered prompt for {first.example_id} ({arm}) ---")
            print(render(first))
            print("--- end ---\n")

        # Priced before anything is sent, and only when something is about to be paid
        # for. Measured off the prompts that were actually built, so a mis-set --k or a
        # forgotten --limit shows up as a number here rather than on a bill.
        paid = [name for name in judges if _is_paid(name)]
        estimates = {
            name: _estimate_judge(
                judges[name], contexts.values(), max_tokens=args.max_tokens
            )
            for name in paid
        }
        if paid:
            # `flush=True`, because the point of a preflight is to be on screen BEFORE
            # the spend. Python block-buffers stdout when it is not a terminal, so
            # `judge-eval ... > run.log` or a pipe into `tee` showed an empty file for
            # the whole run and the estimate appeared only after every call had been
            # paid for. A safety notice that arrives after the event is decoration.
            print(f"arm {arm}: {', '.join(paid)} will be charged for", flush=True)
            for name in paid:
                print(f"  {name}:", flush=True)
                print(format_spend(estimates[name]), flush=True)
            total = sum(e["input_tokens_approx"] for e in estimates.values())
            if len(paid) > 1:
                print(f"  {total:,} estimated input tokens across all paid judges",
                      flush=True)
            if args.max_input_tokens and total > args.max_input_tokens:
                # Denominated in tokens rather than dollars for the same reason the
                # report is: a token budget cannot go stale. Checked against the TOTAL
                # across paid judges rather than per judge: two judges each just under
                # the cap are a bill over it, and the cap exists to bound the bill.
                print(
                    f"  REFUSING: estimated {total:,} input tokens exceeds "
                    f"--max-input-tokens {args.max_input_tokens:,}. Nothing was sent.",
                    file=sys.stderr,
                )
                return 1
            print()

        judgements: dict[str, dict] = {}
        for name, judge in judges.items():
            judgements[name] = {
                example_id: judge.judge(context)  # type: ignore[attr-defined]
                for example_id, context in contexts.items()
            }

        # The same replies, scored a second way, as a row of its own in the same table
        # against the same floors and the same chance range. Not a separate report,
        # deliberately: the whole difficulty with construct validity is that it is invisible
        # next to a number that looks fine, and putting the two rows on one axis is what
        # makes the gap between them readable. Costs nothing -- no call is made.
        for name in list(judgements):
            if not isinstance(judges.get(name), PerClaimJudge):
                continue
            judgements[f"{name} [located]"] = restrict_to_located(
                arm_cases, judgements[name]
            )

        for name in paid:
            print(f"arm {arm}: {name}")
            print(format_spend(estimates[name], measured_spend(judgements[name])))
            # A run that mixes token ceilings has to say so, or the argument for
            # reusing the cheaper replies is unverifiable from the output. Three
            # numbers, because they answer different questions and the first draft of
            # this line conflated the first two: what ceiling each reply was produced
            # under, how many of them were re-asked after dying at a lower one, and
            # how many are STILL truncated. The last is what decides whether the
            # mixture is legitimate at all -- it is sound only while every reply that
            # hit a ceiling was re-asked above it.
            #
            # Read off the judgements rather than off the flags. `--retry-max-tokens
            # 12000` on a cold cache serves every reply at 12,000 and re-asks none of
            # them, so a line built from the flags would report a re-ask that never
            # happened.
            served = Counter(j.max_tokens_used for j in judgements[name].values())
            retried = [j for j in judgements[name].values() if j.retried]
            still = [j for j in judgements[name].values() if j.truncated]
            if len(served) > 1 or retried or still:
                where = ", ".join(
                    f"{count} at {ceiling}"
                    for ceiling, count in sorted(served.items(),
                                                 key=lambda kv: kv[0] or 0)
                )
                print(
                    f"  ceilings: {where} token(s); {len(retried)} re-asked after "
                    f"truncating at a lower ceiling; {len(still)} still truncated"
                    + (" -- raise --retry-max-tokens further, the result is not "
                       "readable yet" if still else " -- the mixture is sound")
                )
            print()

        scored = [c for c in arm_cases if c.example_id in contexts]
        noise[arm] = noise_range(scored, set(contexts), trials=args.null_trials)
        print(format_results(scored, judgements, arm=arm, noise=noise[arm]))
        print()
        by_arm[arm] = judgements

    if args.out:
        payload = to_json(
            cases, by_arm, tally=tally, noise=noise,
            extra={
                "arms": list(args.arms),
                "k": args.k,
                "code_budget": args.code_budget,
                "doc_budget": args.doc_budget,
                # The reply budget and the effort setting are in the cache key too, and
                # were the one part of it a score file did not record. Two runs of the
                # doc-30,000 probe, one with `--retry-max-tokens 12000` and one without,
                # produced different confusion matrices -- 2 truncated replies against 0 --
                # and nothing in either file distinguished them. `retry_max_tokens` is the
                # difference between a case that was answered and a case that ran out of
                # room, so a file that omits it cannot say which of those it measured.
                "max_tokens": args.max_tokens,
                # `or None`, because the flag's "off" value is 0 and a provenance block
                # reading `retry_max_tokens: 0` says a retry happened at a ceiling of
                # nothing. Null is the one value that cannot be misread as a setting.
                "retry_max_tokens": args.retry_max_tokens or None,
                "effort": args.effort,
                # In the cache key by way of the rendered claim batch, so it changes the
                # result and therefore belongs here -- the rule this project settled after
                # two score files differed only in `--retry-max-tokens` and neither said so.
                # Null when no per-claim judge ran, rather than the default, because a
                # recorded 8 on a run that had no per-claim arm reads as a setting that was
                # in force.
                "claim_batch": args.claim_batch if any(
                    n.startswith("per-claim") for n in judges
                ) else None,
                "judges": sorted(judges),
                "repos": args.repos or "all",
                "limit": args.limit,
                # The exact ids, sorted, not just a count. A score file is the project's
                # measurement history, and "9 cases" in a provenance block is not enough
                # to tell a targeted probe apart from a run that lost 36 cases to a
                # loader bug -- which is the mistake the frozen join table exists for.
                "only_cases": sorted(_expand_only_cases(args.only_cases))
                if args.only_cases else None,
            },
        )
        dump_json(args.out, payload)
        print(f"wrote {args.out}")
    return 0


def _median(values) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    middle = len(values) // 2
    if len(values) % 2:
        return float(values[middle])
    return (values[middle - 1] + values[middle]) / 2


def _cmd_null_run(args: argparse.Namespace) -> int:
    """Stage 4: judge the same input several times and report how far the answer moves.

    One arm, not several. `judge-eval` takes `--arms` because comparing arms is the point
    of it; here a second arm multiplies the bill by a factor that buys a second question
    rather than a better answer to this one, and the number every other result needs is the
    width on the arm those results were measured on.
    """
    if args.trials < 2:
        # Refused rather than clamped. One trial has no width at all, and a null run that
        # printed 0.000 from a single pass would be the most convincing wrong answer this
        # harness could produce.
        print(
            f"--trials {args.trials}: a null run needs at least 2 passes to have a width. "
            f"The default is {DEFAULT_TRIALS}, which is the smallest count where a third "
            "draw can contradict the first two.",
            file=sys.stderr,
        )
        return 1

    cases, tally = load_cases(args.review, args.data)
    if not cases:
        print("no labelled cases found; nothing to score", file=sys.stderr)
        return 1
    print(format_case_report(cases, tally))
    print()

    selected = _select_cases(cases, args)
    if selected is None:
        return 1
    cases = selected

    arm = args.arm
    needs_code_side = arm in ("oracle", "seeded")
    arm_cases = [c for c in cases if c.code_path] if needs_code_side else cases
    if not arm_cases:
        print(f"arm {arm}: no cases carry a code_path; nothing to run", file=sys.stderr)
        return 1

    # Built ONCE, outside the trial loop, and that is the measurement rather than an
    # optimisation: if the contexts were rebuilt per trial, a difference between trials
    # could be retrieval moving rather than the judge, and the two would be
    # indistinguishable in the output.
    builder = ContextBuilder(
        args.clone_root, k=args.k,
        code_budget=args.code_budget, doc_budget=args.doc_budget,
    )
    contexts = _build_contexts(builder, arm_cases, arm)
    if not contexts:
        print(f"arm {arm}: no usable contexts; nothing to run", file=sys.stderr)
        return 1
    scored = [c for c in arm_cases if c.example_id in contexts]
    print(
        f"arm {arm}: {len(contexts)} context(s) built once and shared by all "
        f"{args.trials} trial(s)"
    )

    # Trial 0's judges, only to price the run and to name the judges. Each trial rebuilds
    # them against its own cache directory below.
    probe = _build_judges(args, cache=trial_cache(args.cache_root, 0))
    if not probe:
        print("no judges selected", file=sys.stderr)
        return 1

    # Two cases whose rendered prompt is byte-identical share a cache key, so within one
    # trial the second is served the first's reply and the two cannot disagree. Correct --
    # one prompt is one purchase -- and it narrows every width this reports, so it is
    # counted. Only computable for a judge that renders one prompt per case; left as None
    # for a per-claim arm, which the report prints as NOT CHECKED rather than as passing.
    duplicate_prompts: int | None = None
    if not any(isinstance(j, PerClaimJudge) for j in probe.values()):
        rendered = Counter(render(c) for c in contexts.values())
        duplicate_prompts = sum(n - 1 for n in rendered.values() if n > 1)

    paid = [name for name in probe if _is_paid(name)]
    if paid:
        total = 0
        print(
            f"{', '.join(paid)} will be charged for, {args.trials} times over -- the "
            "trials are the cost of this measurement and there is no cached shortcut, "
            "because a cached trial is the thing being avoided",
            flush=True,
        )
        for name in paid:
            estimate = _estimate_judge(
                probe[name], contexts.values(), max_tokens=args.max_tokens
            )
            print(f"  {name}, per trial:", flush=True)
            print(format_spend(estimate), flush=True)
            per_trial = int(estimate["input_tokens_approx"])
            total += per_trial * args.trials
            print(
                f"  x{args.trials} trial(s): ~{per_trial * args.trials:,} estimated input "
                "tokens",
                flush=True,
            )
        print(
            f"  ~{total:,} estimated input tokens for the whole null run. An UPPER bound: "
            "a trial already banked under its own cache directory is re-read for nothing, "
            "and the `cached` column in the report is the exact figure after the fact.",
            flush=True,
        )
        if args.max_input_tokens and total > args.max_input_tokens:
            print(
                f"  REFUSING: estimated {total:,} input tokens exceeds "
                f"--max-input-tokens {args.max_input_tokens:,}. Nothing was sent.",
                file=sys.stderr,
            )
            return 1
        if args.dry_run:
            print(
                "\n--dry-run: nothing was sent. The estimate above is the whole output.\n"
                "Priced before any spend, on the prompts that were actually built, which "
                "is the same\ndiscipline that priced the stage-2d reranker arm to zero "
                "error."
            )
            return 0
    elif args.dry_run:
        print("\n--dry-run: no paid judge was selected, so there was nothing to price.")
        return 0

    per_judge: dict[str, list] = {name: [] for name in probe}
    for index in range(args.trials):
        cache = trial_cache(args.cache_root, index)
        # Rebuilt per trial so that the cache directory differs and nothing else does.
        judges = _build_judges(args, cache=cache)
        print(f"\ntrial {index}: cache {cache}", flush=True)
        for name, judge in judges.items():
            judgements = {
                example_id: judge.judge(context)  # type: ignore[attr-defined]
                for example_id, context in contexts.items()
            }
            trial = summarise_trial(index, scored, judgements)
            per_judge[name].append(trial)
            print(
                f"  {name}: F1 {trial.scores.f1:.3f}, {trial.cached} of "
                f"{len(judgements)} reply/replies from this trial's cache",
                flush=True,
            )

    # The chance range, over the same cases the trials were scored on, so the two widths
    # in the last block of the report are computed against the same denominator.
    chance = noise_range(scored, set(contexts), trials=args.null_trials)

    print()
    print(
        format_null_run(
            scored, per_judge, arm=arm, chance=chance,
            cache_root=args.cache_root, duplicate_prompts=duplicate_prompts,
        )
    )

    if args.out:
        payload = null_run_json(
            scored, per_judge, arm=arm, tally=tally, chance=chance,
            extra={
                "trials": args.trials,
                "cache_root": str(args.cache_root),
                "k": args.k,
                "code_budget": args.code_budget,
                "doc_budget": args.doc_budget,
                "max_tokens": args.max_tokens,
                "retry_max_tokens": args.retry_max_tokens or None,
                "effort": args.effort,
                "claim_batch": args.claim_batch if any(
                    n.startswith("per-claim") for n in probe
                ) else None,
                "judges": sorted(probe),
                "repos": args.repos or "all",
                "limit": args.limit,
                "null_trials": args.null_trials,
                "only_cases": sorted(_expand_only_cases(args.only_cases))
                if args.only_cases else None,
            },
        )
        dump_json(args.out, payload)
        print(f"wrote {args.out}")
    return 0


def _add_corpus_flags(parser: argparse.ArgumentParser) -> None:
    """Which cases a run is about. Shared, so two commands cannot select differently.

    `--only-cases` and `--limit` carry warnings rather than just semantics, and those
    warnings are the reason this is one function: a null run over a set chosen by id is
    as unquotable as an eval over one, and a second copy of the flag would be a second
    copy of the caveat to forget.
    """
    parser.add_argument("--review", type=Path, default=Path("review"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--repos", nargs="*", default=None)
    parser.add_argument(
        "--only-cases", nargs="*", default=None, metavar="EXAMPLE_ID",
        help="score only these `example_id`s; `@file` reads them one per line. For "
             "probing named cases cheaply -- the 9 recall-costing cases cost ~$0.57 "
             "against ~$2.84 for all 45. NOT A RESULT: the cases are selected on the "
             "outcome being measured, so the F1 is unquotable and only the per-case "
             "change of answer means anything. An unknown id is refused, not skipped",
    )
    parser.add_argument("--limit", type=int, default=0, help="smoke test only")


def _add_judge_flags(parser: argparse.ArgumentParser) -> None:
    """Everything that decides what a judge is and what it is asked.

    Shared between `judge-eval` and `judge-null-run` on purpose, and the purpose is
    narrower than saving typing. Almost every flag here is inside the cache key -- the
    budgets, the reply ceiling, the effort setting -- so a null run whose defaults had
    drifted from the eval's would measure the run-to-run width of a harness that produced
    none of the results the width is quoted against.
    """
    parser.add_argument(
        "--judges", nargs="+", default=["floors"], type=_judge_arg,
        metavar="{" + ",".join(JUDGE_CHOICES) + ",model:<id>}",
        help="`floors` is the three that need no key, and is the default; `model` "
             "needs ANTHROPIC_API_KEY and costs money. `model:<id>` is accepted too, "
             "because that is the form the reports and score files print -- pasting one "
             "back should run, not exit",
    )
    parser.add_argument(
        "--lexical-thresholds", nargs="+", type=int, default=[1, 3, 6],
        help="swept rather than fixed, so the free baseline is reported at its best",
    )
    parser.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument(
        "--k", type=int, default=DEFAULT_K,
        help="code files shown per document; 5 is where the measured hit rate on the "
             "45 known-answer cases reaches 60%%, and it is a dimension to sweep",
    )
    parser.add_argument(
        "--code-budget", type=int, default=CODE_BUDGET,
        help="characters kept per code file after windowing. INSIDE THE CACHE KEY: a "
             "different value re-pays for every case in the run, so it is a flag rather "
             "than an edit to the constant. Measured on the 5 budget-cut cases, 9,000 "
             "brings 2 of them on screen for 1.27x the input tokens and 36,000 brings 4 "
             "for 2.96x; below 36,000 nothing further is recovered",
    )
    parser.add_argument(
        "--doc-budget", type=int, default=DOC_BUDGET,
        help="characters kept of the document, head-truncated. ALSO INSIDE THE CACHE "
             "KEY. Measured on the 9 recall-costing cases: on 3 of them the sentence the "
             "fixing commit deleted sits beyond 12,000 characters, so the claim under "
             "test was not in the prompt and no code budget could have answered it",
    )
    parser.add_argument(
        "--claim-batch", type=int, default=DEFAULT_BATCH,
        help="claims per call for `--judges per-claim`. It changes the rendered prompt, "
             "so it changes the cache key: a different value re-asks everything. 8 is "
             "what the pricing diagnostic was read at (168 calls, 3.5x one per-page pass)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
        help="reply budget per case, covering REASONING as well as the answer -- 700 "
             "was enough for the answer and truncated 16 of 45 replies mid-thought",
    )
    parser.add_argument(
        "--retry-max-tokens", type=int, default=0,
        help="re-ask ONLY the replies that hit --max-tokens, at this higher ceiling. "
             "Exists because --max-tokens is inside the cache key, so raising it "
             "re-pays every reply already bought: 4 truncated replies out of 45 cost ~$3 "
             "to repair that way and well under $1 this way. Sound because a ceiling a "
             "reply never reached cannot have changed it; 0 disables",
    )
    parser.add_argument(
        "--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
        help="how many times the SDK re-sends a TRANSIENT failure -- connection errors, "
             "408, 409, 429, 5xx -- with its own backoff. NOT in the cache key: a reply is "
             "the same however many attempts delivered it, so this is the one knob here "
             "that costs nothing to change. Raised from the SDK's 2 because a 168-call run "
             "died at call 148. It does not make a run crash-proof, and it is not the "
             "checkpoint -- the reply cache is, which is why that crash cost $0",
    )
    parser.add_argument(
        "--effort", choices=("low", "medium", "high"), default=None,
        help="how hard the model reasons before answering. Unset means the API default, "
             "which is what the reported runs use; `low` skipped reasoning entirely and "
             "cost 49 output tokens against 4,640 on one measured case. A dimension to "
             "sweep, not a setting to quietly pick -- it changes the cache key",
    )
    parser.add_argument(
        "--max-input-tokens", type=int, default=0,
        help="refuse to send an arm whose estimated input exceeds this, before any "
             "call is made; 0 disables. Denominated in tokens because a token budget "
             "cannot go stale the way a dollar figure can",
    )
    parser.add_argument(
        "--null-trials", type=int, default=200,
        help="trials of the chance control -- a coin at the corpus positive rate. NOT "
             "the null RUN's trial count, which is `--trials`: this one is free and draws "
             "coins, that one is paid and calls the model",
    )


def add_parser(subparsers) -> None:
    cases = subparsers.add_parser(
        "judge-cases",
        help="report the hand-labelled cases, the class balance and the floors",
    )
    cases.add_argument("--review", type=Path, default=Path("review"))
    cases.add_argument("--data", type=Path, default=Path("data"))
    cases.set_defaults(func=_cmd_cases)

    freeze = subparsers.add_parser(
        "judge-freeze",
        help="write the tracked join table so a clean checkout rebuilds the same corpus",
    )
    freeze.add_argument("--review", type=Path, default=Path("review"))
    freeze.add_argument("--data", type=Path, default=Path("data"))
    freeze.add_argument("--out", type=Path, default=None)
    freeze.set_defaults(func=_cmd_freeze)

    ev = subparsers.add_parser(
        "judge-eval", help="score judges against the hand-written verdicts"
    )
    _add_corpus_flags(ev)
    _add_judge_flags(ev)
    ev.add_argument(
        "--arms", nargs="+", choices=ARMS, default=["retrieved"],
        help="oracle = the commit's own code file and nothing else, shape A only -- "
             "superseded, it abstains because one module cannot answer a page; seeded = "
             "that file plus retrieval's top hits to k, shape A only, the arm that "
             "actually isolates judging from retrieval; retrieved = Lexical top-k, the "
             "only arm that covers shape B and the only end-to-end number",
    )
    ev.add_argument(
        "--cache", type=Path, default=Path(".cache/judgements"),
        help="keyed by a hash of the rendered context, prompt and model",
    )
    ev.add_argument(
        "--dump-prompt", action="store_true",
        help="print one rendered prompt, to check by eye that no diff leaked into it",
    )
    ev.add_argument("--out", type=Path, default=None, help="also write JSON")
    ev.set_defaults(func=_cmd_eval)

    null = subparsers.add_parser(
        "judge-null-run",
        help="judge the same input several times and report how far the answer moves",
    )
    _add_corpus_flags(null)
    _add_judge_flags(null)
    null.add_argument(
        "--arm", choices=ARMS, default="retrieved",
        help="one arm, not several. A second arm multiplies the bill by a factor that "
             "buys a different question rather than a better answer to this one, and the "
             "width every other result needs is the width on the arm they were measured on",
    )
    null.add_argument(
        "--trials", type=int, default=DEFAULT_TRIALS,
        help=f"how many times to judge the same input. Default {DEFAULT_TRIALS}, which is "
             "a FLOOR rather than a recommendation: two trials give one comparison and "
             "cannot tell a narrow width from a lucky pair, three let a third draw "
             "contradict the first two. Raising it later re-reads what is already banked "
             "and pays only for the new trials. Fewer than 2 is refused",
    )
    null.add_argument(
        "--cache-root", type=Path, default=Path(".cache/null-run"),
        help="one directory PER TRIAL underneath this, which is how the shared reply "
             "cache is bypassed. `.cache/judgements` is keyed on content, so a null run "
             "over it serves every trial after the first off disk and reports a width of "
             "0.000 from a run that made no calls -- clean, and wrong. The per-trial "
             "directories also make a dead run resumable and a re-read free",
    )
    null.add_argument(
        "--dry-run", action="store_true",
        help="price the whole run -- per trial and multiplied out -- and send nothing. "
             "The same counting-stub discipline that priced the stage-2d reranker arm to "
             "zero error before a 55-hour job started",
    )
    null.add_argument("--out", type=Path, default=None, help="also write JSON")
    null.set_defaults(func=_cmd_null_run)
