"""How many pairs a second this device really scores, before committing hours to it.

Written because a projection was wrong in the expensive direction. The reranker arm was
priced at 55.1 hours from an MPS rate, and the batch size that rate assumed was never
checked: on this laptop 64 is the FASTEST setting and every larger one is worse (196, 146,
136, 122 pairs/sec at 64/128/256/512), which is the opposite of the usual advice. So the
rule is to measure the device rather than reason about it, and to do it for a minute
before spending a day.

Pairs are synthetic but sized like the real ones -- 800 characters each side, the run's
`RERANK_CHUNKING` -- because throughput here is set by sequence length and batch shape,
not by what the text says. The first call at each batch size is discarded: a cold graph on
MPS or a cold autotune on CUDA lands entirely in the first batch and would be charged to
the rate.

    uv run python scripts/rerank_throughput.py --device cuda
"""

from __future__ import annotations

import argparse
import time

from driftwood.retrieval.rerank import RERANK_CHUNKING, CrossEncoderScorer

# Derived, not counted: the priced total for the mined corpus less the 7,927,889 pairs the
# four cheap repos left in the cache. Held here so the projection is against the repo that
# actually costs something rather than against a total nothing runs.
PYDANTIC_PAIRS = 24_625_841


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=None, help="mps, cuda, or cpu")
    parser.add_argument("--batches", type=int, nargs="+", default=[64, 128, 256, 512])
    parser.add_argument("--pairs", type=int, default=2048)
    args = parser.parse_args()

    doc = ("The client sends a request and the response is validated. " * 20)[
        : RERANK_CHUNKING.size
    ]
    code = ("def validate(self, value, field, config):\n    return value\n" * 20)[
        : RERANK_CHUNKING.size
    ]
    # Suffixed per pair so nothing is deduplicated by an upstream cache and every pair
    # reaches the model, which is the thing being timed.
    pairs = [(f"{doc}{i}", f"{code}{i}") for i in range(args.pairs)]

    print(f"loading {CrossEncoderScorer.__name__} on {args.device or 'default'} ...")
    started = time.time()
    scorer = CrossEncoderScorer(device=args.device, batch_size=args.batches[0])
    print(f"  loaded in {time.time() - started:.1f}s\n")

    print(f"  {'batch':>6}  {'pairs/sec':>10}   {PYDANTIC_PAIRS:,} pairs would take")
    best = (0.0, 0)
    for batch in args.batches:
        scorer.batch_size = batch
        scorer.score(pairs[: min(256, args.pairs)])
        started = time.time()
        scorer.score(pairs)
        rate = len(pairs) / (time.time() - started)
        print(f"  {batch:>6}  {rate:>10.0f}   {PYDANTIC_PAIRS / rate / 3600:>5.1f}h")
        best = max(best, (rate, batch))

    print(f"\nfastest: --rerank-batch {best[1]} at {best[0]:.0f} pairs/sec")
    print(
        "A rate under ~400/sec means the device is not worth the transfer -- the laptop "
        "already does 196."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
