"""The `driftwood retrieve-eval`, `doc-sample` and `doc-eval` subcommands.

Lives here rather than in `mining/cli.py` so that the mining package stays what its
docstring claims -- ground truth with no eval logic in it. The top-level parser just
calls `add_parser`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import DEFAULT_MODEL, dataset, evaluate

__all__ = ["add_parser"]

# The three repos whose CODE pools are small enough to put on a checklist a person can
# actually read: 23, 22 and 35 files at HEAD. pydantic (267) and fastapi (685) are
# excluded, and that exclusion is the sharp edge of stage 2c rather than a detail --
# they are the two repos where the dense arm's loss was individually readable against
# its noise range, so 2c cannot confirm or overturn the readable half of the result.
DEFAULT_DOC_REPOS = ("encode/httpx", "psf/requests", "pallets/flask")


def _build_dense(args: argparse.Namespace):
    """The dense arm, or `(None, None, None)` if it was not asked for.

    Shared by `retrieve-eval` and `doc-eval` on purpose. Two corpora scored by two
    separately-constructed dense arms could differ by chunk size or model and the
    tables would not say so; the whole question 2c asks is whether the *same* arm
    behaves differently on ground truth the mining rule did not select.
    """
    if not args.embed_model:
        return None, None, None

    # Imported here, not at module scope, so a run without --embed-model still works
    # on a machine with no inference stack installed.
    from .embed import (
        Chunking,
        Dense,
        EmbeddingCache,
        SentenceTransformerEncoder,
        default_cache_path,
    )

    chunking = Chunking(size=args.embed_chunk, overlap=args.embed_overlap)
    encoder = SentenceTransformerEncoder(
        args.embed_model, device=args.embed_device, batch_size=args.embed_batch
    )
    # Caching is the default, and opting out is the flag. Encoding 8148 blobs is the
    # expensive thing here; a run that forgets the cache looks identical to one that
    # used it apart from taking an hour, which is the wrong way round.
    cache_path = None
    if not args.no_embed_cache:
        cache_path = args.embed_cache or default_cache_path(
            encoder.model_id, chunking, args.embed_cache_root
        )
    embed_cache = EmbeddingCache(cache_path, encoder.model_id, chunking)
    factory = lambda code_texts: Dense(encoder, code_texts, embed_cache)  # noqa: E731
    provenance = {
        "dense_model": encoder.model_id,
        "dense_dim": encoder.dim,
        "chunk_size": chunking.size,
        "chunk_overlap": chunking.overlap,
        "pooling": "max over (doc chunk, code chunk) pairs",
        "ablation": "evidence tokens redacted from doc text, not set-subtracted",
    }
    print(f"dense arm: {encoder.model_id} dim={encoder.dim} chunk={chunking.key}")
    print(f"embedding cache: {cache_path or 'disabled'}")
    print()
    return factory, provenance, embed_cache


def _run(args: argparse.Namespace) -> int:
    splits = dataset.build(
        args.labels,
        clone_root=args.clone_root,
        repos=args.repos or None,
    )
    if not any(split.queries for split in splits):
        print(
            "no shape-A drift queries found; check --repos against the label file",
            file=sys.stderr,
        )
        return 2

    print(dataset.format_dataset_report(splits))
    print()

    # One token cache across every repo. Tokenising is the eval's only real cost and
    # it is keyed by file contents, so a file unchanged across two hundred shas is
    # tokenised once.
    token_cache: dict[str, frozenset[str]] = {}

    dense_factory, provenance, embed_cache = _build_dense(args)

    results = []
    for split in splits:
        results.extend(
            evaluate.evaluate_split(
                split,
                null_trials=args.null_trials,
                token_cache=token_cache,
                dense=dense_factory,
            )
        )
        # Saved per repo rather than once at the end: a run over five repos takes long
        # enough that losing every vector to an interrupt in the last repo would be a
        # real cost, and the cache is the expensive artefact here.
        if embed_cache is not None:
            embed_cache.save()

    print(evaluate.format_results(results, null_trials=args.null_trials))
    if embed_cache is not None:
        total = embed_cache.hits + embed_cache.misses
        print(
            f"\nembedding cache: {embed_cache.hits} hits, {embed_cache.misses} encoded "
            f"({embed_cache.hits / total:.0%} reused)"
        )

    if args.out:
        payload = evaluate.to_json(results, splits, provenance)
        payload["labels"] = str(args.labels)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


def _run_doc_sample(args: argparse.Namespace) -> int:
    from . import doclabel

    specs = []
    for repo in args.repos:
        clone = args.clone_root / doclabel.local_name_for(repo)
        if not clone.exists():
            print(f"no clone at {clone}; run `driftwood mine` first", file=sys.stderr)
            return 2
        specs.append(doclabel.sample_cases(repo, clone, args.per_repo, args.seed))

    sheet = doclabel.write_bundle(specs, args.bundle, args.seed, args.clone_root)
    for spec in specs:
        pool = len(spec.cases[0].pool) if spec.cases else 0
        print(f"{spec.repo:<20}{spec.sha[:12]}  {len(spec.cases)} docs, {pool} code files")
    print()
    print(f"sheet:  {sheet}")
    print(f"text:   {args.bundle / 'text'}")
    print(f"seed:   {args.seed}  (recorded in the sheet; a different seed is a different")
    print("        sample and must not be reported as the same measurement)")
    print()
    print("Nothing in the sheet is pre-filled. A judgement suggested by a ranker cannot")
    print("then be used to grade that ranker, and a judgement suggested by anything else")
    print("is still an anchor -- so the boxes are empty and stay empty until a person")
    print("ticks them.")
    return 0


def _run_doc_eval(args: argparse.Namespace) -> int:
    from . import doclabel

    cases = doclabel.parse_sheet(args.sheet.read_text(encoding="utf-8"))
    if not cases:
        print(f"no `## Case` blocks found in {args.sheet}", file=sys.stderr)
        return 2
    splits, tally = doclabel.splits_from_sheet(cases, args.clone_root)

    print(
        f"sheet: {tally['cases']} cases, {tally['answered']} answered, "
        f"{tally['skipped']} unmarked, {tally['none']} marked NONE, "
        f"{tally['queries']} scoreable queries"
    )
    if tally["unknown_paths"]:
        print(
            f"  WARNING: {tally['unknown_paths']} named path(s) are not in the pinned "
            "tree and were dropped"
        )
    if tally["unresolved"]:
        print(
            f"  WARNING: {tally['unresolved']} case(s) name a tree this clone cannot "
            "resolve and were dropped, not rescored at HEAD"
        )
    if tally["unpinned"]:
        print(
            f"  WARNING: {tally['unpinned']} case(s) lost their `tree` line and were "
            "scored at the clone's current HEAD"
        )
    print(
        "  NONE cases are answers, not queries: a doc that makes no claim about any "
        "module has"
    )
    print(
        "  no correct retrieval result, so scoring it would add a query every ranker "
        "loses."
    )
    if not tally["queries"]:
        print("\nnothing to score yet -- fill in some cases first")
        return 0
    print()
    print(dataset.format_dataset_report(splits))
    print()

    dense_factory, provenance, embed_cache = _build_dense(args)
    token_cache: dict[str, frozenset[str]] = {}
    results = []
    for split in splits:
        if not split.queries:
            continue
        results.extend(
            evaluate.evaluate_split(
                split,
                null_trials=args.null_trials,
                token_cache=token_cache,
                dense=dense_factory,
            )
        )
        if embed_cache is not None:
            embed_cache.save()

    # The ablated arms are dropped rather than not run. `evaluate_split` ablates each
    # query's `evidence`, which is empty on every query here because no mining rule
    # selected these pairs -- so the ablated rows would be byte-identical copies of
    # their unablated ones, and a duplicated row in a results table reads as a
    # measurement that was made.
    kept = [r for r in results if not r.ranker.endswith("-ablated")]
    print(evaluate.format_results(kept, null_trials=args.null_trials))
    print()
    print("No ablated arm, and its absence is the point. Ablation bounds circularity")
    print("injected by the MINING RULE: it strikes the tokens that caused a pair to be")
    print("proposed. These pairs were proposed by a person reading prose, so there is no")
    print("such channel and nothing to strike. Compare these rows against the ABLATED")
    print("rows of the mined eval -- those are that corpus's defensible numbers.")

    if args.out:
        payload = evaluate.to_json(kept, splits, provenance)
        payload["eval"] = "retrieval-doc-to-code-human-labelled"
        payload["ground_truth"] = {
            "source": str(args.sheet),
            "selection": "documents sampled uniformly from the CODE-adjacent doc set; "
            "candidates are the whole tree, proposed by no ranker",
            "ablation": "none -- no mining rule behind these labels, so no evidence "
            "tokens exist to strike",
            "cases": tally["cases"],
            "answered": tally["answered"],
            "marked_none": tally["none"],
            "unmarked": tally["skipped"],
            "unknown_paths_dropped": tally["unknown_paths"],
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


def _add_dense_args(parser: argparse.ArgumentParser) -> None:
    dense = parser.add_argument_group(
        "dense arm (needs `uv sync --extra embed`)",
        "Off unless --embed-model is given, so the free baselines stay runnable with "
        "no inference stack. The bar for a dense arm is `lexical-ablated` per repo, "
        "not the shuffled floor.",
    )
    dense.add_argument(
        "--embed-model",
        nargs="?",
        const=DEFAULT_MODEL,
        default=None,
        help="turn the dense arm on. Bare, it uses "
        f"{DEFAULT_MODEL} (fast, 384-dim); pass a sentence-transformers id such as "
        "BAAI/bge-m3 for a stronger model at roughly 17x the compute",
    )
    dense.add_argument(
        "--embed-cache",
        type=Path,
        default=None,
        help="explicit path for the chunk-vector cache (.npz). Defaults to a name "
        "derived from the model and chunking under --embed-cache-root, so two "
        "configurations get two files instead of colliding on one.",
    )
    dense.add_argument(
        "--embed-cache-root",
        type=Path,
        default=Path(".cache/embeddings"),
        help="where derived cache filenames live (default: .cache/embeddings)",
    )
    dense.add_argument(
        "--no-embed-cache",
        action="store_true",
        help="encode everything every run. Only useful for timing the encoder: the "
        "corpus is 8148 unique code blobs behind 629 trees and the cache is keyed by "
        "content, so this is the slow path on purpose.",
    )
    dense.add_argument(
        "--embed-chunk",
        type=int,
        default=1600,
        help="chunk size in characters (default: 1600, roughly 400 tokens)",
    )
    dense.add_argument(
        "--embed-overlap",
        type=int,
        default=200,
        help="overlap in characters, so a definition on a window boundary survives "
        "intact somewhere (default: 200)",
    )
    dense.add_argument(
        "--embed-device",
        default=None,
        help="torch device: mps on Apple silicon, cuda, or cpu (default: let "
        "sentence-transformers choose)",
    )
    dense.add_argument("--embed-batch", type=int, default=64)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "retrieve-eval",
        help="score doc->code retrieval baselines against a shuffled floor",
        description=(
            "Turns mined shape-A pairs into retrieval judgements and scores the "
            "zero-dependency baselines against a shuffled control on the same "
            "candidate pool. Each query is scored on the tree its judgement was made "
            "at, so no mine manifest is needed and no rename has to be followed. "
            "Reported per repo, never pooled."
        ),
    )
    parser.add_argument("labels", type=Path, help="a mined .jsonl label file")
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument(
        "--repos",
        nargs="+",
        default=[],
        help="restrict to these repo slugs (default: every repo in the manifest)",
    )
    parser.add_argument(
        "--null-trials",
        type=int,
        default=evaluate.NULL_TRIALS,
        help="shuffle trials behind the floor and its noise range "
        f"(default: {evaluate.NULL_TRIALS}). Lower it only to iterate; a narrow "
        "noise range from too few trials overstates how readable a gain is.",
    )
    parser.add_argument("--out", type=Path, default=None, help="also write JSON")
    _add_dense_args(parser)
    parser.set_defaults(func=_run)

    sample = subparsers.add_parser(
        "doc-sample",
        help="build an unlabelled doc->code review sheet with no ranker in it",
        description=(
            "Stage 2c. Samples documents from the pinned tree of each repo and writes a "
            "review sheet whose candidate list is the repository's whole CODE pool, plus "
            "every doc and candidate file as text on disk (the clones are bare, so there "
            "is no working tree to open). The candidate set is proposed by no ranker: "
            "judging a ranker's own suggestions measures whether its suggestions are "
            "good, and can never contain a pair it missed."
        ),
    )
    sample.add_argument(
        "--repos",
        nargs="+",
        default=list(DEFAULT_DOC_REPOS),
        help="repos to sample (default: the three with checklist-sized CODE pools)",
    )
    sample.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    sample.add_argument("--bundle", type=Path, default=Path("review/2c"))
    sample.add_argument(
        "--per-repo",
        type=int,
        default=6,
        help="documents per repo (default: 6). Each one means reading a doc and as much "
        "of a 22-to-35 file pool as it takes to answer, so this is an hour-scale number "
        "and not a thousand-label number.",
    )
    sample.add_argument(
        "--seed",
        type=int,
        default=20260918,
        help="recorded in the sheet and in the results JSON. A different seed is a "
        "different sample, not a re-run of this one.",
    )
    sample.set_defaults(func=_run_doc_sample)

    doc_eval = subparsers.add_parser(
        "doc-eval",
        help="score the same rankers against the hand-labelled 2c sheet",
        description=(
            "Scores a filled `doc-sample` sheet with the same rankers, the same shuffled "
            "floor and the same macro-averaging as `retrieve-eval`, so the only thing "
            "that differs between the two tables is where the ground truth came from. "
            "No ablated arm: ablation strikes the tokens a mining rule selected on, and "
            "no mining rule selected these pairs."
        ),
    )
    doc_eval.add_argument("sheet", type=Path, help="a filled review/2c/SHEET.md")
    doc_eval.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    doc_eval.add_argument(
        "--null-trials",
        type=int,
        default=evaluate.NULL_TRIALS,
        help=f"shuffle trials behind the floor (default: {evaluate.NULL_TRIALS}). With "
        "a handful of queries per repo the noise range is wide, and that width is the "
        "finding rather than a nuisance.",
    )
    doc_eval.add_argument("--out", type=Path, default=None, help="also write JSON")
    _add_dense_args(doc_eval)
    doc_eval.set_defaults(func=_run_doc_eval)
