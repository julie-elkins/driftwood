"""Retrieve the code a documentation file makes claims about, and measure it.

Stage 2. The mining stage produced pairs of (doc, code) that a human confirmed are
about the same thing; this stage treats those pairs as relevance judgements and
asks how far up a ranking the right code file lands.

The direction is doc -> code, which is the direction the pipeline actually needs:
an agent holding a documentation claim has to fetch the code to check it against.
The reverse direction (a changed code file -> which docs are now suspect) is the
GitHub App's entry point and is a separate eval, because it has a separate ground
truth and a separate candidate pool.

Nothing here imports a model. The point of building it first is that every model
added later has a measured number to beat rather than a plausible-sounding one.
"""

__all__ = ["DEFAULT_MODEL", "DEFAULT_RERANK_MODEL", "DEFAULT_TOP_N"]

# Lives here rather than in `embed`, which cannot be imported without numpy, so that
# the argument parser can name the default in its own help text on a machine with no
# inference stack installed. One literal, two readers.
#
# Small and fast, chosen to answer whether the dense arm clears the free baseline at
# all. BAAI/bge-m3 is stronger at roughly 17x the compute and is one flag away.
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

# Here for exactly the same reason, and the reason is load-bearing rather than tidy:
# `numpy` is an extra, not a dependency, so the parser is built on machines where
# `retrieval.rerank` cannot be imported at all. A default named from that module would
# break `driftwood mine` on a bare install.
#
# An ms-marco cross-encoder, 6 layers. NOT interchangeable with DEFAULT_MODEL: a
# bi-encoder id handed to `CrossEncoder` loads and emits numbers that are not relevance
# scores, so the two constants are kept apart even though they sit side by side.
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"

# How many of the base ranker's candidates the reranker reorders. 20 because that is the
# candidate set whose ceiling was measured with `--ks 20` before the reranker was built,
# and recall@k for every k >= this is the base ranker's number by construction.
DEFAULT_TOP_N = 20
