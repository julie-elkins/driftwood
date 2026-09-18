"""Classify a repository path as documentation, code, or neither.

Every label this project mines rests on this module being right. A misread path
does not fail loudly -- it silently emits a mislabeled pair, which is worse than
a crash, because a crash stops the run and a bad label just quietly makes the
eval lie.
"""

from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath

__all__ = ["Kind", "classify", "is_probably_generated"]


class Kind(str, Enum):
    DOC = "doc"
    CODE = "code"
    OTHER = "other"


DOC_SUFFIXES = frozenset({".md", ".mdx", ".rst", ".adoc", ".textile"})

CODE_SUFFIXES = frozenset(
    {
        ".py", ".pyi",
        ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
        ".go", ".rs", ".java", ".kt", ".kts", ".scala", ".rb",
        ".c", ".h", ".cc", ".cpp", ".hpp", ".cs",
        ".php", ".swift", ".m", ".mm",
    }
)

# Paths whose contents a tool produces rather than a person writing them. A
# change inside generated output is the generator running, never a human
# noticing a contradiction, so it can never be evidence of drift.
GENERATED_DIR_MARKERS = (
    "node_modules/", "vendor/", "third_party/", "thirdparty/",
    "site-packages/", "dist/", "build/", "_build/", ".tox/",
    "target/", "generated/", "_generated/", "autogen/",
    "docs/api/", "api-reference/", "apiref/", "javadoc/", "godoc/",
    ".venv/", "venv/", "site/",
)

# Documentation that exists for process reasons and makes no technical claim
# about any symbol. A change here is never a drift fix, and these files change
# constantly -- leaving them in would swamp the real signal.
NON_TECHNICAL_DOC_STEMS = frozenset(
    {
        "changelog", "changes", "history", "news", "releases", "release-notes",
        "license", "licence", "copying", "notice", "patents",
        "authors", "contributors", "maintainers", "codeowners", "owners",
        "code_of_conduct", "code-of-conduct", "security", "support", "funding",
        "governance", "roadmap",
    }
)

# Test code makes claims about behaviour, but a test is not documentation and a
# test change accompanying a doc change is the normal shape of a *feature*
# commit, not a fix. Excluding tests from the "code" side sharpens shape A.
TEST_PATH_MARKERS = ("test/", "tests/", "spec/", "__tests__/", "testdata/", "fixtures/")
TEST_NAME_MARKERS = ("test_", "_test.", ".test.", ".spec.", "conftest.")


def is_probably_generated(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in GENERATED_DIR_MARKERS)


def _is_test(path: str) -> bool:
    lowered = path.lower()
    if any(marker in lowered for marker in TEST_PATH_MARKERS):
        return True
    name = PurePosixPath(lowered).name
    return any(marker in name for marker in TEST_NAME_MARKERS)


def classify(path: str) -> Kind:
    """Return the role this path plays, for drift-mining purposes.

    Anything generated, vendored, non-technical or test-shaped is OTHER: not
    "unknown", but "deliberately excluded from evidence".
    """
    if is_probably_generated(path):
        return Kind.OTHER

    pure = PurePosixPath(path)
    suffix = pure.suffix.lower()

    if suffix in DOC_SUFFIXES:
        stem = pure.stem.lower()
        if stem in NON_TECHNICAL_DOC_STEMS:
            return Kind.OTHER
        # A README at the repo root is genuinely technical documentation and is
        # one of the most drift-prone files in any project. Keep it.
        return Kind.DOC

    if suffix in CODE_SUFFIXES:
        if _is_test(path):
            return Kind.OTHER
        return Kind.CODE

    return Kind.OTHER
