#!/usr/bin/env python3
"""Version comparison and npm-style range evaluation for the upgrade report generator.

`range_satisfies` desugars every comparator into inclusive lower / exclusive upper
bounds so partial ranges (`^18`, `~20.1`, `>=18`, `16.x - 18.x`) behave the way npm
resolves them. It returns `None` only when a range cannot be parsed at all, because
callers treat `None` as "unknown" and escalate it to a blocking gate.
"""

from __future__ import annotations

import re
from typing import Iterable


VERSION_RE = re.compile(r"(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)")
PROTOCOL_PREFIXES = ("workspace:", "file:", "link:", "github:", "git+", "http:", "https:", "catalog:")
_WILDCARDS = {"x", "X", "*", ""}
_HYPHEN_RE = re.compile(r"^\s*(?P<low>[0-9xX*][0-9a-zA-Z.\-+*xX]*)\s+-\s+(?P<high>[0-9xX*][0-9a-zA-Z.\-+*xX]*)\s*$")
_PARTIAL_RE = re.compile(
    r"^v?(?P<major>\d+|[xX*])"
    r"(?:\.(?P<minor>\d+|[xX*]))?"
    r"(?:\.(?P<patch>\d+|[xX*]))?"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)
_OPERATOR_RE = re.compile(r"^(?P<operator>>=|<=|>|<|=|\^|~>|~)\s*(?P<rest>.+)$")
_UPPER_SENTINEL = (10 ** 9, 0, 0, 1, "")

Key = tuple[int, int, int, int, str]


