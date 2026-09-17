"""Tripwire: the ruleset's required checks must be names CI actually produces.

`protect-main` requires eight status checks by exact name and has no bypass
actors. GitHub treats a required context that never reports as permanently
*pending* rather than failing, so a required name that no job produces blocks
every pull request forever, and not even an admin can merge past it — the only
recovery is editing the ruleset.

`.github/required-status-checks.txt` is the reviewable mirror of that list.
These tests prove it still matches what the workflows generate, which is the
half of the contract that can be checked without a network. The other half —
that the list still matches the live ruleset — is `scripts/ruleset-drift.sh`.

Check names here are composed rather than simple job ids: a job called through
`workflow_call` reports as "<caller job name> / <callee job name>", and the
callee name carries matrix values, so `Checks / Test (3.14, windows-latest)`
comes from three separate places. Dropping a Python version from the matrix
renames six contexts at once, which is why the matrix is expanded here rather
than pattern-matched away.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

CHECKS_LIST = Path(".github") / "required-status-checks.txt"
CI_WORKFLOW = Path(".github") / "workflows" / "ci.yml"

MATRIX_REF = re.compile(r"\$\{\{\s*matrix\.([A-Za-z0-9_-]+)\s*\}\}")


def _load_yaml(path: Path) -> dict[str, Any]:
    """Parse a workflow file.

    `encoding` is explicit because the workflow comments contain em dashes and
    the Windows matrix leg would otherwise decode them with the system locale.
    """
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_list(path: Path) -> list[str]:
    """Read the recorded check names, ignoring comments and blank lines."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")
    ]


def _expand_matrix(matrix: Any) -> list[dict[str, str]]:
    """Expand a `strategy.matrix` into the combinations GitHub would run.

    Implements the documented algorithm: the cartesian product of the base
    keys, minus anything `exclude` matches, then each `include` entry merged
    into every combination it does not overwrite an original key in — or
    appended as a new combination when it fits none.

    Anything not modelled raises rather than guesses. A tripwire that silently
    mis-expands a matrix reports a clean bill of health on a wedged repository,
    which is worse than having no tripwire at all.
    """
    if not isinstance(matrix, dict):
        raise TypeError(
            f"unsupported matrix {matrix!r}: only a literal mapping is modelled, "
            "not a fromJSON() expression"
        )

    include: list[dict[str, str]] = matrix.get("include") or []
    exclude: list[dict[str, str]] = matrix.get("exclude") or []
    base_keys = [k for k in matrix if k not in ("include", "exclude")]

    for key in base_keys:
        if not isinstance(matrix[key], list):
            raise TypeError(f"matrix key {key!r} is not a list: {matrix[key]!r}")

    combos: list[dict[str, str]] = [
        dict(zip(base_keys, values, strict=True))
        for values in itertools.product(*(matrix[k] for k in base_keys))
    ]
    combos = [
        c
        for c in combos
        if not any(all(c.get(k) == v for k, v in e.items()) for e in exclude)
    ]

    for entry in include:
        # An entry may only extend a combination; overwriting a value that came
        # from a base key means it describes a different run entirely.
        attached = False
        for combo in combos:
            if any(k in base_keys and combo.get(k) != v for k, v in entry.items()):
                continue
            combo.update(entry)
            attached = True
        if not attached:
            combos.append(dict(entry))

    return combos


def _substitute(template: str, combo: dict[str, str]) -> str:
    """Fill `${{ matrix.key }}` placeholders in a job name from one combination."""
    return MATRIX_REF.sub(lambda m: combo[m.group(1)], template)


def _display_names(workflow: dict[str, Any]) -> set[str]:
    """Return the check name each job in a workflow reports under."""
    names: set[str] = set()
    for job_id, job in workflow["jobs"].items():
        template = job.get("name", job_id)
        matrix = job.get("strategy", {}).get("matrix")
        if matrix is None:
            names.add(template)
            continue
        for combo in _expand_matrix(matrix):
            names.add(_substitute(template, combo))
    return names


def _expected_check_names(ci: dict[str, Any], called: dict[str, Any]) -> set[str]:
    """Compose the contexts a reusable-workflow caller reports.

    GitHub prefixes every job of a called workflow with the calling job's own
    display name and a " / " separator.
    """
    names: set[str] = set()
    for job_id, job in ci["jobs"].items():
        if "uses" not in job:
            names.add(job.get("name", job_id))
            continue
        prefix = job.get("name", job_id)
        names |= {f"{prefix} / {name}" for name in _display_names(called)}
    return names


