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

__all__ = ["DEFAULT_MODEL"]

# Lives here rather than in `embed`, which cannot be imported without numpy, so that
# the argument parser can name the default in its own help text on a machine with no
# inference stack installed. One literal, two readers.
#
# Small and fast, chosen to answer whether the dense arm clears the free baseline at
# all. BAAI/bge-m3 is stronger at roughly 17x the compute and is one flag away.
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