def clean_version(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith(PROTOCOL_PREFIXES):
        return value
    if value.startswith("npm:"):
        match = VERSION_RE.search(value)
        return match.group("version") if match else value
    value = value.split("||", 1)[0].strip()
    match = VERSION_RE.search(value.lstrip("v^~<>= "))
    return match.group("version") if match else value


def semver_key(value: str) -> Key | None:
    version = clean_version(value)
    match = VERSION_RE.fullmatch(version)
    if not match:
        return None
    base = version.split("+", 1)[0]
    main, _, prerelease = base.partition("-")
    major, minor, patch = (int(part) for part in main.split("."))
    return major, minor, patch, 1 if not prerelease else 0, prerelease


def compare_versions(left: str, right: str) -> int | None:
    left_key = semver_key(left)
    right_key = semver_key(right)
    if left_key is None or right_key is None:
        return None
    return (left_key > right_key) - (left_key < right_key)


def classify_change(from_version: str, to_version: str) -> str:
    if not from_version and to_version:
        return "added"
    if from_version and not to_version:
        return "removed"
    before = semver_key(from_version)
    after = semver_key(to_version)
    if before is None or after is None:
        return "unknown"
    if before[0] != after[0]:
        return "major"
    if before[1] != after[1]:
        return "minor"
    if before != after:
        return "patch"
    return "same"


def _key(major: int, minor: int, patch: int, prerelease: str = "") -> Key:
    return major, minor, patch, 1 if not prerelease else 0, prerelease


def _partial(token: str) -> tuple[int | None, int | None, int | None, str] | None:
    match = _PARTIAL_RE.match(token.strip())
    if not match:
        return None
    raw = (match.group("major"), match.group("minor"), match.group("patch"))
    parts: list[int | None] = []
    for value in raw:
        parts.append(None if value is None or value in _WILDCARDS else int(value))
    # `1.x.2` is not a valid npm range; a wildcard makes everything to its right a wildcard.
    if parts[0] is None:
        parts = [None, None, None]
    elif parts[1] is None:
        parts[2] = None
    return parts[0], parts[1], parts[2], match.group("prerelease") or ""


def _bounds_for_partial(token: str) -> tuple[Key, Key] | None:
    """Inclusive lower bound and exclusive upper bound for an X-range token."""
    parsed = _partial(token)
    if parsed is None:
        return None
    major, minor, patch, prerelease = parsed
    if major is None:
        return _key(0, 0, 0, "0"), _UPPER_SENTINEL
    if minor is None:
        return _key(major, 0, 0), _key(major + 1, 0, 0)
    if patch is None:
        return _key(major, minor, 0), _key(major, minor + 1, 0)
    lower = _key(major, minor, patch, prerelease)
    return lower, _key(major, minor, patch + 1)


def _caret_bounds(token: str) -> tuple[Key, Key] | None:
    parsed = _partial(token)
    if parsed is None:
        return None
    major, minor, patch, prerelease = parsed
    if major is None:
        return _key(0, 0, 0, "0"), _UPPER_SENTINEL
    lower = _key(major, minor or 0, patch or 0, prerelease)
    if major > 0 or minor is None:
        return lower, _key(major + 1, 0, 0)
    if minor > 0 or patch is None:
        return lower, _key(0, minor + 1, 0)
    return lower, _key(0, minor, (patch or 0) + 1)


def _tilde_bounds(token: str) -> tuple[Key, Key] | None:
    parsed = _partial(token)
    if parsed is None:
        return None
    major, minor, patch, prerelease = parsed
    if major is None:
        return _key(0, 0, 0, "0"), _UPPER_SENTINEL
    lower = _key(major, minor or 0, patch or 0, prerelease)
    if minor is None:
        return lower, _key(major + 1, 0, 0)
    return lower, _key(major, minor + 1, 0)


def _comparators(token: str) -> list[tuple[str, Key]] | None:
    """Desugar one range token into `(operator, key)` comparators, or `None` when unparseable."""
    token = token.strip()
    if not token or token in _WILDCARDS:
        return [(">=", _key(0, 0, 0, "0"))]
    operator_match = _OPERATOR_RE.match(token)
    if not operator_match:
        bounds = _bounds_for_partial(token)
        if bounds is None:
            return None
        lower, upper = bounds
        return [(">=", lower), ("<", upper)]
    operator = operator_match.group("operator")
    rest = operator_match.group("rest").strip()
    if operator in {"^", "~", "~>"}:
        bounds = _caret_bounds(rest) if operator == "^" else _tilde_bounds(rest)
        if bounds is None:
            return None
        lower, upper = bounds
        return [(">=", lower), ("<", upper)]
    parsed = _partial(rest)
    if parsed is None:
        return None
    major, minor, patch, prerelease = parsed
    if major is None:
        return [(">=", _key(0, 0, 0, "0"))]
    complete = minor is not None and patch is not None
    lower = _key(major, minor or 0, patch or 0, prerelease)
    if operator == "=":
        bounds = _bounds_for_partial(rest)
        if bounds is None:
            return None
        return [(">=", bounds[0]), ("<", bounds[1])]
    if operator == ">=":
        return [(">=", lower)]
    if operator == "<":
        return [("<", lower)]
    if operator == ">":
        if complete:
            return [(">", lower)]
        # `>18` and `>18.2` exclude the whole partial range.
        upper = _key(major + 1, 0, 0) if minor is None else _key(major, minor + 1, 0)
        return [(">=", upper)]
    # `<=`
    if complete:
        return [("<=", lower)]
    upper = _key(major + 1, 0, 0) if minor is None else _key(major, minor + 1, 0)
    return [("<", upper)]


def _hyphen_comparators(alternative: str) -> list[tuple[str, Key]] | None:
    match = _HYPHEN_RE.match(alternative)
    if not match:
        return None
    low_bounds = _bounds_for_partial(match.group("low"))
    high_bounds = _bounds_for_partial(match.group("high"))
    if low_bounds is None or high_bounds is None:
        return None
    high_parsed = _partial(match.group("high"))
    comparators: list[tuple[str, Key]] = [(">=", low_bounds[0])]
    if high_parsed and high_parsed[1] is not None and high_parsed[2] is not None:
        comparators.append(("<=", high_bounds[0]))
    else:
        comparators.append(("<", high_bounds[1]))
    return comparators


def _holds(key: Key, operator: str, wanted: Key) -> bool:
    if operator == ">=":
        return key >= wanted
    if operator == ">":
        return key > wanted
    if operator == "<=":
        return key <= wanted
    if operator == "<":
        return key < wanted
    return key == wanted


def _alternative_satisfied(key: Key, comparators: list[tuple[str, Key]]) -> bool:
    if not all(_holds(key, operator, wanted) for operator, wanted in comparators):
        return False
    if key[3] == 1:
        return True
    # npm only lets a prerelease satisfy a range when a comparator pins the same tuple.
    return any(
        wanted[3] == 0 and wanted[:3] == key[:3]
        for _, wanted in comparators
        if wanted != _UPPER_SENTINEL
    )


def range_satisfies(version: str, requirement: str) -> bool | None:
    """`True`/`False` when the range is understood, `None` when it cannot be parsed."""
    key = semver_key(version)
    if key is None:
        return None
    requirement = str(requirement or "").strip()
    if not requirement or requirement in _WILDCARDS:
        return True
    understood_any = False
    unknown_any = False
    for alternative in requirement.split("||"):
        alternative = alternative.strip()
        comparators = _hyphen_comparators(alternative)
        if comparators is None:
            tokens = [token for token in re.split(r"[\s,]+", alternative) if token]
            comparators = []
            for token in tokens:
                desugared = _comparators(token)
                if desugared is None:
                    comparators = None
                    break
                comparators.extend(desugared)
        if comparators is None:
            unknown_any = True
            continue
        understood_any = True
        if _alternative_satisfied(key, comparators):
            return True
    if unknown_any or not understood_any:
        return None
    return False


def range_witnesses(requirements: Iterable[str]) -> list[str]:
    """Candidate versions able to witness a non-empty intersection of several ranges."""
    candidates: set[str] = {"0.0.0"}
    for requirement in requirements:
        for alternative in str(requirement or "").split("||"):
            for token in re.split(r"[\s,]+", alternative.strip()):
                if not token:
                    continue
                stripped = token.lstrip("><=^~v")
                bounds = _bounds_for_partial(stripped)
                if bounds is None:
                    continue
                for key in bounds:
                    if key == _UPPER_SENTINEL:
                        continue
                    candidates.add(f"{key[0]}.{key[1]}.{key[2]}")
                    candidates.add(f"{key[0]}.{key[1]}.{key[2] + 1}")
                    candidates.add(f"{key[0]}.{key[1] + 1}.0")
                    candidates.add(f"{key[0] + 1}.0.0")
    return sorted(candidates, key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))


def preferred_version(versions: Iterable[str]) -> str:
    """Highest stable even-major (LTS-shaped) candidate, falling back to the highest exact version."""
    exact = [value for value in versions if semver_key(value) is not None]
    if not exact:
        return ""
    lts_candidates = [
        value for value in exact
        if (semver_key(value) or (1, 0, 0, 0, ""))[0] % 2 == 0
        and not (semver_key(value) or (0, 0, 0, 0, ""))[4]
    ]
    pool = lts_candidates or exact
    return max(pool, key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))
