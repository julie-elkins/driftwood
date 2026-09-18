"""Mine documentation-drift labels out of git history.

No model, no inference, no network beyond `git clone`. This package is the
project's ground truth, and it is deliberately the least clever code in the repo:
everything downstream is measured against what comes out of here, so it has to be
something you can read end to end and argue with.
"""