def _called_workflow(ci: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Load the single local workflow that ci.yml calls."""
    targets = {job["uses"] for job in ci["jobs"].values() if "uses" in job}
    assert len(targets) == 1, f"expected exactly one called workflow, got {targets}"
    # removeprefix, not lstrip: lstrip takes a character SET, so "./" would
    # also eat the leading dot of ".github".
    return _load_yaml(repo_root / targets.pop().removeprefix("./"))


def test_recorded_checks_match_the_workflows(repo_root: Path):
    """The recorded list is exactly what CI produces — the gate itself.

    A mismatch means either a workflow job was renamed without updating the
    list, or the list names a context nothing will ever report.
    """
    ci = _load_yaml(repo_root / CI_WORKFLOW)
    expected = _expected_check_names(ci, _called_workflow(ci, repo_root))
    recorded = set(_read_list(repo_root / CHECKS_LIST))

    # Spelled out rather than left to pytest's set diff, which truncates to
    # "{'Checks / Bu...latest)', ...}" and tells the reader nothing. This
    # message is the whole value of the gate at the moment it fires.
    stale = recorded - expected
    missing = expected - recorded
    assert not (stale or missing), (
        f"{CHECKS_LIST} no longer matches the workflows.\n"
        f"  recorded but never reported (would block every PR): {sorted(stale)}\n"
        f"  reported but not recorded: {sorted(missing)}\n"
        "Update the list, and see CONTRIBUTING for the order to change the "
        "ruleset in."
    )


def test_recorded_checks_are_sorted_and_unique(repo_root: Path):
    """The list is stored the way the ruleset API returns it: sorted, no dupes."""
    recorded = _read_list(repo_root / CHECKS_LIST)
    assert recorded == sorted(recorded)
    assert len(recorded) == len(set(recorded))


def test_renaming_a_job_is_detected(repo_root: Path):
    """A renamed job must change the computed set.

    This is the failure that wedged the Go sibling: a job renamed in the
    workflow while the ruleset still required the old context, leaving every
    pull request waiting on a check that would never report.
    """
    ci = _load_yaml(repo_root / CI_WORKFLOW)
    called = _called_workflow(ci, repo_root)
    called["jobs"]["build"]["name"] = "Build & check package (renamed)"
    assert _expected_check_names(ci, called) != set(_read_list(repo_root / CHECKS_LIST))


def test_dropping_a_python_version_is_detected(repo_root: Path):
    """Removing a matrix leg must change the computed set.

    The likely future incident here: 3.11 reaches end of life, someone drops it
    from the matrix, and the ruleset still requires
    `Checks / Test (3.11, ubuntu-latest)`.
    """
    ci = _load_yaml(repo_root / CI_WORKFLOW)
    called = _called_workflow(ci, repo_root)
    versions = called["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    versions.remove("3.11")
    computed = _expected_check_names(ci, called)
    assert "Checks / Test (3.11, ubuntu-latest)" not in computed
    assert computed != set(_read_list(repo_root / CHECKS_LIST))


def test_matrix_include_appends_when_it_conflicts():
    """An include entry that overwrites a base value becomes its own run.

    Both of this repo's include entries conflict on `os` and `python-version`,
    so they append rather than extend — which is what produces the macOS and
    Windows legs.
    """
    combos = _expand_matrix(
        {
            "os": ["ubuntu-latest"],
            "python-version": ["3.11", "3.14"],
            "include": [{"os": "windows-latest", "python-version": "3.14"}],
        }
    )
    assert combos == [
        {"os": "ubuntu-latest", "python-version": "3.11"},
        {"os": "ubuntu-latest", "python-version": "3.14"},
        {"os": "windows-latest", "python-version": "3.14"},
    ]


def test_matrix_include_extends_when_it_does_not_conflict():
    """An include entry adding a new key extends every existing combination."""
    combos = _expand_matrix(
        {"os": ["ubuntu-latest", "macos-latest"], "include": [{"extra": "value"}]}
    )
    assert combos == [
        {"os": "ubuntu-latest", "extra": "value"},
        {"os": "macos-latest", "extra": "value"},
    ]


def test_matrix_exclude_removes_a_combination():
    """`exclude` drops a combination before include entries are applied."""
    combos = _expand_matrix(
        {
            "os": ["ubuntu-latest", "windows-latest"],
            "python-version": ["3.11"],
            "exclude": [{"os": "windows-latest", "python-version": "3.11"}],
        }
    )
    assert combos == [{"os": "ubuntu-latest", "python-version": "3.11"}]


def test_unmodelled_matrix_raises_rather_than_guessing():
    """A dynamic matrix must fail loudly, not expand to nothing."""
    with pytest.raises(TypeError, match="fromJSON"):
        _expand_matrix("${{ fromJSON(needs.setup.outputs.matrix) }}")
